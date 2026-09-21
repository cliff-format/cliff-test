#!/usr/bin/env python3
"""Run the reproducible CLIFF test batteries.

   python tests/run_all.py               # validation suites + benchmark
   python tests/run_all.py --quality     # objective constraints on tests/quality/
   python tests/run_all.py --robustness  # generates the 100 edits, then checks them

Each suite below states the mode it is checked in, because a suite that passes
under the wrong mode is not evidence of anything:

  * valid/    — strict grammar, zero errors
  * invalid/  — strict grammar, at least one hard error
  * layout/   — zero errors by default (CLIFF 1.1 recommends a layout), and at
                least one error once layout consistency is enforced
  * tolerant/ — rejected strictly, repaired tolerantly; the fixtures that must
                still be refused live in the same directory as the ones that
                must be repaired, and are named accordingly
  * style/    — valid CLIFF with zero errors, reported by --style
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _siblings import ENV_VAR, required  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "cliff_validator.py"
FIXTURES = ROOT / "tests" / "fixtures"
SPEC_EXAMPLES = ROOT.parent / "cliff" / "spec" / "examples"

#: The exit code the validator uses for a usage error (no input files, an unknown
#: flag). It means the check never ran, so it can never be read as "failed as
#: expected" - an empty file list would otherwise turn a refusal battery into a suite
#: that passes while testing nothing.
USAGE_ERROR_EXIT = 2

#: The generator for the 100 sequential edits. The directory it writes is gitignored,
#: so the robustness battery produces what it reads instead of failing on a fresh
#: clone.
EDIT_DRIVER = ROOT / "tests" / "edit-robustness" / "apply_edits.py"

#: Tolerant fixtures that must still be REFUSED, with the reason each is a boundary
#: rather than a repairable shape:
#:
#:   unrepairable.zh-CN.cliff        an unquoted value has no determinate end (C.5).
#:   quoted-unknown-key.zh-CN.cliff  C.2.7 removes quotes; it does not widen the key
#:                                   sets, so the word inside is still not a legal key.
#:   closing-tag.zh-CN.cliff         C.2.5 applies to an identifier, and `</terms>` is
#:                                   markup: reading it as an entry manufactured an
#:                                   entry the file does not contain.
UNREPAIRABLE = {
    "unrepairable.zh-CN.cliff",
    "quoted-unknown-key.zh-CN.cliff",
    "closing-tag.zh-CN.cliff",
}

#: Answers that hold more than one CLIFF document - a translated file plus the
#: glossary the terminology workflow produced. Splitting them is part of reading
#: an answer back, and the splitter must accept either version line, so the
#: sample deliberately pairs a 1.0 translation with a 1.1 glossary.
MULTI_DOCUMENT = FIXTURES / "tolerant" / "two-documents.txt"


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def run_suite(title: str, args: list[str], *, expect_success: bool, ok: bool) -> bool:
    rc, out = run([sys.executable, str(VALIDATOR), *args])
    print(out)
    # A usage error is not a verdict: the validator never read a file, so a non-zero
    # expectation must not be satisfied by it.
    passed = (rc == 0) if expect_success else (rc not in (0, USAGE_ERROR_EXIT))
    expected = "0" if expect_success else f"non-zero other than {USAGE_ERROR_EXIT}"
    state = "as expected" if passed else "UNEXPECTED"
    print(f"{title}: exit {rc} ({expected} expected) — {state}")
    return ok and passed


def check_counter_examples(paths: list[Path]) -> bool:
    """Whether the Appendix C.5 battery has anything to refuse.

    An empty list would hand the validator no input, whose usage error used to read as
    "failed as expected" - so the refusal battery passed precisely when it tested
    nothing.
    """
    if paths:
        return True
    print("FAIL: no tolerant counter-example found; Appendix C.5 is untested")
    return False


def ensure_edits(edits: Path, *, generator: Path | None = None) -> bool:
    """Generate the robustness edits when they are absent; True when they are there.

    `tests/edit-robustness/edits/` is gitignored, so the documented
    `python tests/run_all.py --robustness` command would fail on a fresh clone. The
    driver is a parameter so the generation branch can be exercised without touching
    the real tree.
    """
    if any(edits.rglob("*.cliff")):
        return True
    rc, out = run([sys.executable, str(generator or EDIT_DRIVER)])
    print(out)
    return rc == 0 and any(edits.rglob("*.cliff"))


def check_spec_examples(ok: bool) -> bool:
    """Check the specification's example suites in the sibling `cliff` checkout.

    Absent, this skips - unless `CLIFF_REQUIRE_SIBLINGS=1`, where it fails, because the
    examples are the artefact the whole suite is defined against and a green build that
    never checked them is worse than a red one.

    The policy is spelled out here rather than delegated to `_siblings.require_directory`,
    which fails by raising: outside pytest that surfaces as a traceback, and a CI log
    whose last line is a stack trace tells a reader less than one that says FAIL. The
    two answer the same question and are held by the same tests.
    """
    if not SPEC_EXAMPLES.is_dir():
        if required():
            print(
                f"FAIL: {SPEC_EXAMPLES} not found and {ENV_VAR}=1 is set; the specification's "
                "examples are what this suite is defined against, so this is a failure and "
                "not a skip"
            )
            return False
        print(f"skipped: {SPEC_EXAMPLES} not found (set {ENV_VAR}=1 to require it)")
        return ok
    suites = sorted(path for path in SPEC_EXAMPLES.iterdir() if path.is_dir())
    if not suites:
        print(f"FAIL: {SPEC_EXAMPLES} holds no example suite; nothing was checked")
        return False
    for suite in suites:
        ok = run_suite(
            f"spec examples {suite.name}",
            ["--suite", str(suite)],
            expect_success=True,
            ok=ok,
        )
    return ok


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The two extra batteries, declared so a typo is an error instead of a no-op."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quality",
        action="store_true",
        help="also run the quality objective constraints on tests/quality/",
    )
    parser.add_argument(
        "--robustness",
        action="store_true",
        help="also run the 100 sequential edits from tests/edit-robustness/",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ok = True

    print("== spec examples (sibling cliff repository) ==")
    ok = check_spec_examples(ok)

    print("== valid fixtures ==")
    ok = run_suite("valid", ["--suite", str(FIXTURES / "valid")], expect_success=True, ok=ok)

    print("== invalid fixtures (must fail) ==")
    ok = run_suite("invalid", ["--suite", str(FIXTURES / "invalid")], expect_success=False, ok=ok)

    print("== layout fixtures (warnings by default) ==")
    ok = run_suite("layout", ["--suite", str(FIXTURES / "layout")], expect_success=True, ok=ok)

    print("== layout fixtures with --check-layout (must fail) ==")
    ok = run_suite(
        "layout enforced",
        ["--check-layout", "--suite", str(FIXTURES / "layout")],
        expect_success=False,
        ok=ok,
    )

    print("== style fixtures (warnings, never errors) ==")
    ok = run_suite(
        "style",
        ["--style", "--suite", str(FIXTURES / "style")],
        expect_success=True,
        ok=ok,
    )

    print("== tolerant fixtures ==")
    tolerant_dir = FIXTURES / "tolerant"
    repairable = sorted(p for p in tolerant_dir.rglob("*.cliff") if p.name not in UNREPAIRABLE)
    unrepairable = sorted(p for p in tolerant_dir.rglob("*.cliff") if p.name in UNREPAIRABLE)
    ok = run_suite(
        "tolerant repairable",
        ["--tolerant", *(str(p) for p in repairable)],
        expect_success=True,
        ok=ok,
    )
    ok = run_suite(
        "tolerant refusals",
        ["--tolerant", *(str(p) for p in unrepairable)],
        expect_success=False,
        ok=ok,
    )
    if not check_counter_examples(unrepairable):
        ok = False

    print("== an answer holding two documents (translation + glossary) ==")
    if MULTI_DOCUMENT.exists():
        ok = run_suite(
            "multi-document answer",
            ["--multi-document", str(MULTI_DOCUMENT)],
            expect_success=True,
            ok=ok,
        )
    else:
        print(f"WARNING: {MULTI_DOCUMENT} not found; document splitting is untested")
        ok = False

    print("== token benchmark ==")
    rc, out = run([sys.executable, str(ROOT / "tools/token_benchmark.py")])
    print(out)
    ok &= rc == 0

    if args.quality:
        print("== quality objective constraints ==")
        rc, out = run([sys.executable, str(ROOT / "tests/quality/check_constraints.py")])
        print(out)
        ok &= rc == 0

    if args.robustness:
        print("== edit robustness ==")
        edits = ROOT / "tests/edit-robustness/edits"
        if not ensure_edits(edits):
            print(f"FAIL: {edits} is missing and {EDIT_DRIVER.name} could not generate it")
            ok = False
        else:
            files = sorted(edits.rglob("*.cliff"))
            rc, out = run([sys.executable, str(VALIDATOR), "--suite", str(edits)])
            print(out)
            valid = out.count(": VALID")
            print(f"valid edits: {valid}/{len(files)}")
            ok &= bool(files) and valid == len(files)

    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
