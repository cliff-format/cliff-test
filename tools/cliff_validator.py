#!/usr/bin/env python3
"""Reference validator for CLIFF 1.1.

Usage:
  python cliff_validator.py FILE...
  python cliff_validator.py --check-width FILE...
  python cliff_validator.py --check-layout FILE...
  python cliff_validator.py --style FILE...
  python cliff_validator.py --tolerant FILE...
  python cliff_validator.py --suite DIR
  python cliff_validator.py --json FILE
  python cliff_validator.py --ids FILE

Modes:
  * strict (default) — reject everything the normative grammar rejects.
  * --check-layout — report a file-layout/header mismatch as an error. By
    default it is a warning, because CLIFF 1.1 recommends a layout rather than
    requiring it (specification 11.3).
  * --style — report deviations from style/README.md as warnings. A style
    deviation is never an error.
  * --tolerant — apply the documented relaxations of specification Appendix C
    and report every repair. This mode delegates to ``cliff_format`` so that
    there is exactly one implementation of the tolerant contract; without the
    library installed the flag fails rather than checking something weaker.

Exit status: 0 when every file is valid, 1 otherwise.
Requires Python 3.11+.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import unicodedata
from pathlib import Path

VERSION = "1.1"
MAX_ERRORS = 200

# Names: the relaxed CLIFF 1.1 identifier (specification 5.5). A name is one or
# more of A-Z a-z 0-9 _ - and never contains "." because the dot separates group
# path segments and canonical ID components.
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
# Tags: unchanged from 1.0, and deliberately narrow. A closed vocabulary that
# tolerates spellings is not closed.
TAG_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
LANG_RE = re.compile(r"^[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*$")
# Stricter folder-detection subset of the BCP 47 envelope.  Directory names
# such as ``valid``, ``quality``, or ``001`` must not be mistaken for a
# language folder, while real language folders such as ``ja-JP``, ``zh-CN``,
# ``en``, or ``zh-Hant-TW`` are recognized.
FOLDER_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{1,8})*$")
VERSION_RE = re.compile(r"^[ \t]*CLIFF (1\.0|1\.1)[ \t]*$")
UNSUPPORTED_VERSION_RE = re.compile(r"^[ \t]*CLIFF[ \t]+(\S+)[ \t]*$", re.IGNORECASE)
SECTION_RE = re.compile(r"^[ \t]*\[([^\]]*)\][ \t]*$")
ENTRY_RE = re.compile(r"^[ \t]*<([^<>]*)>[ \t]*$")
OLD_ENTRY_RE = re.compile(r"^[ \t]*entry\b")

# Style predicates (informative; style/README.md). Used by --style only.
STYLE_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STYLE_PASCAL_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
POSITIONAL_RE = re.compile(r"^[0-9]+[^A-Za-z]*")

TYPE_TAGS = {
    "noun", "verb", "adjective", "adverb", "pronoun", "numeral",
    "preposition", "conjunction", "particle", "interjection", "proper-noun",
    "noun-phrase", "verb-phrase", "adjective-phrase", "adverb-phrase",
    "fixed-phrase", "idiom", "sentence", "description", "narration",
    "dialogue", "monologue", "prompt", "label", "subtitle",
    "accessibility-cue",
}
EMOTION_TAGS = {
    "neutral", "objective", "mechanical",
    "joyful", "sad", "angry", "fearful", "surprised", "curious",
    "disgusted", "anxious", "calm", "playful", "serious", "urgent",
    "romantic", "hopeful", "grateful", "formal", "informal", "polite",
    "rude", "nostalgic",
}
STATUS_TAGS = {"initial", "translated", "reviewed", "final"}
GLOSSARY_TYPES = {
    "noun", "verb", "adjective", "adverb", "pronoun", "numeral",
    "preposition", "conjunction", "particle", "interjection", "proper-noun",
    "noun-phrase", "verb-phrase", "adjective-phrase", "adverb-phrase",
    "fixed-phrase", "idiom",
}

HEADER_KEYS = {
    "namespace", "clan", "source-language", "target-language", "version",
    "variant", "title", "info", "standard", "dependency",
}
HEADER_SINGLE_KEYS = {
    "namespace", "clan", "source-language", "target-language", "version",
    "variant", "title", "dependency",
}
HEADER_REPEATABLE_KEYS = {"info", "standard"}
GROUP_KEYS = {"context", "type", "emotion", "max-width"}
ENTRY_KEYS = {
    "source", "target", "type", "emotion", "status", "context",
    "max-width", "reference", "reviewer",
}
ENTRY_SINGLE_KEYS = {
    "source", "target", "type", "emotion", "status", "max-width", "reviewer",
}
ENTRY_REPEATABLE_KEYS = {"context", "reference"}

LIST_KEYS = {"emotion", "reference", "dependency"}
STRING_KEYS = {
    "title", "info", "standard", "source", "target", "context", "reviewer",
    "version",
}
TAG_KEYS = {"type", "status", "emotion", "variant"}
LANG_KEYS = {"source-language", "target-language"}
NAME_KEYS = {"namespace", "clan"}
INT_KEYS = {"max-width"}

ESCAPES = {'"': '"', "'": "'", "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}


@dataclasses.dataclass
class Issue:
    line: int
    cls: str  # syntax | semantic | vocabulary | icu | id | extension | warning | style | correction
    message: str
    text: str = ""


#: Categories that are reported without making a document invalid. ``layout`` is
#: advisory because CLIFF 1.1 recommends a layout rather than requiring it;
#: ``--check-layout`` re-tags those findings as ``semantic``, which is an error.
ADVISORY_CLASSES = frozenset({"warning", "extension", "style", "correction", "layout"})


#: The vocabulary each tag-typed field validates against.
TAG_VOCABULARIES: dict[str, set[str]] = {
    "variant": {"standard", "glossary"},
    "type": set(TYPE_TAGS),
    "status": set(STATUS_TAGS),
    "emotion": set(EMOTION_TAGS),
}


def is_name(text: str) -> bool:
    """Whether ``text`` is a conforming CLIFF 1.1 identifier."""
    return bool(text) and NAME_RE.match(text) is not None


def is_style_identifier(text: str) -> bool:
    """Whether ``text`` follows a recommended shape of style/README.md."""
    return bool(text) and bool(
        STYLE_KEBAB_RE.match(text) or STYLE_PASCAL_RE.match(text)
    )


def strip_line_terminator(line: str) -> tuple[str, str, int]:
    """Split the trailing ``,`` / ``;`` terminators off a raw line.

    Returns ``(body, terminators, extra)``. Mirrors the reference
    implementation: at most one terminator is legal (specification 5.6), the
    scan is right-to-left over trailing whitespace and terminators only, and a
    ``,`` or ``;`` inside a quoted string (or the optional trailing comma inside
    a ``[a, b,]`` list) is never touched.
    """
    index = len(line)
    while index > 0 and line[index - 1] in " \t":
        index -= 1
    if index == 0 or line[index - 1] not in ",;":
        return line[:index], "", 0
    terminators = [line[index - 1]]
    index -= 1
    probe = index
    while probe > 0 and line[probe - 1] in " \t":
        probe -= 1
    if probe > 0 and line[probe - 1] in ",;":
        terminators.append(line[probe - 1])
        index = probe - 1
    terminators.reverse()
    return line[:index], "".join(terminators), max(len(terminators) - 1, 0)


@dataclasses.dataclass
class Entry:
    line: int
    entry_id: str
    section_path: str
    fields: dict[str, list[tuple[int, object, str]]]
    raw_line: str = ""


@dataclasses.dataclass
class Section:
    line: int
    path: str
    group_fields: dict[str, list[tuple[int, object, str]]]


def unescape_run(text: str, line: int, raw: str, quote: str) -> tuple[str | None, str | None]:
    allowed = {'"', '\\', 'n', 'r', 't'} if quote == '"' else {"'", '\\', 'n', 'r', 't'}
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 >= len(text):
                return None, "trailing backslash"
            nxt = text[i + 1]
            if nxt not in allowed:
                return None, f"unknown escape sequence \\{nxt}"
            out.append(ESCAPES[nxt])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out), None


def is_quote_start(text: str) -> bool:
    return text.startswith('"') or text.startswith("'")


def parse_string(text: str) -> tuple[str | None, str | None, str | None]:
    """Parse a double- or single-quoted string at the start of text."""
    if text.startswith('"'):
        quote = '"'
    elif text.startswith("'"):
        quote = "'"
    else:
        return None, None, "expected a quoted string"
    i = 1
    out: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == quote:
            rest = text[i + 1:]
            value, err = unescape_run("".join(out), 0, text, quote)
            if err:
                return None, rest, err
            return value, rest, None
        if ch == "\\":
            if i + 1 >= len(text):
                return None, text, "trailing backslash"
            out.append(text[i:i + 2])
            i += 2
            continue
        if ch in "\n\r\t" or ord(ch) < 0x20:
            return None, text, "raw control character inside string"
        out.append(ch)
        i += 1
    return None, text, "unterminated string"


def parse_adjacent_strings(text: str) -> tuple[str | None, str | None]:
    """Parse one or more adjacent double-quoted strings; concatenate verbatim (C rules)."""
    text = text.strip()
    if not text:
        return None, "empty value"
    parts: list[str] = []
    rest = text
    while rest:
        if not is_quote_start(rest):
            return None, "expected a quoted string"
        value, after, err = parse_string(rest)
        if err:
            return None, err
        parts.append(value)
        rest = after.lstrip()
    return "".join(parts), None


def find_separator(text: str) -> int | None:
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch in "\"'":
                in_string = False
        else:
            if ch in "\"'":
                in_string = True
            elif ch in "=:":
                return i
    return None


def parse_field_line(line: str) -> tuple[str | None, str | None, str | None]:
    idx = find_separator(line)
    if idx is None:
        return None, None, "expected 'key: value' or 'key = value' field"
    key = line[:idx].strip()
    value = line[idx + 1:].strip()
    if not is_name(key):
        return None, None, (
            f"invalid field name '{key}' (a name is one or more of A-Z a-z 0-9 _ -)"
        )
    return key, value, None


def split_list_items(body: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_string = False
    escaped = False
    for ch in body:
        if in_string:
            buf.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch in "\"'":
                in_string = False
            continue
        if ch in "\"'":
            in_string = True
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def parse_language_tag(text: str) -> tuple[str | None, str | None]:
    text = text.strip()
    if not text:
        return None, "empty language tag"
    if not LANG_RE.match(text):
        return None, f"'{text}' is not a plausible BCP 47 language tag"
    return text, None


def parse_tag(text: str, key: str = "type") -> tuple[str | None, str | None]:
    """Read a tag value: a bare lowercase word drawn from a closed vocabulary.

    Quotes around a tag are a shape error (specification 6.1, "tags are never
    quoted"): the tolerant mode of Appendix C.2.3 is what removes them, and this
    validator never applies a relaxation implicitly. A word outside the
    vocabulary is reported as a vocabulary error by the caller, listing the
    allowed values, rather than as a generic syntax error.
    """
    text = text.strip()
    if not text:
        return None, "empty tag"
    if text.startswith('"') or text.startswith("'"):
        return None, (
            "tag values are unquoted lowercase words; write "
            f"{text.strip(chr(34) + chr(39))} without quotes"
        )
    allowed = TAG_VOCABULARIES.get(key, set())
    if not TAG_NAME_RE.match(text) and text.lower() not in allowed:
        return None, f"{text!r} is not a valid tag (lowercase kebab-case required)"
    return text, None


def parse_scalar(text: str, key: str) -> tuple[object | None, str | None]:
    text = text.strip()
    if not text:
        return None, "empty value"
    if text.startswith('"') or text.startswith("'"):
        value, rest, err = parse_string(text)
        if err:
            return None, err
        if rest.strip():
            return None, "unexpected content after the closing quote"
        return value, None
    if key in LANG_KEYS:
        return parse_language_tag(text)
    if key in NAME_KEYS:
        if not NAME_RE.match(text):
            return None, f"'{text}' is not a valid name (lowercase kebab-case required)"
        return text, None
    if key in INT_KEYS:
        if not text.isdigit() or int(text) <= 0:
            return None, f"'{text}' is not a positive integer"
        return int(text), None
    if key in STRING_KEYS:
        return None, f"'{key}' expects a quoted string"
    if NAME_RE.match(text):
        return text, None
    return None, f"'{text}' is not a valid name, string, or integer"


def parse_value(text: str, key: str, line: int) -> tuple[object | None, str | None]:
    """Read a field value under the strict grammar of specification 6.1.

    The three shapes are not interchangeable: brackets mean a list, quotes mean
    text, and a bare word means a tag or an identifier. In particular the
    list-typed fields (`emotion`, `dependency`, `reference`) are always lists,
    even for one item — a bare scalar there is an error, and it is Appendix C.2.1
    that makes a tolerant reader accept it.
    """
    text = text.strip()
    if not text:
        return None, "empty value"
    if key in LIST_KEYS and not text.startswith("["):
        hint = {
            "emotion": "emotion: [neutral]",
            "dependency": 'dependency: ["../terms/terms.zh-CN.cliff"]',
            "reference": 'reference: ["src/ui.cpp:12"]',
        }.get(key, f"{key}: [value]")
        if key == "emotion":
            _, err = parse_tag(text, "emotion")
            if err:
                return None, err
        return None, (
            f"{key} is a list-typed field and must be written as a list, even for a "
            f"single item (for example: {hint})"
        )
    if not text.startswith("["):
        return parse_scalar(text, key)

    if not text.endswith("]"):
        return None, "unclosed list (closing bracket must be on the same line)"
    if key not in LIST_KEYS:
        return None, f"'{key}' does not accept a list; expected a scalar value"
    body = text[1:-1].strip()
    items: list[object] = []
    if body:
        parts = split_list_items(body)
        for part in parts:
            part = part.strip()
            if not part:
                return None, "empty list item"
            if part.startswith("["):
                return None, "nested lists are not allowed"
            if key in ("dependency", "reference"):
                if not is_quote_start(part):
                    return None, f"{key} list items must be quoted strings"
                item, err = parse_scalar(part, "reference" if key == "reference" else "dependency")
                if err:
                    return None, err
            elif key == "emotion":
                item, err = parse_tag(part, "emotion")
                if err:
                    return None, err
            else:
                item, err = parse_scalar(part, key)
                if err:
                    return None, err
            items.append(item)
    return items, None


def check_vocab(values: list[str], allowed: set[str], label: str) -> str | None:
    for val in values:
        if val not in allowed:
            return f"{label}: invalid tag '{val}'; allowed: {', '.join(sorted(allowed))}"
    return None


def brace_balance(text: str, line: int) -> list[Issue]:
    issues: list[Issue] = []
    if "{" not in text and "}" not in text:
        return issues
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                issues.append(Issue(line, "icu", "unmatched closing brace '}' inside string", text))
                return issues
        i += 1
    if depth != 0:
        issues.append(Issue(line, "icu", f"unbalanced ICU braces: {depth} unclosed '{{'", text))
    return issues


def display_cells(text: str) -> int:
    """UAX #11-based display cell count used by max-width."""
    total = 0
    for ch in text:
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Cf", "Zl", "Zp"):
            continue
        width = unicodedata.east_asian_width(ch)
        total += 2 if width in ("W", "F") else 1
    return total


def is_ignorable(line: str) -> bool:
    return line.strip() == "" or line.lstrip().startswith("#")


def parse_filename(filename: str) -> tuple[str | None, str | None, str | None]:
    """Return (clan, langtag, error) using the canonical <clan>.<langtag>.cliff shape."""
    if not filename.endswith(".cliff"):
        return None, None, "filename must end with .cliff"
    stem = filename[: -len(".cliff")]
    parts = stem.split(".")
    if len(parts) != 2:
        return None, None, "filename must be '<clan>.<target-language>.cliff'"
    clan, lang = parts
    if not NAME_RE.match(clan):
        return None, None, f"invalid clan name in filename: '{clan}'"
    if not LANG_RE.match(lang):
        return None, None, f"invalid language tag in filename: '{lang}'"
    return clan, lang, None


def parse_folder_language(parent: str) -> str | None:
    """Return the parent directory name when it is a plausible BCP 47 language tag.

    The folder-candidate test is deliberately stricter than the general
    LANG_RE envelope used for header fields: plain directory names such as
    ``valid``, ``quality`` or ``001`` are not language folders, while
    ``ja-JP``, ``zh-CN``, ``en`` and ``zh-Hant-TW`` are recognized.
    """
    if not parent:
        return None
    return parent if FOLDER_LANG_RE.match(parent) else None


class Document:
    def __init__(self, path: Path | None):
        self.path = path
        self.lines: list[str] = []
        self.raw_lines: list[str] = []
        self.header: dict[str, list[tuple[int, object, str]]] = {}
        self.sections: list[Section] = []
        self.entries: list[Entry] = []
        self.issues: list[Issue] = []
        self.namespace: str | None = None
        self.clan: str | None = None
        self.target_language: str | None = None
        self.variant: str = "standard"
        self.check_width = False
        self.check_layout = False
        self.style = False

    def issue(self, line: int, cls: str, message: str, text: str = "") -> None:
        if len(self.issues) < MAX_ERRORS:
            self.issues.append(Issue(line, cls, message, text))

    def load(self, data: str) -> None:
        if data.startswith("\ufeff"):
            data = data[1:]
        if "\r" in data:
            # A CRLF is a line ending; a bare CR is invalid.
            bad_bare_cr = False
            for i, ch in enumerate(data):
                if ch == "\r":
                    if i + 1 >= len(data) or data[i + 1] != "\n":
                        bad_bare_cr = True
                        self.issue(0, "syntax", "bare CR is not a valid line ending")
                        break
            data = data.replace("\r\n", "\n")
        self.raw_lines = data.split("\n")
        self.lines = [line.rstrip() for line in self.raw_lines]

    def validate(self) -> None:
        if not self.lines:
            self.issue(0, "syntax", "empty file")
            return
        self._parse()
        self._validate_header()
        self._validate_sections_entries()

    # ----- parsing -----

    def _parse(self) -> None:
        seen_version = False
        current_section: Section | None = None
        current_entry: Entry | None = None
        section_entry_started = False
        last_container: dict | None = None
        last_key: str | None = None

        for idx, raw in enumerate(self.lines, start=1):
            line, _terminators, extra = strip_line_terminator(raw)
            if extra:
                self.issue(
                    idx,
                    "syntax",
                    "at most one trailing ',' or ';' is allowed on a line",
                    raw,
                )
                last_container = None
                last_key = None
                continue
            if is_ignorable(line):
                last_container = None
                last_key = None
                continue

            if not seen_version:
                if VERSION_RE.match(line):
                    seen_version = True
                    continue
                unsupported = UNSUPPORTED_VERSION_RE.match(line)
                if unsupported:
                    self.issue(
                        idx,
                        "semantic",
                        f"unsupported CLIFF version '{unsupported.group(1)}'; "
                        "this implementation implements 1.0, 1.1",
                        raw,
                    )
                    seen_version = True
                    continue
                # The version line is invalid or missing: report the first
                # non-blank non-comment line and keep parsing as tolerant input.
                self.issue(idx, "syntax",
                           "version line 'CLIFF 1.1' must be the first non-blank, non-comment line",
                           raw)
                seen_version = True
                if re.match(r"^[ \t]*CLIFF\b", line, re.IGNORECASE):
                    continue
                # fall through: parse the line as a header/body line

            sec = SECTION_RE.match(line)
            if sec:
                path = sec.group(1).strip()
                current_section = Section(idx, path, {})
                self.sections.append(current_section)
                current_entry = None
                section_entry_started = False
                last_container = None
                last_key = None
                continue

            ent = ENTRY_RE.match(line)
            if ent:
                last_container = None
                last_key = None
                if current_section is None:
                    self.issue(idx, "syntax", "entry declared before any [group] section", raw)
                    current_entry = None
                    section_entry_started = False
                    continue
                entry_id = ent.group(1)
                current_entry = Entry(idx, entry_id, current_section.path, {}, raw)
                self.entries.append(current_entry)
                section_entry_started = True
                continue

            if OLD_ENTRY_RE.match(line):
                last_container = None
                last_key = None
                if current_section is None:
                    self.issue(idx, "syntax", "entry declared before any [group] section", raw)
                else:
                    self.issue(idx, "syntax", "expected '<id>' entry marker", raw)
                continue

            # Continuation lines: bare strings attach to the preceding string
            # field; a bare single-line list attaches to the preceding list
            # field. Both must immediately follow their parent line.
            if last_container is not None and last_key is not None:
                stripped = line.strip()
                if last_key in STRING_KEYS and is_quote_start(stripped):
                    fragment, err = parse_adjacent_strings(stripped)
                    if err:
                        self.issue(idx, "syntax", f"invalid string continuation: {err}", raw)
                    else:
                        self._append_string_continuation(last_container, last_key, fragment)
                    continue
                if last_key in LIST_KEYS and stripped.startswith("["):
                    fragment, err = parse_value(stripped, last_key, idx)
                    if err is not None or not isinstance(fragment, list):
                        self.issue(idx, "syntax",
                                   f"invalid list continuation: {err or 'expected a single-line list'}",
                                   raw)
                    else:
                        if last_key == "emotion":
                            chart = check_vocab(fragment, EMOTION_TAGS, "emotion")
                            if chart:
                                self.issue(idx, "vocabulary", chart, raw)
                        self._append_list_continuation(last_container, last_key, fragment)
                    continue
                if is_quote_start(stripped) or stripped.startswith("["):
                    self.issue(idx, "syntax",
                               f"continuation line does not match the preceding '{last_key}' field",
                               raw)
                    continue

            key, value, err = parse_field_line(line)
            if err:
                self.issue(idx, "syntax", err, raw)
                last_container = None
                last_key = None
                continue

            if current_section is None:
                container = self.header
                before = len(container.get(key, []))
                self._store_header(idx, key, value, raw)
            elif current_entry is not None:
                container = current_entry.fields
                before = len(container.get(key, []))
                self._store_entry(current_entry, idx, key, value, raw)
            elif not section_entry_started:
                container = current_section.group_fields
                before = len(container.get(key, []))
                self._store_group(current_section, idx, key, value, raw)
            else:
                # Should not happen: after the first entry, current_entry is set.
                container = current_section.group_fields
                before = len(container.get(key, []))
                self._store_group(current_section, idx, key, value, raw)

            if len(container.get(key, [])) > before:
                last_container = container
                last_key = key
            else:
                last_container = None
                last_key = None

        if not seen_version:
            self.issue(0, "syntax", "empty file")

    @staticmethod
    def _append_string_continuation(container: dict, key: str, fragment: str) -> None:
        line, value, raw = container[key][-1]
        container[key][-1] = (line, str(value) + fragment, raw)

    @staticmethod
    def _append_list_continuation(container: dict, key: str, fragment: list) -> None:
        line, value, raw = container[key][-1]
        merged = list(value) + list(fragment)
        container[key][-1] = (line, merged, raw)

    def _store_header(self, idx: int, key: str, value: str, raw: str) -> None:
        if key in self.header:
            self.issue(idx, "semantic",
                       f"header field '{key}' may appear at most once (CLIFF has no repeatable fields)",
                       raw)
            return
        if key.startswith("x-"):
            self.issue(idx, "extension", f"extension header key '{key}'", raw)
            self.header.setdefault(key, []).append((idx, value, raw))
            return
        if key not in HEADER_KEYS:
            self.issue(idx, "semantic",
                       f"unknown header key '{key}'; known keys: {', '.join(sorted(HEADER_KEYS))}",
                       raw)
            self.header.setdefault(key, []).append((idx, value, raw))
            return

        if key in ("info", "standard", "title", "version"):
            parsed, err = parse_adjacent_strings(value)
            if err:
                self.issue(idx, "syntax", f"{key}: {err}", raw)
                return
            self.header.setdefault(key, []).append((idx, parsed, raw))
            return

        if key == "dependency":
            parsed, err = parse_value(value, key, idx)
            if err:
                self.issue(idx, "syntax", f"dependency: {err}", raw)
                return
            self.header.setdefault(key, []).append((idx, parsed, raw))
            return

        if key == "variant":
            parsed, err = parse_tag(value, "variant")
            if err:
                self.issue(idx, "syntax", f"variant: {err}", raw)
                return
            self.header.setdefault(key, []).append((idx, parsed, raw))
            return

        if key in TAG_KEYS:
            parsed, err = parse_tag(value, key)
            if err:
                self.issue(idx, "syntax", f"{key}: {err}", raw)
                return
            self.header.setdefault(key, []).append((idx, parsed, raw))
            return

        parsed, err = parse_scalar(value, key)
        if err:
            self.issue(idx, "syntax", f"{key}: {err}", raw)
            return
        self.header.setdefault(key, []).append((idx, parsed, raw))

    def _store_group(self, section: Section, idx: int, key: str, value: str, raw: str) -> None:
        if key in section.group_fields:
            self.issue(idx, "semantic",
                       f"group field '{key}' may appear at most once (CLIFF has no repeatable fields)",
                       raw)
            return
        if key.startswith("x-"):
            self.issue(idx, "extension", f"extension group key '{key}'", raw)
            return
        if key not in GROUP_KEYS:
            self.issue(idx, "semantic",
                       f"key '{key}' is not allowed in group metadata "
                       f"(allowed: {', '.join(sorted(GROUP_KEYS))})", raw)
            return
        if key == "context":
            parsed, err = parse_adjacent_strings(value)
            if err:
                self.issue(idx, "syntax", f"context: {err}", raw)
                return
            section.group_fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "max-width":
            parsed, err = parse_scalar(value, key)
            if err:
                self.issue(idx, "syntax", f"max-width: {err}", raw)
                return
            section.group_fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "type":
            parsed, err = parse_tag(value, "type")
            if err:
                self.issue(idx, "syntax", f"type: {err}", raw)
                return
            chart = check_vocab([parsed], TYPE_TAGS, "type")
            if chart:
                self.issue(idx, "vocabulary", chart, raw)
            section.group_fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "emotion":
            parsed, err = parse_value(value, key, idx)
            if err:
                self.issue(idx, "syntax", f"emotion: {err}", raw)
                return
            items = parsed if isinstance(parsed, list) else [parsed]
            chart = check_vocab(items, EMOTION_TAGS, "emotion")
            if chart:
                self.issue(idx, "vocabulary", chart, raw)
            section.group_fields.setdefault(key, []).append((idx, parsed, raw))
            return
        # unreachable
        self.issue(idx, "semantic", f"key '{key}' is not allowed in group metadata", raw)

    def _store_entry(self, entry: Entry, idx: int, key: str, value: str, raw: str) -> None:
        if key in entry.fields:
            self.issue(idx, "semantic",
                       f"entry field '{key}' may appear at most once (CLIFF has no repeatable fields)",
                       raw)
            return
        if key.startswith("x-"):
            self.issue(idx, "extension", f"extension entry key '{key}'", raw)
            entry.fields.setdefault(key, []).append((idx, value, raw))
            return
        if key not in ENTRY_KEYS:
            self.issue(idx, "semantic",
                       f"unknown entry key '{key}'; known keys: {', '.join(sorted(ENTRY_KEYS))}",
                       raw)
            entry.fields.setdefault(key, []).append((idx, value, raw))
            return

        if key in ("type", "status"):
            parsed, err = parse_tag(value, key)
            if err:
                self.issue(idx, "syntax", f"{key}: {err}", raw)
                return
            allowed = TYPE_TAGS if key == "type" else STATUS_TAGS
            chart = check_vocab([parsed], allowed, key)
            if chart:
                self.issue(idx, "vocabulary", chart, raw)
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "emotion":
            parsed, err = parse_value(value, key, idx)
            if err:
                self.issue(idx, "syntax", f"emotion: {err}", raw)
                return
            items = parsed if isinstance(parsed, list) else [parsed]
            chart = check_vocab(items, EMOTION_TAGS, "emotion")
            if chart:
                self.issue(idx, "vocabulary", chart, raw)
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "context":
            parsed, err = parse_adjacent_strings(value)
            if err:
                self.issue(idx, "syntax", f"context: {err}", raw)
                return
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key in ("source", "target"):
            parsed, err = parse_adjacent_strings(value)
            if err:
                self.issue(idx, "syntax", f"{key}: {err}", raw)
                return
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "reviewer":
            parsed, err = parse_adjacent_strings(value)
            if err:
                self.issue(idx, "syntax", f"reviewer: {err}", raw)
                return
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "max-width":
            parsed, err = parse_scalar(value, key)
            if err:
                self.issue(idx, "syntax", f"max-width: {err}", raw)
                return
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        if key == "reference":
            parsed, err = parse_value(value, key, idx)
            if err:
                self.issue(idx, "syntax", f"reference: {err}", raw)
                return
            entry.fields.setdefault(key, []).append((idx, parsed, raw))
            return
        # unreachable
        self.issue(idx, "semantic", f"unknown entry key '{key}'", raw)

    # ----- validation -----

    def _header_value(self, key: str) -> object | None:
        items = self.header.get(key, [])
        if not items:
            return None
        return items[0][1]

    def _validate_header(self) -> None:
        for key in ("namespace", "clan", "source-language", "target-language"):
            if key not in self.header:
                self.issue(0, "semantic", f"missing required header field '{key}'")
        if "namespace" in self.header:
            ns = self.header["namespace"][0][1]
            if isinstance(ns, str):
                self.namespace = ns
        if "clan" in self.header:
            clan = self.header["clan"][0][1]
            if isinstance(clan, str):
                self.clan = clan
        if "target-language" in self.header:
            lang = self.header["target-language"][0][1]
            if isinstance(lang, str):
                self.target_language = lang
        for key in HEADER_SINGLE_KEYS:
            if key in self.header and len(self.header[key]) != 1:
                self.issue(self.header[key][0][0], "semantic",
                           f"header field '{key}' is single-valued but appears {len(self.header[key])} times")
        for key in HEADER_REPEATABLE_KEYS:
            if key in self.header:
                for _, val, raw in self.header[key]:
                    if not isinstance(val, str):
                        # parse_scalar already enforced strings, but keep the guard.
                        self.issue(0, "syntax", f"{key} must be a string", raw)

        if self._header_value("variant") is not None:
            variant = str(self._header_value("variant"))
            if variant in ("standard", "glossary"):
                self.variant = variant
            else:
                self.issue(self.header["variant"][0][0], "vocabulary",
                           f"variant: invalid tag '{variant}'; allowed: standard, glossary",
                           self.header["variant"][0][2])

        self._resolve_filename_languages()

    def _resolve_filename_languages(self) -> None:
        """Check CLIFF 1.1 §11.3 layout consistency.

        The header is authoritative: namespace, clan, source-language, and
        target-language are required header fields. The layout is a delivery
        convention that SHOULD agree with the header; it never supplies missing
        header values. In 1.1 a mismatch is a **warning**, because the header
        identifies the file whether or not its name agrees; ``--check-layout``
        promotes it to an error for a project that keeps the convention
        mandatory in its own CI.
        """
        cls = "semantic" if self.check_layout else "layout"
        suffix = "" if self.check_layout else " (layout is a recommendation in CLIFF 1.1)"
        filename = self.path.name if self.path is not None else None
        parent_name = ""
        if self.path is not None:
            parent_name = self.path.parent.name
            if parent_name in (".", ".."):
                parent_name = ""

        header_clan = self._header_value("clan")
        header_lang = self._header_value("target-language")

        folder_lang = parse_folder_language(parent_name) if parent_name else None
        folder_clan = None
        if folder_lang is not None and filename is not None:
            folder_clan = (
            filename[: -len(".cliff")] if filename.endswith(".cliff") else filename
        )

        file_clan = None
        file_lang = None
        if filename is not None:
            file_clan, file_lang, _ = parse_filename(filename)

        # Rule 4: when both layout candidates exist they must agree.
        if folder_lang is not None and file_lang is not None:
            if folder_clan != file_clan or folder_lang.lower() != file_lang.lower():
                self.issue(
                    0,
                    cls,
                    "layout conflict: folder candidate resolves "
                    f"clan '{folder_clan}' and target-language '{folder_lang}', "
                    "but file-name candidate resolves "
                    f"clan '{file_clan}' and target-language '{file_lang}'{suffix}",
                )

        # Rule 5: header values must agree with every value supplied by the layout.
        layout_clans = [c for c in (folder_clan, file_clan) if c is not None]
        layout_langs = [t for t in (folder_lang, file_lang) if t is not None]
        if header_clan is not None:
            for layout_clan in layout_clans:
                if str(header_clan) != layout_clan:
                    self.issue(
                        self.header["clan"][0][0],
                        cls,
                        f"header clan '{header_clan}' does not match layout clan "
                        f"'{layout_clan}'{suffix}",
                        self.header["clan"][0][2],
                    )
        if header_lang is not None:
            for layout_lang in layout_langs:
                if str(header_lang).lower() != layout_lang.lower():
                    self.issue(
                        self.header["target-language"][0][0],
                        cls,
                        f"header target-language '{header_lang}' does not match "
                        f"layout language '{layout_lang}'{suffix}",
                        self.header["target-language"][0][2],
                    )

    def _effective_group(self, section: Section, key: str) -> object | None:
        items = section.group_fields.get(key, [])
        if not items:
            return None
        if key == "context":
            return " ".join(str(v) for _, v, _ in items)
        return items[-1][1]

    def _find_section(self, path: str) -> Section | None:
        for s in self.sections:
            if s.path == path:
                return s
        return None

    def _canonical_id(self, entry: Entry) -> str:
        if self.namespace and self.clan:
            return ".".join([self.namespace, self.clan, entry.section_path, entry.entry_id])
        return ".".join([entry.section_path, entry.entry_id])

    def _validate_sections_entries(self) -> None:
        seen_paths: set[str] = set()
        seen_entry_ids: dict[str, Entry] = {}
        seen_canonical: set[str] = set()

        for section in self.sections:
            path = section.path
            if not all(is_name(seg) for seg in path.split(".")):
                self.issue(section.line, "id",
                           f"invalid group path '[{path}]'; segments must be names "
                           "(one or more of A-Z a-z 0-9 _ -)",
                           "[{}]".format(path))
            if path in seen_paths:
                self.issue(section.line, "id", f"duplicate section path '[{path}]'")
            seen_paths.add(path)
            for key in ("type", "emotion", "max-width"):
                if key in section.group_fields and len(section.group_fields[key]) != 1:
                    self.issue(section.line, "semantic",
                               f"group metadata '{key}' is single-valued but appears "
                               f"{len(section.group_fields[key])} times")
            # context is repeatable
            for key, values in section.group_fields.items():
                if key == "context":
                    for _, val, raw in values:
                        if not isinstance(val, str):
                            self.issue(section.line, "syntax", "context must be a string", raw)

        for entry in self.entries:
            if not is_name(entry.entry_id):
                self.issue(entry.line, "id",
                           f"invalid entry id '{entry.entry_id}'; a name is one or more "
                           "of A-Z a-z 0-9 _ -")
            if entry.entry_id in seen_entry_ids:
                first_entry = seen_entry_ids[entry.entry_id]
                first_canonical = self._canonical_id(first_entry)
                current_canonical = self._canonical_id(entry)
                self.issue(
                    entry.line,
                    "id",
                    f"duplicate entry id '{entry.entry_id}'; conflicting canonical IDs are "
                    f"'{first_canonical}' (first: line {first_entry.line}, "
                    f"{first_entry.raw_line.strip()}) and '{current_canonical}' "
                    f"(second: line {entry.line}, {entry.raw_line.strip()})",
                    text=entry.raw_line,
                )
            else:
                seen_entry_ids[entry.entry_id] = entry

            section = self._find_section(entry.section_path)
            if section is None:
                self.issue(entry.line, "syntax", f"entry '{entry.entry_id}' is not inside a known section")
                continue

            canonical = self._canonical_id(entry)
            if canonical in seen_canonical:
                self.issue(entry.line, "id", f"duplicate canonical id '{canonical}'")
            seen_canonical.add(canonical)

            if "source" not in entry.fields:
                self.issue(entry.line, "semantic", f"entry '{entry.entry_id}' is missing required field 'source'")
            if "status" not in entry.fields:
                self.issue(entry.line, "semantic", f"entry '{entry.entry_id}' is missing required field 'status'")
            if "type" not in entry.fields and "type" not in section.group_fields:
                self.issue(entry.line, "semantic",
                           f"entry '{entry.entry_id}' is missing required field 'type' and the group has no type")

            for key in ENTRY_SINGLE_KEYS:
                if key in entry.fields and len(entry.fields[key]) != 1:
                    self.issue(entry.line, "semantic",
                               f"{key} is single-valued but appears {len(entry.fields[key])} times")

            for key in ("source", "target"):
                if key in entry.fields:
                    value = entry.fields[key][0][1]
                    if isinstance(value, str):
                        self.issues.extend(brace_balance(value, entry.fields[key][0][0]))

            self._validate_status_consistency(entry)
            self._validate_entry_width(entry, section)

            if self.variant == "glossary":
                self._validate_glossary_entry(entry, section)

        if self.variant == "standard" and not self.entries:
            self.issue(0, "warning", "standard variant file has no entries")

    def _validate_status_consistency(self, entry: Entry) -> None:
        if "status" not in entry.fields:
            return
        status = str(entry.fields["status"][0][1])
        has_target = "target" in entry.fields
        if status in ("translated", "reviewed", "final") and not has_target:
            self.issue(entry.line, "semantic",
                       f"status '{status}' requires a target field")
        if status == "initial" and has_target:
            self.issue(entry.line, "warning", "target is present but status is 'initial'")

    def _effective_max_width(self, entry: Entry, section: Section) -> int | None:
        if "max-width" in entry.fields:
            return int(entry.fields["max-width"][0][1])
        if "max-width" in section.group_fields:
            return int(section.group_fields["max-width"][-1][1])
        return None

    def _validate_entry_width(self, entry: Entry, section: Section) -> None:
        if not self.check_width:
            return
        if "target" not in entry.fields:
            return
        maxw = self._effective_max_width(entry, section)
        if maxw is None:
            return
        target = str(entry.fields["target"][0][1])
        cells = display_cells(target)
        if cells > maxw:
            self.issue(entry.line, "warning",
                       f"target display width {cells} cells exceeds max-width {maxw}: '{target}'")

    def _effective_type(self, entry: Entry, section: Section) -> str | None:
        if "type" in entry.fields:
            return str(entry.fields["type"][0][1])
        if "type" in section.group_fields:
            return str(section.group_fields["type"][-1][1])
        return None

    def _validate_glossary_entry(self, entry: Entry, section: Section) -> None:
        etype = self._effective_type(entry, section)
        if etype is not None and etype not in GLOSSARY_TYPES:
            self.issue(entry.line, "warning",
                       f"glossary type '{etype}' is not term-level; term-level types are: "
                       f"{', '.join(sorted(GLOSSARY_TYPES))}")
        if "target" not in entry.fields:
            self.issue(entry.line, "warning", "glossary entry is missing target")

    def _effective_emotion(self, entry: Entry, section: Section) -> list[str]:
        if "emotion" in entry.fields:
            value = entry.fields["emotion"][0][1]
            return list(value) if isinstance(value, list) else [str(value)]
        if "emotion" in section.group_fields:
            value = section.group_fields["emotion"][-1][1]
            return list(value) if isinstance(value, list) else [str(value)]
        etype = self._effective_type(entry, section)
        default = "neutral" if etype in ("dialogue", "monologue", "idiom") else "objective"
        return [default]

    def canonical_ids(self) -> list[dict[str, str | list[str]]]:
        out: list[dict[str, str | list[str]]] = []
        for e in self.entries:
            section = self._find_section(e.section_path)
            emotion = self._effective_emotion(e, section) if section is not None else ["objective"]
            out.append({
                "entry": e.entry_id,
                "group": e.section_path,
                "canonical_id": ".".join([self.namespace or "", self.clan or "", e.section_path, e.entry_id]),
                "emotion": emotion,
            })
        return out


def tolerant_issues(text: str) -> list[Issue]:
    """Repair a document with the reference implementation and report the repairs.

    The tolerant contract of specification Appendix C is implemented exactly once
    — in ``cliff_format`` — so this repository does not carry a second copy that
    could diverge from it. Without the library the mode fails loudly instead of
    quietly checking something weaker.
    """
    try:
        import cliff_format  # noqa: PLC0415 - optional, resolved at call time
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "error: --tolerant requires cliff_format (install cliff-python, or run with\n"
            "       PYTHONPATH pointing at cliff-python/src). Tolerant parsing is not\n"
            "       reimplemented here, so that both tools share one contract."
        ) from exc

    issues: list[Issue] = []
    try:
        document = cliff_format.parse(text, tolerant=True)
    except cliff_format.CliffParseError as exc:
        cls = exc.category if exc.category else "syntax"
        # A tolerant parser is allowed to refuse (Appendix C.5); a refusal is an
        # error, not a repair.
        return [Issue(exc.line, "semantic" if cls == "vocabulary" else cls, exc.message, exc.text)]
    for issue in cliff_format.validate_document(document):
        issues.append(Issue(issue.line, issue.category, issue.message, issue.text))
    return issues


def style_issues(doc: Document, text: str) -> list[Issue]:
    """Report deviations from style/README.md. Never an error.

    Style is informative (specification 10.1): a document that spells its ids
    ``snake_case`` is valid CLIFF, and a validator that rejected it would be
    enforcing one project's convention on every other project.
    """
    issues: list[Issue] = []

    def note(line: int, kind: str, value: str, raw: str = "") -> None:
        if not value or is_style_identifier(value) or POSITIONAL_RE.match(value):
            return
        issues.append(
            Issue(
                line,
                "style",
                f"{kind} '{value}' is valid CLIFF but does not follow style/README.md "
                "(recommended: kebab-case or PascalCase, not mixed)",
                raw or value,
            )
        )

    note(0, "namespace", str(doc._header_value("namespace") or ""))
    note(0, "clan", str(doc._header_value("clan") or ""))
    for section in doc.sections:
        for segment in section.path.split("."):
            note(section.line, "group segment", segment, f"[{section.path}]")
    for entry in doc.entries:
        note(entry.line, "entry id", entry.entry_id, f"<{entry.entry_id}>")
    for index, raw in enumerate(text.split("\n"), start=1):
        _, terminators, _ = strip_line_terminator(raw)
        if terminators:
            issues.append(
                Issue(
                    index,
                    "style",
                    f"line ends with a '{terminators[-1]}' terminator; CLIFF 1.1 accepts "
                    "it but style/README.md recommends not writing it",
                    raw.strip(),
                )
            )
    return issues


def validate_file(
    path: Path,
    check_width: bool,
    *,
    check_layout: bool = False,
    style: bool = False,
    tolerant: bool = False,
) -> tuple[Document, bool]:
    doc = Document(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        doc.issue(0, "syntax", f"cannot read file: {exc}")
        return doc, False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        doc.issue(0, "syntax", f"file is not valid UTF-8: {exc}")
        return doc, False
    doc.load(text)
    doc.check_width = check_width
    doc.check_layout = check_layout
    doc.validate()
    if style:
        doc.issues.extend(style_issues(doc, text))
    if tolerant:
        # Tolerant mode replaces the strict reading rather than adding to it:
        # the two answer the same question with different strictness, and
        # merging them would report every repaired line twice.
        doc.issues = [i for i in doc.issues if i.cls in ADVISORY_CLASSES]
        doc.issues.extend(tolerant_issues(text))
    if not check_width:
        doc.issues = [i for i in doc.issues if not (i.cls == "warning" and "display width" in i.message)]
    errors = [i for i in doc.issues if i.cls not in ADVISORY_CLASSES]
    return doc, len(errors) == 0


def format_issues(doc: Document) -> str:
    lines: list[str] = []
    for issue in doc.issues:
        cls = issue.cls.upper()
        where = f"{doc.path}:{issue.line}" if issue.line and doc.path is not None else str(doc.path)
        lines.append(f"{where}: [{cls}] {issue.message}")
        if issue.text:
            lines.append(f"    | {issue.text}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="CLIFF 1.1 reference validator",
        epilog=(
            "Layout mismatches are warnings by default: CLIFF 1.1 recommends a "
            "layout rather than requiring it (specification 11.3). Style "
            "deviations are always warnings. Tolerant mode delegates to "
            "cliff_format, the single implementation of Appendix C."
        ),
    )
    ap.add_argument("paths", nargs="*", help=".cliff files or directories (with --suite)")
    ap.add_argument("--suite", action="store_true", help="treat paths as directories of .cliff files")
    ap.add_argument("--check-width", action="store_true", help="report max-width overflow warnings")
    ap.add_argument(
        "--check-layout",
        action="store_true",
        help="report a file-layout/header mismatch as an error instead of a warning",
    )
    ap.add_argument(
        "--style",
        action="store_true",
        help="report style/README.md deviations as warnings",
    )
    ap.add_argument(
        "--tolerant",
        action="store_true",
        help="repair the Appendix C deviations with cliff_format and report each repair",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON results")
    ap.add_argument("--ids", action="store_true", help="print canonical ids")
    args = ap.parse_args(argv)

    files: list[Path] = []
    if args.suite:
        for p in args.paths or ["."]:
            base = Path(p)
            files.extend(sorted(base.rglob("*.cliff")))
    else:
        files = [Path(p) for p in args.paths]
    if not files:
        ap.error("no input files")

    results = []
    exit_code = 0
    for path in files:
        doc, ok = validate_file(
            path,
            args.check_width,
            check_layout=args.check_layout,
            style=args.style,
            tolerant=args.tolerant,
        )
        results.append({"path": str(path), "valid": ok, "issues": [dataclasses.asdict(i) for i in doc.issues]})
        if not ok:
            exit_code = 1
        if args.json:
            continue
        text = format_issues(doc)
        if text:
            print(text)
        if args.ids:
            for cid in doc.canonical_ids():
                emotion = ",".join(cid["emotion"]) if isinstance(cid["emotion"], list) else str(cid["emotion"])
                print(f"{path}: {cid['canonical_id']} [{emotion}]")
        errors = sum(1 for i in doc.issues if i.cls not in ADVISORY_CLASSES)
        advisories = sum(1 for i in doc.issues if i.cls in ADVISORY_CLASSES)
        print(f"{path}: {'VALID' if ok else 'INVALID'} "
              f"({len(doc.sections)} sections, {len(doc.entries)} entries, "
              f"{advisories} warnings, {errors} errors)")
        if not ok:
            print()

    if args.json:
        print(json.dumps({"valid": exit_code == 0, "files": results}, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
