"""The two CLIFF readings, and the fixtures that pin them.

CLIFF 1.1 defines a tolerant parsing mode for one consumer - an automated
translation pipeline that must not lose a translation because a model punctuated
a line differently (specification Appendix C) - and CLARION is that consumer.
These tests hold the harness to the two contract points that make the mode
usable in a report:

* the reading in effect is always observable, and a strict read still rejects
  what the strict grammar rejects (Appendix C.1);
* every repair is reported exactly once, with its category, and a repaired
  document serializes into one the strict grammar accepts (Appendix C.6).

The fixtures asserted here are hand-written CLIFF documents in
``tests/fixtures/tolerant/``; the counts are asserted rather than described, so
a change in the repair set has to be deliberate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clarion.formats.parse import parse_back, split_cliff_documents
from clarion.formats.read_mode import READ_MODES, STRICT, TOLERANT
from clarion.formats.validity import check_validity
from clarion.metrics.structure import evaluate_structure
from clarion.paths import ensure_cliff_format

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tolerant"

#: Repairs each tolerant fixture must produce, by category. Pinned so that
#: "the tolerant parser repaired it" can never quietly become "the tolerant
#: parser repaired more than it used to".
EXPECTED_REPAIRS: dict[str, dict[str, int]] = {
    "terminators-and-quoted-tags.zh-CN.cliff": {"tag-quote": 3, "list-shape": 1},
    "quoted-id-and-bare-list.zh-CN.cliff": {"name-quote": 1, "list-shape": 3},
}


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _correction_categories(document) -> dict[str, int]:
    counts: dict[str, int] = {}
    for correction in document.corrections:
        counts[correction.category] = counts.get(correction.category, 0) + 1
    return counts


@pytest.mark.parametrize("name", sorted(EXPECTED_REPAIRS))
def test_tolerant_fixture_repairs_exactly_as_documented(name: str) -> None:
    """Each fixture is refused strictly and repaired tolerantly, by category."""
    text = _fixture(name)

    strict = check_validity(text, "cliff", tolerant=False)
    assert not strict.ok, "a tolerant fixture must fail the strict grammar"
    assert strict.read_mode == STRICT
    assert strict.repairs == 0, "a strict read never repairs"

    tolerant = check_validity(text, "cliff", tolerant=True)
    assert tolerant.ok, tolerant.errors
    assert tolerant.read_mode == TOLERANT
    assert tolerant.repairs == sum(EXPECTED_REPAIRS[name].values())

    outcome = parse_back(text, "cliff", read_mode=TOLERANT)
    assert outcome.ok, outcome.error
    assert outcome.read_mode == TOLERANT
    assert outcome.repairs == tolerant.repairs
    assert _correction_categories(outcome.document) == EXPECTED_REPAIRS[name]


@pytest.mark.parametrize("name", sorted(EXPECTED_REPAIRS))
def test_each_repair_is_reported_once(name: str) -> None:
    """Appendix C.6: an unreported repair is indistinguishable from data loss.

    It is also the regression test for the double-report defect: the CLIFF
    checker used to append one warning from ``document.corrections`` on top of
    the ones ``validate_document`` already emits.
    """
    report = check_validity(_fixture(name), "cliff", tolerant=True)
    corrections = [w for w in report.warnings if w.category == "correction"]
    assert len(corrections) == report.repairs
    assert len({(w.line, w.message) for w in corrections}) == len(corrections), (
        "the same repair was reported twice"
    )


@pytest.mark.parametrize("name", sorted(EXPECTED_REPAIRS))
def test_terminators_are_never_reported_as_repairs(name: str) -> None:
    """A trailing `,`/`;` is standard 1.1 syntax (5.6), not a repair."""
    text = _fixture(name)
    report = check_validity(text, "cliff", tolerant=True)
    assert not [w for w in report.warnings if "terminator" in w.message.lower()]


@pytest.mark.parametrize("name", sorted(EXPECTED_REPAIRS))
def test_repaired_document_serializes_into_strictly_valid_cliff(name: str) -> None:
    """Appendix C.6: fixing the input is the point, so the output must be valid."""
    ensure_cliff_format()
    import cliff_format

    outcome = parse_back(_fixture(name), "cliff", read_mode=TOLERANT)
    assert outcome.document is not None
    serialized = cliff_format.serialize(outcome.document)
    assert check_validity(serialized, "cliff", tolerant=False).ok


def test_identifiers_are_never_rewritten_by_a_tolerant_read() -> None:
    """5.5/10.1: the id is the translation match key, so it is copied verbatim."""
    outcome = parse_back(
        _fixture("quoted-id-and-bare-list.zh-CN.cliff"), "cliff", read_mode=TOLERANT
    )
    assert outcome.document is not None
    ids = [entry.id for group in outcome.document.groups for entry in group.entries]
    assert ids == ["resolution", "Fullscreen"]


def test_read_mode_rejects_an_unknown_value() -> None:
    """A typo must fail loudly: silently scoring under the wrong reading would
    make every number in a report unreadable."""
    with pytest.raises(ValueError, match="read_mode must be one of"):
        parse_back("CLIFF 1.1\n", "cliff", read_mode="lenient")
    assert READ_MODES == (STRICT, TOLERANT)


def test_strict_and_tolerant_readings_differ_on_the_same_answers() -> None:
    """The two readings must bracket each other, never agree by accident."""
    for name in sorted(EXPECTED_REPAIRS):
        text = _fixture(name)
        assert not check_validity(text, "cliff", tolerant=False).ok
        assert check_validity(text, "cliff", tolerant=True).ok


def test_tolerant_reading_still_refuses_what_appendix_c5_forbids() -> None:
    """Appendix C.5: tolerant parsing preserves information, it never guesses it.

    Each of these answers is missing content that no repair could invent, so the
    tolerant reading must fail them exactly as the strict one does.
    """
    header = (
        'CLIFF 1.1\nnamespace: demo\nclan: forbidden\n'
        'source-language: en-US\ntarget-language: zh-CN\n\n[video]\ntype: label\n\n'
    )
    forbidden = {
        "missing source": '<a>\ntarget: "保存"\nstatus: final\n',
        "missing status": '<a>\nsource: "Save"\ntarget: "保存"\n',
        "missing effective type": None,  # gets its own document below
        "status contradicts target": '<a>\nsource: "Save"\nstatus: translated\n',
        "unbalanced ICU": '<a>\nsource: "Save"\ntarget: "{n, plural, other {x}"\nstatus: final\n',
        "tag outside the vocabulary": '<a>\nsource: "Save"\ntarget: "保存"\nstatus: Finished\n',
        "unknown non-x- key": '<a>\nsource: "Save"\ntarget: "保存"\nstatus: final\nnickname: "x"\n',
    }
    for label, body in forbidden.items():
        if body is None:
            text = (
                'CLIFF 1.1\nnamespace: demo\nclan: forbidden\n'
                'source-language: en-US\ntarget-language: zh-CN\n\n'
                '<a>\nsource: "Save"\ntarget: "保存"\nstatus: final\n'
            )
        else:
            text = header + body
        tolerant = check_validity(text, "cliff", tolerant=True)
        assert not tolerant.ok, f"tolerant parsing must refuse {label}"


def test_split_cliff_documents_recognises_both_version_lines() -> None:
    """An answer may carry a translated file plus a glossary; both are 1.0 or 1.1.

    A 1.1 implementation accepts either version line (6), and the terminology
    workflow appends a second document to the answer, so a splitter that only
    recognised `CLIFF 1.0` would hand two documents to a parser that reads one.
    """
    for version in ("1.0", "1.1"):
        answer = (
            f"CLIFF {version}\nnamespace: demo\nclan: settings\n"
            "source-language: en-US\ntarget-language: zh-CN\n\n"
            '[main]\ntype: label\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n\n'
            f"CLIFF {version}\nnamespace: demo\nclan: settings-terms\n"
            "source-language: en-US\ntarget-language: zh-CN\nvariant: glossary\n\n"
            '[terms]\ntype: noun\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n'
        )
        parts = split_cliff_documents(answer)
        assert len(parts) == 2, f"version {version} was not split: {len(parts)} part(s)"
        assert parts[1].lstrip().startswith(f"CLIFF {version}")

        outcome = parse_back(answer, "cliff")
        assert outcome.document is not None, outcome.error
        assert (outcome.document.header.variant or "standard") == "standard"
        assert outcome.glossary is not None
        assert outcome.glossary.header.variant == "glossary"


def test_split_handles_a_1_0_translation_with_a_1_1_glossary() -> None:
    """The fixture the validator suite also uses: a 1.0 answer, a 1.1 glossary.

    Real answers mix the two, because a translator returns the file it was given
    and writes the glossary in the version the current specification describes.
    """
    answer = (FIXTURES / "two-documents.txt").read_text(encoding="utf-8")
    parts = split_cliff_documents(answer)
    assert len(parts) == 2, [p.splitlines()[0] for p in parts]

    outcome = parse_back(answer, "cliff")
    assert outcome.document is not None, outcome.error
    assert outcome.document.spec_version == "1.0"
    assert outcome.glossary is not None
    assert outcome.glossary.spec_version == "1.1"
    # One translation and one glossary is the documented two-deliverable shape,
    # so nothing beyond that pair is counted as an extra document.
    assert outcome.extra_documents == 0


def test_split_ignores_a_comment_that_mentions_a_version() -> None:
    """A licence comment may contain the text 'CLIFF 1.1'; it is not a document start."""
    answer = (
        "# Imported corpus file. Generated for CLIFF 1.1 and dedicated to the public domain.\n"
        "# SPDX-License-Identifier: CC0-1.0\n"
        "CLIFF 1.1\nnamespace: demo\nclan: settings\n"
        "source-language: en-US\ntarget-language: zh-CN\n\n"
        '[main]\ntype: label\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n'
    )
    parts = split_cliff_documents(answer)
    assert len(parts) == 1
    assert parts[0].lstrip().startswith("#")


def test_an_answer_that_is_only_a_glossary_is_refused() -> None:
    """The glossary is a second deliverable, never the translation itself."""
    answer = (
        "CLIFF 1.1\nnamespace: demo\nclan: settings-terms\n"
        "source-language: en-US\ntarget-language: zh-CN\nvariant: glossary\n\n"
        '[terms]\ntype: noun\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n'
    )
    outcome = parse_back(answer, "cliff")
    assert outcome.document is None
    assert outcome.error is not None and "only a glossary" in outcome.error


def test_structure_report_carries_the_reading_it_used(sample_document) -> None:
    """A report row must be able to state which question its number answers."""
    deviant = (
        'CLIFF 1.1\nnamespace: clarion\nclan: fixture\n'
        'source-language: en-US\ntarget-language: zh-CN\n\n'
        '[settings.video]\ntype: label\n\n<resolution>\nsource: "Resolution"\n'
        'target: "分辨率"\nstatus: "final"\n'
    )
    strict, _targets, _glossary = evaluate_structure(
        sample_document, deviant, "cliff", read_mode=STRICT
    )
    assert strict.read_mode == STRICT
    assert strict.repairs == 0
    assert not strict.valid

    tolerant, _targets, _glossary = evaluate_structure(
        sample_document, deviant, "cliff", read_mode=TOLERANT
    )
    assert tolerant.read_mode == TOLERANT
    assert tolerant.repairs == 1
    assert tolerant.valid
    assert tolerant.as_dict()["read_mode"] == TOLERANT
    assert tolerant.as_dict()["repairs"] == 1
