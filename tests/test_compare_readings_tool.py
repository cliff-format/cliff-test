"""The two-readings tool reproduces the numbers the acceptance criteria publish.

`docs/acceptance-criteria.md` quotes a table of strict-versus-tolerant validity
percentages for the recorded run, and names `tools/compare_readings.py` as the way
to reproduce it. A tool cited as evidence has to be checked against the claim it
supports, or the citation is decoration.

The recorded run lives in `results/`, which is gitignored: a fresh clone has no run
to score. The tests skip in that case rather than passing quietly on nothing - but
only when the directory holds **no run at all**. They used to skip whenever one
particular run was absent, which meant that pruning `results/` turned the C6.11
guard into three green skips; `test_the_recorded_run_is_the_one_on_disk` fails
loudly instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._tool_loader import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "compare_readings.py"
RESULTS = ROOT / "results"

#: The run the acceptance criteria quote, and the figures it quotes from it.
#:
#: The run is the shipped protocol - `deepseek-flash`, reasoning `low`, temperature
#: 1.3, the compressed CLIFF specification (`prompt_style: spec`), read back
#: tolerantly - over the same 16 documents and 392 entries as every earlier one.
RECORDED = RESULTS / "clarion-deepseek-flash-20260921T211031+0000-de29a5"
PUBLISHED = {
    "bare": {"strict": 87.5, "tolerant": 91.7, "repairs": 2},
    "context": {"strict": 85.4, "tolerant": 91.7, "repairs": 13},
}

#: True only where nothing has been run yet - a fresh clone, or a tree whose
#: `results/` was pruned to nothing. A missing *particular* run is a failure, not a
#: skip: see the module docstring.
NO_RUNS = not RESULTS.is_dir() or not any(RESULTS.glob("clarion-*/records.jsonl"))

needs_run = pytest.mark.skipif(NO_RUNS, reason="no run on disk (results/ is gitignored)")


def _load_tool():
    return load_module(TOOL, "compare_readings")


def _records(run: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_the_tool_exists_and_parses() -> None:
    """Guard the guard: a typo in the path would make every check below skip."""
    assert TOOL.is_file(), TOOL


def test_the_recorded_run_is_the_one_on_disk() -> None:
    """Pruning `results/` must break this file, not silence it.

    Three tests here compare a stored run against a published table. When the run
    they name is absent they skip, and a suite of green skips is indistinguishable
    from a suite that checked something - so the absence of *this* run, where other
    runs exist, is asserted rather than skipped.
    """
    if NO_RUNS:
        pytest.skip("no run on disk (results/ is gitignored)")
    assert RECORDED.is_dir(), (
        f"{RECORDED.name} is not on disk, but {RESULTS} holds other runs. Point RECORDED at "
        "the run the documents quote, or delete the runs it was pruned with - do not leave "
        "the two-readings guard skipping."
    )


@needs_run
def test_the_published_two_readings_table_is_reproducible() -> None:
    """Recompute the table from the stored answers and compare with the document."""
    from clarion.formats.validity import check_validity

    run = RECORDED
    answers = [
        row
        for row in _records(run)
        if row.get("kind") == "translation" and row["format"] == "cliff"
    ]
    assert answers, "the recorded run has no CLIFF translation rows"

    for arm, expected in PUBLISHED.items():
        cells = [row for row in answers if row.get("arm") == arm]
        strict_ok = tolerant_ok = repairs = reread = 0
        for row in cells:
            path = run / str(row["answer_file"])
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            reread += 1
            strict_ok += 1 if check_validity(text, "cliff", tolerant=False).ok else 0
            tolerant = check_validity(text, "cliff", tolerant=True)
            tolerant_ok += 1 if tolerant.ok else 0
            repairs += tolerant.repairs
        assert reread == 48, f"{arm}: expected 48 stored answers, re-read {reread}"
        assert round(100.0 * strict_ok / reread, 1) == expected["strict"], arm
        assert round(100.0 * tolerant_ok / reread, 1) == expected["tolerant"], arm
        assert repairs == expected["repairs"], arm
        # The tolerant reading may only ever salvage: every strictly valid answer is
        # tolerantly valid too, and the repairs are the difference.
        assert tolerant_ok >= strict_ok, arm


@needs_run
def test_the_tool_reports_the_same_numbers_as_the_test(capsys) -> None:
    """And the tool itself prints them, so the citation is the tool's own output."""
    module = _load_tool()
    assert module.main([str(RECORDED)]) == 0
    out = capsys.readouterr().out
    assert "strict   valid: 42/48 = 87.5%" in out, out
    assert "tolerant valid: 44/48 = 91.7%" in out, out
    assert "repairs made  : 2 (0.04 per answer)" in out, out
    assert "strict   valid: 41/48 = 85.4%" in out, out
    assert "repairs made  : 13 (0.27 per answer)" in out, out
    # Every repair is a shape repair. A run whose repairs included invented content
    # would be a different claim about what the tolerant reading does, and the kinds
    # are printed per arm precisely so this can be read rather than assumed.
    assert "C.2.5 identifier containing a reserved character" in out, out
