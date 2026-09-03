"""Corpus lint: the dataset standard, enforced instead of hoped for.

Three defects have already cost this benchmark a wrong number, so each is now
a check that runs in 'clarion corpus validate':

1. **A rule its own reference fails.** If the gold translation cannot satisfy
   the rule attached to it, every model is measured against something
   impossible.
2. **An identifier that leaks the answer.** In a minimal pair, ids like
   'praise-sincere' and 'praise-sarcastic' hand the distinction to the model
   for free: the plain arm then "disambiguates" without any context, and the
   value of context is measured as far smaller than it is. Ids of a pair MUST
   differ only by a neutral suffix.
3. **A context line that contains the answer.** Writing the target rendering
   into the brief turns the context arm into a copying exercise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..metrics.instruction import check_rules
from .model import CorpusFile

__all__ = ["LintFinding", "lint_file"]

_NEUTRAL_SUFFIX = re.compile(r"^(?P<stem>.+?)[-_]?(?P<tag>[a-z]|\d{1,2})$")
_DIGIT = re.compile(r"\d")
_LATIN = re.compile(r"[A-Za-z]")
_PLACEHOLDER = re.compile(r"%\d*\$?[sdf@]|\{[A-Za-z0-9_]+\}|<[a-zA-Z/][^>]*>")


def _vacuous(kind: str, params: dict[str, Any], source: str, reference: str,
             occurrences: int) -> str | None:
    """Return why a rule can never fail, or None when it carries signal.

    A rule that passes no matter what the model writes inflates the rule count
    and measures nothing. The checks below are per kind preconditions: an ICU
    rule on a segment without braces, a numerals rule on a segment without
    digits, a consistency rule on a term that occurs once.
    """
    values = params or {}
    if kind in {"require", "forbid", "keep-verbatim"} and not (
        values.get("text") or values.get("texts")
    ):
        return "no text configured, so the rule cannot fail"
    if kind == "term" and not (values.get("target") or values.get("forbidden")):
        return "neither an expected nor a forbidden rendering is configured"
    if kind == "name-policy" and not (values.get("expected") or values.get("rejected")):
        return "neither expected nor rejected renderings are configured"
    if kind == "icu-preserve" and "{" not in source and "}" not in source:
        return "the source carries no MessageFormat payload"
    if kind == "placeholder-preserve" and not _PLACEHOLDER.search(source):
        return "the source carries no placeholder of a recognised shape"
    if kind == "numerals" and not _DIGIT.search(source):
        return "the source contains no digits"
    if kind == "cjk-latin-space" and not (_LATIN.search(reference) or _DIGIT.search(reference)):
        return "the reference has no Latin letters or digits, so spacing cannot be wrong"
    if kind == "consistency" and occurrences < 2:
        return "the term occurs in fewer than two entries, so consistency cannot be violated"
    if kind == "regex" and not values.get("pattern"):
        return "no pattern configured"
    if kind == "length-ratio":
        low = float(values.get("min", 0.0))
        high = float(values.get("max", 99.0))
        if low <= 0.05 and high >= 20:
            return f"the bounds {low}-{high} accept any translation"
    if kind == "max-width" and not values.get("cells"):
        return "no cell budget configured"
    return None


@dataclass(frozen=True)
class LintFinding:
    """One defect in a corpus file."""

    file: str
    entry: str
    kind: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {"file": self.file, "entry": self.entry, "kind": self.kind, "detail": self.detail}


def _pairs_by_source(corpus_file: CorpusFile) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for entry_id, source in corpus_file.sources().items():
        key = " ".join((source or "").split()).lower()
        groups.setdefault(key, []).append(entry_id)
    return {key: ids for key, ids in groups.items() if len(ids) > 1 and key}


def lint_file(corpus_file: CorpusFile) -> list[LintFinding]:
    """Check one corpus file against the dataset standard."""
    findings: list[LintFinding] = []
    name = corpus_file.path.name
    sources = corpus_file.sources()
    references = corpus_file.references()

    results = check_rules(
        corpus_file.rules(),
        sources,
        references,
        target_language=corpus_file.target_language,
        widths=corpus_file.widths(),
    )
    for item in results:
        if item.severity == "error" and not item.passed:
            findings.append(
                LintFinding(name, item.entry, "reference-fails-own-rule",
                            f"{item.kind}: {item.detail}")
            )

    for _source, ids in _pairs_by_source(corpus_file).items():
        stems = set()
        for entry_id in ids:
            match = _NEUTRAL_SUFFIX.match(entry_id)
            stems.add(match.group("stem") if match else entry_id)
        if len(stems) > 1:
            findings.append(
                LintFinding(
                    name,
                    ", ".join(sorted(ids)),
                    "identifier-leak",
                    "entries that share a source must differ only by a neutral suffix "
                    f"(found stems {sorted(stems)}); a meaningful id hands the "
                    "distinction to the model and hides the value of context",
                )
            )

    for group in corpus_file.document.groups:
        for entry in group.entries:
            reference = references.get(entry.id, "")
            context = f"{entry.context or ''} {group.context or ''}"
            if reference and len(reference) > 3 and reference in context:
                findings.append(
                    LintFinding(name, entry.id, "context-contains-answer",
                                "the context line repeats the reference translation")
                )

    lowered = [text.lower() for text in sources.values()]
    for entry_id, gold in corpus_file.gold.items():
        source = sources.get(entry_id, "")
        reference = references.get(entry_id, "")
        for rule in gold.rules:
            term = str(rule.params.get("source", "")).lower()
            occurrences = sum(1 for text in lowered if term and term in text)
            reason = _vacuous(rule.kind, rule.params, source, reference, occurrences)
            if reason:
                findings.append(
                    LintFinding(name, entry_id, "rule-without-signal",
                                f"{rule.id} ({rule.kind}): {reason}")
                )
    return findings
