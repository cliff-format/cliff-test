"""Edit-robustness replay: 100 sequential model-style edits stay valid.

This is the deterministic half of criterion C4. The recorded run is a model
performing the edits; `tasks.json` describes the same edits in a machine-
readable form and `apply_edits.py` replays them without a model, so the result
is reproducible in CI.

The replay exists to catch driver bugs, and it has caught one: `is_entry_line`
matched the legacy `entry: id` syntax and not the `<id>` marker, so an "entry
block" ran from one entry to the next *section*. Field lookups then found the
first match in several entries, edits landed on the wrong entry, and the
intended entry lost fields until it was invalid — a failure that looked like a
model-quality result but was a two-character bug in a fixture helper. These
tests therefore assert on the *contents* of a block, not only on the score, so
a regression reports where it broke instead of only how many files failed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EDIT_DIR = ROOT / "tests" / "edit-robustness"


def _load_driver():
    """Import `apply_edits` without running its `main()`."""
    spec = importlib.util.spec_from_file_location(
        "cliff_edit_apply_edits", EDIT_DIR / "apply_edits.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


@pytest.fixture(scope="module")
def tasks() -> list[dict]:
    return json.loads((EDIT_DIR / "tasks.json").read_text(encoding="utf-8"))


def _replay(driver, tasks: list[dict]) -> tuple[list[list[str]], list[tuple[int, str]]]:
    """Apply every task in order, returning each intermediate state."""
    lines = (EDIT_DIR / "base.cliff").read_text(encoding="utf-8").splitlines()
    states: list[list[str]] = []
    problems: list[tuple[int, str]] = []
    for task in sorted(tasks, key=lambda t: int(t["id"])):
        try:
            driver.process_task(lines, task)
        except Exception as exc:  # noqa: BLE001 - report which task broke
            problems.append((int(task["id"]), f"{type(exc).__name__}: {exc}"))
            break
        states.append(list(lines))
    return states, problems


def test_the_task_file_describes_one_hundred_sequential_edits(tasks: list[dict]) -> None:
    assert len(tasks) == 100
    assert [int(t["id"]) for t in tasks] == list(range(1, 101))


def test_entry_lines_are_marker_lines_not_the_legacy_form(driver) -> None:
    """The boundary predicate every other helper depends on."""
    assert driver.is_entry_line("<resolution>")
    assert driver.is_entry_line("  <bad_id>  ")
    assert driver.is_entry_line("<Resolution>,")  # optional terminator
    # The legacy form is what CLIFF rejects, so the driver must not accept it.
    assert not driver.is_entry_line("entry: resolution")
    assert not driver.is_entry_line("source: \"Resolution\"")
    assert not driver.is_entry_line("[video]")


def test_an_entry_block_stops_at_the_next_entry(driver) -> None:
    lines = (EDIT_DIR / "base.cliff").read_text(encoding="utf-8").splitlines()
    start = driver.find_entry(lines, "resolution")
    end = driver.entry_block_end(lines, start)
    block = lines[start:end]
    assert block[0] == "<resolution>"
    assert not any(line.strip().startswith("<") for line in block[1:]), (
        "an entry block must not contain a second entry marker"
    )
    # The next entry is the first structural line after the block.
    assert lines[end].strip() == "<fullscreen>"


def test_every_replayed_edit_is_a_valid_document(driver, tasks: list[dict]) -> None:
    """C4: all 100 intermediate documents must validate with zero errors."""
    cliff_format = pytest.importorskip(
        "cliff_format", reason="cliff-python is not importable"
    )
    states, problems = _replay(driver, tasks)
    assert problems == [], f"the replay aborted: {problems}"
    assert len(states) == 100

    for number, lines in enumerate(states, start=1):
        text = "\n".join(lines) + "\n"
        try:
            document = cliff_format.parse(text)
        except cliff_format.CliffParseError as exc:
            pytest.fail(f"edit {number:03d} does not parse: {exc}")
        errors = [
            issue
            for issue in cliff_format.validate_document(document)
            if issue.category not in ("warning", "extension")
        ]
        assert errors == [], (
            f"edit {number:03d} is invalid: "
            + "; ".join(f"line {i.line}: {i.message}" for i in errors)
        )


def test_an_edit_lands_on_the_entry_it_names(driver, tasks: list[dict]) -> None:
    """A retargeted `target` must change that entry, not an earlier one.

    The original bug changed `vsync`'s target while the task named
    `resolution`, and stripped `source` from `vsync` along the way.
    """
    lines = (EDIT_DIR / "base.cliff").read_text(encoding="utf-8").splitlines()
    first = next(t for t in tasks if t["op"] == "set-target")
    other = "vsync"
    before = "\n".join(
        lines[driver.find_entry(lines, other) : driver.entry_block_end(lines, driver.find_entry(lines, other))]
    )
    driver.process_task(lines, first)
    for entry_id in ("resolution", other):
        start = driver.find_entry(lines, entry_id)
        block = lines[start : driver.entry_block_end(lines, start)]
        assert any(line.startswith("source:") for line in block), (
            f"{entry_id} lost its source field"
        )
    untouched = "\n".join(
        lines[driver.find_entry(lines, other) : driver.entry_block_end(lines, driver.find_entry(lines, other))]
    )
    assert untouched == before, "a task must not touch another entry"


def test_reference_paths_merge_instead_of_repeating_the_key(driver) -> None:
    """`reference` is list-typed, so adding paths lengthens one list."""
    lines = (EDIT_DIR / "base.cliff").read_text(encoding="utf-8").splitlines()
    start = driver.find_entry(lines, "icu-count")
    end = driver.entry_block_end(lines, start)
    existing = [line for line in lines[start:end] if line.startswith("reference:")]
    assert len(existing) == 1
    driver.add_reference(lines, "icu-count", ["src/a.cpp:1", "src/b.cpp:2"])
    end = driver.entry_block_end(lines, start)
    references = [line for line in lines[start:end] if line.startswith("reference:")]
    assert len(references) == 1, "a second reference line would be a duplicate key"
    assert "src/dialog/guide.cpp:12" in references[0], "the existing path is kept"
    assert "src/a.cpp:1" in references[0] and "src/b.cpp:2" in references[0]
