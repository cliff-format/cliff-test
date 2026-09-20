"""Every format must render, validate, read back and lose nothing it claims to keep."""

from __future__ import annotations

import pytest

from clarion.formats import (
    DEFAULT_FORMATS,
    Arm,
    check_validity,
    extract_targets,
    get_format,
    parse_back,
    render,
    unwrap,
)
from clarion.metrics.fidelity import roundtrip_fidelity


@pytest.mark.parametrize("format_id", DEFAULT_FORMATS)
@pytest.mark.parametrize("arm", [Arm.BARE, Arm.CONTEXT])
def test_render_validate_roundtrip(sample_document, format_id: str, arm: Arm) -> None:
    spec = get_format(format_id)
    if arm is Arm.CONTEXT and not spec.context_capable:
        pytest.skip("format cannot carry context")
    text = render(sample_document, format_id, arm=arm, blank=True)
    report = check_validity(text, format_id)
    assert report.ok, report.errors
    outcome = parse_back(text, format_id)
    assert outcome.document is not None, outcome.error
    assert len(extract_targets(outcome.document)) == 4


@pytest.mark.parametrize("format_id", DEFAULT_FORMATS)
def test_bare_arm_drops_context(sample_document, format_id: str) -> None:
    bare = render(sample_document, format_id, arm=Arm.BARE, blank=True)
    assert "Video settings screen of the console." not in bare
    assert "Use 默认 for default" not in bare


@pytest.mark.parametrize("format_id", [f for f in DEFAULT_FORMATS if f != "cliff"])
def test_context_arm_carries_context(sample_document, format_id: str) -> None:
    text = render(sample_document, format_id, arm=Arm.CONTEXT, blank=True)
    assert "Video settings screen of the console." in text


def test_blank_task_document_has_no_targets(sample_document) -> None:
    text = render(sample_document, "cliff", arm=Arm.CONTEXT, blank=True)
    assert "分辨率" not in text
    assert "Resolution" in text


def test_cliff_roundtrips_losslessly(sample_document) -> None:
    report = roundtrip_fidelity(sample_document, "cliff", arm=Arm.CONTEXT)
    assert report.ok
    assert report.retention == pytest.approx(1.0)


@pytest.mark.parametrize("format_id", DEFAULT_FORMATS)
def test_fidelity_is_measurable_for_every_format(sample_document, format_id: str) -> None:
    report = roundtrip_fidelity(sample_document, format_id, arm=Arm.CONTEXT)
    assert report.ok, report.error
    assert 0.0 <= report.retention <= 1.0


def test_unwrap_strips_markdown_fence() -> None:
    body, unwrapped = unwrap("Here you go:\n\n```cliff\nCLIFF 1.1\n```\n")
    assert unwrapped is True
    assert body == "CLIFF 1.1"


def test_unwrap_leaves_plain_text_alone() -> None:
    body, unwrapped = unwrap("CLIFF 1.1\nnamespace: demo\n")
    assert unwrapped is False
    assert body.startswith("CLIFF 1.1")


@pytest.mark.parametrize(
    ("format_id", "broken"),
    [
        # A 1.0 version line is valid input, so what makes this document broken
        # is the unterminated string - the assertion below is about the string.
        ("cliff", "CLIFF 1.0\nnamespace: demo\n\n[a]\n<x>\nsource: \"unterminated\n"),
        ("xliff-2.1", "<xliff version='2.1' srcLang='en'><file></xliff>"),
        ("po", 'msgid "hello"\nmsgstr broken\n'),
        ("fluent", "this line has no equals sign\n"),
        ("json-cliff", '{"header": {'),
        ("csv", "id,source\n"),
        ("android", "<resources><string>no name</string>"),
        ("ios", '"key" = "value"\n'),
    ],
)
def test_broken_documents_are_rejected(format_id: str, broken: str) -> None:
    report = check_validity(broken, format_id)
    assert not report.ok
    assert report.errors
    assert all(error.line >= 1 for error in report.errors)
