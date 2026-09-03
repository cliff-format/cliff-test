"""Importing an external corpus: context enrichment and licence compliance.

An established machine-translation corpus is a list of sentence pairs with no
translator brief at all. These tests pin the two things that have to be true
before such a corpus may enter CLARION and be published from it: the context
has to be created deterministically from what the corpus already contains, and
the result has to carry its licence with it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clarion.corpus.enrich import EnrichmentPolicy, enrich_document, has_native_context
from clarion.corpus.fetchers import Pair, Recipe, build_corpus_file, pairs_to_document
from clarion.corpus.licensing import license_check, spdx_header, tier_root
from clarion.paths import ensure_clif_format

ensure_clif_format()

FLAT_RECIPE = Recipe(
    id="test-flat",
    title="Test flat corpus",
    kind="hf",
    source="example/flat",
    license="Apache-2.0",
    spdx="Apache-2.0",
    tier="vendor",
    languages={"source": "en-US", "target": "zh-CN"},
    strata=["news"],
)

PAIRS = [
    Pair(key="s1", source="The ferry service resumed at dawn.", target="轮渡在黎明恢复运营。",
         domain="news", document="doc-1"),
    Pair(key="s2", source="Officials said the repairs cost 4 million euros.",
         target="官员表示,维修费用为 400 万欧元。", domain="news", document="doc-1"),
    Pair(key="s3", source="{count, plural, other {# passengers waited}}",
         target="{count, plural, other {# 名乘客等候}}", domain="news", document="doc-1"),
]


def test_flat_pairs_have_no_context_before_enrichment() -> None:
    document = pairs_to_document(PAIRS, recipe=FLAT_RECIPE, clan="test-flat")
    assert not has_native_context(document), "a sentence-pair corpus carries no brief"


def test_enrichment_creates_context_deterministically() -> None:
    document = pairs_to_document(PAIRS, recipe=FLAT_RECIPE, clan="test-flat")
    first, report = enrich_document(document, source_title=FLAT_RECIPE.title)
    second, _ = enrich_document(document, source_title=FLAT_RECIPE.title)

    assert report.context_origin == "derived"
    assert report.group_context == 1
    assert report.entry_context == 3
    assert report.icu_detected == 1

    group = first.groups[0]
    assert group.context and "segments in their original order" in group.context
    assert group.type, "an imported group must resolve to a content type"
    middle = group.entries[1]
    assert "Preceding segment" in (middle.context or "")
    assert "Following segment" in (middle.context or "")
    icu_entry = group.entries[2]
    assert "placeholder" in (icu_entry.context or "").lower()

    # Deterministic: the same input must produce byte-identical context.
    import clif_format

    assert clif_format.serialize(first) == clif_format.serialize(second)


def test_enrichment_never_overwrites_upstream_context() -> None:
    document = pairs_to_document(
        [Pair(key="s1", source="Save", target="保存", context="Toolbar button, 6 cells maximum.")],
        recipe=FLAT_RECIPE,
        clan="test-flat",
    )
    assert has_native_context(document)
    enriched, report = enrich_document(document)
    assert report.context_origin == "native"
    entry = enriched.groups[0].entries[0]
    assert entry.context is not None
    assert entry.context.startswith("Toolbar button, 6 cells maximum.")


def test_policy_can_disable_derivation() -> None:
    document = pairs_to_document(PAIRS, recipe=FLAT_RECIPE, clan="test-flat")
    policy = EnrichmentPolicy(domain_context=False, neighbour_context=False, detect_icu=False)
    enriched, report = enrich_document(document, policy=policy)
    assert report.entry_context == 0
    assert enriched.groups[0].context is None


CATALOGUE_RECIPE = Recipe(
    id="test-catalogue",
    title="Test string catalogue",
    kind="http",
    source="https://example.org/strings.po",
    license="MIT",
    spdx="MIT",
    tier="vendor",
    languages={"source": "en-US", "target": "zh-CN"},
    strata=["ui"],
    context_origin="native",
    structure="catalogue",
)


def test_catalogue_derivation_does_not_invent_reading_order() -> None:
    """A neighbouring UI key is not context, so it must not be written as one."""
    pairs = [
        Pair(key="export-all", source="Export All", target="全部导出",
             context="Button in the export dialog.", document="export",
             reference=["editor/export_dialog.cpp:142"]),
        Pair(key="empty", source="Nothing here yet", target="这里还没有内容",
             context="Shown when a project has no scenes yet.", document="export"),
    ]
    document = pairs_to_document(pairs, recipe=CATALOGUE_RECIPE, clan="test-catalogue")
    enriched, report = enrich_document(
        document,
        policy=EnrichmentPolicy(structure="catalogue"),
        source_title=CATALOGUE_RECIPE.title,
    )
    assert report.context_origin == "native"
    assert report.entry_context == 0, "catalogue entries must not get neighbour context"
    group = enriched.groups[0]
    assert "string catalogue" in (group.context or "")
    assert group.type == "label", "a catalogue defaults to labels, not sentences"
    first = group.entries[0]
    assert first.context == "Button in the export dialog.", "upstream comment kept verbatim"
    assert first.reference == ["editor/export_dialog.cpp:142"], "upstream source reference kept"


def test_document_and_catalogue_derivations_differ() -> None:
    pairs = [
        Pair(key="a", source="First sentence.", target="第一句。", document="doc-1"),
        Pair(key="b", source="Second sentence.", target="第二句。", document="doc-1"),
    ]
    as_document, doc_report = enrich_document(
        pairs_to_document(pairs, recipe=FLAT_RECIPE, clan="d"),
        policy=EnrichmentPolicy(structure="document"),
    )
    as_catalogue, cat_report = enrich_document(
        pairs_to_document(pairs, recipe=CATALOGUE_RECIPE, clan="c"),
        policy=EnrichmentPolicy(structure="catalogue"),
    )
    assert doc_report.entry_context == 2
    assert cat_report.entry_context == 0
    assert "continuous document" in (as_document.groups[0].context or "")
    assert "independently" in (as_catalogue.groups[0].context or "")


def test_tier_routing_keeps_licences_apart() -> None:
    assert tier_root("vendor", "Apache-2.0").name == "clarion-core"
    assert tier_root("vendor", "MPL-2.0").name == "mpl-2.0"
    assert tier_root("sharealike", "CC-BY-SA-4.0").name == "cc-by-sa"
    assert "clarion-core" not in str(tier_root("fetch-only", "NOASSERTION"))


def test_spdx_header_is_a_clif_comment_block() -> None:
    header = spdx_header(
        title="Test flat corpus",
        url="https://example.org",
        license_name="Apache-2.0",
        spdx="Apache-2.0",
        revision="abc123",
        context_origin="derived",
    )
    assert all(line.startswith("#") for line in header.strip().split("\n"))
    assert "SPDX-License-Identifier: Apache-2.0" in header
    assert "abc123" in header


def test_imported_file_is_publishable(tmp_path_factory: pytest.TempPathFactory) -> None:
    import clif_format

    from clarion.corpus import licensing

    sandbox = Path(__file__).resolve().parent / "_import_sandbox"
    original_core = licensing.CORE_ROOT
    licensing.CORE_ROOT = sandbox
    try:
        result = build_corpus_file(PAIRS, FLAT_RECIPE, stratum="news", revision="v1.2.3")
        text = result.clif_path.read_text(encoding="utf-8")
        assert text.startswith("# CLARION imported corpus file.")
        assert "SPDX-License-Identifier: Apache-2.0" in text
        assert (result.clif_path.parent / "ATTRIBUTION.md").exists()
        assert result.context_origin == "derived"
        assert result.entries == 3

        issues = [
            issue
            for issue in clif_format.validate(text)
            if issue.category not in {"warning", "extension"}
        ]
        assert not issues, issues

        gold = result.gold_path.read_text(encoding="utf-8")
        assert "source_sha256" in gold
        assert "upstream_revision" in gold
        assert "v1.2.3" in gold

        problems = license_check(sandbox.parent)
        assert not [p for p in problems if "_import_sandbox" in p.path], problems
    finally:
        licensing.CORE_ROOT = original_core


def test_shipped_corpus_is_licence_compliant() -> None:
    problems = license_check()
    assert not problems, [problem.as_dict() for problem in problems]
