"""The MQM judge: reading its answer, and the arithmetic that turns it into a score.

The judge is the optional tier-2 metric, disabled by default, which is exactly why
it needs a test: nothing in the default runs exercises it, so it could drift for
months. The two halves that can go wrong silently are asserted here - a judge that
answers in prose around its JSON must still be read, and a malformed answer must be
an error rather than a score of zero, because a zero would look like a bad
translation instead of a broken judge.
"""

from __future__ import annotations

import pytest

from clarion.metrics.judge import (
    CATEGORIES,
    SEVERITY_WEIGHTS,
    JudgeResult,
    MqmError,
    judge_entry,
    judge_score,
    parse_judgement,
)
from clarion.providers.base import Completion, CompletionRequest


class Scripted:
    """A judge that returns whatever the test scripted."""

    name = "scripted"
    model = "scripted-judge"

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> Completion:
        self.requests.append(request)
        return Completion(
            text=self.answer, provider=self.name, model=self.model, latency_ms=1.0
        )


def test_a_bare_json_answer_is_read() -> None:
    errors, comment, failure = parse_judgement(
        '{"errors": [{"category": "terminology", "severity": "major", '
        '"span": "缺省", "note": "use 默认"}], "comment": "one term"}'
    )
    assert failure is None
    assert comment == "one term"
    assert len(errors) == 1
    assert errors[0].category == "terminology"
    assert errors[0].weight == SEVERITY_WEIGHTS["major"]


def test_json_wrapped_in_prose_is_still_read() -> None:
    """A judge that explains itself first is normal, not a failure."""
    errors, _, failure = parse_judgement(
        'Looking at the pair, I found:\n{"errors": [], "comment": "fine"}\nHope that helps.'
    )
    assert failure is None
    assert errors == []


def test_an_answer_without_json_is_an_error_not_a_zero() -> None:
    """Zero would read as a bad translation; the difference matters."""
    errors, _, failure = parse_judgement("The translation is good.")
    assert errors == []
    assert failure is not None and "JSON" in failure
    assert JudgeResult(entry="x", error=failure).score == 0.0


def test_malformed_json_is_reported_with_a_reason() -> None:
    # A brace that closes but does not parse: the JSON the judge returned is
    # malformed, and the reason names that.
    _, _, invalid = parse_judgement('{"errors": [}')
    assert invalid is not None and "invalid" in invalid
    # A brace that never closes - the usual shape of a truncated answer - has no
    # JSON object in it at all, so it is reported as absent rather than malformed.
    _, _, absent = parse_judgement('{"errors": [')
    assert absent is not None and "JSON" in absent


def test_a_malformed_error_entry_is_skipped_rather_than_crashing() -> None:
    """A judge that returns a list of strings must not take the run down."""
    errors, _, failure = parse_judgement('{"errors": ["not an object", 7]}')
    assert failure is None
    assert errors == []


@pytest.mark.parametrize(
    ("severity", "weight"),
    [("critical", 25.0), ("major", 5.0), ("minor", 1.0)],
)
def test_the_mqm_weights_are_the_published_ones(severity: str, weight: float) -> None:
    assert MqmError(category="accuracy", severity=severity).weight == weight
    # Case does not change the severity, and an unknown severity is not free.
    assert MqmError(category="accuracy", severity=severity.upper()).weight == weight
    assert MqmError(category="accuracy", severity="catastrophic").weight == 1.0


def test_the_score_is_a_hundred_minus_the_penalty_and_never_negative() -> None:
    clean = JudgeResult(entry="a")
    assert clean.score == 100.0
    one_major = JudgeResult(entry="a", errors=[MqmError("accuracy", "major")])
    assert one_major.score == 95.0
    five_criticals = JudgeResult(
        entry="a", errors=[MqmError("accuracy", "critical") for _ in range(5)]
    )
    assert five_criticals.score == 0.0, "the score must clamp at zero, not go negative"


def test_a_failed_call_scores_zero_and_keeps_the_reason() -> None:
    result = JudgeResult(entry="a", error="HTTP 500")
    assert result.score == 0.0
    assert result.as_dict()["error"] == "HTTP 500"


def test_the_group_score_averages_only_the_judged_entries() -> None:
    scored = [JudgeResult(entry="a"), JudgeResult(entry="b", errors=[MqmError("fluency", "major")])]
    assert judge_score(scored) == 97.5
    # An entry the judge never answered is excluded, not counted as a zero.
    assert judge_score([*scored, JudgeResult(entry="c", error="timeout")]) == 97.5
    assert judge_score([]) == 0.0


def test_judge_entry_asks_about_one_entry_and_reports_its_cost() -> None:
    provider = Scripted('{"errors": [{"category": "style", "severity": "minor"}], "comment": ""}')
    result = judge_entry(
        provider,
        entry_id="resolution",
        source="Resolution",
        target="解析度",
        reference="分辨率",
        context="Toolbar button.",
        source_language="en-US",
        target_language="zh-CN",
    )
    assert result.error is None
    assert result.entry == "resolution"
    assert result.score == 99.0
    assert result.latency_ms == 1.0
    assert len(provider.requests) == 1
    message = provider.requests[0].messages[-1].content
    for fragment in ("Resolution", "解析度", "分辨率", "Toolbar button."):
        assert fragment in message, f"the judge was not told the {fragment!r}"


def test_the_prompt_names_the_categories_the_parser_accepts() -> None:
    """A judge told the wrong vocabulary reports categories nothing can read."""
    provider = Scripted('{"errors": []}')
    judge_entry(
        provider,
        entry_id="e",
        source="s",
        target="t",
        reference=None,
        context=None,
        source_language="en-US",
        target_language="zh-CN",
    )
    prompt = provider.requests[0].messages[0].content + provider.requests[0].messages[-1].content
    for category in CATEGORIES:
        assert category in prompt, f"the judge prompt does not offer '{category}'"
