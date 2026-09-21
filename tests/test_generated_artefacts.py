"""The tracked artefacts the suite regenerates, and the ones nothing regenerates.

Five files are both committed and produced by running the suite, and until now nothing
compared the two: a code change could leave the committed copy stale with no test
failing (the specification repository runs the equivalent check in CI,
`python tools/regenerate_examples.py --check`).

* `tools/token_benchmark.py --check` now renders its nine artefacts - two reports and
  seven fixture files - in memory and compares them byte for byte with the tracked
  files. The first three tests below hold that check to the tree, to a perturbed
  report, and to a perturbed fixture (which also proves the check mode writes nothing).
* `tests/quality/translator-output.cliff` and `tests/quality/quality-report.md` have no
  generator at all: a translator agent wrote the first and an evaluator agent the
  second, from `corpus.cliff`. What can be checked deterministically is checked here -
  the committed output still satisfies the mechanical constraints, and the count the
  report publishes is the count the checker prints.
* `tests/edit-robustness/report.md` is in the same position and is *not* guarded: its
  subject is the `edits/` tree it describes, which is gitignored, so there is nothing
  in the repository to recompute it from. Recorded rather than faked.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from tests._tool_loader import load_module

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "tools" / "token_benchmark.py"
QUALITY = ROOT / "tests" / "quality"

#: A tracked artefact of each kind the check covers, chosen small so a perturbation is
#: cheap to write and restore.
REPORT = ROOT / "tests" / "benchmark" / "report.md"
FIXTURE = ROOT / "tests" / "benchmark" / "fixtures" / "data.csv"


def _benchmark():
    return load_module(BENCHMARK, "token_benchmark_under_test")


def test_the_check_passes_on_the_current_tree(capsys) -> None:
    """The committed artefacts are what the tool renders today."""
    tool = _benchmark()
    assert tool.check() == 0, capsys.readouterr().out
    assert "every tracked artefact matches" in capsys.readouterr().out


def test_the_check_reaches_the_tree_through_its_command_line(capsys) -> None:
    """`python tools/token_benchmark.py --check` is what CI will run, not `check()`.

    The dispatch is part of the guard: a `--check` flag that is parsed and then ignored
    would let a stale artefact through while `check()` itself passed.
    """
    tool = _benchmark()
    assert tool.main(["--check"]) == 0, capsys.readouterr().out


def test_the_check_writes_nothing(monkeypatch, capsys) -> None:
    """`--check` must be safe to run in CI, where a clean tree is the point.

    Asserted by intercepting `Path.write_text` rather than by comparing the tree with
    itself: rendering the artefacts and writing them back unchanged is a no-op, so a
    content comparison would pass while the check mode was still writing to the
    repository.
    """
    tool = _benchmark()
    written: list[str] = []
    original = Path.write_text

    def record(self, data, *args, **kwargs):
        written.append(str(self))
        return original(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", record)
    assert tool.main(["--check"]) == 0, capsys.readouterr().out
    assert written == [], f"--check wrote to the tree: {written}"
    # And prove the interceptor is live, so `written == []` above means the check did
    # not write rather than the recorder being unable to see writes. Deliberately not
    # by running the writer (`main()` without `--check`): that would rewrite the tracked
    # artefacts inside a test, which is the thing this file exists to prevent.
    probe = ROOT / "tests" / "_write_probe.txt"
    try:
        probe.write_text("probe", encoding="utf-8")
        assert written == [str(probe)], "the write interceptor missed a write"
    finally:
        probe.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "path,label",
    [(REPORT, "report.md"), (FIXTURE, "data.csv")],
    ids=["report", "fixture"],
)
def test_the_check_fails_and_names_the_file_when_one_is_perturbed(
    path: Path, label: str, capsys
) -> None:
    """Perturb one tracked file, watch the check name it, then put it back."""
    original = path.read_text(encoding="utf-8")
    try:
        path.write_text(original + "perturbed\n", encoding="utf-8")
        assert _benchmark().check() == 1, f"a perturbed {label} did not fail the check"
        output = capsys.readouterr().out
        assert path.relative_to(ROOT).as_posix() in output, output
        assert "tracked:" in output and "rendered:" in output, output
        # And the check must report, not repair: the perturbation is still on disk.
        assert path.read_text(encoding="utf-8").endswith("perturbed\n")
    finally:
        path.write_text(original, encoding="utf-8")
    assert _benchmark().check() == 0, "the tree did not come back clean after the perturbation"


def test_the_quality_report_publishes_the_count_the_checker_produces(capsys) -> None:
    """A published number read from the artefact and recomputed from the inputs.

    `quality-report.md` says "Objective constraint check (`tests/quality/check_constraints.py`):
    **48/48 PASS**". The count is read out of that sentence and compared with what the
    checker prints when it runs over the committed `translator-output.cliff`, so the
    report cannot go on publishing a stale total.
    """
    pytest.importorskip("cliff_format", reason="cliff-python is not importable")
    import sys

    sys.path.insert(0, str(ROOT / "tests" / "quality"))
    checker = load_module(QUALITY / "check_constraints.py", "quality_check_under_test")
    assert checker.main() == 0, "the committed translator output fails its own constraints"
    printed = re.search(r"Objective constraints: (\d+)/(\d+)", capsys.readouterr().out)
    assert printed is not None, "the checker no longer prints a count"
    measured = f"{printed.group(1)}/{printed.group(2)}"

    report = (QUALITY / "quality-report.md").read_text(encoding="utf-8")
    claimed = re.search(r"check_constraints\.py`\): \*\*(\d+/\d+) PASS\*\*", report)
    assert claimed is not None, "the quality report no longer publishes the constraint count"
    assert claimed.group(1) == measured, (
        f"the quality report publishes {claimed.group(1)}; the checker measures {measured}"
    )


def test_the_unregenerable_artefacts_are_still_present() -> None:
    """Two tracked reports have no generator, so the least a test can do is notice.

    `edit-robustness/report.md` describes the `edits/` tree, which is gitignored:
    nothing in the repository can recompute it. `quality-report.md` is recomputed only
    in the sense asserted above. If either disappears, that is worth knowing - a
    deleted report is not caught by anything else.
    """
    assert (ROOT / "tests" / "edit-robustness" / "report.md").is_file()
    assert (QUALITY / "quality-report.md").is_file()
    assert (QUALITY / "translator-output.cliff").is_file()
    assert importlib.util.find_spec("clarion") is not None
