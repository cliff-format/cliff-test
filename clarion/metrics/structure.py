"""Structural scoring of a model answer against the document it was given.

A translation answer is only usable when the file still parses, still carries
every identifier it was given, and did not quietly rewrite the source text.
These are format properties, not model properties, which is why they are
measured for every format in exactly the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..formats.parse import parse_back
from ..formats.read_mode import DEFAULT_READ_MODE, is_tolerant
from ..formats.validity import check_validity

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cliff_format import CliffDocument


def _normalize(text: str | None) -> str:
    return " ".join((text or "").split())


@dataclass
class StructureReport:
    """How well an answer preserved the structure it was handed."""

    format_id: str
    parsed: bool
    valid: bool
    unwrapped: bool = False
    #: Which reading of the answer produced ``parsed``/``valid``, and how many
    #: Appendix C repairs the tolerant reading needed (always 0 under strict).
    read_mode: str = DEFAULT_READ_MODE
    repairs: int = 0
    expected_entries: int = 0
    returned_entries: int = 0
    matched_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)
    extra_ids: list[str] = field(default_factory=list)
    translated_ids: list[str] = field(default_factory=list)
    untranslated_ids: list[str] = field(default_factory=list)
    source_drift_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def id_preservation(self) -> float:
        """Share of expected entries that came back with their identifier."""
        if not self.expected_entries:
            return 0.0
        return len(self.matched_ids) / self.expected_entries

    @property
    def coverage(self) -> float:
        """Share of expected entries that came back with a non-empty target."""
        if not self.expected_entries:
            return 0.0
        return len(self.translated_ids) / self.expected_entries

    @property
    def source_fidelity(self) -> float:
        """Share of matched entries whose source text was left untouched."""
        matched = len(self.matched_ids)
        if not matched:
            return 0.0
        return 1.0 - len(self.source_drift_ids) / matched

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "format": self.format_id,
            "parsed": self.parsed,
            "valid": self.valid,
            "unwrapped": self.unwrapped,
            "read_mode": self.read_mode,
            "repairs": self.repairs,
            "expected_entries": self.expected_entries,
            "returned_entries": self.returned_entries,
            "id_preservation": round(self.id_preservation, 6),
            "coverage": round(self.coverage, 6),
            "source_fidelity": round(self.source_fidelity, 6),
            "missing_ids": self.missing_ids,
            "extra_ids": self.extra_ids,
            "untranslated_ids": self.untranslated_ids,
            "source_drift_ids": self.source_drift_ids,
            "errors": self.errors[:10],
        }


def evaluate_structure(
    reference: CliffDocument,
    answer_text: str,
    format_id: str,
    *,
    bilingual: bool = True,
    read_mode: str = DEFAULT_READ_MODE,
) -> tuple[StructureReport, dict[str, str], CliffDocument | None]:
    """Score an answer structurally and return the targets it produced.

    The second element maps entry id to translated text and is what the
    quality, terminology and instruction-following metrics consume.

    ``read_mode`` selects the CLIFF reading used for both the validity check and
    the read-back, so the two can never disagree about the same answer.
    """
    tolerant = is_tolerant(read_mode)
    validity = check_validity(answer_text, format_id, tolerant=tolerant)
    outcome = parse_back(answer_text, format_id, read_mode=read_mode)
    glossary_document = outcome.glossary

    expected: dict[str, str] = {}
    for group in reference.groups:
        for entry in group.entries:
            expected[entry.id] = _normalize(entry.source)

    report = StructureReport(
        format_id=format_id,
        parsed=outcome.ok,
        valid=validity.ok,
        unwrapped=validity.unwrapped or outcome.unwrapped,
        read_mode=read_mode,
        repairs=max(outcome.repairs, validity.repairs),
        expected_entries=len(expected),
        errors=[f"{d.line}: {d.message}" for d in validity.errors],
    )
    if outcome.error:
        report.errors.insert(0, outcome.error)
    if outcome.document is None:
        report.missing_ids = sorted(expected)
        return report, {}, glossary_document

    answers: dict[str, tuple[str, str]] = {}
    for group in outcome.document.groups:
        for entry in group.entries:
            value = entry.target if entry.target is not None else entry.source
            answers[entry.id] = (_normalize(entry.source), value or "")
    report.returned_entries = len(answers)

    # Entries whose identifier was lost can still be recovered by source text,
    # which keeps the quality metrics measurable while id_preservation records
    # the structural failure.
    by_source = {source: key for key, (source, _) in answers.items() if source}
    targets: dict[str, str] = {}
    for entry_id, source_text in expected.items():
        found_key = entry_id if entry_id in answers else by_source.get(source_text)
        if found_key is None:
            report.missing_ids.append(entry_id)
            continue
        if found_key == entry_id:
            report.matched_ids.append(entry_id)
        answer_source, answer_target = answers[found_key]
        if bilingual and answer_source and source_text and answer_source != source_text:
            report.source_drift_ids.append(entry_id)
        if answer_target.strip():
            targets[entry_id] = answer_target
            report.translated_ids.append(entry_id)
        else:
            report.untranslated_ids.append(entry_id)

    report.extra_ids = sorted(set(answers) - set(expected))
    return report, targets, glossary_document
