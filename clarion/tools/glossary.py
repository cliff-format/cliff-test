"""Automatic glossary bootstrap and maintenance for CLIF projects.

CLIF has a glossary variant, but a project only benefits from it if the
glossary exists. When a translator - human or model - receives a file with no
attached terminology, the right first move is to build one: pull the terms that
actually repeat or that carry naming decisions, propose canonical renderings
once, and reuse them everywhere.

This module does that deterministically:

1. mine term candidates from a CLIF document (typed terms, proper nouns,
   repeated phrases, brand-like tokens, short repeated UI labels);
2. write them into a CLIF glossary document (variant: glossary);
3. optionally ask a model for the canonical rendering of each new term, under
   the project de-jargon policy;
4. merge into an existing glossary without ever overwriting a reviewed or final
   term, reporting conflicts instead.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..metrics.terminology import JargonPolicy
from ..paths import ensure_pyclif
from ..providers.base import CompletionRequest, Message, Provider
from ..util import slug

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyclif import ClifDocument

TERM_TYPES = {"proper-noun", "fixed-phrase", "idiom", "noun-phrase"}
LOCKED_STATUSES = {"reviewed", "final"}
_BRAND_RE = re.compile(r"\b(?:[A-Z][a-z]+[A-Z][A-Za-z]*|[A-Z]{2,})\b")
_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
_CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]{2,6}")
_STOPWORDS = {
    "The", "A", "An", "This", "That", "These", "Those", "You", "Your", "We", "It",
    "If", "When", "Please", "Note", "New", "All", "And", "Or", "For", "To", "In",
    "On", "Of", "Is", "Are", "Was", "Were", "Be", "Not", "No", "Yes", "OK",
}


@dataclass
class Candidate:
    """A term worth pinning down before translation starts."""

    text: str
    kind: str
    count: int = 1
    entries: list[str] = field(default_factory=list)
    entry_type: str | None = None

    @property
    def id(self) -> str:
        """CLIF entry id for this term."""
        return slug(self.text, fallback="term")


def extract_candidates(
    document: ClifDocument,
    *,
    min_count: int = 2,
    max_terms: int = 60,
) -> list[Candidate]:
    """Mine glossary candidates from a CLIF document."""
    ensure_pyclif()
    typed: dict[str, Candidate] = {}
    phrases: Counter[str] = Counter()
    phrase_entries: dict[str, list[str]] = {}

    for group in document.groups:
        for entry in group.entries:
            source = (entry.source or "").strip()
            if not source:
                continue
            entry_type = entry.type or group.type
            if entry_type in TERM_TYPES:
                candidate = typed.setdefault(
                    source.lower(),
                    Candidate(text=source, kind="typed", entry_type=entry_type),
                )
                candidate.count += 1
                candidate.entries.append(entry.id)
                continue
            for match in set(_BRAND_RE.findall(source)):
                if match in _STOPWORDS:
                    continue
                phrases[match] += 1
                phrase_entries.setdefault(match, []).append(entry.id)
            for match in set(_CAPITALIZED_RE.findall(source)):
                if match in _STOPWORDS or len(match) < 3:
                    continue
                if source.startswith(match) and " " not in match:
                    continue  # sentence-initial word, not a name
                phrases[match] += 1
                phrase_entries.setdefault(match, []).append(entry.id)
            for match in set(_CJK_RUN_RE.findall(source)):
                phrases[match] += 1
                phrase_entries.setdefault(match, []).append(entry.id)
            if entry_type == "label" and len(source.split()) <= 3:
                phrases[source] += 1
                phrase_entries.setdefault(source, []).append(entry.id)

    candidates = list(typed.values())
    for text, count in phrases.most_common():
        if count < min_count:
            continue
        if text.lower() in typed:
            continue
        candidates.append(
            Candidate(text=text, kind="repeated", count=count, entries=phrase_entries.get(text, []))
        )
    candidates.sort(key=lambda item: (-item.count, item.text.lower()))
    return candidates[:max_terms]


def build_glossary_document(
    source_document: ClifDocument,
    candidates: list[Candidate],
    *,
    clan: str | None = None,
    targets: dict[str, str] | None = None,
) -> ClifDocument:
    """Create a CLIF glossary document for the mined candidates."""
    ensure_pyclif()
    from pyclif import ClifDocument, Entry, Group, Header

    header = Header(
        namespace=source_document.header.namespace or "project",
        clan=clan or f"{source_document.header.clan}-terms",
        source_language=source_document.header.source_language,
        target_language=source_document.header.target_language,
        variant="glossary",
        title="Auto-generated project glossary",
        standard=(
            "Canonical renderings for this project. Terms marked reviewed or final "
            "are locked and must be used exactly."
        ),
    )
    document = ClifDocument(header=header)
    group = Group(path="terms")
    document.groups.append(group)
    seen: set[str] = set()
    targets = targets or {}
    for candidate in candidates:
        entry_id = candidate.id
        if entry_id in seen:
            continue
        seen.add(entry_id)
        target = targets.get(candidate.text)
        default_type = "proper-noun" if candidate.kind == "repeated" else "noun-phrase"
        group.entries.append(
            Entry(
                id=entry_id,
                source=candidate.text,
                target=target,
                type=candidate.entry_type or default_type,
                status="translated" if target else "initial",
                context=(
                    f"Appears in {candidate.count} entries: "
                    f"{', '.join(candidate.entries[:5])}" if candidate.entries else None
                ),
            )
        )
    return document


PROPOSAL_SYSTEM = (
    "You are a terminology manager for a localization project. You choose one "
    "canonical rendering per term and you prefer the wording a normal reader of the "
    "target language would use over the wording found in old textbooks."
)


def propose_targets(
    provider: Provider,
    candidates: list[Candidate],
    *,
    source_language: str,
    target_language: str,
    policy: JargonPolicy | None = None,
    max_output_tokens: int = 2048,
) -> dict[str, str]:
    """Ask a model for canonical renderings of the mined terms."""
    if not candidates:
        return {}
    listing = "\n".join(f"- {candidate.text}" for candidate in candidates)
    policy_block = policy.prompt_fragment() if policy else ""
    user = (
        f"Propose the canonical {target_language} rendering of each {source_language} term.\n"
        "Answer with one line per term in the form: term => rendering\n"
        "Keep product names, trademarks and established Latin-script terms unchanged.\n"
        f"{policy_block}\n\nTerms:\n{listing}\n"
    )
    completion = provider.complete(
        CompletionRequest(
            messages=[Message("system", PROPOSAL_SYSTEM), Message("user", user)],
            temperature=0.0,
            max_output_tokens=max_output_tokens,
        )
    )
    proposals: dict[str, str] = {}
    if completion.error:
        return proposals
    for line in completion.text.split("\n"):
        if "=>" not in line:
            continue
        left, _, right = line.partition("=>")
        term = left.strip(" -*\t")
        rendering = right.strip()
        if term and rendering:
            proposals[term] = rendering
    return proposals


@dataclass
class MergeReport:
    """What changed when a mined glossary met an existing one."""

    added: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    conflicts: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {"added": self.added, "kept": self.kept, "conflicts": self.conflicts}


def merge_glossary(existing: ClifDocument, mined: ClifDocument) -> tuple[ClifDocument, MergeReport]:
    """Merge mined terms into an existing glossary without overwriting decisions."""
    ensure_pyclif()
    import copy

    merged = copy.deepcopy(existing)
    report = MergeReport()
    index = {
        entry.source: (group, entry)
        for group in merged.groups
        for entry in group.entries
        if entry.source
    }
    target_group = merged.groups[0] if merged.groups else None
    if target_group is None:
        from pyclif import Group

        target_group = Group(path="terms")
        merged.groups.append(target_group)

    for group in mined.groups:
        for entry in group.entries:
            found = index.get(entry.source or "")
            if found is None:
                target_group.entries.append(entry)
                report.added.append(entry.id)
                continue
            _, current = found
            report.kept.append(current.id)
            if (
                entry.target
                and current.target
                and entry.target != current.target
                and (current.status or "") in LOCKED_STATUSES
            ):
                report.conflicts.append(
                    {
                        "term": entry.source or "",
                        "locked": current.target,
                        "proposed": entry.target,
                        "status": current.status or "",
                    }
                )
    return merged, report


def attach_dependency(document: ClifDocument, glossary_path: str) -> ClifDocument:
    """Add the glossary to a document's dependency list, once."""
    import copy

    updated = copy.deepcopy(document)
    if glossary_path not in updated.header.dependency:
        updated.header.dependency = [*updated.header.dependency, glossary_path]
    return updated


def bootstrap(
    source_path: Path,
    *,
    glossary_path: Path | None = None,
    provider: Provider | None = None,
    policy: JargonPolicy | None = None,
    min_count: int = 2,
    max_terms: int = 60,
) -> tuple[ClifDocument, MergeReport, list[Candidate]]:
    """Mine, propose, merge and return the glossary for one CLIF file."""
    ensure_pyclif()
    import pyclif

    document = pyclif.load(source_path)
    candidates = extract_candidates(document, min_count=min_count, max_terms=max_terms)
    targets: dict[str, str] = {}
    if provider is not None:
        targets = propose_targets(
            provider,
            candidates,
            source_language=document.header.source_language,
            target_language=document.header.target_language,
            policy=policy,
        )
    mined = build_glossary_document(document, candidates, targets=targets)
    if glossary_path and Path(glossary_path).exists():
        existing = pyclif.load(glossary_path)
        merged, report = merge_glossary(existing, mined)
        return merged, report, candidates
    added = [entry.id for group in mined.groups for entry in group.entries]
    return mined, MergeReport(added=added), candidates
