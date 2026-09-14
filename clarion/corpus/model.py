"""The CLARION-Core data model.

A corpus file is a normal, specification-valid CLIFF document whose targets are
the human reference translations. The task document handed to a model is that
file with the targets blanked, so the corpus and the gold can never drift
apart.

Everything a benchmark must be able to answer about an item - where the text
came from, under which licence, whether a human verified the reference, which
instructions must be obeyed, and whether the text predates the model's training
data - lives in a sidecar gold manifest next to the CLIFF file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..metrics.instruction import Rule


@dataclass(frozen=True)
class Provenance:
    """Where one item came from and what may be done with it.

    context_origin is the field that keeps this benchmark honest. An external
    machine-translation corpus is a list of sentence pairs: it carries no
    translator context at all, and CLARION exists to measure what context is
    worth. Every item therefore records where its context came from:

    native      the upstream project wrote it (translator comments, msgctxt,
                intents, source references) - the strongest material
    derived     computed deterministically from upstream metadata (document
                grouping, domain labels, neighbouring segments) - no invention
    annotated   written by a model in a separate annotation pass, never by the
                system under test, and pending human review
    original    written by hand for CLARION together with the text itself
    none        the item has no context and may only be used in the plain arm
    """

    source: str
    url: str = ""
    license: str = ""
    license_url: str = ""
    redistributable: bool = True
    human_verified: bool = False
    verifier: str = ""
    retrieved: str = ""
    origin: str = "public"
    context_origin: str = "original"
    annotator: str = ""
    upstream_revision: str = ""
    source_sha256: str = ""
    reference_sha256: str = ""
    notes: str = ""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Provenance:
        """Build provenance from its manifest representation."""
        return Provenance(
            source=str(data.get("source", "unknown")),
            url=str(data.get("url", "")),
            license=str(data.get("license", "")),
            license_url=str(data.get("license_url", "")),
            redistributable=bool(data.get("redistributable", True)),
            human_verified=bool(data.get("human_verified", False)),
            verifier=str(data.get("verifier", "")),
            retrieved=str(data.get("retrieved", "")),
            origin=str(data.get("origin", "public")),
            context_origin=str(data.get("context_origin", "original")),
            annotator=str(data.get("annotator", "")),
            upstream_revision=str(data.get("upstream_revision", "")),
            source_sha256=str(data.get("source_sha256", "")),
            reference_sha256=str(data.get("reference_sha256", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class ItemGold:
    """Reference translation and obligations for one entry."""

    entry: str
    reference: str
    alternatives: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    provenance: Provenance | None = None
    difficulty: str = "normal"
    tags: list[str] = field(default_factory=list)

    @property
    def references(self) -> list[str]:
        """Every acceptable reference translation."""
        return [self.reference, *self.alternatives] if self.reference else list(self.alternatives)


@dataclass
class CorpusFile:
    """One corpus document plus its gold manifest."""

    id: str
    stratum: str
    path: Path
    source_language: str
    target_language: str
    document: Any
    gold: dict[str, ItemGold] = field(default_factory=dict)
    glossary_path: Path | None = None
    glossary_document: Any = None
    provenance: Provenance | None = None
    notes: str = ""

    @property
    def entry_count(self) -> int:
        """Number of translation entries in the file."""
        return sum(len(group.entries) for group in self.document.groups)

    def sources(self) -> dict[str, str]:
        """Entry id to source text."""
        table: dict[str, str] = {}
        for group in self.document.groups:
            for entry in group.entries:
                table[entry.id] = entry.source or ""
        return table

    def references(self) -> dict[str, str]:
        """Entry id to the primary human reference translation."""
        table: dict[str, str] = {}
        for group in self.document.groups:
            for entry in group.entries:
                gold = self.gold.get(entry.id)
                fallback = entry.target or ""
                reference = gold.reference if gold and gold.reference else fallback
                if reference:
                    table[entry.id] = reference
        return table

    def widths(self) -> dict[str, int]:
        """Entry id to effective max-width, where one is declared."""
        from ..paths import ensure_cliff_format

        ensure_cliff_format()
        from cliff_format import effective_max_width

        table: dict[str, int] = {}
        for group in self.document.groups:
            for entry in group.entries:
                width = effective_max_width(entry, group)
                if width is not None:
                    table[entry.id] = width
        return table

    def rules(self) -> list[Rule]:
        """Every instruction-following rule declared for this file."""
        collected: list[Rule] = []
        for entry_id, gold in self.gold.items():
            for rule in gold.rules:
                collected.append(
                    rule if rule.entry else Rule(
                        id=rule.id,
                        kind=rule.kind,
                        params=rule.params,
                        entry=entry_id,
                        severity=rule.severity,
                        description=rule.description,
                    )
                )
        return collected


@dataclass
class Corpus:
    """A loaded corpus: several files across several strata."""

    name: str
    version: str
    files: list[CorpusFile] = field(default_factory=list)
    license_note: str = ""

    def strata(self) -> list[str]:
        """Distinct strata in load order."""
        seen: list[str] = []
        for item in self.files:
            if item.stratum not in seen:
                seen.append(item.stratum)
        return seen

    def entry_count(self) -> int:
        """Total number of entries across all files."""
        return sum(item.entry_count for item in self.files)

    def filter(self, strata: list[str] | None = None) -> Corpus:
        """A copy restricted to the named strata."""
        if not strata:
            return self
        wanted = set(strata)
        return Corpus(
            name=self.name,
            version=self.version,
            files=[item for item in self.files if item.stratum in wanted],
            license_note=self.license_note,
        )
