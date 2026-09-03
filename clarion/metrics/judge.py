"""LLM-as-judge quality scoring (metric tier 2), GEMBA-MQM style.

Surface metrics cannot see whether a translation followed the brief, and a
neural metric cannot explain itself. An MQM-style judge marks error spans with
a category and a severity, which is both explainable and comparable across
formats. Weights follow the MQM convention: critical 25, major 5, minor 1,
subtracted from 100.

The judge is optional and costs tokens; it is never enabled by default.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..providers.base import CompletionRequest, Provider

SEVERITY_WEIGHTS = {"critical": 25.0, "major": 5.0, "minor": 1.0}
CATEGORIES = ("accuracy", "fluency", "terminology", "style", "locale-convention", "design")
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class MqmError:
    """One error span reported by the judge."""

    category: str
    severity: str
    span: str = ""
    note: str = ""

    @property
    def weight(self) -> float:
        """MQM penalty of this error."""
        return SEVERITY_WEIGHTS.get(self.severity.lower(), 1.0)


@dataclass
class JudgeResult:
    """Judged quality of one translated entry."""

    entry: str
    errors: list[MqmError] = field(default_factory=list)
    comment: str = ""
    error: str | None = None
    latency_ms: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def score(self) -> float:
        """MQM score in 0..100."""
        if self.error:
            return 0.0
        penalty = sum(item.weight for item in self.errors)
        return max(0.0, 100.0 - penalty)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "entry": self.entry,
            "score": round(self.score, 4),
            "comment": self.comment,
            "error": self.error,
            "errors": [
                {
                    "category": item.category,
                    "severity": item.severity,
                    "span": item.span,
                    "note": item.note,
                }
                for item in self.errors
            ],
        }


def parse_judgement(text: str) -> tuple[list[MqmError], str, str | None]:
    """Read the judge's JSON answer, tolerating surrounding prose."""
    match = _JSON_RE.search(text or "")
    if not match:
        return [], "", "judge did not return JSON"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        return [], "", f"judge JSON invalid: {exc.msg}"
    errors: list[MqmError] = []
    for item in data.get("errors", []) or []:
        if not isinstance(item, dict):
            continue
        errors.append(
            MqmError(
                category=str(item.get("category", "accuracy")).lower(),
                severity=str(item.get("severity", "minor")).lower(),
                span=str(item.get("span", "")),
                note=str(item.get("note", "")),
            )
        )
    return errors, str(data.get("comment", "")), None


def judge_entry(
    provider: Provider,
    *,
    entry_id: str,
    source: str,
    target: str,
    reference: str | None,
    context: str | None,
    source_language: str,
    target_language: str,
    max_output_tokens: int = 1024,
) -> JudgeResult:
    """Score one translated entry with an MQM-style judge."""
    # Imported here rather than at module scope: prompt assembly depends on the
    # token metrics, so a top-level import would close a cycle.
    from ..prompts.assembly import build_judge_prompt

    messages = build_judge_prompt(
        source=source,
        target=target,
        reference=reference,
        context=context,
        source_language=source_language,
        target_language=target_language,
    )
    completion = provider.complete(
        CompletionRequest(messages=messages, temperature=0.0, max_output_tokens=max_output_tokens)
    )
    if completion.error:
        return JudgeResult(entry=entry_id, error=completion.error, latency_ms=completion.latency_ms)
    errors, comment, failure = parse_judgement(completion.text)
    return JudgeResult(
        entry=entry_id,
        errors=errors,
        comment=comment,
        error=failure,
        latency_ms=completion.latency_ms,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
    )


def judge_score(results: list[JudgeResult]) -> float:
    """Mean MQM score over judged entries."""
    scored = [result for result in results if result.error is None]
    if not scored:
        return 0.0
    return sum(result.score for result in scored) / len(scored)
