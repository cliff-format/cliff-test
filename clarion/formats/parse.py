"""Read a model's answer back into the CLIF data model.

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

from ..paths import ensure_clif_format
from .plain import parse_json_plain, parse_yaml_plain
from .registry import get_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument

_FENCE_RE = re.compile(
    r"```[A-Za-z0-9_.+-]*[ \t]*\r?\n(?P<body>.*?)\r?\n```",
    re.DOTALL,
)


@dataclass
class ParseOutcome:
    """Result of reading a model answer in one format."""

    format_id: str
    document: ClifDocument | None
    error: str | None = None
    unwrapped: bool = False
    notes: list[str] = field(default_factory=list)
    glossary: ClifDocument | None = None
    extra_documents: int = 0

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


_CLIF_HEADER_RE = re.compile(r"^CLIF 1\.0\s*$", re.MULTILINE)


def split_clif_documents(text: str) -> list[str]:
    """Split an answer that contains more than one CLIF document.

    The terminology workflow lets a model answer with the translated file plus
    a glossary file. Splitting on the version line is exact, because CLIF
    requires it to be the first non-blank line of every document.
    """
    starts = [match.start() for match in _CLIF_HEADER_RE.finditer(text)]
    if len(starts) <= 1:
        return [text]
    bounds = [*starts, len(text)]
    return [text[bounds[i] : bounds[i + 1]].strip() for i in range(len(starts))]


def parse_back(text: str, format_id: str) -> ParseOutcome:
    """Parse a model answer in the given format into a CLIF document.

    For CLIF the answer may legitimately contain a second document: a
    'variant: glossary' file produced by the terminology workflow. It is parsed
    out and reported separately, never scored as the translation and never
    counted as a failure.
    """
    ensure_clif_format()
    import clif_format

    spec = get_format(format_id)
    body, unwrapped = unwrap(text)
    glossary: ClifDocument | None = None
    extra = 0
    try:
        if spec.id == "clif":
            parts = split_clif_documents(body)
            documents = [clif_format.parse(part) for part in parts]
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
            document = clif_format.from_xliff(body)
        elif spec.id == "po":
            document = clif_format.from_po(body)
        elif spec.id == "fluent":
            document = clif_format.from_fluent(body)
        elif spec.id == "json-clif":
            document = clif_format.from_json(body)
        elif spec.id == "yaml-clif":
            document = clif_format.from_yaml(body)
        elif spec.id == "json-plain":
            document = parse_json_plain(body)
        elif spec.id == "yaml-plain":
            document = parse_yaml_plain(body)
        elif spec.id == "csv":
            document = clif_format.from_csv(body)
        elif spec.id == "android":
            document = clif_format.from_android_strings(body)
        elif spec.id == "ios":
            document = clif_format.from_ios_strings(body)
        else:  # pragma: no cover - registry guards this
            raise KeyError(f"no reader for format '{format_id}'")
    except Exception as exc:  # noqa: BLE001 - any parser failure is a data point
        return ParseOutcome(
            format_id=format_id,
            document=None,
            error=f"{type(exc).__name__}: {exc}",
            unwrapped=unwrapped,
        )
    return ParseOutcome(
        format_id=format_id,
        document=document,
        unwrapped=unwrapped,
        glossary=glossary,
        extra_documents=extra,
    )


def entry_index(document: ClifDocument) -> dict[str, tuple[str, object]]:
    """Map entry id to (group path, entry) for every entry in a document."""
    index: dict[str, tuple[str, object]] = {}
    for group in document.groups:
        for entry in group.entries:
            index[entry.id] = (group.path, entry)
    return index


def extract_targets(document: ClifDocument) -> dict[str, str]:
    """Map entry id to translated text.

    Monolingual formats (Android, iOS, Fluent, plain JSON/YAML) keep the only
    text they have in the value slot, which clif-python reads back as the target;
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
