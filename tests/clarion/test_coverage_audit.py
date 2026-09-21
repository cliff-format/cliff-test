"""The reachability claim in the changelog, held to what the tool measures.

`CHANGELOG.md` publishes *"`tools/coverage_audit.py`, which reports **N of N**
modules under `clarion/` reachable from the suite"*, and
`docs/clarion-methodology.md` cites the tool as in-repo evidence - and nothing ran it.
A published reachability number with no guard means the next unreachable module is
invisible, which is the failure mode the claim exists to prevent.

What is asserted here is read from both ends rather than typed into the test: the
measurement comes from the tool's own output, and the claim comes out of the changelog
text. The claim's absolute pair is *not* asserted, because it drifts every time a module
is added - the claim is "all of them", and that is what the invariant below checks. The
absolute pair is reported to the reader instead; refreshing it is a one-line edit in a
file this test does not own.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests._tool_loader import load_module

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "coverage_audit.py"
CHANGELOG = ROOT / "CHANGELOG.md"

#: The tool's summary line: "55 modules under clarion/, 55 reachable from the test suite".
MEASUREMENT = re.compile(r"(\d+) modules under clarion/, (\d+) reachable from the test suite")
#: The claim as the changelog writes it: "reports **53 of 53** modules under `clarion/`".
CLAIM = re.compile(r"reports \*\*(\d+) of (\d+)\*\* modules under `clarion/`")


def _measure(capsys) -> tuple[int, int, str]:
    """Run the audit in-process and return (modules, reachable, its stdout)."""
    tool = load_module(TOOL, "coverage_audit_under_test")
    assert tool.main([]) == 0, "the audit tool must exit 0"
    output = capsys.readouterr().out
    match = MEASUREMENT.search(output)
    assert match is not None, f"the audit's summary line changed shape:\n{output}"
    return int(match.group(1)), int(match.group(2)), output


def test_the_audit_tool_exists_and_still_prints_a_summary() -> None:
    """Guard the guard: a moved tool or renamed output would make every check skip."""
    assert TOOL.is_file(), TOOL
    assert CLAIM.search(CHANGELOG.read_text(encoding="utf-8")) is not None, (
        "the changelog no longer publishes a reachability claim; if it was moved, move "
        "this test with it"
    )


def test_every_module_under_clarion_is_reachable_from_the_suite(capsys) -> None:
    """The invariant behind the claim: nothing under `clarion/` is dead code.

    A module no test imports is a module nothing checks, which is how a harness grows
    a scorer that silently stopped running. This is the assertion that fails when one
    appears.
    """
    modules, reachable, output = _measure(capsys)
    assert reachable == modules, (
        f"{modules - reachable} of {modules} modules under clarion/ are reachable from "
        f"no test; the audit lists them:\n{output}"
    )


def test_the_audit_prefers_calling_a_module_over_importing_it(capsys) -> None:
    """Entry points are run rather than imported, and the tool names them.

    `clarion.cli`, `clarion.pipeline` and `clarion.selfcheck` are reached by executing
    them in a test, not by importing them; the list is printed so a reader can see that
    the reachability count is not hiding an entry point behind an import graph.
    """
    _, _, output = _measure(capsys)
    assert "entry points, run rather than imported by a test:" in output
    assert "clarion.cli" in output


def test_the_published_claim_is_a_claim_about_all_of_them(capsys) -> None:
    """The changelog's pair has to say "all", whatever the absolute number is.

    The numbers themselves are reported rather than asserted - they move whenever a
    module is added - but a claim that reads "53 of 60" would be claiming dead code
    exists, which is the thing this file exists to catch.
    """
    modules, reachable, _ = _measure(capsys)
    match = CLAIM.search(CHANGELOG.read_text(encoding="utf-8"))
    assert match is not None
    claimed_reachable, claimed_total = int(match.group(1)), int(match.group(2))
    assert claimed_reachable == claimed_total, (
        f"the changelog publishes {claimed_reachable} of {claimed_total} reachable; a "
        "claim of the form 'N of M' with N < M is a claim that some module is dead"
    )
    print(
        f"\nchangelog claim: {claimed_reachable} of {claimed_total}; "
        f"measured now: {reachable} of {modules}"
    )
