"""Turn an imported corpus into a context-carrying CLARION document.

The problem this module exists for: every established machine-translation
corpus is a list of sentence pairs. FLORES, WMT24++ and the rest were built to
measure a MODEL, so they carry no translator brief - no situation, no content
type, no tone, no width budget, no terminology. Dropping them into CLARION
unchanged would make the context arm identical to the plain arm and the
benchmark would measure nothing.

There are exactly three honest ways to give an imported corpus context, and
this module implements the first two:

native
    The upstream project already wrote it. gettext extracted comments (#.),
    source references (#:), msgctxt disambiguation, Fluent comment levels and
    MASSIVE intent labels are real, human-written translator context. Nothing
    is invented; the importer only maps it onto CLIF fields. This is the best
    material for the context arm and is preferred wherever it exists.

derived
    Computed deterministically from metadata the corpus already ships:
    document ids become groups, domain labels become group context, and
    neighbouring segments become the document context an entry sits in. No
    fact is created that the corpus did not already contain, so the result is
    reproducible byte for byte and is safe to publish.

annotated
    Written by a model in a separate pass (see clarion.corpus.annotate). It is
    opt-in, recorded per item, and never mixed silently into a native or
    derived corpus.

Whatever the origin, the context is generated ONCE into the CLIF document and
every other format is converted from that same document, so the choice can
never favour one format over another.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..paths import ensure_clif_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument

_ICU_RE = re.compile(r"\{[^{}]*,\s*(?:plural|select|selectordinal)\s*,")
_PLACEHOLDER_RE = re.compile(r"%\d*\$?[sdf@]|\{[A-Za-z0-9_]+\}")
_TERMINAL_PUNCTUATION = ".!?。！？…"

# Content types that a deterministic rule may assign. Anything subtler is a
# judgement call and belongs to the annotation pass or to a human.
CATALOGUE_DEFAULT_TYPE = "label"

DOMAIN_TYPES = {
    "ui": "label",
    "app": "label",
    "news": "sentence",
    "social": "sentence",
    "speech": "dialogue",
    "literary": "narration",
    "legal": "description",
    "canary": "sentence",
}


@dataclass
class EnrichmentPolicy:
    """What the deterministic enrichment is allowed to write.

    'structure' decides which derivation makes sense at all:

    document   continuous text - news reports, articles, literary passages.
               Neighbouring segments are genuine context and the group is a
               document that must read as one piece.
    catalogue  independent resource strings - a UI catalogue. Neighbouring
               keys are NOT context (a button next to a menu item tells a
               translator nothing), so neighbour derivation is switched off and
               the group context describes the resource instead.
    """

    structure: str = "document"
    group_by_document: bool = True
    domain_context: bool = True
    neighbour_context: bool = True
    neighbour_chars: int = 90
    detect_icu: bool = True
    default_type: str = "sentence"
    domain_types: dict[str, str] = field(default_factory=lambda: dict(DOMAIN_TYPES))
    family_info: str = ""
    family_standard: str = ""


@dataclass
class EnrichmentReport:
    """What enrichment actually wrote, for the dataset card."""

    entries: int = 0
    group_context: int = 0
    entry_context: int = 0
    types_assigned: int = 0
    icu_detected: int = 0
    context_origin: str = "derived"

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "entries": self.entries,
            "group_context": self.group_context,
            "entry_context": self.entry_context,
            "types_assigned": self.types_assigned,
            "icu_detected": self.icu_detected,
            "context_origin": self.context_origin,
        }


def _shorten(text: str, limit: int) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"


def has_native_context(document: ClifDocument) -> bool:
    """True when the imported document already carries upstream context."""
    for group in document.groups:
        if group.context:
            return True
        for entry in group.entries:
            if entry.context or entry.reference:
                return True
    return False


def enrich_document(
    document: ClifDocument,
    *,
    policy: EnrichmentPolicy | None = None,
    domain_labels: dict[str, str] | None = None,
    source_title: str = "",
) -> tuple[ClifDocument, EnrichmentReport]:
    """Add deterministic context to an imported document.

    Existing values are never overwritten: an upstream comment always wins over
    a derived sentence, which is why a native corpus keeps its native context
    and only the gaps are filled.
    """
    ensure_clif_format()
    policy = policy or EnrichmentPolicy()
    labels = domain_labels or {}
    enriched = copy.deepcopy(document)
    report = EnrichmentReport(
        context_origin="native" if has_native_context(document) else "derived"
    )

    # The provenance sentence is a fallback: it is only written when neither
    # the upstream nor the annotation pass supplied a family brief.
    if not enriched.header.info:
        enriched.header.info = policy.family_info or (
            f"Imported from {source_title}." if source_title else None
        )
    if not enriched.header.standard:
        enriched.header.standard = policy.family_standard or (
            "Reference translations are the upstream human translations; do not edit them."
        )

    for group in enriched.groups:
        entries = group.entries
        report.entries += len(entries)
        domain = labels.get(group.path, group.path)

        if policy.domain_context and not group.context:
            pieces = []
            if source_title:
                pieces.append(f"Imported from {source_title}.")
            if policy.structure == "catalogue":
                pieces.append(
                    f"Resource group '{domain}' of a string catalogue, {len(entries)} strings. "
                    "Each string is used independently in the interface; translate it on its "
                    "own and keep it short enough for its control."
                )
            else:
                pieces.append(
                    f"Document '{domain}', {len(entries)} segments in their original order; "
                    "translate them as one continuous document, not as isolated sentences."
                )
            group.context = " ".join(pieces)
            report.group_context += 1

        if not group.type and not all(entry.type for entry in entries):
            fallback = (
                CATALOGUE_DEFAULT_TYPE if policy.structure == "catalogue" else policy.default_type
            )
            group.type = policy.domain_types.get(domain, fallback)
            report.types_assigned += 1

        for index, entry in enumerate(entries):
            source = entry.source or ""
            if policy.detect_icu and (_ICU_RE.search(source) or _PLACEHOLDER_RE.search(source)):
                report.icu_detected += 1
                icu_note = (
                    "Contains message-format placeholders; keep every placeholder and "
                    "its syntax exactly as written and translate only the literal text."
                )
                entry.context = f"{entry.context} {icu_note}".strip() if entry.context else icu_note

            # A catalogue has no reading order, so the neighbouring key is not
            # context; deriving it anyway would be inventing a fact.
            if not policy.neighbour_context or policy.structure == "catalogue":
                continue
            neighbours: list[str] = []
            if index > 0 and entries[index - 1].source:
                previous = _shorten(entries[index - 1].source or "", policy.neighbour_chars)
                neighbours.append(f"Preceding segment: {previous}")
            if index + 1 < len(entries) and entries[index + 1].source:
                following = _shorten(entries[index + 1].source or "", policy.neighbour_chars)
                neighbours.append(f"Following segment: {following}")
            if neighbours:
                joined = " ".join(neighbours)
                entry.context = f"{entry.context} {joined}".strip() if entry.context else joined
                report.entry_context += 1

    return enriched, report


def looks_like_label(text: str) -> bool:
    """Heuristic used only for user-interface imports: short, no final stop."""
    stripped = text.strip()
    return bool(stripped) and len(stripped) <= 30 and stripped[-1] not in _TERMINAL_PUNCTUATION
