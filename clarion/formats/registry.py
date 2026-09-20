"""The format registry: which localization formats CLARION compares.

Every format in this registry can be produced from, and read back into, a CLIFF
document with cliff-python (the two plain key/value dialects are produced by
clarion.formats.plain, which is written against the same data model). This is
the fairness rule of the whole benchmark: no format is ever hand-written, so a
format never wins or loses because of how a human phrased its fixture.

Two properties decide how a format is used in an experiment:

bilingual
    The format has a place for source and target in the same file (CLIFF,
    XLIFF, PO, CSV and the CLIFF-shaped JSON/YAML). A bilingual translation
    task ships the source and asks the model to fill the target.

context_capable
    The format has a documented channel that can carry the CLIFF context
    payload (comments, notes or metadata elements). Formats that are not
    context capable can only ever run the bare arm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatSpec:
    """Static description of one competing localization format."""

    id: str
    label: str
    extension: str
    bilingual: bool
    context_capable: bool
    context_channel: str
    requires: tuple[str, ...] = ()
    xliff_version: str | None = None


FORMATS: dict[str, FormatSpec] = {
    "cliff": FormatSpec(
        id="cliff",
        label="CLIFF 1.1",
        extension=".cliff",
        bilingual=True,
        context_capable=True,
        context_channel="native fields (info, standard, group metadata, entry context)",
    ),
    "xliff-2.1": FormatSpec(
        id="xliff-2.1",
        label="XLIFF 2.1",
        extension=".xlf",
        bilingual=True,
        context_capable=True,
        context_channel="mda:metadata metaGroup plus xliff notes",
        xliff_version="2.1",
    ),
    "xliff-2.2": FormatSpec(
        id="xliff-2.2",
        label="XLIFF 2.2",
        extension=".xlf",
        bilingual=True,
        context_capable=True,
        context_channel="mda:metadata metaGroup, notes and the glossary module",
        xliff_version="2.2",
    ),
    "po": FormatSpec(
        id="po",
        label="gettext PO",
        extension=".po",
        bilingual=True,
        context_capable=True,
        context_channel="extracted comments (#.) and msgctxt",
    ),
    "fluent": FormatSpec(
        id="fluent",
        label="Fluent",
        extension=".ftl",
        bilingual=False,
        context_capable=True,
        context_channel="message comments (#)",
    ),
    "json-cliff": FormatSpec(
        id="json-cliff",
        label="JSON (CLIFF data model)",
        extension=".json",
        bilingual=True,
        context_capable=True,
        context_channel="native JSON fields of the CLIFF data model",
    ),
    "json-plain": FormatSpec(
        id="json-plain",
        label="JSON (plain i18n)",
        extension=".json",
        bilingual=False,
        context_capable=True,
        context_channel="Chrome-extension style message/description objects",
    ),
    "yaml-cliff": FormatSpec(
        id="yaml-cliff",
        label="YAML (CLIFF data model)",
        extension=".yaml",
        bilingual=True,
        context_capable=True,
        context_channel="native YAML fields of the CLIFF data model",
        requires=("yaml",),
    ),
    "yaml-plain": FormatSpec(
        id="yaml-plain",
        label="YAML (plain i18n)",
        extension=".yaml",
        bilingual=False,
        context_capable=True,
        context_channel="YAML comments above each key",
        requires=("yaml",),
    ),
    "csv": FormatSpec(
        id="csv",
        label="CSV",
        extension=".csv",
        bilingual=True,
        context_capable=True,
        context_channel="dedicated context/type/emotion/max-width columns",
    ),
    "android": FormatSpec(
        id="android",
        label="Android strings.xml",
        extension=".xml",
        bilingual=False,
        context_capable=True,
        context_channel="XML comment preceding the string element",
    ),
    "ios": FormatSpec(
        id="ios",
        label="iOS Localizable.strings",
        extension=".strings",
        bilingual=False,
        context_capable=True,
        context_channel="block comment preceding the key",
    ),
}

DEFAULT_FORMATS: tuple[str, ...] = (
    "cliff",
    "xliff-2.1",
    "po",
    "fluent",
    "json-cliff",
    "json-plain",
    "yaml-cliff",
    "csv",
    "android",
    "ios",
)


def format_ids() -> list[str]:
    """All registered format ids, in registry order."""
    return list(FORMATS)


def get_format(format_id: str) -> FormatSpec:
    """Look up a format, raising a helpful error for unknown ids."""
    try:
        return FORMATS[format_id]
    except KeyError:
        raise KeyError(
            f"unknown format '{format_id}'; known formats: {', '.join(FORMATS)}"
        ) from None
