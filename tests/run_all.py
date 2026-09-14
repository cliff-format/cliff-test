#!/usr/bin/env python3
"""Run the reproducible CLIFF test batteries.

   python tests/run_all.py               # validation suites + benchmark
   python tests/run_all.py --quality     # after translator-output.cliff exists
   python tests/run_all.py --robustness  # after edits/ exists
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "cliff_validator.py"
SPEC_EXAMPLES = ROOT.parent / "cliff" / "spec" / "examples" / "cliff-1.0.0"


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    ok = True

    print("== spec examples (sibling cliff repository) ==")
    if SPEC_EXAMPLES.exists():
        rc, out = run([sys.executable, str(VALIDATOR), "--suite", str(SPEC_EXAMPLES)])
        print(out)
        ok &= rc == 0
    else:
        print(f"skipped: {SPEC_EXAMPLES} not found")

    print("== valid fixtures ==")
    rc, out = run([sys.executable, str(VALIDATOR), "--suite", str(ROOT / "tests/fixtures/valid")])
    print(out)
    ok &= rc == 0

    print("== invalid fixtures (must fail) ==")
    rc, out = run([sys.executable, str(VALIDATOR), "--suite", str(ROOT / "tests/fixtures/invalid")])
    ok &= rc != 0
    print(out)

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
