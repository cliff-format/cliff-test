"""Format rendering, reading and validation for the CLARION benchmark."""

from __future__ import annotations

from .arms import Arm, blank_targets, ensure_required_fields, project, strip_context
from .parse import ParseOutcome, entry_index, extract_targets, parse_back, unwrap
from .plain import parse_json_plain, parse_yaml_plain, render_json_plain, render_yaml_plain
from .registry import DEFAULT_FORMATS, FORMATS, FormatSpec, format_ids, get_format
from .render import FormatUnavailableError, render, render_document
from .validity import Diagnostic, ValidityReport, check_validity

__all__ = [
    "DEFAULT_FORMATS",
    "FORMATS",
    "Arm",
    "Diagnostic",
    "FormatSpec",
    "FormatUnavailableError",
    "ParseOutcome",
    "ValidityReport",
    "blank_targets",
    "check_validity",
    "ensure_required_fields",
    "entry_index",
    "extract_targets",
    "format_ids",
    "get_format",
    "parse_back",
    "parse_json_plain",
    "parse_yaml_plain",
    "project",
    "render",
    "render_document",
    "render_json_plain",
    "render_yaml_plain",
    "strip_context",
    "unwrap",
]
