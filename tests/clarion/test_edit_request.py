"""An edit run must edit at the temperature it is configured to use.

`run_robustness` built its own `CompletionRequest` with a hard-coded
`temperature=0.0`, and `build_provider` never passes a temperature to the
provider. The Web of that was silent: `ProviderConfig.temperature` reached the
wire only on the translation path, so dimension 7 ignored the configured value
entirely. Every published D7 number - including the ones labelled as the shipped
1.3 settings - was therefore measured at 0.0, and `d7_pilot.py --temperature 1.3`
was a no-op.

These tests pin the two halves of the contract: the request carries the value it
is given, and the matrix gives it the value from the configuration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clarion.config import ProviderConfig, RunConfig
from clarion.experiments.robustness import (
    EDIT_SYSTEM,
    default_tasks,
    run_robustness,
)
from clarion.formats.arms import Arm
from clarion.providers.base import Completion, CompletionRequest
from clarion.providers.mock import MockProvider


class RecordingProvider:
    """Answers like the mock, and keeps every request it was handed."""

    def __init__(self, inner: MockProvider) -> None:
        self.inner = inner
        self.name = "recording"
        self.model = inner.model
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> Completion:
        self.requests.append(request)
        return self.inner.complete(request)


def _provider() -> RecordingProvider:
    return RecordingProvider(MockProvider(mode="perfect", model="mock-1"))


def _config(temperature: float) -> RunConfig:
    return RunConfig(
        name="edit-temperature",
        formats=["cliff"],
        arms=["context"],
        isolation="per-task",
        concurrency=1,
        provider=ProviderConfig(
            kind="mock", model="mock-1", mode="perfect", temperature=temperature
        ),
    )


@pytest.mark.parametrize("temperature", [0.0, 0.7, 1.3])
def test_edit_request_carries_the_temperature_it_is_given(
    sample_document, temperature: float
) -> None:
    """The parameter reaches the wire; it was a constant before this test."""
    provider = _provider()
    run_robustness(
        sample_document,
        format_id="cliff",
        arm=Arm.CONTEXT,
        provider=provider,
        tasks=default_tasks(sample_document, count=3),
        temperature=temperature,
    )
    assert provider.requests, "no edit request was sent"
    assert {request.temperature for request in provider.requests} == {temperature}


def test_edit_matrix_forwards_the_configured_temperature(
    sample_document, corpus_root, monkeypatch
) -> None:
    """The drift guard: the matrix must hand the config's value to the path.

    This is the assertion that would have caught the hard-coded 0.0. It fails if
    `run_robustness_matrix` stops forwarding `provider.temperature`, whatever the
    reason - a new parameter, a copied call site, a refactor.

    The run directory goes inside the repository rather than through `tmp_path`:
    the file sandbox denies the system temporary directory, which is also why
    `conftest.py` writes its fixture corpus here. `.gitignore` covers it.
    """
    from clarion.corpus.store import load_corpus
    from clarion.runner import RunPaths, run_robustness_matrix

    provider = _provider()
    monkeypatch.setattr("clarion.runner.build_provider", lambda _config: provider)

    config = _config(temperature=1.3)
    corpus = load_corpus("fixture", root=corpus_root)
    base = Path(__file__).resolve().parent / "_edit_temperature_runs"
    run_robustness_matrix(
        config,
        corpus,
        edits=2,
        use_model=True,
        paths=RunPaths.create("edit-temperature", base=base),
    )

    assert provider.requests, "the matrix sent no edit request"
    sent = {request.temperature for request in provider.requests}
    assert sent == {config.provider.temperature}, (
        f"edits were sent at {sorted(sent)} while the configuration said "
        f"{config.provider.temperature}: dimension 7 is not measuring the run it claims to"
    )


def test_edit_prompt_states_the_field_facts_only_under_examples(
    sample_document,
) -> None:
    """CLIFF-specific: the field table is what stops an invented key.

    Appendix C.5 forbids a tolerant parser from repairing an unknown key, so this
    prompt content is the only defence, and it must be present exactly when the
    `examples` style asks for it.
    """
    from clarion.prompts import cliff_prompt_v2

    prompts: dict[str, str] = {}
    for style in ("examples", "digest"):
        provider = _provider()
        run_robustness(
            sample_document,
            format_id="cliff",
            arm=Arm.CONTEXT,
            provider=provider,
            tasks=default_tasks(sample_document, count=2),
            prompt_style=style,
        )
        prompts[style] = provider.requests[0].messages[0].content

    assert prompts["digest"] == EDIT_SYSTEM, "the historical style must stay CLIFF-free"
    assert cliff_prompt_v2.CLIFF_FACTS in prompts["examples"]
    assert cliff_prompt_v2.CLIFF_TASK_RULES in prompts["examples"]
    assert "reference" in prompts["examples"], "the field name that D7 must create"
