#!/usr/bin/env python3
"""Run the reproducible CLIFF test batteries.

   python tests/run_all.py               # validation suites + benchmark
   python tests/run_all.py --quality     # after translator-output.cliff exists
   python tests/run_all.py --robustness  # after edits/ exists

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

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "cliff_validator.py"
FIXTURES = ROOT / "tests" / "fixtures"
SPEC_EXAMPLES = ROOT.parent / "cliff" / "spec" / "examples"

#: Tolerant fixtures that must still be *refused* (specification Appendix C.5):
#: tolerant parsing repairs shape, never content. The second file is refused
#: *after* the quoted-key relaxation of C.2.7 has applied: the quotes come off and
#: the word inside is still not a legal key, which is the boundary that keeps the
#: relaxation from widening the key sets.
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
    passed = (rc == 0) if expect_success else (rc != 0)
    state = "as expected" if passed else "UNEXPECTED"
    print(f"{title}: exit {rc} ({'0' if expect_success else 'non-zero'} expected) — {state}")
    return ok and passed


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_known_args()
    ok = True

    print("== spec examples (sibling cliff repository) ==")
    if SPEC_EXAMPLES.exists():
        for version in sorted(p.name for p in SPEC_EXAMPLES.iterdir() if p.is_dir()):
            ok = run_suite(
                f"spec examples {version}",
                ["--suite", str(SPEC_EXAMPLES / version)],
                expect_success=True,
                ok=ok,
            )
    else:
        print(f"skipped: {SPEC_EXAMPLES} not found")

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
    if not unrepairable:
        print("WARNING: no tolerant counter-example found; Appendix C.5 is untested")

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

    if "--quality" in sys.argv:
        print("== quality objective constraints ==")
        rc, out = run([sys.executable, str(ROOT / "tests/quality/check_constraints.py")])
        print(out)
        ok &= rc == 0

    if "--robustness" in sys.argv:
        print("== edit robustness ==")
        edits = ROOT / "tests/edit-robustness/edits"
        if edits.exists():
            files = sorted(edits.rglob("*.cliff"))
            rc, out = run([sys.executable, str(VALIDATOR), "--suite", str(edits)])
            print(out)
            valid = out.count(": VALID")
            print(f"valid edits: {valid}/{len(files)}")
            ok &= valid == len(files)
        else:
            print("tests/edit-robustness/edits does not exist")
            ok = False

    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
