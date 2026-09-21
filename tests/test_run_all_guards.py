"""The suite runner's own guards: a battery must fail when it tests nothing.

Three ways a battery can report success while checking nothing, and the answer to each
is pinned here rather than left to review:

* a missing sibling checkout or corpus tree, which skips locally and must fail when CI
  sets `CLIFF_REQUIRE_SIBLINGS=1` (`tests/_siblings.py`, item 1 of the audit);
* a validator invocation that never ran, because an empty file list makes it exit with a
  usage error that used to read as "failed as expected" (the Appendix C.5 refusal
  battery, item 2);
* a gitignored generated directory, which the documented `--robustness` command has to
  produce rather than fail on (item 9).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_all  # noqa: E402

from tests._siblings import (  # noqa: E402
    ENV_VAR,
    require_directory,
    require_sibling,
    skip_if_missing,
)

#: A directory that does not exist, standing in for a checkout the pipeline failed to
#: make. It is under a repository directory on purpose: nothing here creates or deletes
#: anything.
ABSENT = Path(__file__).resolve().parent / "fixtures" / "_no_such_checkout"

PRESENT = Path(__file__).resolve().parent / "fixtures" / "valid"


def test_require_directory_returns_the_paths_it_found() -> None:
    paths = require_directory(PRESENT, "the valid fixtures")
    assert paths, f"{PRESENT} should hold fixtures"
    assert all(path.suffix == ".cliff" for path in paths)
    assert paths == sorted(paths)


def test_require_directory_fails_when_the_environment_demands_siblings(monkeypatch) -> None:
    """The CI branch: a failed checkout must not become a silent skip."""
    monkeypatch.setenv(ENV_VAR, "1")
    with pytest.raises(pytest.fail.Exception) as failure:
        require_directory(ABSENT, "the CLARION-Core corpus")
    assert "the CLARION-Core corpus not found at" in str(failure.value)
    with pytest.raises(pytest.fail.Exception) as sibling:
        require_sibling(ABSENT, "cliff")
    assert "sibling checkout cliff not found at" in str(sibling.value)


def test_require_directory_returns_empty_without_the_environment_variable(monkeypatch) -> None:
    """The developer branch: absent, so the caller skips instead of failing."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert require_directory(ABSENT, "the CLARION-Core corpus") == []
    with pytest.raises(pytest.skip.Exception) as skipped:
        skip_if_missing([], "cliff")
    assert "sibling checkout cliff is not available" in str(skipped.value)


def test_the_runner_fails_when_a_required_sibling_is_absent(monkeypatch, capsys) -> None:
    """The runner half of item 1: a failed spec checkout must not end in ALL PASS.

    CI checks the specification out with `continue-on-error: true`, so this is the
    state a broken pipeline actually presents. It reports a FAIL line rather than a
    traceback: this function runs in a plain script outside pytest, and a CI log whose
    last line is a stack trace tells a reader less than one that says FAIL.
    """
    monkeypatch.setattr(run_all, "SPEC_EXAMPLES", ABSENT)
    monkeypatch.setenv(ENV_VAR, "1")
    assert run_all.check_spec_examples(True) is False
    out = capsys.readouterr().out
    assert "FAIL:" in out and "not found" in out, out
    # And without the switch it stays a skip, which is what a developer wants.
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert run_all.check_spec_examples(True) is True
    assert "skipped:" in capsys.readouterr().out


def test_the_runner_fails_when_the_sibling_holds_no_suite(monkeypatch, capsys) -> None:
    """A checkout that is present but empty is the same silent zero as an absent one.

    `tests/fixtures/tolerant` stands in for such a checkout: it holds fixtures but no
    version directories, which is the shape that would otherwise check nothing.
    """
    stand_in = run_all.FIXTURES / "tolerant"
    assert not [path for path in stand_in.iterdir() if path.is_dir()]
    monkeypatch.setattr(run_all, "SPEC_EXAMPLES", stand_in)
    assert run_all.check_spec_examples(True) is False
    assert "holds no example suite" in capsys.readouterr().out


def test_a_usage_error_is_not_read_as_failed_as_expected(capsys) -> None:
    """An empty file list exits 2, and 2 means the validator never ran.

    Without the distinction the Appendix C.5 refusal battery passes precisely when it
    has nothing to refuse: `--tolerant` with no paths is a usage error, not a refusal.
    """
    assert run_all.run_suite("no input at all", [], expect_success=False, ok=True) is False
    assert "UNEXPECTED" in capsys.readouterr().out


def test_a_real_refusal_is_still_read_as_failed_as_expected() -> None:
    """The other half: a genuine refusal (exit 1) keeps counting as the expected result."""
    refusal = run_all.FIXTURES / "tolerant" / "closing-tag.zh-CN.cliff"
    assert refusal.is_file(), "the counter-example fixture has moved"
    assert (
        run_all.run_suite(
            "tolerant refusal", ["--tolerant", str(refusal)], expect_success=False, ok=True
        )
        is True
    )
    assert (
        run_all.run_suite(
            "invalid fixtures",
            ["--suite", str(run_all.FIXTURES / "invalid")],
            expect_success=False,
            ok=True,
        )
        is True
    )


def test_an_empty_counter_example_set_fails_the_battery(capsys) -> None:
    """The refusal battery is only evidence if it has a file to refuse."""
    assert run_all.check_counter_examples([PRESENT / "one.cliff"]) is True
    assert run_all.check_counter_examples([]) is False
    assert "FAIL: no tolerant counter-example found" in capsys.readouterr().out


def test_the_robustness_battery_generates_the_edits_it_reads(monkeypatch) -> None:
    """`edits/` is gitignored, so the documented command must produce it, not fail."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str]) -> tuple[int, str]:
        calls.append(cmd)
        return 0, "Wrote 100 sequential edit files"

    monkeypatch.setattr(run_all, "run", fake_run)
    absent = Path(__file__).resolve().parent / "edit-robustness" / "_no_such_edits"
    assert run_all.ensure_edits(absent) is False, "a driver that wrote nothing is not success"
    assert any("apply_edits.py" in " ".join(cmd) for cmd in calls), (
        "the generator was never invoked; the battery fails on a fresh clone again"
    )


def test_existing_edits_are_used_without_regenerating(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str]) -> tuple[int, str]:
        calls.append(cmd)
        return 0, ""

    monkeypatch.setattr(run_all, "run", fake_run)
    edits = Path(__file__).resolve().parent / "edit-robustness" / "edits"
    if not any(edits.rglob("*.cliff")):
        pytest.skip("the generated edits are not on disk in this checkout")
    assert run_all.ensure_edits(edits) is True
    assert calls == [], "generation ran although the edits were already there"


def test_the_two_extra_batteries_are_declared_arguments() -> None:
    """`--help` used to list no options and `--qualty` was silently ignored."""
    args = run_all.parse_args(["--quality", "--robustness"])
    assert args.quality is True
    assert args.robustness is True
    assert run_all.parse_args([]).quality is False
    with pytest.raises(SystemExit):
        run_all.parse_args(["--qualty"])
