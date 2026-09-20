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
    """D1/D2 claim to cost the prompt a translation run sends, so the two
    builders must agree **argument for argument**.

    Until this test existed, ``token_matrix`` omitted ``allow_glossary_output``
    and ``workflow_style``. That is not a detail: with ``spec_reference`` on, the
    reference specification is appended only to the CLIFF prompt, and the
    terminology workflow block only to CLIFF's. Omitting them made the CLIFF row
    of the token tables about half of what the run actually pays, while every
    other format's row was correct.
    """
    from clarion.corpus.store import load_corpus
    from clarion.formats.render import render_document
    from clarion.metrics.terminology import load_policy
    from clarion.runner import _blank, token_matrix

    config = RunConfig(
        name="token-parity",
        formats=["cliff"],
        arms=["bare", "context"],
        spec_location="split",
        spec_reference=True,
        include_policy=True,
        allow_glossary_output=True,
        workflow_style="deliverable",
    )
    corpus = load_corpus("fixture", root=corpus_root)
    tokenizer = get_tokenizer(config.tokenizer)
    policy = load_policy(config.target_language)

    rows = token_matrix(config, corpus, tokenizer=tokenizer, policy=policy)
    assert rows, "the token matrix produced no rows"

    corpus_file = corpus.files[0]
    for row in rows:
        arm = Arm(row["arm"])
        # The same projection the matrix applies: the task document has every
        # target blanked, which is what changes the prompt's token count.
        task_document = _blank(corpus_file, arm)
        document_text = render_document(task_document, row["format"], arm=arm)
        bundle = build_translation_prompt(
            document_text=document_text,
            format_id=row["format"],
            tokenizer=tokenizer,
            source_language=corpus_file.source_language,
            target_language=corpus_file.target_language,
            arm=arm.value,
            spec_location=config.spec_location,
            spec_reference=config.spec_reference,
            glossary_text="",
            policy_fragment=policy.prompt_fragment(),
            document=task_document,
            allow_glossary_output=config.allow_glossary_output,
            workflow_style=config.workflow_style,
        )
        assert row["prompt_tokens"] == bundle.budget.total, (
            f"{row['format']}/{row['arm']}: the token matrix and the translation "
            f"prompt disagree ({row['prompt_tokens']} vs {bundle.budget.total})"
        )
        # The reference specification is what makes the CLIFF row look expensive,
        # and it is exactly what the old argument list lost.
        assert bundle.budget.tokens_of("spec.reference") > 0


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
