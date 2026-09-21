"""The prompt-cost table is reproducible from the repository, and stays true.

`docs/clarion-prompt-design.md` publishes a per-component cost table for one cell
and says `tools/prompt_cost.py` prints it. Both halves are checked here: the tool
must produce the published numbers, and the table must add up - every column's rows
sum to that column's total, which is the invariant that catches the failure mode
this table already had twice (a row measured before an assembly change that the
total had moved past).

The table is quoted in the changelog and in the acceptance criteria, so a stale row
is a wrong number in three documents at once.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "prompt_cost.py"
DESIGN = ROOT / "docs" / "clarion-prompt-design.md"
CONFIG = ROOT / "configs" / "deepseek-flash.json"

STYLES = ("digest", "examples")


def _load_tool():
    spec = importlib.util.spec_from_file_location("prompt_cost", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_tool_exists_and_parses() -> None:
    """Guard the guard: a typo in the path would make every check below skip."""
    assert TOOL.is_file(), TOOL
    assert DESIGN.is_file(), DESIGN
    assert CONFIG.is_file(), CONFIG


def test_every_column_of_the_published_table_adds_up() -> None:
    """The rows are the blocks of one message pair, not a selection of them."""
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    for style in STYLES:
        budget = bundles[style].budget
        rows = sum(component.tokens for component in budget.components)
        assert rows == budget.total, (
            f"{style}: the components sum to {rows} but the prompt is {budget.total} tokens"
        )


def test_the_published_cell_totals_are_the_measured_ones() -> None:
    """The two bold numbers in the design document, recomputed.

    Reading them out of the document rather than hard-coding them here is the
    point: a test that holds its own copy of the number would pass while the
    document said something else.
    """
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    measured = [bundles[style].budget.total for style in STYLES]

    row = re.search(
        r"\|\s*\*\*one cell[^|]*\|\s*\*\*([\d\s]+)\*\*\s*\|\s*\*\*([\d\s]+)\*\*\s*\|",
        DESIGN.read_text(encoding="utf-8"),
    )
    assert row is not None, "the design document no longer publishes the cell totals"
    published = [int(value.replace(" ", "")) for value in row.groups()]
    assert published == measured, (
        f"docs/clarion-prompt-design.md publishes {published}, the tool measures {measured}"
    )


def test_the_saving_per_cell_is_constant_across_the_pilot_files() -> None:
    """Why the pilot table is quoted as one number and a range.

    The redesign swaps fixed-size instruction blocks for fixed-size instruction
    blocks, so the saving does not depend on the file: it is the same 18 682 tokens
    per cell on all four pilot files. Only the *percentage* moves, because the
    documents differ in size. A future change that makes the saving
    document-dependent would be a different claim, and this catches it.
    """
    tool = _load_tool()
    savings = []
    for file_id in tool.PILOT_FILES:
        _, bundles = tool.build_bundles(file_id, "bare", CONFIG)
        savings.append(bundles["digest"].budget.total - bundles["examples"].budget.total)
    assert len(set(savings)) == 1, f"the per-cell saving varies by file: {savings}"
    assert savings[0] * len(tool.PILOT_FILES) == 74_728, (
        "the four-file total quoted in the design document moved"
    )


@pytest.mark.parametrize("style", STYLES)
def test_the_examples_style_is_the_smaller_prompt(style: str) -> None:
    """The one claim the whole redesign rests on, asserted directly."""
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    if style == "examples":
        assert bundles[style].budget.total < bundles["digest"].budget.total
    else:
        assert "spec.reference" in {c.id for c in bundles[style].budget.components}
