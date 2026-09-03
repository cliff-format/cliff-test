"""Loading CLARION-Core from disk.

A stratum directory holds CLIF documents whose targets are human reference
translations, an optional CLIF glossary, and one gold manifest per document.
Loading validates nothing on purpose - validation is a test, not a side effect
of reading - but the corpus self-check command runs the official validator over
every file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..metrics.instruction import Rule
from ..paths import CORE_CORPUS_ROOT, DATASETS_ROOT, ensure_clif_format
from ..util import load_json, read_text
from .model import Corpus, CorpusFile, ItemGold, Provenance

GOLD_SUFFIX = ".gold.json"
MANIFEST_NAME = "manifest.json"


def _gold_path(clif_path: Path) -> Path:
    """Gold manifest beside a corpus file: ui-news.zh-CN.clif -> ui-news.gold.json."""
    return clif_path.parent / (clif_path.name.split(".")[0] + GOLD_SUFFIX)


def parse_gold(data: dict[str, Any]) -> dict[str, ItemGold]:
    """Read the items block of a gold manifest."""
    raw_provenance = data.get("provenance")
    default_provenance = (
        Provenance.from_dict(raw_provenance) if isinstance(raw_provenance, dict) else None
    )
    items: dict[str, ItemGold] = {}
    for entry_id, payload in (data.get("items") or {}).items():
        if not isinstance(payload, dict):
            continue
        provenance = (
            Provenance.from_dict(payload["provenance"])
            if isinstance(payload.get("provenance"), dict)
            else default_provenance
        )
        raw_rules = payload.get("rules", [])
        rules = [Rule.from_dict(rule) for rule in raw_rules if isinstance(rule, dict)]
        items[entry_id] = ItemGold(
            entry=entry_id,
            reference=str(payload.get("reference", "")),
            alternatives=[str(value) for value in payload.get("alternatives", [])],
            rules=rules,
            provenance=provenance,
            difficulty=str(payload.get("difficulty", "normal")),
            tags=[str(tag) for tag in payload.get("tags", [])],
        )
    return items


def load_corpus_file(
    clif_path: Path,
    *,
    stratum: str,
    glossary_path: Path | None = None,
) -> CorpusFile:
    """Load one corpus document and its gold manifest."""
    ensure_clif_format()
    import clif_format

    document = clif_format.load(clif_path)
    gold_path = _gold_path(clif_path)
    gold: dict[str, ItemGold] = {}
    provenance: Provenance | None = None
    notes = ""
    if gold_path.exists():
        data = load_json(gold_path)
        gold = parse_gold(data)
        if isinstance(data.get("provenance"), dict):
            provenance = Provenance.from_dict(data["provenance"])
        notes = str(data.get("notes", ""))

    glossary_document = None
    if glossary_path is not None and glossary_path.exists():
        glossary_document = clif_format.load(glossary_path)

    return CorpusFile(
        id=clif_path.name.split(".")[0],
        stratum=stratum,
        path=clif_path,
        source_language=document.header.source_language,
        target_language=document.header.target_language,
        document=document,
        gold=gold,
        glossary_path=glossary_path,
        glossary_document=glossary_document,
        provenance=provenance,
        notes=notes,
    )


def _is_glossary(path: Path) -> bool:
    """A glossary declares itself in the header, so the file name is free."""
    for line in read_text(path).split("\n")[:20]:
        stripped = line.strip()
        if stripped.startswith("variant"):
            _, _, value = stripped.partition(":")
            if not value:
                _, _, value = stripped.partition("=")
            return value.strip().strip('"') == "glossary"
        if stripped.startswith("["):
            break
    return False


def _stratum_files(directory: Path) -> tuple[list[Path], Path | None]:
    documents: list[Path] = []
    glossary: Path | None = None
    for path in sorted(directory.glob("*.clif")):
        if _is_glossary(path):
            glossary = path
        else:
            documents.append(path)
    return documents, glossary


def load_corpus(
    name: str = "clarion-core",
    *,
    root: Path | None = None,
    strata: list[str] | None = None,
) -> Corpus:
    """Load a corpus by name from the datasets directory."""
    base = root or (CORE_CORPUS_ROOT if name == "clarion-core" else DATASETS_ROOT / name)
    if not base.exists():
        raise FileNotFoundError(f"corpus '{name}' not found at {base}")

    manifest: dict[str, Any] = {}
    manifest_path = base / MANIFEST_NAME
    if manifest_path.exists():
        manifest = load_json(manifest_path)

    declared = [str(item["id"]) for item in manifest.get("strata", []) if isinstance(item, dict)]
    directories = declared or sorted(
        child.name for child in base.iterdir() if child.is_dir() and not child.name.startswith(".")
    )

    wanted = set(strata) if strata else None
    files: list[CorpusFile] = []
    for stratum in directories:
        if wanted and stratum not in wanted:
            continue
        directory = base / stratum
        if not directory.is_dir():
            continue
        documents, glossary = _stratum_files(directory)
        for path in documents:
            files.append(load_corpus_file(path, stratum=stratum, glossary_path=glossary))

    return Corpus(
        name=str(manifest.get("name", name)),
        version=str(manifest.get("version", "0.0.0")),
        files=files,
        license_note=str(manifest.get("license_note", "")),
    )
