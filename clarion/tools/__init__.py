"""Authoring tools that ship with CLARION."""

from __future__ import annotations

from .glossary import (
    Candidate,
    MergeReport,
    attach_dependency,
    bootstrap,
    build_glossary_document,
    extract_candidates,
    merge_glossary,
    propose_targets,
)

__all__ = [
    "Candidate",
    "MergeReport",
    "attach_dependency",
    "bootstrap",
    "build_glossary_document",
    "extract_candidates",
    "merge_glossary",
    "propose_targets",
]
