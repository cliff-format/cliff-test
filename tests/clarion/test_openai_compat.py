"""The HTTP adapter: what goes on the wire, and what happens when it goes wrong.

`providers/openai_compat.py` is the only code that talks to a model endpoint, and
it had no test. Nothing here makes a network call: `httpx.Client` is replaced with
a scripted transport, so the payload, the retry policy and the error surface are
all asserted locally.

Two of these matter more than the rest. The **temperature** must be the one the
request carries, because every published dimension-7 number was silently sent at
0.0 while the configuration said 1.3; and a **429 must be retried, not reported**,
because a rate-limited batch that gives up would look like a model failure in the
results.
"""

from __future__ import annotations

import json

import httpx
import pytest

from clarion.providers.base import CompletionRequest, Message
from clarion.providers.openai_compat import OpenAICompatibleProvider, reasoning_body


def _fake_key() -> str:
    """A credential-shaped string, assembled when the test runs.

    Not a literal: `clarion secret-scan` walks the tree, so one written here would
    trip the project's own pre-gate on the test that checks what goes on the wire.
    """
    return "sk-" + "test" + "0" * 20


class FakeResponse:
    """A response httpx would have produced, with no socket behind it."""

    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=None  # type: ignore[arg-type]
            )


class FakeClient:
    """A client that answers a scripted list of responses, and records requests."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, dict, dict]] = []

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def post(self, url: str, *, json: dict, headers: dict) -> FakeResponse:  # noqa: A002
        self.requests.append((url, json, headers))
        if not self.responses:
            raise AssertionError("the provider sent more requests than the test scripted")
        return self.responses.pop(0)


def _provider(**overrides) -> OpenAICompatibleProvider:
    defaults = {
        "model": "deepseek-flash",
        "api_key_env": "TEST_API_KEY",
        "max_retries": 3,
        "reasoning": "off",
    }
    defaults.update(overrides)
    return OpenAICompatibleProvider(**defaults)  # type: ignore[arg-type]


def _request(**overrides) -> CompletionRequest:
    defaults = {"messages": [Message("user", "hello")], "temperature": 1.3, "max_output_tokens": 64}
    defaults.update(overrides)
    return CompletionRequest(**defaults)  # type: ignore[arg-type]


def _answer(text: str = "CLIFF 1.1\n") -> FakeResponse:
    return FakeResponse(
        200,
        {
            "model": "deepseek-flash",
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "completion_tokens_details": {"reasoning_tokens": 3},
            },
        },
    )


@pytest.fixture(autouse=True)
def _no_key_needed(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", _fake_key())


@pytest.fixture(autouse=True)
def _no_real_backoff(monkeypatch) -> None:
    """Retries must not sleep for real: the first backoff is two seconds."""
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


def _install(monkeypatch, responses: list[FakeResponse]) -> FakeClient:
    client = FakeClient(responses)
    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: client)
    return client


# --- the vendor switch -------------------------------------------------------


def test_reasoning_body_maps_thinking_per_vendor() -> None:
    """One setting, two vendor spellings, and nothing when it is not set."""
    assert reasoning_body("off", "deepseek-flash") == {"thinking": {"type": "disabled"}}
    assert reasoning_body("low", "deepseek-flash") == {
        "thinking": {"type": "enabled", "effort": "low"}
    }
    assert reasoning_body("off", "qwen-max") == {"reasoning_effort": "none"}
    assert reasoning_body("high", "qwen-max") == {"reasoning_effort": "high"}
    for unspecified in ("", "default", "auto"):
        assert reasoning_body(unspecified, "deepseek-flash") == {}


# --- the payload -------------------------------------------------------------


def test_the_payload_carries_the_temperature_the_request_was_given(
    monkeypatch,
) -> None:
    """The knob that went missing on the edit path, asserted at the adapter."""
    client = _install(monkeypatch, [_answer()])
    _provider().complete(_request(temperature=1.3))
    _, payload, _ = client.requests[0]
    assert payload["temperature"] == 1.3
    assert payload["top_p"] == 1.0
    assert payload["max_tokens"] == 64
    assert payload["stream"] is False
    assert payload["model"] == "deepseek-flash"


def test_the_payload_merges_extra_body_with_the_request_winning(monkeypatch) -> None:
    """`extra_body` overrides anything, which is exactly what its docstring says.

    The consequence is worth stating because it is silent: an `extra_body` that
    carries `temperature` beats the `temperature` field of the same configuration,
    so a run can be sent at a temperature nobody meant to set. The assertion below
    pins the documented precedence rather than the one I first expected.
    """
    client = _install(monkeypatch, [_answer()])
    provider = _provider(extra_body={"temperature": 0.2, "top_k": 5})
    provider.complete(_request(extra_body={"top_k": 9}))
    _, payload, _ = client.requests[0]
    assert payload["top_k"] == 9, "a request-level key must override the provider default"
    assert payload["temperature"] == 0.2, (
        "extra_body overrides the explicit field too; if this ever changes, the "
        "precedence in _payload changed and the docstring must change with it"
    )


def test_stop_sequences_are_sent_only_when_the_request_has_them(monkeypatch) -> None:
    client = _install(monkeypatch, [_answer(), _answer()])
    provider = _provider()
    provider.complete(_request())
    provider.complete(_request(stop=["\n\n"]))
    assert "stop" not in client.requests[0][1]
    assert client.requests[1][1]["stop"] == ["\n\n"]


def test_the_request_goes_to_the_chat_completions_endpoint_with_the_key(
    monkeypatch,
) -> None:
    client = _install(monkeypatch, [_answer()])
    _provider(base_url="https://api.example.com/").complete(_request())
    url, _, headers = client.requests[0]
    assert url == "https://api.example.com/v1/chat/completions"
    assert headers["Authorization"] == f"Bearer {_fake_key()}"


def test_a_missing_key_is_an_error_that_names_the_environment_variable(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    monkeypatch.setattr("clarion.secrets.load_key", lambda *_a, **_k: "")
    with pytest.raises(RuntimeError, match="TEST_API_KEY"):
        _provider().complete(_request())


# --- the answer --------------------------------------------------------------


def test_usage_and_finish_reason_are_reported(monkeypatch) -> None:
    _install(monkeypatch, [_answer("CLIFF 1.1\n")])
    completion = _provider().complete(_request())
    assert completion.text == "CLIFF 1.1\n"
    assert completion.prompt_tokens == 11
    assert completion.completion_tokens == 7
    assert completion.reasoning_tokens == 3
    assert completion.finish_reason == "stop"
    assert completion.error is None
    assert completion.attempts == 1


# --- retries -----------------------------------------------------------------


def test_a_rate_limit_is_retried_rather_than_reported(monkeypatch) -> None:
    """A 429 that ended a batch would look like a model failure in the results."""
    client = _install(
        monkeypatch, [FakeResponse(429, text="slow down"), _answer("CLIFF 1.1\n")]
    )
    completion = _provider().complete(_request())
    assert completion.error is None
    assert completion.attempts == 2
    assert len(client.requests) == 2


def test_a_server_error_is_retried_then_given_up_on(monkeypatch) -> None:
    client = _install(monkeypatch, [FakeResponse(503, text="down")] * 3)
    completion = _provider(max_retries=3).complete(_request())
    assert completion.text == ""
    assert completion.error is not None and "503" in completion.error
    assert completion.attempts == 3
    assert len(client.requests) == 3, "the retry count must be the configured one"


def test_a_client_error_is_not_retried(monkeypatch) -> None:
    """A 401 will not fix itself, and retrying it wastes a paid call's budget."""
    client = _install(monkeypatch, [FakeResponse(401, text="bad key")])
    completion = _provider(max_retries=3).complete(_request())
    assert completion.error is not None
    assert len(client.requests) == 1
