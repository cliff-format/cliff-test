"""Read a model's answer back into the CLIFF data model.

Models wrap files in Markdown fences, add a sentence of prose, or return the
file with a stray heading. None of that is a format failure, so the reader
unwraps the payload first and records that it did. Anything that still fails
to parse is a genuine structural failure of that format under LLM editing,
which is exactly what dimension 7 measures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..paths import ensure_cliff_format
from .plain import parse_json_plain, parse_yaml_plain
from .read_mode import DEFAULT_READ_MODE, READ_MODES, is_tolerant
from .registry import get_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cliff_format import CliffDocument

_FENCE_RE = re.compile(
    r"```[A-Za-z0-9_.+-]*[ \t]*\r?\n(?P<body>.*?)\r?\n```",
    re.DOTALL,
)


@dataclass
class ParseOutcome:
    """Result of reading a model answer in one format."""

    format_id: str
    document: CliffDocument | None
    error: str | None = None
    unwrapped: bool = False
    notes: list[str] = field(default_factory=list)
    glossary: CliffDocument | None = None
    extra_documents: int = 0
    #: Reading that produced this outcome, and the number of Appendix C repairs
    #: it took. A strict read never repairs, so it reports zero.
    read_mode: str = DEFAULT_READ_MODE
    repairs: int = 0

    @property
    def ok(self) -> bool:
        """True when the answer parsed into a document."""
        return self.document is not None


def unwrap(text: str) -> tuple[str, bool]:
    """Strip a surrounding Markdown code fence, if the model added one."""
    stripped = text.strip()
    if "```" not in stripped:
        return stripped, False
    match = _FENCE_RE.search(stripped)
    if match:
        return match.group("body").strip(), True
    # Unbalanced fence: keep everything after the opening fence line.
    lines = stripped.split("\n")
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            rest = [item for item in lines[index + 1 :] if not item.lstrip().startswith("```")]
            return "\n".join(rest).strip(), True
    return stripped, False


_CLIFF_HEADER_RE = re.compile(r"^[ \t]*CLIFF[ \t]+1\.[0-9]+[ \t]*$", re.MULTILINE)


def split_cliff_documents(text: str) -> list[str]:
    """Split an answer that contains more than one CLIFF document.

    The terminology workflow lets a model answer with the translated file plus
    a glossary file. Splitting on the version line is exact, because CLIFF
    requires it to be the first non-blank, non-comment line of every document
    section: the pattern matches the whole line and only a version line, so the
    licence comment block an imported corpus carries ("... CLIFF 1.1 ..." in
    prose) can never be mistaken for a document start. Both 1.0 and 1.1 are
    recognised, because a 1.1 implementation accepts either version line
    (specification 6).
    """
    starts = [match.start() for match in _CLIFF_HEADER_RE.finditer(text)]
    if len(starts) <= 1:
        return [text]
    bounds = [*starts, len(text)]
    return [text[bounds[i] : bounds[i + 1]].strip() for i in range(len(starts))]


def parse_back(text: str, format_id: str, *, read_mode: str = DEFAULT_READ_MODE) -> ParseOutcome:
    """Parse a model answer in the given format into a CLIFF document.

    For CLIFF the answer may legitimately contain a second document: a
    'variant: glossary' file produced by the terminology workflow. It is parsed
    out and reported separately, never scored as the translation and never
    counted as a failure.

    ``read_mode`` selects the CLIFF reading. ``"tolerant"`` (the default) applies
    the documented relaxations of specification Appendix C and counts every
    repair it made, which is the question this harness asks: how much of a
    model's answer is usable. ``"strict"`` asks the other question - would the
    reference toolchain accept the bytes - and is what a source-of-truth check
    needs. The mode is recorded on the outcome so two readings can never be
    confused in a report (Appendix C.1, Appendix C.6).
    """
    if read_mode not in READ_MODES:
        raise ValueError(f"read_mode must be one of {', '.join(READ_MODES)}, got '{read_mode}'")
    tolerant = is_tolerant(read_mode)
    ensure_cliff_format()
    import cliff_format

    spec = get_format(format_id)
    body, unwrapped = unwrap(text)
    glossary: CliffDocument | None = None
    extra = 0
    repairs = 0
    try:
        if spec.id == "cliff":
            parts = split_cliff_documents(body)
            documents = []
            for part in parts:
                document = cliff_format.parse(part, tolerant=tolerant)
                repairs += len(document.corrections)
                documents.append(document)
            translations = [
                item for item in documents if (item.header.variant or "standard") != "glossary"
            ]
            glossaries = [
                item for item in documents if (item.header.variant or "standard") == "glossary"
            ]
            glossary = glossaries[0] if glossaries else None
            extra = max(0, len(translations) - 1) + max(0, len(glossaries) - 1)
            if not translations:
                raise ValueError("the answer contains only a glossary, not a translated file")
            document = translations[0]
        elif spec.id.startswith("xliff"):
            document = cliff_format.from_xliff(body)
        elif spec.id == "po":
            document = cliff_format.from_po(body)
        elif spec.id == "fluent":
            document = cliff_format.from_fluent(body)
        elif spec.id == "json-cliff":
            document = cliff_format.from_json(body)
        elif spec.id == "yaml-cliff":
            document = cliff_format.from_yaml(body)
        elif spec.id == "json-plain":
            document = parse_json_plain(body)
        elif spec.id == "yaml-plain":
            document = parse_yaml_plain(body)
        elif spec.id == "csv":
            document = cliff_format.from_csv(body)
        elif spec.id == "android":
            document = cliff_format.from_android_strings(body)
        elif spec.id == "ios":
            document = cliff_format.from_ios_strings(body)
        else:  # pragma: no cover - registry guards this
            raise KeyError(f"no reader for format '{format_id}'")
    except Exception as exc:  # noqa: BLE001 - any parser failure is a data point
        return ParseOutcome(
            format_id=format_id,
            document=None,
            error=f"{type(exc).__name__}: {exc}",
            unwrapped=unwrapped,
            read_mode=read_mode,
            repairs=repairs,
        )
    return ParseOutcome(
        format_id=format_id,
        document=document,
        unwrapped=unwrapped,
        glossary=glossary,
        extra_documents=extra,
        read_mode=read_mode,
        repairs=repairs,
    )


def entry_index(document: CliffDocument) -> dict[str, tuple[str, object]]:
    """Map entry id to (group path, entry) for every entry in a document."""
    index: dict[str, tuple[str, object]] = {}
    for group in document.groups:
        for entry in group.entries:
            index[entry.id] = (group.path, entry)
    return index


def extract_targets(document: CliffDocument) -> dict[str, str]:
    """Map entry id to translated text.

    Monolingual formats (Android, iOS, Fluent, plain JSON/YAML) keep the only
    text they have in the value slot, which cliff-python reads back as the target;
    bilingual formats keep source and target apart. Reading target first and
    falling back to source therefore works for both without special cases.
    """
    targets: dict[str, str] = {}
    for group in document.groups:
        for entry in group.entries:
            value = entry.target if entry.target is not None else entry.source
            if value is not None:
                targets[entry.id] = value
    return targets
