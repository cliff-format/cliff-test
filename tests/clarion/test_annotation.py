"""The annotation pass and the guards that keep it from rigging the benchmark."""

from __future__ import annotations

import json

import pytest

from clarion.corpus.annotate import (
    AnnotationConfig,
    annotate_document,
    leaks_reference,
    summarize_document,
)
from clarion.corpus.fetchers import Pair, Recipe, pairs_to_document
from clarion.providers.base import Completion, CompletionRequest

RECIPE = Recipe(
    id="test-annotate",
    title="Test corpus",
    kind="hf",
    source="example/test",
    license="Apache-2.0",
    spdx="Apache-2.0",
    tier="vendor",
    languages={"source": "en-US", "target": "zh-CN"},
    strata=["ui"],
)

PAIRS = [
    Pair(key="save", source="Save", target="保存", document="toolbar"),
    Pair(key="discard", source="Discard changes", target="放弃更改", document="toolbar"),
]


class ScriptedProvider:
    """Deterministic annotator that returns whatever the test scripted."""

    def __init__(self, answers: list[str], model: str = "scripted-1") -> None:
        self.name = "scripted"
        self.model = model
        self.answers = list(answers)
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> Completion:
        self.requests.append(request)
        text = self.answers.pop(0) if self.answers else "{}"
        return Completion(text=text, provider=self.name, model=self.model, latency_ms=1.0)


def _document():
    return pairs_to_document(PAIRS, recipe=RECIPE, clan="test-annotate")


def test_summary_pass_writes_the_family_brief() -> None:
    answer = json.dumps(
        {
            "info": "Toolbar strings of an invented editor, shown to end users.",
            "standard": "Keep labels short; no trailing period; keep product names untranslated.",
            "groups": {"toolbar": "Buttons in the main editing toolbar."},
        }
    )
    document = _document()
    document.header.info = None
    document.header.standard = None
    for group in document.groups:
        group.context = None
    summarized, report = summarize_document(document, ScriptedProvider([answer]))
    assert report.wrote_family_brief
    assert report.summarized_groups == 1
    assert "Toolbar strings" in (summarized.header.info or "")
    assert "no trailing period" in (summarized.header.standard or "")
    assert summarized.groups[0].context == "Buttons in the main editing toolbar."


def test_annotator_never_receives_a_target() -> None:
    provider = ScriptedProvider(['{"items": {}}', '{"items": {}}'])
    annotate_document(
        _document(),
        provider,
        references={"save": "保存", "discard": "放弃更改"},
        config=AnnotationConfig(summarize=True),
    )
    for request in provider.requests:
        prompt = request.prompt_text()
        assert "保存" not in prompt
        assert "放弃更改" not in prompt


def test_leaky_context_is_rejected() -> None:
    answer = json.dumps(
        {
            "items": {
                "discard": {
                    "context": "Translate this as 放弃更改 in the toolbar.",
                    "type": "label",
                    "emotion": ["objective"],
                }
            }
        }
    )
    document = _document()
    annotated, report = annotate_document(
        document,
        ScriptedProvider([answer]),
        references={"discard": "放弃更改"},
        config=AnnotationConfig(summarize=False),
    )
    assert report.rejected_leak == 1
    entry = annotated.groups[0].entries[1]
    assert entry.context is None, "a brief that contains the answer must not be kept"


def test_invalid_tags_are_rejected_not_coerced() -> None:
    answer = json.dumps(
        {
            "items": {
                "save": {
                    "context": "Primary toolbar button that stores the current document.",
                    "type": "Button",
                    "emotion": ["Objective", "calm"],
                }
            }
        }
    )
    annotated, report = annotate_document(
        _document(),
        ScriptedProvider([answer]),
        references={"save": "保存"},
        config=AnnotationConfig(summarize=False),
    )
    assert report.rejected_type == 1
    assert report.rejected_emotion == 1
    entry = annotated.groups[0].entries[0]
    assert entry.type is None
    assert entry.emotion == ["calm"], "valid tags survive, invalid ones are dropped"


def test_impossible_width_budget_is_rejected() -> None:
    answer = json.dumps(
        {
            "items": {
                "discard": {
                    "context": "Secondary toolbar button next to the save action.",
                    "type": "label",
                    "emotion": ["objective"],
                    "max-width": 2,
                }
            }
        }
    )
    annotated, report = annotate_document(
        _document(),
        ScriptedProvider([answer]),
        references={"discard": "放弃更改"},
        config=AnnotationConfig(summarize=False, propose_width=True),
    )
    assert report.rejected_width == 1, "the reference is 8 cells wide, so a budget of 2 is invalid"
    assert annotated.groups[0].entries[1].max_width is None


def test_plausible_width_budget_is_accepted() -> None:
    answer = json.dumps(
        {
            "items": {
                "discard": {
                    "context": "Secondary toolbar button next to the save action.",
                    "type": "label",
                    "emotion": ["objective"],
                    "max-width": 10,
                }
            }
        }
    )
    annotated, report = annotate_document(
        _document(),
        ScriptedProvider([answer]),
        references={"discard": "放弃更改"},
        config=AnnotationConfig(summarize=False, propose_width=True),
    )
    assert report.rejected_width == 0
    assert annotated.groups[0].entries[1].max_width == 10


@pytest.mark.parametrize(
    ("context", "reference", "leaks"),
    [
        ("Use 放弃更改 here", "放弃更改", True),
        ("A toolbar button that discards edits", "放弃更改", False),
        ("Render it as the quick brown fox jumps", "the quick brown fox jumps over", True),
        ("A sentence about animals in a story", "the quick brown fox jumps over", False),
        ("", "保存", False),
    ],
)
def test_leak_detection(context: str, reference: str, leaks: bool) -> None:
    assert leaks_reference(context, reference) is leaks
