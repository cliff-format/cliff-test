"""Strict per-format validity checks (dimension 7).

Dimension 7 asks a simple question: after a model has edited a localization
file, is the file still a valid file of that format? Answering it fairly means
every format needs a check of comparable strictness - not 'does some tolerant
library survive it', but 'would the project's own toolchain accept it'.

CLIF is checked with the official validator in pyclif. Every other format is
checked against its own syntax rules here: XML well-formedness plus the
structural requirements for XLIFF and Android, the msgid/msgstr grammar for
PO, the identifier grammar for Fluent, strict JSON/YAML/CSV parsing, and the
quoted assignment grammar for iOS strings files.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from ..paths import ensure_pyclif
from .parse import unwrap
from .registry import get_format

_XLIFF_NS = "urn:oasis:names:tc:xliff:document:2.0"
_FLUENT_ID_RE = re.compile(r"^-?[A-Za-z][A-Za-z0-9_-]*\s*=")
_IOS_LINE_RE = re.compile(r'^\s*"(?:[^"\\]|\\.)*"\s*=\s*"(?:[^"\\]|\\.)*"\s*;\s*$')
_PO_KEYWORDS = ("msgid", "msgstr", "msgctxt", "msgid_plural")


@dataclass(frozen=True)
class Diagnostic:
    """One validity finding, always carrying a line number."""

    line: int
    category: str
    message: str


@dataclass
class ValidityReport:
    """Outcome of validating one document in one format."""

    format_id: str
    ok: bool
    errors: list[Diagnostic] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)
    unwrapped: bool = False

    def summary(self) -> str:
        """One-line human summary."""
        state = "VALID" if self.ok else "INVALID"
        return (
            f"{self.format_id}: {state} "
            f"({len(self.errors)} errors, {len(self.warnings)} warnings)"
        )


def _fail(
    format_id: str, line: int, category: str, message: str, unwrapped: bool
) -> ValidityReport:
    return ValidityReport(
        format_id=format_id,
        ok=False,
        errors=[Diagnostic(line=line, category=category, message=message)],
        unwrapped=unwrapped,
    )


def _check_clif(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    """Validate a CLIF answer, which may carry a glossary as a second document.

    CLIF's terminology workflow lets a translator return the translated file
    plus a 'variant: glossary' file. Each document is validated on its own,
    because concatenating two valid documents is not one valid document - and
    counting that as a format failure would punish the format for using its own
    feature.
    """
    ensure_pyclif()
    import pyclif

    from .parse import split_clif_documents

    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    parts = split_clif_documents(text)
    offset = 0
    for part in parts:
        for issue in pyclif.validate(part):
            diagnostic = Diagnostic(
                line=issue.line + offset, category=issue.category, message=issue.message
            )
            if issue.category in {"warning", "extension"}:
                warnings.append(diagnostic)
            else:
                errors.append(diagnostic)
        offset += part.count("\n") + 1
    return errors, warnings


def _check_xliff(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        line = getattr(exc, "position", (1, 0))[0]
        message = f"XML is not well-formed: {exc}"
        return [Diagnostic(line=line, category="syntax", message=message)], []
    tag = root.tag.split("}")[-1]
    if tag != "xliff":
        errors.append(Diagnostic(1, "semantic", f"root element must be xliff, found '{tag}'"))
    if not root.get("version"):
        errors.append(Diagnostic(1, "semantic", "xliff element is missing the version attribute"))
    if not root.get("srcLang"):
        errors.append(Diagnostic(1, "semantic", "xliff element is missing srcLang"))
    units = root.findall(f".//{{{_XLIFF_NS}}}unit") or root.findall(".//unit")
    if not units:
        errors.append(Diagnostic(1, "semantic", "no translation unit found"))
    for unit in units:
        unit_id = unit.get("id") or "?"
        sources = unit.findall(f".//{{{_XLIFF_NS}}}source") or unit.findall(".//source")
        if not sources:
            errors.append(Diagnostic(1, "semantic", f"unit '{unit_id}' has no source element"))
    return errors, warnings


def _check_po(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    expect_msgstr = False
    saw_entry = False
    for number, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith('"'):
            if stripped.count('"') % 2 or not stripped.endswith('"'):
                errors.append(Diagnostic(number, "syntax", "unterminated continuation string"))
            continue
        keyword = stripped.split(None, 1)[0]
        if keyword not in _PO_KEYWORDS:
            errors.append(Diagnostic(number, "syntax", f"unknown PO keyword '{keyword}'"))
            continue
        remainder = stripped[len(keyword) :].strip()
        if not remainder.startswith('"') or not remainder.endswith('"') or len(remainder) < 2:
            errors.append(Diagnostic(number, "syntax", f"{keyword} value must be a quoted string"))
        if keyword == "msgid":
            expect_msgstr = True
            saw_entry = True
        elif keyword == "msgstr":
            expect_msgstr = False
    if expect_msgstr:
        errors.append(Diagnostic(len(text.split("\n")), "semantic", "msgid without a msgstr"))
    if not saw_entry:
        errors.append(Diagnostic(1, "semantic", "no msgid found"))
    return errors, warnings


def _check_fluent(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    saw_message = False
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in {" ", "\t"}:
            continue  # continuation line
        if _FLUENT_ID_RE.match(line):
            saw_message = True
            continue
        errors.append(
            Diagnostic(number, "syntax", "line is neither a comment nor 'identifier = value'")
        )
    if not saw_message:
        errors.append(Diagnostic(1, "semantic", "no Fluent message found"))
    return errors, warnings


def _check_json(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [Diagnostic(exc.lineno, "syntax", f"invalid JSON: {exc.msg}")], []
    if not isinstance(data, dict | list):
        return [Diagnostic(1, "semantic", "JSON root must be an object or array")], []
    return [], []


def _check_yaml(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    try:
        import yaml
    except ModuleNotFoundError:  # pragma: no cover - env specific
        return [], [Diagnostic(1, "warning", "PyYAML missing: YAML validity not checked")]
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = (mark.line + 1) if mark is not None else 1
        return [Diagnostic(line, "syntax", f"invalid YAML: {exc}")], []
    if data is None:
        return [Diagnostic(1, "semantic", "YAML document is empty")], []
    return [], []


def _check_csv(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        return [Diagnostic(1, "syntax", f"invalid CSV: {exc}")], []
    if not rows:
        return [Diagnostic(1, "semantic", "CSV file is empty")], []
    header = [column.strip() for column in rows[0]]
    if "id" not in header:
        errors.append(Diagnostic(1, "semantic", "CSV header has no 'id' column"))
    if "source" not in header and "target" not in header:
        errors.append(Diagnostic(1, "semantic", "CSV header has neither 'source' nor 'target'"))
    width = len(header)
    for number, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        # A trailing empty field is a counting slip, not data loss: the values
        # still line up with their columns. A consumer sees one spurious empty
        # column, so it is reported - as a warning, because calling it fatal
        # would score CSV for a defect that costs nothing.
        trimmed = list(row)
        while len(trimmed) > width and trimmed[-1] == "":
            trimmed.pop()
        if len(trimmed) == width and len(row) != width:
            warnings.append(
                Diagnostic(
                    number,
                    "warning",
                    f"row has {len(row) - width} trailing empty field(s) beyond the header",
                )
            )
            continue
        if len(trimmed) != width:
            errors.append(
                Diagnostic(number, "syntax", f"row has {len(row)} fields, header has {width}")
            )
    if len(rows) < 2:
        errors.append(Diagnostic(1, "semantic", "CSV file has no data rows"))
    return errors, warnings


def _check_android(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        line = getattr(exc, "position", (1, 0))[0]
        return [Diagnostic(line, "syntax", f"XML is not well-formed: {exc}")], []
    errors: list[Diagnostic] = []
    if root.tag != "resources":
        errors.append(
            Diagnostic(1, "semantic", f"root element must be resources, found '{root.tag}'")
        )
    strings = root.findall("string")
    if not strings:
        errors.append(Diagnostic(1, "semantic", "no string resource found"))
    for element in strings:
        if not element.get("name"):
            errors.append(Diagnostic(1, "semantic", "string element without a name attribute"))
    return errors, []


def _check_ios(text: str) -> tuple[list[Diagnostic], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    saw_pair = False
    in_block_comment = False
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if not line or line.startswith("//"):
            continue
        if line.startswith("/*"):
            if "*/" not in line:
                in_block_comment = True
            continue
        if _IOS_LINE_RE.match(line):
            saw_pair = True
            continue
        errors.append(Diagnostic(number, "syntax", 'line is not a "key" = "value"; assignment'))
    if in_block_comment:
        errors.append(Diagnostic(len(text.split("\n")), "syntax", "unterminated block comment"))
    if not saw_pair:
        errors.append(Diagnostic(1, "semantic", "no key/value assignment found"))
    return errors, []


_CHECKERS = {
    "clif": _check_clif,
    "xliff-2.1": _check_xliff,
    "xliff-2.2": _check_xliff,
    "po": _check_po,
    "fluent": _check_fluent,
    "json-clif": _check_json,
    "json-plain": _check_json,
    "yaml-clif": _check_yaml,
    "yaml-plain": _check_yaml,
    "csv": _check_csv,
    "android": _check_android,
    "ios": _check_ios,
}


def check_validity(text: str, format_id: str, *, allow_unwrap: bool = True) -> ValidityReport:
    """Validate a document in one format and report line-numbered findings."""
    get_format(format_id)
    body, unwrapped = unwrap(text) if allow_unwrap else (text, False)
    if not body.strip():
        return _fail(format_id, 1, "syntax", "document is empty", unwrapped)
    checker = _CHECKERS[format_id]
    try:
        errors, warnings = checker(body)
    except Exception as exc:  # noqa: BLE001 - a crashing checker is still a failure
        return _fail(format_id, 1, "syntax", f"{type(exc).__name__}: {exc}", unwrapped)
    return ValidityReport(
        format_id=format_id,
        ok=not errors,
        errors=errors,
        warnings=warnings,
        unwrapped=unwrapped,
    )
