"""Terminology metrics: glossary adherence and de-jargon policy.

Two different failures are measured here.

Glossary adherence
    The project shipped a CLIF glossary (variant: glossary). Did the model use
    the canonical rendering of every term that actually occurs in the source?
    This is the metric that a context-carrying format is supposed to win.

De-jargon policy
    Some renderings dominate training data yet read badly to a normal reader:
    'default' as the 1980s calque instead of the modern word, 'robust' as a
    transliteration, 'token' as a coined compound. The policy file is editable
    project data; the metric counts how often a model fell back to the
    textbook rendering instead of following the brief.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..paths import POLICY_ROOT, ensure_pyclif
from ..util import read_text

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyclif import ClifDocument


@dataclass(frozen=True)
class GlossaryTerm:
    """One canonical term pair from a CLIF glossary file."""

    id: str
    source: str
    target: str
    type: str | None = None
    context: str | None = None
    forbidden: tuple[str, ...] = ()


def glossary_from_document(document: ClifDocument) -> list[GlossaryTerm]:
    """Read every term of a parsed CLIF glossary document."""
    terms: list[GlossaryTerm] = []
    for group in document.groups:
        for entry in group.entries:
            if not entry.source or not entry.target:
                continue
            terms.append(
                GlossaryTerm(
                    id=entry.id,
                    source=entry.source,
                    target=entry.target,
                    type=entry.type or group.type,
                    context=entry.context,
                )
            )
    return terms


def load_glossary(path: Path) -> list[GlossaryTerm]:
    """Load a CLIF glossary file through pyclif."""
    ensure_pyclif()
    import pyclif

    return glossary_from_document(pyclif.load(path))


@dataclass
class TerminologyReport:
    """Glossary adherence over one answer."""

    applicable: int = 0
    respected: int = 0
    violations: list[dict[str, str]] = field(default_factory=list)

    @property
    def adherence(self) -> float:
        """Percentage of applicable term occurrences rendered canonically."""
        if not self.applicable:
            return 100.0
        return 100.0 * self.respected / self.applicable

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "applicable": self.applicable,
            "respected": self.respected,
            "adherence": round(self.adherence, 4),
            "violations": self.violations[:20],
        }


def check_glossary(
    terms: list[GlossaryTerm],
    sources: dict[str, str],
    targets: dict[str, str],
) -> TerminologyReport:
    """Count how often the canonical rendering was used where it applied."""
    report = TerminologyReport()
    for entry_id, source_text in sources.items():
        target_text = targets.get(entry_id)
        if target_text is None:
            continue
        lowered = source_text.lower()
        for term in terms:
            if not term.source or term.source.lower() not in lowered:
                continue
            report.applicable += 1
            if term.target and term.target in target_text:
                report.respected += 1
            else:
                report.violations.append(
                    {
                        "entry": entry_id,
                        "term": term.source,
                        "expected": term.target,
                        "target": target_text,
                    }
                )
    return report


@dataclass(frozen=True)
class JargonRule:
    """One discouraged rendering and its accepted alternatives."""

    source: str
    bad: str
    good: tuple[str, ...]
    confidence: str = "medium"
    note: str = ""


@dataclass
class JargonPolicy:
    """A locale's de-jargon policy."""

    locale: str
    rules: list[JargonRule] = field(default_factory=list)
    keep_english: list[dict[str, str]] = field(default_factory=list)
    version: str = ""

    def enforceable(self, minimum: str = "medium") -> list[JargonRule]:
        """Rules at or above a confidence threshold."""
        order = {"low": 0, "medium": 1, "high": 2}
        floor = order.get(minimum, 1)
        return [rule for rule in self.rules if order.get(rule.confidence, 1) >= floor]

    def prompt_fragment(self, limit: int = 12) -> str:
        """A compact instruction block for a translation prompt."""
        lines = ["Terminology policy (project rules override training habits):"]
        for rule in self.enforceable("medium")[:limit]:
            good = " / ".join(rule.good)
            lines.append(f"- {rule.source}: use {good}; do not use {rule.bad}.")
        if self.keep_english:
            keep = ", ".join(item["term"] for item in self.keep_english)
            lines.append(f"- Keep these in Latin script: {keep}.")
        return "\n".join(lines)


def load_policy(locale: str = "zh-CN", root: Path | None = None) -> JargonPolicy:
    """Load the de-jargon policy for a locale, or an empty policy."""
    directory = root or POLICY_ROOT
    path = directory / f"dejargon.{locale}.json"
    if not path.exists():
        return JargonPolicy(locale=locale)
    data = json.loads(read_text(path))
    rules = [
        JargonRule(
            source=str(item.get("source", "")),
            bad=str(item["bad"]),
            good=tuple(str(value) for value in item.get("good", [])),
            confidence=str(item.get("confidence", "medium")),
            note=str(item.get("note", "")),
        )
        for item in data.get("rules", [])
    ]
    return JargonPolicy(
        locale=str(data.get("locale", locale)),
        rules=rules,
        keep_english=list(data.get("keep_english", [])),
        version=str(data.get("version", "")),
    )


@dataclass
class JargonReport:
    """How often an answer fell back to a discouraged rendering."""

    checked_entries: int = 0
    hits: list[dict[str, str]] = field(default_factory=list)

    @property
    def clean_rate(self) -> float:
        """Percentage of entries with no discouraged rendering."""
        if not self.checked_entries:
            return 100.0
        offending = {hit["entry"] for hit in self.hits}
        return 100.0 * (self.checked_entries - len(offending)) / self.checked_entries

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "checked_entries": self.checked_entries,
            "hits": self.hits[:20],
            "hit_count": len(self.hits),
            "clean_rate": round(self.clean_rate, 4),
        }


def check_jargon(
    policy: JargonPolicy,
    targets: dict[str, str],
    *,
    minimum_confidence: str = "medium",
) -> JargonReport:
    """Find discouraged renderings in an answer."""
    report = JargonReport(checked_entries=len(targets))
    rules = policy.enforceable(minimum_confidence)
    for entry_id, target_text in targets.items():
        for rule in rules:
            if rule.bad and rule.bad in target_text:
                report.hits.append(
                    {
                        "entry": entry_id,
                        "bad": rule.bad,
                        "good": " / ".join(rule.good),
                        "source": rule.source,
                    }
                )
    return report
