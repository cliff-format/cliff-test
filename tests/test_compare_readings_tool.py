"""The two-readings tool reproduces the numbers the acceptance criteria publish.

`docs/acceptance-criteria.md` quotes a table of strict-versus-tolerant validity
percentages for the recorded run, and names `tools/compare_readings.py` as the way
to reproduce it. A tool cited as evidence has to be checked against the claim it
supports, or the citation is decoration.

The recorded run lives in `results/`, which is gitignored: a fresh clone has no run
to score. The test skips in that case rather than passing quietly on nothing, the
same convention the sibling-checkout tests use.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._tool_loader import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "compare_readings.py"

#: The run the acceptance criteria quote, and the figures it quotes from it.
RECORDED = ROOT / "results" / "clarion-deepseek-flash-20260920T114819+0000-6a5259"
PUBLISHED = {
    # The repair counts fell by one (bare) and two (context) when Appendix C.2.5 was
    # clarified: two answers in this run end with marker-shaped markup, and the
    # reading used to normalize the tag name into an entry and report a
    # `name-normalized` repair for it (plus an `id-collision` where the name already
    # existed). Those answers were failing before the clarification and still are, so
    # only the repair column moved - the two rates are unchanged, which is what this
    # test exists to hold.
    "bare": {"strict": 89.6, "tolerant": 95.8, "repairs": 3},
    "context": {"strict": 83.3, "tolerant": 89.6, "repairs": 4},
}


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


@pytest.mark.skipif(not RECORDED.is_dir(), reason="the recorded run is not on disk")
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


@pytest.mark.skipif(not RECORDED.is_dir(), reason="the recorded run is not on disk")
def test_the_tool_reports_the_same_numbers_as_the_test(capsys) -> None:
    """And the tool itself prints them, so the citation is the tool's own output."""
    module = _load_tool()
    assert module.main([str(RECORDED)]) == 0
    out = capsys.readouterr().out
    assert "strict   valid: 43/48 = 89.6%" in out, out
    assert "tolerant valid: 46/48 = 95.8%" in out, out
    assert "repairs made  : 3 (0.06 per answer)" in out, out
    assert "strict   valid: 40/48 = 83.3%" in out, out
