"""Degenerate-output controls: proving the metric is not fooled.

WMT24's analysis of COMET showed that an empty translation can outscore a real
system, and that a sentence-shuffled hypothesis can score about as well as an
empty one. A benchmark that reports quality without checking for that is not
measuring quality, it is measuring an artefact - and this benchmark
deliberately produces broken outputs, because a format that survives an LLM
edit badly will return exactly these shapes.

CLARION therefore scores four control hypotheses on every corpus file:

empty        nothing was returned
copy-source  the source text was echoed untranslated
shuffled     the reference translations were shuffled between entries
truncated    every reference cut to its first half

A metric that ranks any control at or above a real system is disqualified for
that run, and the report says so instead of quietly averaging it in.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..util import mean
from .surface import sentence_chrf

CONTROL_NAMES = ("empty", "copy-source", "shuffled", "truncated")


def build_controls(
    sources: dict[str, str],
    references: dict[str, str],
    *,
    seed: int = 20260101,
) -> dict[str, dict[str, str]]:
    """Build the four degenerate hypothesis sets for one file."""
    keys = sorted(references)
    shuffled_values = [references[key] for key in keys]
    random.Random(seed).shuffle(shuffled_values)
    return {
        "empty": {key: "" for key in keys},
        "copy-source": {key: sources.get(key, "") for key in keys},
        "shuffled": dict(zip(keys, shuffled_values, strict=True)),
        "truncated": {
            key: references[key][: max(1, len(references[key]) // 2)] for key in keys
        },
    }


def score_hypotheses(
    hypotheses: dict[str, str],
    references: dict[str, str],
) -> float:
    """Mean sentence chrF++ of a hypothesis set, in 0..100."""
    scores = [
        sentence_chrf(hypotheses.get(key, ""), [reference])
        for key, reference in references.items()
    ]
    return mean(scores)


@dataclass
class ControlReport:
    """Control scores for one file, and whether the metric stayed sane."""

    file_id: str
    system_score: float
    controls: dict[str, float] = field(default_factory=dict)

    @property
    def worst_control(self) -> tuple[str, float]:
        """The highest-scoring control, which is the dangerous one."""
        if not self.controls:
            return ("none", 0.0)
        name = max(self.controls, key=lambda key: self.controls[key])
        return (name, self.controls[name])

    @property
    def sane(self) -> bool:
        """True when the real system beats every degenerate control."""
        name, score = self.worst_control
        del name
        return self.system_score > score

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        name, score = self.worst_control
        return {
            "kind": "controls",
            "file": self.file_id,
            "system_score": round(self.system_score, 4),
            "controls": {key: round(value, 4) for key, value in self.controls.items()},
            "worst_control": name,
            "worst_control_score": round(score, 4),
            "sane": self.sane,
        }


def evaluate_controls(
    *,
    file_id: str,
    sources: dict[str, str],
    references: dict[str, str],
    system: dict[str, str],
    seed: int = 20260101,
) -> ControlReport:
    """Score a real answer against the degenerate controls."""
    controls = build_controls(sources, references, seed=seed)
    return ControlReport(
        file_id=file_id,
        system_score=score_hypotheses(system, references),
        controls={name: score_hypotheses(values, references) for name, values in controls.items()},
    )
