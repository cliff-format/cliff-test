"""Prompt assembly, specification digest and the glossary bootstrap tool."""

from __future__ import annotations

from clarion.config import RunConfig
from clarion.formats import Arm, render
from clarion.metrics.tokens import get_tokenizer
from clarion.prompts import build_grammar_plus, build_translation_prompt, emotion_tags, type_tags
from clarion.tools.glossary import (
    attach_dependency,
    build_glossary_document,
    extract_candidates,
    merge_glossary,
)


def test_spec_digest_lists_the_closed_vocabularies() -> None:
    assert len(type_tags()) == 26
    assert len(emotion_tags()) == 23
    sheet = build_grammar_plus()
    # The digest injects the *current* specification; the 1.0 files stay as the
    # frozen definition but are not what a prompt should teach.
    assert "CLIFF 1.1" in sheet
    assert "accessibility-cue" in sheet
    assert "nostalgic" in sheet
    assert "initial, translated, reviewed, final" in sheet
    # 1.1's relaxed identifier rule reaches the model, not the 1.0 one.
    assert "lowercase kebab-case and" not in sheet
    assert "case-sensitive" in sheet


def test_prompt_components_are_measured_separately(sample_document) -> None:
    tokenizer = get_tokenizer("o200k_base")
    document_text = render(sample_document, "cliff", arm=Arm.CONTEXT, blank=True)
    bundle = build_translation_prompt(
        document_text=document_text,
        format_id="cliff",
        tokenizer=tokenizer,
        source_language="en-US",
        target_language="zh-CN",
        arm="context",
    )
    ids = {component.id for component in bundle.budget.components}
    assert {"system.role", "task.rules", "format.notes", "spec.digest", "document"} <= ids
    assert bundle.budget.tokens_of("spec.digest") > 100
    assert bundle.tokens_without_format_instructions() < bundle.total_tokens
    assert document_text in bundle.user


def test_non_cliff_formats_get_no_specification_block(sample_document) -> None:
    tokenizer = get_tokenizer("o200k_base")
    document_text = render(sample_document, "po", arm=Arm.BARE, blank=True)
    bundle = build_translation_prompt(
        document_text=document_text,
        format_id="po",
        tokenizer=tokenizer,
        source_language="en-US",
        target_language="zh-CN",
        arm="bare",
    )
    assert bundle.budget.tokens_of("spec.digest") == 0
    assert bundle.budget.tokens_of("format.notes") > 0


def test_d1_d2_price_the_prompt_the_translation_arms_actually_send(
    corpus_root, sample_document
) -> None:
    """D1/D2 claim to cost the prompt a translation run sends - so compare with a run.

    Twice now an argument was in the run's prompt and not in the matrix's:
    ``allow_glossary_output``/``workflow_style`` (the terminology block, worth about
    half the CLIFF row), and later ``prompt_style``. The second one is the reason
    this test no longer rebuilds the prompt itself: a hand-written argument list
    reproduces whatever the code omits, so both sides agreed while the run directory
    named a style neither path used. A recording provider makes the run the source
    of truth, and the assertion on the system message makes the configuration the
    other one.
    """
    from clarion.corpus.store import load_corpus
    from clarion.experiments.translate import run_translation_task
    from clarion.metrics.terminology import load_policy
    from clarion.prompts import cliff_prompt_v2 as v2
    from clarion.runner import token_matrix

    config = RunConfig(
        name="token-parity",
        formats=["cliff"],
        arms=["bare", "context"],
        spec_location="split",
        spec_reference=True,
        include_policy=True,
        allow_glossary_output=True,
        workflow_style="deliverable",
        prompt_style="examples",
    )
    corpus = load_corpus("fixture", root=corpus_root)
    tokenizer = get_tokenizer(config.tokenizer)
    policy = load_policy(config.target_language)

    rows = token_matrix(config, corpus, tokenizer=tokenizer, policy=policy)
    assert rows, "the token matrix produced no rows"

    # Compared against the run, not against a second hand-written argument list.
    # The earlier version of this test rebuilt the bundle itself and therefore
    # reproduced whatever the matrix omitted: both sides left out `prompt_style`, so
    # the numbers agreed while the run directory named a style neither path used. A
    # recording provider makes the run the source of truth.
    import clarion.runner as runner_module
    from clarion.providers.base import Completion, CompletionRequest
    from clarion.providers.mock import MockProvider

    class Recording:
        name = "recording"
        model = "mock-1"

        def __init__(self) -> None:
            self.inner = MockProvider(mode="perfect", model="mock-1")
            self.requests: list[CompletionRequest] = []

        def complete(self, request: CompletionRequest) -> Completion:
            self.requests.append(request)
            return self.inner.complete(request)

    provider = Recording()
    original = runner_module.build_provider
    runner_module.build_provider = lambda _config: provider  # type: ignore[assignment]
    try:
        corpus_file = corpus.files[0]
        result = run_translation_task(
            corpus_file,
            format_id="cliff",
            arm=Arm.CONTEXT,
            provider=provider,
            tokenizer=tokenizer,
            config=config,
            policy=policy,
        )
    finally:
        runner_module.build_provider = original  # type: ignore[assignment]

    matrix_row = next(
        row for row in rows if row["format"] == "cliff" and row["arm"] == "context"
    )
    assert matrix_row["prompt_tokens"] == result.prompt_tokens, (
        "the token matrix and the translation run price different prompts "
        f"({matrix_row['prompt_tokens']} vs {result.prompt_tokens})"
    )
    # And the run reflects the configuration rather than a default: the style the
    # config names must be the style in the system message it actually sends.
    system = provider.requests[-1].messages[0].content
    assert "FIELD NAMES AND THEIR SCOPE" in system, (
        "prompt_style='examples' must reach the system message; the configuration "
        "naming a style is not the same as the run using it"
    )
    assert v2.CLIFF_FACTS in system
    assert "spec.reference" not in system

    # The run keeps the prompt it sent as evidence, and that evidence has to be the
    # whole prompt: for CLIFF the system message is where the field table lives, so a
    # file that holds only the user message cannot show what the prompt said.
    assert result.prompt_text.startswith(system), (
        "the stored prompt must begin with the system message"
    )
    assert "FILE TO TRANSLATE" in result.prompt_text, (
        "the stored prompt must also carry the user message with the document"
    )


def test_glossary_candidates_and_merge(sample_document, sample_glossary) -> None:
    candidates = extract_candidates(sample_document, min_count=1)
    assert candidates
    mined = build_glossary_document(sample_document, candidates)
    assert mined.header.variant == "glossary"
    merged, report = merge_glossary(sample_glossary, mined)
    assert report.added or report.kept
    ids = {entry.id for group in merged.groups for entry in group.entries}
    assert "default" in ids


def test_merge_never_overwrites_locked_terms(sample_glossary) -> None:
    import copy

    mined = copy.deepcopy(sample_glossary)
    for group in mined.groups:
        for entry in group.entries:
            if entry.source == "Default":
                entry.target = "缺省"
    merged, report = merge_glossary(sample_glossary, mined)
    kept = {
        entry.source: entry.target for group in merged.groups for entry in group.entries
    }
    assert kept["Default"] == "默认"
    assert report.conflicts


def test_attach_dependency_is_idempotent(sample_document) -> None:
    once = attach_dependency(sample_document, "glossary.zh-CN.cliff")
    twice = attach_dependency(once, "glossary.zh-CN.cliff")
    assert twice.header.dependency.count("glossary.zh-CN.cliff") == 1
