"""End-to-end pipeline: corpus loading, translation scoring, edit robustness.

These tests are the harness proving itself. A perfect answer must score
perfectly, and a deliberately damaged answer must be caught by the metric that
owns that damage; otherwise a benchmark number means nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clarion.config import ProviderConfig, RunConfig
from clarion.corpus.store import load_corpus
from clarion.experiments.robustness import apply_edit, default_tasks, run_robustness, verify_edit
from clarion.experiments.translate import run_translation_task
from clarion.formats import DEFAULT_FORMATS, Arm
from clarion.metrics.terminology import load_policy
from clarion.metrics.tokens import get_tokenizer
from clarion.providers.mock import MockProvider
from clarion.report import build_report
from clarion.runner import token_matrix


def _config(mode: str = "perfect") -> RunConfig:
    return RunConfig(
        name="test",
        formats=list(DEFAULT_FORMATS),
        arms=["bare", "context"],
        provider=ProviderConfig(kind="mock", model="mock-1", mode=mode),
    )


def test_corpus_loads_with_gold_and_glossary(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    assert len(corpus.files) == 1
    corpus_file = corpus.files[0]
    assert corpus_file.entry_count == 4
    assert corpus_file.glossary_document is not None
    assert corpus_file.references()["resolution"] == "分辨率"
    assert corpus_file.widths()["resolution"] == 12
    assert len(corpus_file.rules()) >= 6


def test_perfect_answer_scores_perfectly(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    result = run_translation_task(
        corpus.files[0],
        format_id="cliff",
        arm=Arm.CONTEXT,
        provider=MockProvider(mode="perfect"),
        tokenizer=get_tokenizer("o200k_base"),
        config=_config(),
        policy=load_policy("zh-CN"),
    )
    assert result.error is None
    assert result.structure["valid"] is True
    assert result.structure["coverage"] == 1.0
    assert result.structure["id_preservation"] == 1.0
    assert result.quality["chrf"] > 99.0
    assert result.instruction["score"] == 100.0
    assert result.terminology["adherence"] == 100.0
    assert result.jargon["clean_rate"] == 100.0
    assert result.prompt_tokens > 0
    assert result.document_tokens > 0


def test_damaged_answer_is_detected(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    result = run_translation_task(
        corpus.files[0],
        format_id="cliff",
        arm=Arm.CONTEXT,
        provider=MockProvider(mode="noisy"),
        tokenizer=get_tokenizer("o200k_base"),
        config=_config("noisy"),
        policy=load_policy("zh-CN"),
    )
    assert result.structure["unwrapped"] is True, "a code fence must be unwrapped, not fatal"
    assert result.structure["coverage"] < 1.0, "the dropped entry must be visible"
    assert result.quality["chrf"] < 100.0
    assert result.instruction["score"] < 100.0 or result.jargon["hit_count"] > 0


@pytest.mark.parametrize("format_id", DEFAULT_FORMATS)
def test_every_format_survives_a_perfect_answer(corpus_root: Path, format_id: str) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    result = run_translation_task(
        corpus.files[0],
        format_id=format_id,
        arm=Arm.CONTEXT,
        provider=MockProvider(mode="perfect"),
        tokenizer=get_tokenizer("o200k_base"),
        config=_config(),
        policy=load_policy("zh-CN"),
    )
    assert result.structure["parsed"] is True, result.structure.get("errors")
    assert result.structure["coverage"] == 1.0


def test_token_matrix_covers_every_cell(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    rows = token_matrix(_config(), corpus, tokenizer=get_tokenizer("o200k_base"))
    assert rows
    cliff_bare = next(r for r in rows if r["format"] == "cliff" and r["arm"] == "bare")
    cliff_context = next(r for r in rows if r["format"] == "cliff" and r["arm"] == "context")
    assert cliff_context["document_tokens"] > cliff_bare["document_tokens"]
    assert cliff_bare["spec_tokens"] > 0
    assert (
        cliff_bare["prompt_tokens_without_format_instructions"]
        == cliff_bare["prompt_tokens"]
        - cliff_bare["spec_tokens"]
        - cliff_bare["format_notes_tokens"]
    )
    po_row = next(r for r in rows if r["format"] == "po" and r["arm"] == "bare")
    assert po_row["spec_tokens"] == 0


def test_deterministic_edits_keep_every_format_valid(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    document = corpus.files[0].document
    tasks = default_tasks(document, count=12)
    assert tasks
    for format_id in DEFAULT_FORMATS:
        result = run_robustness(
            document,
            format_id=format_id,
            arm=Arm.CONTEXT,
            provider=None,
            tasks=tasks,
            file_id="fixture",
        )
        assert result.applicable > 0
        assert result.validity_rate == 100.0, f"{format_id}: {result.as_dict()}"
        # The deterministic replay is the control for dimension 7: if the
        # reference application of an intent does not verify, the harness -
        # not the model - is the problem.
        assert result.intent_rate == 100.0, f"{format_id}: {result.as_dict()}"


def test_edit_intents_are_verifiable(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    document = corpus.files[0].document
    for task in default_tasks(document, count=12):
        edited = apply_edit(document, task)
        assert verify_edit(edited, task), task.op
        if task.op in {"set-target", "set-status", "rename-entry"}:
            assert not verify_edit(document, task), f"{task.op} verified before it was applied"


def test_report_renders_from_records(corpus_root: Path) -> None:
    corpus = load_corpus("fixture", root=corpus_root)
    config = _config()
    tokenizer = get_tokenizer("o200k_base")
    rows = token_matrix(config, corpus, tokenizer=tokenizer)
    records = []
    for format_id in ("cliff", "po"):
        result = run_translation_task(
            corpus.files[0],
            format_id=format_id,
            arm=Arm.CONTEXT,
            provider=MockProvider(mode="perfect"),
            tokenizer=tokenizer,
            config=config,
            policy=load_policy("zh-CN"),
        )
        record = result.as_dict()
        record["kind"] = "translation"
        records.append(record)
    report = build_report(
        title="test", config=config.as_dict(), token_rows=rows, records=records
    )
    assert "D1 - token cost" in report
    assert "D4 - quality" in report
    assert "cliff" in report


def test_structure_report_states_modification_correctness(corpus_root: Path) -> None:
    """The rewrite's integrity is reported, with the columns that decide it.

    The second half is the reason the table exists: an answer can be a perfectly
    **valid** CLIFF file and still be the wrong document - the model kept one entry
    and dropped the rest. Validity alone cannot see that, and every translation
    memory keyed on the missing ids would miss.
    """
    from clarion.providers.base import Completion
    from clarion.report import structure_report

    class OneEntry:
        """Returns a valid CLIFF file that has lost three of the four entries."""

        name = "scripted"
        model = "scripted-1"

        def complete(self, request):  # noqa: ANN001, ANN201 - test double
            text = (
                "CLIFF 1.1\n"
                "namespace: clarion\n"
                "clan: fixture\n"
                "source-language: en-US\n"
                "target-language: zh-CN\n"
                "\n"
                "[settings.video]\n"
                "type: label\n"
                "\n"
                "<resolution>\n"
                'source: "Resolution"\n'
                'target: "分辨率"\n'
                "status: final\n"
            )
            return Completion(text=text, provider=self.name, model=self.model, latency_ms=1.0)

    corpus = load_corpus("fixture", root=corpus_root)
    config = _config()
    tokenizer = get_tokenizer("o200k_base")

    def row(provider) -> dict:  # noqa: ANN001 - test helper
        result = run_translation_task(
            corpus.files[0],
            format_id="cliff",
            arm=Arm.CONTEXT,
            provider=provider,
            tokenizer=tokenizer,
            config=config,
            policy=load_policy("zh-CN"),
        )
        record = result.as_dict()
        record["kind"] = "translation"
        return record

    perfect = structure_report([row(MockProvider(mode="perfect"))])
    for column in ("ids kept %", "coverage %", "source kept %", "repairs/answer"):
        assert column in perfect, f"the table lost the '{column}' column"
    assert "100.0" in perfect, perfect

    partial = structure_report([row(OneEntry())])
    assert partial != perfect, "a document that lost entries must not read like a perfect one"

    def cells(report: str) -> dict[str, str]:
        lines = [line for line in report.split("\n") if line.startswith("|")]
        headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
        values = [cell.strip() for cell in lines[2].strip("|").split("|")]
        return dict(zip(headers, values, strict=True))

    kept = cells(perfect)
    lost = cells(partial)
    # The discrimination must land in the integrity columns, which is the whole
    # point: the fixture has four entries, the scripted answer kept one, so the
    # file is valid and three quarters of the document is gone.
    assert kept["valid %"] == "100.0" and lost["valid %"] == "100.0"
    assert kept["ids kept %"] == "100.0" and lost["ids kept %"] == "25.0"
    assert kept["coverage %"] == "100.0" and lost["coverage %"] == "25.0"
    assert kept["missing ids"] == "0" and lost["missing ids"] == "3"
    assert kept["source kept %"] == "100.0" and lost["source kept %"] == "100.0", (
        "a dropped entry is a coverage failure, not a source rewrite"
    )
