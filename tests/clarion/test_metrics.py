"""Metric behaviour: width, instruction rules, terminology, tokens."""

from __future__ import annotations

import pytest

from clarion.metrics.instruction import Rule, RuleContext, check_rules, instruction_score
from clarion.metrics.terminology import (
    check_glossary,
    check_jargon,
    glossary_from_document,
    load_policy,
)
from clarion.metrics.tokens import PromptBudget, get_tokenizer
from clarion.metrics.width import display_cells


@pytest.mark.parametrize(
    ("text", "cells"),
    [("分辨率", 6), ("OK", 2), ("OK 分辨率", 9), ("", 0), ("e\u0301", 1)],
)
def test_display_cells(text: str, cells: int) -> None:
    assert display_cells(text) == cells


def test_display_cells_matches_pycliff(sample_document) -> None:
    from cliff_format.validator import _display_cells

    for text in ["分辨率", "OK 分辨率", "Hello", "全屏模式"]:
        assert display_cells(text) == _display_cells(text)


def _run(kind: str, params: dict, source: str, target: str, width: int | None = None) -> bool:
    rule = Rule(id="r", kind=kind, params=params, entry="e")
    results = check_rules(
        [rule], {"e": source}, {"e": target}, widths={"e": width} if width else {}
    )
    return results[0].passed


def test_max_width_rule() -> None:
    assert _run("max-width", {"cells": 6}, "Accept", "接受")
    assert not _run("max-width", {"cells": 6}, "Accept", "接受并继续")


def test_cjk_latin_space_rule() -> None:
    assert _run("cjk-latin-space", {}, "Paste your API Token", "粘贴你的 API Token")
    assert not _run("cjk-latin-space", {}, "Paste your API Token", "粘贴你的API Token")


def test_icu_preserve_rule() -> None:
    source = "{count, plural, =0 {No alerts} other {# alerts}}"
    good = "{count, plural, =0 {没有提醒} other {# 条提醒}}"
    bad = "{amount, plural, =0 {没有提醒} other {# 条提醒}}"
    broken = "(count, plural, =0 {没有提醒} other {# 条提醒}}"
    assert _run("icu-preserve", {}, source, good)
    assert not _run("icu-preserve", {}, source, bad)
    assert not _run("icu-preserve", {}, source, broken)


def test_placeholder_preserve_rule() -> None:
    assert _run("placeholder-preserve", {}, "Hello %s and {0}", "你好 %s 与 {0}")
    assert not _run("placeholder-preserve", {}, "Hello %s and {0}", "你好 %s")


def test_term_and_name_policy_rules() -> None:
    assert _run(
        "term",
        {"source": "Resolution", "target": ["分辨率"], "forbidden": ["解析度"]},
        "Resolution",
        "分辨率",
    )
    assert not _run(
        "term",
        {"source": "Resolution", "target": ["分辨率"], "forbidden": ["解析度"]},
        "Resolution",
        "解析度",
    )
    assert _run(
        "name-policy",
        {"expected": ["余烬"], "rejected": ["艾什", "艾许"], "mode": "semantic"},
        "Ash draws her blade.",
        "余烬拔出了剑。",
    )
    assert not _run(
        "name-policy",
        {"expected": ["余烬"], "rejected": ["艾什", "艾许"], "mode": "semantic"},
        "Ash draws her blade.",
        "艾什拔出了剑。",
    )


def test_no_trailing_punctuation_and_translated_rules() -> None:
    assert _run("no-trailing-punctuation", {}, "Save", "保存")
    assert not _run("no-trailing-punctuation", {}, "Save", "保存。")
    assert not _run("translated", {}, "Save", "Save")


def test_consistency_rule_detects_drift() -> None:
    rule = Rule(id="c", kind="consistency", params={"source": "Ash", "target": ["余烬", "艾什"]})
    sources = {"a": "Ash speaks.", "b": "Ash waits."}
    consistent = check_rules([rule], sources, {"a": "余烬开口。", "b": "余烬等待。"})
    drifted = check_rules([rule], sources, {"a": "余烬开口。", "b": "艾什等待。"})
    assert all(item.passed for item in consistent)
    assert not all(item.passed for item in drifted)


def test_missing_entry_fails_every_rule() -> None:
    rule = Rule(id="r", kind="require", params={"text": "x"}, entry="missing")
    results = check_rules([rule], {"missing": "source"}, {})
    assert results and not results[0].passed
    assert instruction_score(results) == 0.0


def test_rule_context_defaults() -> None:
    ctx = RuleContext(entry_id="e", source="s", target="t", all_sources={}, all_targets={})
    assert ctx.target_language == "zh-CN"


def test_glossary_adherence(sample_glossary) -> None:
    terms = glossary_from_document(sample_glossary)
    sources = {"a": "Restore Default", "b": "Paste your API Token"}
    good = check_glossary(terms, sources, {"a": "恢复默认", "b": "粘贴你的 API Token"})
    bad = check_glossary(terms, sources, {"a": "恢复缺省", "b": "粘贴你的 API 词元"})
    assert good.adherence == 100.0
    assert bad.adherence < 100.0
    assert bad.violations


def test_dejargon_policy_detects_textbook_renderings() -> None:
    policy = load_policy("zh-CN")
    assert policy.rules
    report = check_jargon(policy, {"a": "恢复缺省设置", "b": "系统很健壮"})
    assert report.hit_count if hasattr(report, "hit_count") else report.hits
    assert any(hit["bad"] == "缺省" for hit in report.hits)
    assert report.clean_rate < 100.0
    assert "默认" in policy.prompt_fragment()


def test_degenerate_controls_score_below_a_real_answer() -> None:
    from clarion.metrics.controls import build_controls, evaluate_controls

    sources = {"a": "Restore Default", "b": "Streaming", "c": "Paste your API Token"}
    references = {"a": "恢复默认", "b": "流媒体", "c": "粘贴你的 API Token"}
    controls = build_controls(sources, references)
    assert set(controls) == {"empty", "copy-source", "shuffled", "truncated"}
    report = evaluate_controls(
        file_id="fixture", sources=sources, references=references, system=references
    )
    assert report.system_score == pytest.approx(100.0)
    assert report.sane
    assert report.controls["empty"] == 0.0
    assert report.controls["copy-source"] < 50.0

    weak = evaluate_controls(
        file_id="fixture",
        sources=sources,
        references=references,
        system={key: "" for key in references},
    )
    assert not weak.sane, "an empty answer must never pass the control gate"


def test_prompt_budget_arithmetic() -> None:
    tokenizer = get_tokenizer("o200k_base")
    budget = PromptBudget(tokenizer=tokenizer.name)
    budget.add("a", "user", "hello world", tokenizer)
    budget.add("spec.digest", "user", "a much longer specification block " * 20, tokenizer)
    assert budget.total > budget.without("spec.digest")
    assert budget.without("spec.digest") == budget.total - budget.tokens_of("spec.digest")


def test_tokenizer_fallback_is_deterministic() -> None:
    heuristic = get_tokenizer("heuristic")
    assert heuristic.name == "heuristic"
    assert heuristic.count("分辨率 Resolution 1080") == heuristic.count("分辨率 Resolution 1080")
    assert heuristic.count("") == 0
