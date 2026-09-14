"""Prompt assembly, specification digest and the glossary bootstrap tool."""

from __future__ import annotations

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
    assert "CLIFF 1.0" in sheet
    assert "accessibility-cue" in sheet
    assert "nostalgic" in sheet
    assert "initial, translated, reviewed, final" in sheet


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
