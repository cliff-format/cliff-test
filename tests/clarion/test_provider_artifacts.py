"""Leaked vendor markup: detected, stripped, reported, never confused with CLIFF.

The signature exercised here is the one two recorded CLIFF answers actually carried: a
DeepSeek tool-call delimiter inside a translated file, followed by the XML-ish attribute
line the model attached to it. The vendor calls the format DSML and its documented client
behaviour is that the delimiter arrives in the message content rather than in
``tool_calls``, so a harness that scores content has to expect it.

Held here: the fragment and its tail go, the CLIFF structure around it stays, the strict
reading still rejects it (it is not a format relaxation), and the strip is counted under
``provider-markup`` so a project can see that its endpoint did this.
"""

from __future__ import annotations

from clarion.formats.parse import parse_back
from clarion.formats.provider_artifacts import (
    CATEGORY,
    has_provider_markup,
    strip_provider_markup,
)

BAR = chr(0xFF5C)  # the full-width vertical bar the vendor's delimiter uses

DOCUMENT = (
    "CLIFF 1.1\nnamespace: demo\nclan: settings\n"
    "source-language: en-US\ntarget-language: zh-CN\n\n[video]\ntype: noun\n\n"
    '<resolution>\nsource: "Resolution"\ntarget: "\u5206\u8fa8\u7387"\nstatus: final\n'
)
FRAGMENT = f'</{BAR}{BAR}DSML{BAR}{BAR} parameter>\n<parameter name="final">\n'


def test_the_delimiter_is_recognised_in_every_spelling_a_leak_carries() -> None:
    assert has_provider_markup(FRAGMENT)
    assert has_provider_markup(f"<{BAR}DSML{BAR} parameter>")
    assert has_provider_markup("<|DSML| parameter>")
    assert not has_provider_markup(DOCUMENT)


def test_the_fragment_and_its_tail_are_removed_and_reported() -> None:
    text, fragments = strip_provider_markup(DOCUMENT + FRAGMENT + "CLIFF 1.1\n")
    assert f"{BAR}DSML{BAR}" not in text
    assert "name=\"final\"" not in text, "the attribute line the model attached must go too"
    assert "CLIFF 1.1" in text, "the next document's version line must survive"
    assert len(fragments) == 1
    line, removed = fragments[0]
    assert line == len(DOCUMENT.splitlines()) + 1
    assert removed == [f"</{BAR}{BAR}DSML{BAR}{BAR} parameter>", '<parameter name="final">']


def test_the_document_around_the_fragment_is_untouched() -> None:
    text, _ = strip_provider_markup(DOCUMENT + FRAGMENT + "CLIFF 1.1\n")
    assert text.splitlines()[:4] == DOCUMENT.splitlines()[:4]
    assert "<resolution>" in text and 'status: final' in text


def test_only_the_tolerant_reading_strips_it() -> None:
    """The strict reading is the reference toolchain's: a non-CLIFF line is an error."""
    leaked = DOCUMENT + FRAGMENT
    strict = parse_back(leaked, "cliff", read_mode="strict")
    assert not strict.ok, "strict mode must reject a fragment that is not CLIFF"
    tolerant = parse_back(leaked, "cliff", read_mode="tolerant")
    assert tolerant.ok, "the tolerant reading must survive the leak"
    assert tolerant.repairs == 1, "and report it, once"
    assert [entry.id for group in tolerant.document.groups for entry in group.entries] == [
        "resolution"
    ]


def test_a_clean_answer_is_not_touched_by_the_stripper() -> None:
    text, fragments = strip_provider_markup(DOCUMENT)
    assert text == DOCUMENT
    assert fragments == []


def test_the_category_is_its_own_name_and_not_a_c_repair() -> None:
    assert CATEGORY == "provider-markup"
    assert CATEGORY not in {"list-shape", "field-repeat", "tag-quote", "name-quote",
                            "name-normalized", "version", "id-collision"}
