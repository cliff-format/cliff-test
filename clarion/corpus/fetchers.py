"""Recipe-driven import of external corpora.

Nothing is downloaded implicitly. A recipe records where a corpus lives, what
its licence is, whether it may be committed to this repository, and how to map
it onto the CLIF data model. The fetcher then produces a normal CLARION corpus
file plus a gold manifest carrying that provenance, so a licence fact is never
separated from the text it governs.

Tiers:
    vendor       permissive; may be committed after fetching, with attribution
    sharealike   CC-BY-SA; written to a segregated directory with its own LICENSE
    fetch-only   never committed; used locally or for metric calibration only
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..paths import CLIF_TEST_ROOT, DATASETS_ROOT, ensure_pyclif
from ..providers.base import Provider
from ..util import dump_json, load_json, sha256_text, short_hash, slug, utc_now, write_text
from .annotate import AnnotationConfig, AnnotationReport, annotate_document
from .enrich import EnrichmentPolicy, EnrichmentReport, enrich_document
from .licensing import spdx_header, tier_root, write_attribution, write_license_file

RECIPES_FILE = DATASETS_ROOT / "recipes" / "recipes.json"
SHAREALIKE_ROOT = DATASETS_ROOT / "cc-by-sa"
FETCH_CACHE = CLIF_TEST_ROOT / ".clarion-cache" / "fetch"


@dataclass
class Recipe:
    """How to obtain one external corpus and what may be done with it."""

    id: str
    title: str
    kind: str
    source: str
    license: str
    spdx: str
    tier: str
    languages: dict[str, str]
    strata: list[str] = field(default_factory=list)
    config: str | None = None
    split: str | None = None
    source_book: int | None = None
    target_book: int | None = None
    chapters: list[int] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)
    format: str | None = None
    context_origin: str = "derived"
    structure: str = "document"
    license_url: str = ""
    human_verified: bool = False
    origin: str = "public"
    notes: str = ""

    @property
    def redistributable(self) -> bool:
        """Whether the fetched text may be committed to this repository."""
        return self.tier == "vendor"

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Recipe:
        """Build a recipe from its manifest entry."""
        return Recipe(
            id=str(data["id"]),
            title=str(data.get("title", data["id"])),
            kind=str(data.get("kind", "http")),
            source=str(data.get("source", "")),
            license=str(data.get("license", "")),
            spdx=str(data.get("spdx", "NOASSERTION")),
            tier=str(data.get("tier", "fetch-only")),
            languages=dict(data.get("languages", {})),
            strata=[str(item) for item in data.get("strata", [])],
            config=data.get("config"),
            split=data.get("split"),
            source_book=data.get("source_book"),
            target_book=data.get("target_book"),
            chapters=[int(value) for value in data.get("chapters", [])],
            fields=dict(data.get("fields", {})),
            format=data.get("format"),
            context_origin=str(data.get("context_origin", "derived")),
            structure=str(data.get("structure", "document")),
            license_url=str(data.get("license_url", "")),
            human_verified=bool(data.get("human_verified", False)),
            origin=str(data.get("origin", "public")),
            notes=str(data.get("notes", "")),
        )


def load_recipes(path: Path | None = None) -> list[Recipe]:
    """Read every recipe."""
    data = load_json(path or RECIPES_FILE)
    return [Recipe.from_dict(item) for item in data.get("recipes", [])]


def get_recipe(recipe_id: str, path: Path | None = None) -> Recipe:
    """Look up one recipe by id."""
    for recipe in load_recipes(path):
        if recipe.id == recipe_id:
            return recipe
    raise KeyError(f"unknown recipe '{recipe_id}'")


def destination_for(recipe: Recipe, stratum: str) -> Path:
    """Where a fetched corpus is written, according to its licence tier.

    Permissive output joins the corpus tree, file-level copyleft (MPL) and
    ShareAlike output are segregated with their own LICENSE, and anything that
    may not be redistributed goes to the gitignored fetch cache.
    """
    root = tier_root(recipe.tier, recipe.spdx)
    if recipe.tier == "fetch-only":
        return root / recipe.id
    return root / stratum


@dataclass
class Pair:
    """One source/target segment with whatever context the source carried."""

    key: str
    source: str
    target: str
    context: str | None = None
    domain: str | None = None
    document: str | None = None
    reference: list[str] = field(default_factory=list)
    entry_type: str | None = None


HF_ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"
HF_PAGE = 100
# Public benchmarks plant canary rows to detect training-data contamination.
# They are not translations and must never enter a corpus.
CANARY_MARKERS = ("CANARY GUID", "canary")


def _hf_rows(recipe: Recipe, wanted: int) -> list[dict[str, Any]]:
    """Read rows through the HuggingFace datasets server (no heavy dependency)."""
    import httpx

    rows: list[dict[str, Any]] = []
    offset = 0
    with httpx.Client(timeout=60.0) as client:
        while len(rows) < wanted:
            response = client.get(
                HF_ROWS_ENDPOINT,
                params={
                    "dataset": recipe.source,
                    "config": recipe.config or "default",
                    "split": recipe.split or "train",
                    "offset": offset,
                    "length": min(HF_PAGE, wanted - len(rows) + HF_PAGE),
                },
            )
            response.raise_for_status()
            page = response.json().get("rows", [])
            if not page:
                break
            rows.extend(item["row"] for item in page)
            offset += len(page)
    return rows


def _rows_from_hf(recipe: Recipe, limit: int) -> list[Pair]:
    """Import a HuggingFace corpus, keeping documents whole and canaries out.

    Sampling is document-aware: a document-level corpus is only useful when the
    segments of a document stay together and in order, because that order is
    exactly the context the derivation step turns into a brief.
    """
    source_field = recipe.fields.get("source", "source")
    target_field = recipe.fields.get("target", "target")
    document_field = recipe.fields.get("document")
    domain_field = recipe.fields.get("domain")

    raw = _hf_rows(recipe, max(limit * 2, limit + HF_PAGE))
    clean: list[dict[str, Any]] = []
    for row in raw:
        source = str(row.get(source_field, "") or "")
        target = str(row.get(target_field, "") or "")
        if not source or not target:
            continue
        if row.get("is_bad_source"):
            continue
        labels = " ".join(
            str(row.get(field, "")) for field in (domain_field, document_field) if field
        )
        haystack = f"{source} {labels}"
        if any(marker in haystack for marker in CANARY_MARKERS):
            continue
        clean.append(row)

    def order(row: dict[str, Any]) -> tuple[str, int]:
        document = str(row.get(document_field, "")) if document_field else ""
        try:
            segment = int(row.get("segment_id", 0))
        except (TypeError, ValueError):
            segment = 0
        return (document, segment)

    clean.sort(key=order)
    pairs: list[Pair] = []
    seen_documents: set[str] = set()
    for row in clean:
        document = str(row.get(document_field, "")) if document_field else "imported"
        if len(pairs) >= limit and document not in seen_documents:
            break  # stop on a document boundary, never mid-document
        seen_documents.add(document)
        pairs.append(
            Pair(
                key=f"{slug(document, fallback='doc')}-{row.get('segment_id', len(pairs) + 1)}",
                source=str(row.get(source_field, "")),
                target=str(row.get(target_field, "")),
                document=document,
                domain=str(row.get(domain_field)) if domain_field else None,
            )
        )
    return pairs


def _rows_from_gutenberg(recipe: Recipe, limit: int, aligner: Provider) -> list[Pair]:
    """Align a public-domain Chinese book with its public-domain translation."""
    from .gutenberg import align_chapter, download, split_chapters, strip_boilerplate

    if recipe.source_book is None or recipe.target_book is None:
        raise RuntimeError(f"recipe '{recipe.id}' needs source_book and target_book")
    source_language = recipe.languages.get("source", "zh-CN")
    target_language = recipe.languages.get("target", "en-US")
    source_text = strip_boilerplate(download(recipe.source_book))
    target_text = strip_boilerplate(download(recipe.target_book))
    source_chapters = split_chapters(source_text, language=source_language)
    target_chapters = split_chapters(target_text, language=target_language)

    wanted = recipe.chapters or [1]
    pairs: list[Pair] = []
    for chapter_number in wanted:
        index = chapter_number - 1
        if index >= len(source_chapters) or index >= len(target_chapters):
            continue
        source_chapter = source_chapters[index]
        target_chapter = target_chapters[index]
        aligned, report = align_chapter(
            source_chapter.paragraphs, target_chapter.paragraphs, aligner
        )
        document = slug(f"chapter-{chapter_number}", fallback="chapter")
        for order, (source_index, target_index) in enumerate(aligned, start=1):
            if len(pairs) >= limit:
                break
            pairs.append(
                Pair(
                    key=f"{document}-{order:03d}",
                    source=source_chapter.paragraphs[source_index],
                    target=target_chapter.paragraphs[target_index],
                    document=document,
                    context=(
                        f"{source_chapter.title} / {target_chapter.title}. "
                        f"Paragraph {order} of the chapter, aligned by index and verified "
                        f"({report.accepted} of {report.proposed} proposals accepted)."
                    ),
                )
            )
    return pairs


def _catalogue_group(path: str, references: list[str]) -> str:
    """Group a catalogue string by the subsystem its source reference names.

    'editor/scene/gui/theme_editor_plugin.cpp' becomes 'editor.scene', which is
    real, upstream-supplied information about where the string lives - far more
    useful to a translator than one flat bucket.
    """
    if path and path != "imported":
        return path
    if not references:
        return "imported"
    parts = [segment for segment in references[0].split(":")[0].split("/") if segment]
    if not parts:
        return "imported"
    head = parts[:2] if len(parts) > 2 else parts[:1]
    return ".".join(slug(segment, fallback="group") for segment in head) or "imported"


def _properties_to_document(text: str) -> Any:
    """Read a key = value properties catalogue (Unciv and similar)."""
    ensure_pyclif()
    from pyclif import ClifDocument, Entry, Group, Header

    document = ClifDocument(header=Header(namespace="properties", clan="imported"))
    group = Group(path="strings")
    document.groups.append(group)
    seen: set[str] = set()
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        source, separator, target = stripped.partition(" = ")
        if not separator:
            continue
        entry_id = slug(source, fallback="item")
        candidate, counter = entry_id, 2
        while candidate in seen:
            candidate, counter = f"{entry_id}-{counter}", counter + 1
        seen.add(candidate)
        group.entries.append(
            Entry(id=candidate, source=source, target=target or None, status="final")
        )
    return document


def _rows_from_http(recipe: Recipe, limit: int) -> list[Pair]:
    import httpx

    response = httpx.get(recipe.source, timeout=60.0, follow_redirects=True)
    response.raise_for_status()
    text = response.text
    ensure_pyclif()
    import pyclif

    if recipe.format == "po":
        document = pyclif.from_po(text)
    elif recipe.format == "fluent":
        document = pyclif.from_fluent(text)
    elif recipe.format == "properties":
        document = _properties_to_document(text)
    else:
        raise NotImplementedError(
            f"recipe '{recipe.id}' has format '{recipe.format}', which needs a manual importer; "
            "the downloaded text is cached for inspection"
        )
    catalogue = recipe.structure == "catalogue"
    pairs: list[Pair] = []
    for group in document.groups:
        for entry in group.entries:
            if len(pairs) >= limit:
                break
            source = entry.source or ""
            # A generated identifier such as 'entry-7' carries no information.
            # Prefer the upstream key, then a slug of the source text.
            key = entry.id
            if not key or key.startswith("entry-"):
                key = slug(source[:40], fallback="item")
            pairs.append(
                Pair(
                    key=key,
                    source=source,
                    target=entry.target or "",
                    context=entry.context or group.context,
                    document=_catalogue_group(group.path, entry.reference) if catalogue
                    else group.path,
                    reference=list(entry.reference),
                    # pyclif stamps an imported PO entry with a default type of
                    # 'sentence'; for a UI catalogue that is wrong, and the
                    # enrichment step assigns a better one from the structure.
                    entry_type=None if catalogue else (entry.type or group.type),
                )
            )
    return pairs


def pairs_to_document(
    pairs: list[Pair],
    *,
    recipe: Recipe,
    clan: str,
    entry_type: str | None = None,
) -> Any:
    """Build a CLIF document from fetched pairs."""
    ensure_pyclif()
    from pyclif import ClifDocument, Entry, Group, Header

    header = Header(
        namespace="clarion",
        clan=clan,
        source_language=recipe.languages.get("source", "en-US"),
        target_language=recipe.languages.get("target", "zh-CN"),
        title=recipe.title,
    )
    document = ClifDocument(header=header)
    groups: dict[str, Group] = {}
    seen: set[str] = set()
    for pair in pairs:
        path = slug(pair.domain or pair.document or "imported", fallback="group")
        group = groups.get(path)
        if group is None:
            # The group type is deliberately left unset when the upstream does
            # not state one: the enrichment step decides it from the corpus
            # structure, instead of silently stamping every string 'sentence'.
            group = Group(path=path, type=entry_type)
            groups[path] = group
            document.groups.append(group)
        entry_id = slug(pair.key, fallback="item")
        candidate = entry_id
        counter = 2
        while candidate in seen:
            candidate = f"{entry_id}-{counter}"
            counter += 1
        seen.add(candidate)
        group.entries.append(
            Entry(
                id=candidate,
                source=pair.source,
                target=pair.target or None,
                type=pair.entry_type,
                status="final" if pair.target else "initial",
                context=pair.context,
                reference=list(pair.reference),
            )
        )
    return document


def gold_for(
    document: Any,
    recipe: Recipe,
    clif_name: str,
    stratum: str,
    *,
    context_origin: str,
    annotator: str = "",
    revision: str = "",
    fingerprint_value: str = "",
) -> dict[str, Any]:
    """Build the gold manifest that records where every item came from.

    The reference translation of an imported corpus is the upstream human
    translation, so it is recorded per item together with a checksum of the
    source and the reference. The checksums make an imported corpus verifiable
    against its upstream without republishing anything extra.
    """
    provenance = {
        "source": recipe.title,
        "url": recipe.source,
        "license": recipe.license,
        "spdx": recipe.spdx,
        "license_url": recipe.license_url,
        "redistributable": recipe.redistributable,
        "human_verified": recipe.human_verified,
        "verifier": "upstream project",
        "retrieved": utc_now(),
        "origin": recipe.origin,
        "context_origin": context_origin,
        "annotator": annotator,
        "upstream_revision": revision,
        "fingerprint": fingerprint_value,
        "notes": f"Fetched by CLARION recipe '{recipe.id}' (tier {recipe.tier}).",
    }
    items: dict[str, Any] = {}
    for group in document.groups:
        for entry in group.entries:
            items[entry.id] = {
                "reference": entry.target or "",
                "difficulty": "normal",
                "tags": [stratum, f"context-{context_origin}"],
                "rules": [],
                "provenance": {
                    **provenance,
                    "source_sha256": sha256_text(entry.source or ""),
                    "reference_sha256": sha256_text(entry.target or ""),
                },
            }
    return {
        "file": clif_name,
        "stratum": stratum,
        "notes": recipe.notes,
        "provenance": provenance,
        "items": items,
    }


@dataclass
class FetchResult:
    """What a fetch produced."""

    recipe_id: str
    clif_path: Path
    gold_path: Path
    entries: int
    tier: str
    committed: bool
    context_origin: str = "derived"
    cached: bool = False
    enrichment: EnrichmentReport | None = None
    annotation: AnnotationReport | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "recipe": self.recipe_id,
            "clif": str(self.clif_path),
            "gold": str(self.gold_path),
            "entries": self.entries,
            "tier": self.tier,
            "committed": self.committed,
            "context_origin": self.context_origin,
            "cached": self.cached,
            "enrichment": self.enrichment.as_dict() if self.enrichment else None,
            "annotation": self.annotation.as_dict() if self.annotation else None,
        }


def build_corpus_file(
    pairs: list[Pair],
    recipe: Recipe,
    *,
    stratum: str,
    annotator: Provider | None = None,
    annotation_config: AnnotationConfig | None = None,
    policy: EnrichmentPolicy | None = None,
    revision: str = "",
    fingerprint_value: str = "",
) -> FetchResult:
    """Turn imported pairs into a context-carrying, publishable corpus file.

    This is where an ordinary machine-translation corpus becomes a CLARION
    corpus: pairs to CLIF, deterministic enrichment, an optional annotation
    pass, then the licence header, the gold manifest with checksums and the
    attribution file that make the result publishable.
    """
    ensure_pyclif()
    import pyclif

    if not pairs:
        raise RuntimeError(
            f"recipe '{recipe.id}' produced no usable segments; nothing was written. "
            "For an aligned literary pair this usually means the chapter split or the "
            "alignment verification rejected everything."
        )
    clan = recipe.id
    document = pairs_to_document(pairs, recipe=recipe, clan=clan)

    # Order matters. The annotation pass runs FIRST, on the raw import, so the
    # model writes the brief where the corpus is silent. Deterministic
    # enrichment runs afterwards and fills only what is still empty - if it ran
    # first it would occupy every slot with derived filler and the annotator
    # would have nothing to do.
    annotation: AnnotationReport | None = None
    annotator_name = ""
    working = document
    if annotator is not None:
        references = {
            entry.id: entry.target or ""
            for group in document.groups
            for entry in group.entries
        }
        working, annotation = annotate_document(
            document,
            annotator,
            target_language=document.header.target_language,
            config=annotation_config or AnnotationConfig(),
            references=references,
        )

    enriched, enrichment = enrich_document(
        working,
        policy=policy or EnrichmentPolicy(structure=recipe.structure),
        source_title=recipe.title,
    )
    context_origin = enrichment.context_origin
    if annotation is not None and (annotation.annotated or annotation.wrote_family_brief):
        context_origin = "annotated"
        annotator_name = annotation.model

    directory = destination_for(recipe, stratum)
    directory.mkdir(parents=True, exist_ok=True)
    clif_path = directory / f"{clan}.{enriched.header.target_language}.clif"
    gold_path = directory / f"{clan}.gold.json"

    header = spdx_header(
        title=recipe.title,
        url=recipe.source,
        license_name=recipe.license,
        spdx=recipe.spdx,
        revision=revision,
        context_origin=context_origin,
    )
    write_text(clif_path, header + pyclif.serialize(enriched))
    dump_json(
        gold_path,
        gold_for(
            enriched,
            recipe,
            clif_path.name,
            stratum,
            context_origin=context_origin,
            annotator=annotator_name,
            revision=revision,
            fingerprint_value=fingerprint_value,
        ),
    )

    if recipe.tier != "fetch-only":
        write_attribution(
            directory,
            [
                {
                    "file": clif_path.name,
                    "title": recipe.title,
                    "url": recipe.source,
                    "license": recipe.license,
                    "revision": revision,
                    "retrieved": utc_now(),
                }
            ],
        )
    if recipe.tier == "sharealike" or recipe.spdx == "MPL-2.0":
        write_license_file(
            directory.parent,
            title=recipe.title,
            url=recipe.source,
            license_name=recipe.license,
            spdx=recipe.spdx,
        )

    return FetchResult(
        recipe_id=recipe.id,
        clif_path=clif_path,
        gold_path=gold_path,
        entries=sum(len(group.entries) for group in enriched.groups),
        tier=recipe.tier,
        committed=recipe.redistributable,
        context_origin=context_origin,
        enrichment=enrichment,
        annotation=annotation,
    )


def fingerprint(recipe: Recipe, *, limit: int, annotate: bool, revision: str) -> str:
    """Stable identity of one import, used to skip work that is already done."""
    payload = "|".join(
        [
            recipe.id,
            recipe.source,
            recipe.config or "",
            recipe.split or "",
            recipe.structure,
            str(limit),
            str(annotate),
            revision,
        ]
    )
    return short_hash(payload, 16)


def cached_result(recipe: Recipe, stratum: str, expected: str) -> FetchResult | None:
    """Return the already-processed import when its fingerprint still matches."""
    directory = destination_for(recipe, stratum)
    clif_path = directory / f"{recipe.id}.{recipe.languages.get('target', 'zh-CN')}.clif"
    gold_path = directory / f"{recipe.id}.gold.json"
    if not clif_path.exists() or not gold_path.exists():
        return None
    data = load_json(gold_path)
    provenance = data.get("provenance") or {}
    if provenance.get("fingerprint") != expected:
        return None
    return FetchResult(
        recipe_id=recipe.id,
        clif_path=clif_path,
        gold_path=gold_path,
        entries=len(data.get("items") or {}),
        tier=recipe.tier,
        committed=recipe.redistributable,
        context_origin=str(provenance.get("context_origin", "derived")),
        cached=True,
    )


def fetch(
    recipe_id: str,
    *,
    stratum: str | None = None,
    limit: int = 200,
    annotator: Provider | None = None,
    annotation_config: AnnotationConfig | None = None,
    revision: str = "",
    force: bool = False,
) -> FetchResult:
    """Fetch one recipe and write it as a CLARION corpus file.

    A completed import is cached: downloading and briefing the same corpus twice
    costs money and time and produces the same file, so the fingerprint of the
    recipe, its limit and its annotation setting is stored in the gold manifest
    and reused until one of them changes or force=True is passed.
    """
    recipe = get_recipe(recipe_id)
    target_stratum = stratum or (recipe.strata[0] if recipe.strata else "external")
    expected = fingerprint(recipe, limit=limit, annotate=annotator is not None, revision=revision)
    if not force:
        cached = cached_result(recipe, target_stratum, expected)
        if cached is not None:
            return cached
    if recipe.kind == "hf":
        pairs = _rows_from_hf(recipe, limit)
    elif recipe.kind == "http":
        pairs = _rows_from_http(recipe, limit)
    elif recipe.kind == "gutenberg-pair":
        if annotator is None:
            raise RuntimeError(
                f"recipe '{recipe.id}' aligns two public-domain books and needs a model for "
                "the alignment pass: run it with --annotate"
            )
        pairs = _rows_from_gutenberg(recipe, limit, annotator)
    else:
        raise NotImplementedError(f"recipe kind '{recipe.kind}' is not supported")
    return build_corpus_file(
        pairs,
        recipe,
        stratum=target_stratum,
        annotator=annotator,
        annotation_config=annotation_config,
        revision=revision,
        fingerprint_value=expected,
    )
