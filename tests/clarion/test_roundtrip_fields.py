"""Does every format read back the fields it wrote? One field at a time.

`roundtrip_fidelity` answers this in aggregate over the corpus, and the corpus
hides the failure: it has only two entries with a multi-valued list, so a codec
that loses the second element of every list still scores 98 %. This asks the
precise question instead, on a synthetic document built to contain each field in
both its single-valued and its multi-valued form.

Why multi-valued matters: a codec that joins a list with the same character it
uses between fields cannot round-trip two elements, and no single-element value can
ever reveal that. The json-plain cases below are exactly that defect, pinned with a
strict xfail so that fixing the codec turns the marker into an XPASS failure
instead of silently passing.
"""

from __future__ import annotations

import pytest

from clarion.formats import DEFAULT_FORMATS
from clarion.formats.arms import Arm
from clarion.formats.parse import parse_back
from clarion.formats.render import render
from clarion.metrics.fidelity import _effective
from clarion.paths import ensure_cliff_format

#: One entry per field, with the multi-valued form for every field that allows a
#: list. A single element cannot collide with a separator, so the multi-valued
#: cases are the ones a codec has to be able to represent.
PROBES: dict[str, dict[str, object]] = {
    "list-one": {"reference": ["src/ui/panel.cpp:42"]},
    "list-two": {"reference": ["src/ui/panel.cpp:42", "src/ui/dialog.cpp:88"]},
    "emotion-one": {"emotion": ["calm"]},
    "emotion-two": {"emotion": ["serious", "urgent"]},
    "context": {"context": "Reviewed in the 2026 audit."},
    "max-width": {"max_width": 24},
    "status": {"status": "reviewed"},
}

#: Known losses, with the reason the xfail exists. `strict=True` on the marker
#: means a fix makes this suite fail until the entry is deleted.
KNOWN_LOSSES: dict[tuple[str, str], str] = {
    ("json-plain", "list-two"): (
        "plain.py joins a list value with '|' and also separates its fields with '|', so "
        "every element after the first is read back as context; the codec is "
        "clarion/formats/plain.py (_description / _parse_description), and "
        "docs/clarion-prompt-design.md records the measurement"
    ),
    ("json-plain", "emotion-two"): (
        "the same '|' collision: 'serious|urgent' is split into a one-item list plus "
        "a context fragment"
    ),
}

CASES = [
    pytest.param(
        format_id,
        label,
        marks=(
            pytest.mark.xfail(strict=True, reason=KNOWN_LOSSES[(format_id, label)])
            if (format_id, label) in KNOWN_LOSSES
            else ()
        ),
        id=f"{format_id}-{label}",
    )
    for format_id in DEFAULT_FORMATS
    for label in sorted(PROBES)
]


def _document():
    ensure_cliff_format()
    from cliff_format import CliffDocument, Entry, Group, Header

    document = CliffDocument(
        header=Header(
            namespace="probe", clan="roundtrip", source_language="en-US", target_language="zh-CN"
        )
    )
    group = Group(path="ui")
    for label, fields in PROBES.items():
        values: dict[str, object] = {
            "source": f"Source for {label}",
            "target": "初始译文",
            "type": "label",
            "status": "translated",
        }
        values.update(fields)
        group.entries.append(Entry(id=label, **values))  # type: ignore[arg-type]
    document.groups.append(group)
    return document


@pytest.mark.parametrize(("format_id", "label"), CASES)
def test_a_field_survives_the_round_trip(format_id: str, label: str) -> None:
    """Render, read back, and compare the field that this case is about."""
    document = _document()
    text = render(document, format_id, arm=Arm.CONTEXT, blank=False)
    outcome = parse_back(text, format_id)
    assert outcome.ok, f"{format_id} could not read back its own output: {outcome.error}"
    assert outcome.document is not None

    written = _effective(document)[label]
    returned = _effective(outcome.document).get(label)
    assert returned is not None, f"{format_id} dropped the entry '{label}' entirely"
    for field in ("reference", "emotion", "context", "max-width", "status"):
        expected = written.get(field, "")
        if not expected:
            continue
        assert returned.get(field, "") == expected, (
            f"{format_id} lost '{field}' on entry '{label}': "
            f"wrote {expected!r}, read back {returned.get(field, '')!r}"
        )


def test_the_corpus_does_not_hold_the_only_multi_valued_entries() -> None:
    """Guard the guard: this suite is worth nothing if the probes stop being lists.

    If `PROBES` ever lost its two-element cases the defect above would go back to
    being invisible, which is how it survived in the first place.
    """
    lists = {
        label: fields
        for label, fields in PROBES.items()
        if len(fields.get("reference") or fields.get("emotion") or []) > 1
    }
    assert len(lists) >= 2, f"the multi-valued probes are missing: {sorted(PROBES)}"
