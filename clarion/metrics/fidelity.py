"""Round-trip fidelity: how much context a format loses on the way home.

CLIFF claims to be a lossless working format. The honest way to test that claim
is to convert a document into every other format and back, then count how many
context facts survived. Because cliff-python resolves group inheritance when it
writes flat formats, the comparison uses EFFECTIVE values (what a translator
would actually see for an entry), not the raw group/entry split.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..formats.arms import Arm
from ..formats.parse import parse_back
from ..formats.read_mode import DEFAULT_READ_MODE
from ..formats.render import render
from ..paths import ensure_cliff_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cliff_format import CliffDocument

HEADER_FIELDS = ("title", "info", "standard", "dependency", "version")
ENTRY_FIELDS = ("source", "target", "type", "emotion", "status", "context", "max-width",
                "reference", "reviewer")


def _effective(document: CliffDocument) -> dict[str, dict[str, str]]:
    ensure_cliff_format()
    from cliff_format import (
        effective_context,
        effective_emotion,
        effective_max_width,
        effective_type,
    )

    table: dict[str, dict[str, str]] = {}
    for group in document.groups:
        for entry in group.entries:
            width = effective_max_width(entry, group)
            table[entry.id] = {
                "source": (entry.source or "").strip(),
                "target": (entry.target or "").strip(),
                "type": effective_type(entry, group) or "",
                "emotion": "|".join(effective_emotion(entry, group)),
                "status": entry.status or "",
                "context": (effective_context(entry, group) or "").strip(),
                "max-width": "" if width is None else str(width),
                "reference": "|".join(entry.reference),
                "reviewer": entry.reviewer or "",
            }
    return table


def _header(document: CliffDocument) -> dict[str, str]:
    header = document.header
    return {
        "title": header.title or "",
        "info": (header.info or "").strip(),
        "standard": (header.standard or "").strip(),
        "dependency": "|".join(header.dependency),
        "version": header.version or "",
    }


@dataclass
class FidelityReport:
    """Field-level information loss of one format round trip."""

    format_id: str
    arm: str
    ok: bool
    facts_present: int = 0
    facts_kept: int = 0
    lost_by_field: dict[str, int] = field(default_factory=dict)
    changed_by_field: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    #: Reading used for the CLIFF read-back, and the repairs it needed. A
    #: tolerant round trip of our own canonical output must need zero.
    read_mode: str = DEFAULT_READ_MODE
    repairs: int = 0

    @property
    def retention(self) -> float:
        """Share of context facts that survived the round trip."""
        if not self.facts_present:
            return 1.0
        return self.facts_kept / self.facts_present

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "format": self.format_id,
            "arm": self.arm,
            "ok": self.ok,
            "facts_present": self.facts_present,
            "facts_kept": self.facts_kept,
            "retention": round(self.retention, 6),
            "lost_by_field": self.lost_by_field,
            "changed_by_field": self.changed_by_field,
            "read_mode": self.read_mode,
            "repairs": self.repairs,
            "error": self.error,
        }


def roundtrip_fidelity(
    document: CliffDocument,
    format_id: str,
    *,
    arm: Arm | str = Arm.CONTEXT,
    read_mode: str = DEFAULT_READ_MODE,
) -> FidelityReport:
    """Render a document into a format, read it back, and count what survived.

    ``read_mode`` applies to the CLIFF read-back. It is a genuine control rather
    than a formality: this direction renders canonical CLIFF with cliff-python
    itself, so a tolerant read must find nothing to repair. A non-zero repair
    count here would mean the serializer emitted something its own parser needs
    help with, which is why the count is carried on the report.
    """
    report = FidelityReport(format_id=format_id, arm=str(Arm(arm).value), ok=False)
    report.read_mode = read_mode
    try:
        text = render(document, format_id, arm=arm, blank=False)
    except Exception as exc:  # noqa: BLE001 - unavailable formats are data too
        report.error = f"render failed: {type(exc).__name__}: {exc}"
        return report

    outcome = parse_back(text, format_id, read_mode=read_mode)
    report.repairs = outcome.repairs
    if outcome.document is None:
        report.error = outcome.error or "answer did not parse"
        return report

    report.ok = True
    original_entries = _effective(document)
    returned_entries = _effective(outcome.document)
    original_header = _header(document)
    returned_header = _header(outcome.document)

    for name in HEADER_FIELDS:
        value = original_header[name]
        if not value:
            continue
        report.facts_present += 1
        returned = returned_header.get(name, "")
        if returned == value:
            report.facts_kept += 1
        elif returned:
            report.changed_by_field[f"header.{name}"] = (
                report.changed_by_field.get(f"header.{name}", 0) + 1
            )
        else:
            report.lost_by_field[f"header.{name}"] = (
                report.lost_by_field.get(f"header.{name}", 0) + 1
            )

    for entry_id, fields in original_entries.items():
        returned_fields = returned_entries.get(entry_id, {})
        for name in ENTRY_FIELDS:
            value = fields.get(name, "")
            if not value:
                continue
            report.facts_present += 1
            returned = returned_fields.get(name, "")
            if returned == value:
                report.facts_kept += 1
            elif returned:
                key = f"entry.{name}"
                report.changed_by_field[key] = report.changed_by_field.get(key, 0) + 1
            else:
                key = f"entry.{name}"
                report.lost_by_field[key] = report.lost_by_field.get(key, 0) + 1
    return report
