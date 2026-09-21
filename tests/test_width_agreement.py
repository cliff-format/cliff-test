"""The width metric exists three times, and this holds the copies to each other.

The specification defines `max-width` in **display cells** (§15), and three modules
compute it independently:

* `tools/cliff_validator.py` (the in-repo reference validator, for its own
  `max-width` diagnostic) - public as `display_cells`;
* `cliff_format.validator` (the published package) - private as `_display_cells`;
* `clarion.metrics.width` (the harness) - public as `display_cells`.

`tests/quality/check_constraints.py` used to be a fourth; it now calls the validator's,
which is why this test exists rather than an assertion inside it. The alternative - a
public alias for the package's private function - would have changed a released
package's API for the sake of a test tool, and the private name is deliberate there.
So the copies are compared instead, on a table chosen for the cases where a width
function can disagree: a combining mark that must not be counted, CJK and fullwidth
characters that must count as two, halfwidth katakana that must count as one, an emoji
outside the East Asian ranges, and the empty string.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from tests._tool_loader import load_module  # noqa: E402

#: (case, text) pairs. The names say what each one is for, because a width failure
#: reads as an off-by-one without them.
CASES: tuple[tuple[str, str], ...] = (
    ("ascii", "Resolution"),
    ("cjk", "分辨率"),
    ("fullwidth", "ＡＢＣ"),
    ("halfwidth-katakana", "ｱｲｳ"),
    ("combining-mark", "e\u0301"),          # one cell: the accent is not a character
    ("combining-in-cjk", "\u304b\u3099"),   # one cell too
    ("emoji", "\U0001f642"),                # East Asian Width 'W', so two cells
    ("mixed", "Token 令牌 42"),
    ("empty", ""),
)


def _implementations():
    """Every module that computes the metric, as (name, function) pairs."""
    from cliff_format.validator import _display_cells as package_width

    from clarion.metrics.width import display_cells as clarion_width

    validator = load_module(ROOT / "tools" / "cliff_validator.py", "width_agreement_validator")
    return (
        ("cliff_format.validator", package_width),
        ("clarion.metrics.width", clarion_width),
        ("tools/cliff_validator", validator.display_cells),
    )


def test_the_checker_does_not_carry_its_own_width_function() -> None:
    """Guard the guard: the point of the agreement test is that there are three.

    If a fourth copy appears in the quality checker, comparing the three that exist
    would say nothing about the number the report publishes.
    """
    source = (ROOT / "tests" / "quality" / "check_constraints.py").read_text(encoding="utf-8")
    assert "def display_cells" not in source, "the checker re-implemented the metric again"
    assert "cv.display_cells(" in source, "the checker must call the validator's function"


@pytest.mark.parametrize("name,text", CASES, ids=[case for case, _ in CASES])
def test_every_implementation_agrees(name: str, text: str) -> None:
    measured = {impl_name: function(text) for impl_name, function in _implementations()}
    assert len(set(measured.values())) == 1, (
        f"{name} ({text!r}): the width implementations disagree: {measured}"
    )


def test_the_table_separates_the_cases_that_matter() -> None:
    """A table where every case scored the same would pass a broken implementation.

    Each assertion is the specification's own reading of §15: two cells for CJK and
    fullwidth, one for halfwidth and for a combining mark, and no credit for the
    empty string.
    """
    _, width = _implementations()[0]
    values = {name: width(text) for name, text in CASES}
    assert values["cjk"] == 6 and values["fullwidth"] == 6
    assert values["ascii"] == 10
    assert values["halfwidth-katakana"] == 3
    # `e` + U+0301 is one cell (the accent contributes nothing), and か + U+3099 is
    # two: the mark is skipped, the base kana is wide. Written down because the pair
    # is what distinguishes "skip combining marks" from "skip everything non-ASCII".
    assert values["combining-mark"] == 1
    assert values["combining-in-cjk"] == 2
    assert values["emoji"] == 2
    assert values["empty"] == 0
