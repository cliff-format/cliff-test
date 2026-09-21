"""The prompt-cost table is reproducible from the repository, and stays true.

`docs/clarion-prompt-design.md` publishes a per-component cost table for one cell
and says `tools/prompt_cost.py` prints it. Both halves are checked here: the tool
must produce the published numbers, and the table must add up - every column's rows
sum to that column's total, which is the invariant that catches the failure mode
this table already had twice (a row measured before an assembly change that the
total had moved past).

The same document publishes the decomposition of the compressed `spec` block, part
by part. That table was the one place the project's own rule - every published token
number is reproducible from an in-repo tool - was broken: the numbers were written
by hand, had drifted from 2 834 to 2 925, and were guarded only by a ceiling with
16 % slack. They are recomputed here, from the document, with the tool's own
function.

Three styles are priced, including the one the shipped configuration selects: a
table that prices only the styles a run does *not* send cannot catch a regression in
the prompt that actually ships.

The table is quoted in the changelog and in the acceptance criteria, so a stale row
is a wrong number in three documents at once.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests._tool_loader import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "prompt_cost.py"
DESIGN = ROOT / "docs" / "clarion-prompt-design.md"
CONFIG = ROOT / "configs" / "deepseek-flash.json"

STYLES = ("digest", "examples", "spec")


def _load_tool():
    return load_module(TOOL, "prompt_cost")


def _published_cell_totals() -> list[int]:
    """The bold numbers of the "one cell" row, read out of the document."""
    row = re.search(r"^\|\s*\*\*one cell[^\n]*$", DESIGN.read_text(encoding="utf-8"), re.M)
    assert row is not None, "the design document no longer publishes the cell totals"
    values = re.findall(r"\*\*([\d\s]+)\*\*", row.group(0))
    return [int(value.replace(" ", "")) for value in values]


def _published_decomposition() -> dict[str, int]:
    """The part-by-part table of the compressed block, read out of the document."""
    text = DESIGN.read_text(encoding="utf-8")
    start = text.index("| part of the compressed block | tokens |")
    rows: dict[str, int] = {}
    for line in text[start:].splitlines()[1:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or not re.fullmatch(r"\*{0,2}[\d ]+\*{0,2}", cells[1]):
            continue  # the header's separator row, and anything that is not a count
        rows[cells[0].strip("* ")] = int(cells[1].strip("* ").replace(" ", ""))
    assert rows, "the design document no longer publishes the block decomposition"
    return rows


def test_the_tool_exists_and_parses() -> None:
    """Guard the guard: a typo in the path would make every check below skip."""
    assert TOOL.is_file(), TOOL
    assert DESIGN.is_file(), DESIGN
    assert CONFIG.is_file(), CONFIG


def test_the_shipped_style_is_one_of_the_priced_styles() -> None:
    """The configuration's style has to be a column of the table.

    This is the failure the table had: it priced `digest` and `examples` while the
    shipped configuration selected `spec`, so the number the release narrative rests
    on was the one nothing measured.
    """
    import json

    shipped = json.loads(CONFIG.read_text(encoding="utf-8"))["prompt_style"]
    tool = _load_tool()
    assert shipped in tool.STYLES, (
        f"the configuration ships prompt_style={shipped!r} and tools/prompt_cost.py "
        f"prices only {tool.STYLES}"
    )


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
    """The bold numbers in the design document, recomputed.

    Reading them out of the document rather than hard-coding them here is the
    point: a test that holds its own copy of the number would pass while the
    document said something else.
    """
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    measured = [bundles[style].budget.total for style in STYLES]
    assert _published_cell_totals() == measured, (
        f"docs/clarion-prompt-design.md publishes {_published_cell_totals()}, "
        f"the tool measures {measured}"
    )


def test_the_published_decomposition_is_the_measured_one() -> None:
    """Every part of the compressed block, recomputed from the document's own rows.

    A ceiling is not a guard for a number that is published: `TOKEN_CEILING` has
    16 % of slack, which is how the block drifted from 2 834 to 2 925 unnoticed.
    """
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts import cliff_rules

    tokenizer = get_tokenizer(json.loads(CONFIG.read_text(encoding="utf-8"))["tokenizer"])
    parts = cliff_rules.block_decomposition(tokenizer)
    published = _published_decomposition()

    assert published["sum of the parts"] == sum(parts.values()), (
        f"the document says the parts sum to {published['sum of the parts']}, "
        f"they sum to {sum(parts.values())}"
    )
    block = tokenizer.count(cliff_rules.build_normative_rules())
    assert published["the block as sent"] == block, (
        f"the document says the block is {published['the block as sent']} tokens, it is {block}"
    )
    # The rows the document names are the parts the tool measures, in the same order,
    # so a part that is added, removed or renamed fails here rather than silently
    # leaving the document describing a block that no longer exists.
    named = [label for label in published if label not in {"sum of the parts", "the block as sent"}]
    assert len(named) == len(parts), f"the document lists {len(named)} parts, the tool {len(parts)}"
    for label, cost in zip(named, parts.values(), strict=True):
        assert published[label] == cost, f"{label}: document {published[label]}, measured {cost}"


def test_the_saving_per_cell_is_constant_across_the_pilot_files() -> None:
    """Why the pilot table is quoted as one number and a range.

    The redesign swaps fixed-size instruction blocks for fixed-size instruction
    blocks, so the saving does not depend on the file: it is the same number of
    tokens per cell on all four pilot files. Only the *percentage* moves, because the
    documents differ in size. A future change that makes the saving
    document-dependent would be a different claim, and this catches it.
    """
    tool = _load_tool()
    savings = []
    for file_id in tool.PILOT_FILES:
        _, bundles = tool.build_bundles(file_id, "bare", CONFIG)
        savings.append(bundles["digest"].budget.total - bundles["examples"].budget.total)
    assert len(set(savings)) == 1, f"the per-cell saving varies by file: {savings}"
    published = re.search(r"\*\*([\d\s]+) tokens per cell\*\*", DESIGN.read_text(encoding="utf-8"))
    assert published is not None, "the design document no longer publishes the per-cell saving"
    assert savings[0] == int(published.group(1).replace(" ", "")), (
        "the per-cell saving quoted in the design document moved"
    )


def test_the_examples_style_is_the_smaller_prompt() -> None:
    """The one claim the whole redesign rests on, asserted directly."""
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    assert bundles["examples"].budget.total < bundles["digest"].budget.total


def test_the_digest_style_is_the_only_one_that_sends_the_specification_text() -> None:
    """The cost the redesign removed, measured rather than asserted."""
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    for style, bundle in bundles.items():
        components = {component.id for component in bundle.budget.components}
        if style == "digest":
            assert "spec.reference" in components, style
        else:
            assert "spec.reference" not in components, style


@pytest.mark.parametrize("style", STYLES)
def test_every_priced_style_renders_its_own_instruction_block(style: str) -> None:
    """Each column of the table is a prompt the harness can actually build.

    A style that rendered nothing distinctive would make its column a copy of
    another, which is how a table comes to describe a prompt nobody sends. The
    document is asserted in every column as well, because that is the one block all
    three share.
    """
    tool = _load_tool()
    _, bundles = tool.build_bundles("ui-console", "bare", CONFIG)
    components = {component.id: component.tokens for component in bundles[style].budget.components}
    assert components["document"] > 0, "every style carries the document it translates"
    distinctive = {
        "digest": "spec.reference",
        "examples": "cliff.examples",
        "spec": "cliff.answer_reminder",
    }[style]
    assert components.get(distinctive, 0) > 0, f"{style} does not render {distinctive}"
