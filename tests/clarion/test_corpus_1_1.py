"""The CLARION-Core corpus: declared version, canonical shape, provenance.

A benchmark corpus is evidence, so the properties the reports rely on are
asserted here rather than assumed:

* every document declares a version line the implementation actually supports,
  and every entry keeps the data the gold manifest says it has;
* the documents parse strictly, need no tolerant repair, and still carry the
  provenance digests their manifests recorded (so a data edit cannot quietly
  invalidate a licence or attribution claim);
* the gold manifests and the documents agree in both directions - no entry
  without a reference translation, no reference to an entry that is gone.

The 18 documents are deliberately *not* cliff-python's canonical output: the
authors order fields the way a translator reads them, keep long header values as
adjacent-string continuation lines, and keep the licence attribution block at the
top of imported files. That is why the shape is checked as "strictly valid and
repair-free" instead of "byte-identical to the serializer".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clarion.paths import CORE_CORPUS_ROOT, ensure_cliff_format

pytestmark = pytest.mark.skipif(
    not CORE_CORPUS_ROOT.is_dir(), reason="CLARION-Core is not checked out"
)

#: The documents that carry translatable items, as opposed to the per-stratum
#: `variant: glossary` term files the harness attaches in the context arm.
EXPECTED_DOCUMENTS = 16
EXPECTED_GLOSSARIES = 2
EXPECTED_ENTRIES = 392


def _documents() -> list[Path]:
    return sorted(CORE_CORPUS_ROOT.rglob("*.cliff"))


def _load(path: Path):
    ensure_cliff_format()
    import cliff_format

    return cliff_format.parse(path.read_text(encoding="utf-8"))


def test_corpus_has_the_documented_shape() -> None:
    """16 standard documents plus one glossary per stratum that needs one."""
    documents = _documents()
    standards, glossaries = [], []
    for path in documents:
        document = _load(path)
        target = glossaries if document.header.variant == "glossary" else standards
        target.append(path)
    assert len(standards) == EXPECTED_DOCUMENTS, [p.name for p in standards]
    assert len(glossaries) == EXPECTED_GLOSSARIES, [p.name for p in glossaries]
    entries = sum(
        len(group.entries) for path in standards for group in _load(path).groups
    )
    assert entries == EXPECTED_ENTRIES


@pytest.mark.parametrize("path", _documents(), ids=lambda path: path.name)
def test_dataset_document_declares_a_supported_version(path: Path) -> None:
    """The corpus follows the current specification, so it declares 1.1."""
    ensure_cliff_format()
    from cliff_format.parser import SUPPORTED_VERSIONS

    document = _load(path)
    assert document.spec_version == "1.1"
    assert document.spec_version in SUPPORTED_VERSIONS


@pytest.mark.parametrize("path", _documents(), ids=lambda path: path.name)
def test_dataset_document_is_strictly_valid_and_needs_no_repair(path: Path) -> None:
    """Two claims in one test, because a corpus that needs a repair is suspect.

    Validity is what the reports assume; a tolerant repair would mean the corpus
    is only readable because the reader is forgiving, which is a different
    (weaker) claim than "the corpus is specification-conformant".
    """
    ensure_cliff_format()
    import cliff_format

    text = path.read_text(encoding="utf-8")
    document = cliff_format.parse(text)
    errors = [
        issue
        for issue in cliff_format.validate_document(document)
        if issue.category not in cliff_format.ADVISORY_CATEGORIES
    ]
    assert not errors, [f"line {i.line}: {i.message}" for i in errors]
    _repaired, corrections = cliff_format.parse_tolerant(text)
    assert not corrections, [f"line {c.line}: {c.describe()}" for c in corrections]


def test_every_entry_keeps_its_recorded_provenance_digest() -> None:
    """The imported corpora store a SHA-256 of each source and reference string.

    The digests are what makes the licence and attribution claim checkable, so
    they are re-verified against the text the documents actually hold. The
    authored documents keep provenance at file level and are skipped.
    """
    ensure_cliff_format()
    from clarion.util import sha256_text

    checked = 0
    for path in _documents():
        gold_path = path.parent / (path.name.split(".")[0] + ".gold.json")
        if not gold_path.exists():
            continue
        document = _load(path)
        entries = {entry.id: entry for group in document.groups for entry in group.entries}
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        default = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
        for entry_id, item in (data.get("items") or {}).items():
            provenance = (
                item.get("provenance") if isinstance(item.get("provenance"), dict) else default
            )
            source_digest = str(provenance.get("source_sha256", ""))
            reference_digest = str(provenance.get("reference_sha256", ""))
            if not (source_digest or reference_digest):
                continue
            assert entry_id in entries, f"{path.name}: gold knows no entry '{entry_id}'"
            checked += 1
            if source_digest:
                assert source_digest == sha256_text(entries[entry_id].source or ""), entry_id
            if reference_digest:
                assert reference_digest == sha256_text(entries[entry_id].target or ""), entry_id
    assert checked >= 100, f"only {checked} digests were verifiable"


def test_gold_manifests_and_documents_agree() -> None:
    """No translatable entry without a reference, no reference to a lost entry."""
    for path in _documents():
        document = _load(path)
        if document.header.variant == "glossary":
            # A glossary is attached as context, not scored: its renderings are
            # the corpus's own terminology, so a per-entry gold item is optional.
            continue
        ids = {entry.id for group in document.groups for entry in group.entries}
        gold_path = path.parent / (path.name.split(".")[0] + ".gold.json")
        assert gold_path.exists(), f"{path.name} has no gold manifest"
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        items = data.get("items") or {}
        stray = sorted(set(items) - ids)
        assert not stray, f"{path.name}: gold references unknown entries {stray}"
        missing = sorted(ids - set(items))
        assert not missing, f"{path.name}: entries without a reference translation {missing}"
        for entry_id in ids:
            assert str(items[entry_id].get("reference", "")).strip(), (
                f"{path.name}: '{entry_id}' has an empty reference"
            )
