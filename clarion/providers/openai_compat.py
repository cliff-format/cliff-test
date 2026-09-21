"""OpenAI-compatible chat completions provider.

One adapter covers DeepSeek, Kimi, Qwen, vLLM, Ollama and every other endpoint
that speaks /v1/chat/completions. Reasoning controls differ between vendors, so
the adapter maps a single 'reasoning' setting onto the parameters each vendor
documents and lets extra_body override anything.
"""

from __future__ import annotations

import os
import random
import time
from typing import Any

from .base import Completion, CompletionRequest

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_TIMEOUT = 180.0


def reasoning_body(reasoning: str, model: str) -> dict[str, Any]:
    """Vendor-specific switch for thinking or reasoning effort.

    'off' asks for no reasoning tokens at all, 'low' asks for the cheapest
    reasoning tier. Endpoints that do not understand these fields ignore them,
    which is why the mapping is data rather than control flow.
    """
    normalized = reasoning.lower()
    if normalized in {"", "default", "auto"}:
        return {}
    lowered = model.lower()
    if "deepseek" in lowered:
        if normalized == "off":
            return {"thinking": {"type": "disabled"}}
        return {"thinking": {"type": "enabled", "effort": normalized}}
    if normalized == "off":
        return {"reasoning_effort": "none"}
    return {"reasoning_effort": normalized}


class OpenAICompatibleProvider:
    """Chat-completions client with retries and usage accounting."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str | None = None,
        api_key_env: str = "CLARION_API_KEY",
        timeout_s: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        reasoning: str = "off",
        name: str = "openai-compatible",
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.reasoning = reasoning
        self.extra_body = dict(extra_body or {})

    def _headers(self) -> dict[str, str]:
        from ..secrets import load_key

        api_key = os.environ.get(self.api_key_env, "") or load_key(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"environment variable {self.api_key_env} is not set; "
                "CLARION never stores API keys in configuration files"
            )
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def _payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [message.as_dict() for message in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        if request.stop:
            payload["stop"] = request.stop
        payload.update(reasoning_body(self.reasoning, self.model))
        payload.update(self.extra_body)
        payload.update(request.extra_body)
        return payload

    def complete(self, request: CompletionRequest) -> Completion:
        """Send one request, retrying transient failures with backoff."""
        try:
            import httpx
        except ModuleNotFoundError as exc:  # pragma: no cover - env specific
            raise RuntimeError("httpx is required for HTTP providers (pip install httpx)") from exc

        url = f"{self.base_url}/v1/chat/completions"
        payload = self._payload(request)
        headers = self._headers()
        last_error = "unknown error"
        started = time.perf_counter()
        for attempt in range(1, self.max_retries + 1):
            call_started = time.perf_counter()
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.post(url, json=payload, headers=headers)
                if response.status_code >= 500 or response.status_code == 429:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    raise TransientProviderError(last_error)
                if 400 <= response.status_code < 500:
                    # A client error that is not a rate limit will not fix itself,
                    # and the retry loop below would pay for the same rejection
                    # again: a 401 leaves with one attempt, not three.
                    return Completion(
                        text="",
                        provider=self.name,
                        model=self.model,
                        latency_ms=(time.perf_counter() - started) * 1000.0,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                        attempts=attempt,
                    )
                response.raise_for_status()
                data = response.json()
            except TransientProviderError:
                if attempt == self.max_retries:
                    break
                time.sleep(min(30.0, 2.0**attempt) * (0.5 + random.random()))  # noqa: S311
                continue
            except Exception as exc:  # noqa: BLE001 - network errors are data
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt == self.max_retries:
                    break
                time.sleep(min(30.0, 2.0**attempt) * (0.5 + random.random()))  # noqa: S311
                continue

            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            usage = data.get("usage") or {}
            details = usage.get("completion_tokens_details") or {}
            return Completion(
                text=str(message.get("content") or ""),
                provider=self.name,
                model=str(data.get("model") or self.model),
                latency_ms=(time.perf_counter() - call_started) * 1000.0,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                reasoning_tokens=details.get("reasoning_tokens"),
                finish_reason=choice.get("finish_reason"),
                attempts=attempt,
                raw={"id": data.get("id"), "usage": usage},
            )

        return Completion(
            text="",
            provider=self.name,
            model=self.model,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            error=last_error,
            attempts=self.max_retries,
        )


class TransientProviderError(RuntimeError):
    """Retryable endpoint failure (rate limit or server error)."""
