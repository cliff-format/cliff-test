"""CLARION-Core corpus model, loader, enrichment and licence plumbing."""

from __future__ import annotations

from .annotate import (
    AnnotationConfig,
    AnnotationReport,
    annotate_document,
    leaks_reference,
    review_rows,
    summarize_document,
)
from .enrich import EnrichmentPolicy, EnrichmentReport, enrich_document, has_native_context
from .licensing import ComplianceProblem, license_check, spdx_header, tier_root
from .model import Corpus, CorpusFile, ItemGold, Provenance
from .store import load_corpus, load_corpus_file, parse_gold

__all__ = [
    "AnnotationConfig",
    "AnnotationReport",
    "ComplianceProblem",
    "Corpus",
    "CorpusFile",
    "EnrichmentPolicy",
    "EnrichmentReport",
    "ItemGold",
    "Provenance",
    "annotate_document",
    "enrich_document",
    "has_native_context",
    "leaks_reference",
    "license_check",
    "load_corpus",
    "load_corpus_file",
    "parse_gold",
    "review_rows",
    "spdx_header",
    "summarize_document",
    "tier_root",
]
