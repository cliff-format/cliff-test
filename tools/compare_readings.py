#!/usr/bin/env python3
"""Compare the two CLIFF readings over a recorded run's answers.

Re-scores every stored CLIFF answer under the strict and the tolerant reading of
CLIFF 1.1 Appendix C, without any model call. This is the comparison the read-mode
work exists to make possible, and the source of the "two readings, on the same
answers" tables in docs/acceptance-criteria.md (C6.11): how much of a model's CLIFF
output a strict toolchain rejects, and how much of that the documented tolerant
reading salvages, at what repair cost.

It lives in the repository rather than beside it because those tables cite it: a
number a reader cannot reproduce is a number a reader has to take on trust.

Usage:
    python tools/compare_readings.py [run-dir]
    python tools/compare_readings.py results/clarion-deepseek-flash-<stamp>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_RUN = ROOT / "results"


def _kind(message: str) -> str:
    """Classify a repair message into its Appendix C clause."""
    lowered = message.lower()
    for needle, label in (
        ("quotes around a tag", "C.2.3 quoted tag"),
        ("quotes around an entry id", "C.2.4 quoted entry id"),
        ("quotes around a key", "C.2.7 quoted key"),
        ("one-item list", "C.2.1 bare scalar in a list-typed field"),
        ("normalized", "C.2.5 identifier containing a reserved character"),
        ("version", "C.2.6 version line spelling"),
        ("repeat", "C.2.2 repeated field"),
    ):
        if needle in lowered:
            return label
    return message[:40]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir",
        nargs="?",
        type=Path,
        help="a run directory holding records.jsonl and answers/ (default: the newest)",
    )
    args = parser.parse_args(argv)

    run = args.run_dir
    if run is None:
        candidates = sorted(
            (path for path in DEFAULT_RUN.iterdir() if (path / "records.jsonl").is_file()),
            key=lambda path: path.stat().st_mtime,
        )
        if not candidates:
            print(f"no run directory with records.jsonl under {DEFAULT_RUN}", file=sys.stderr)
            return 2
        run = candidates[-1]

    from clarion.formats.validity import check_validity

    rows = [
        json.loads(line)
        for line in (run / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    answers = [
        row
        for row in rows
        if row.get("kind") == "translation" and row.get("format") == "cliff"
    ]
    print(f"run: {run.name}")
    print(f"CLIFF answers in this run: {len(answers)}")
    if not answers:
        return 0

    for arm in ("bare", "context"):
        cells = [row for row in answers if row.get("arm") == arm]
        if not cells:
            continue
        strict_ok = tolerant_ok = repairs = reread = 0
        salvaged: list[str] = []
        categories: Counter[str] = Counter()
        for row in cells:
            path = run / str(row.get("answer_file", ""))
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            reread += 1
            strict = check_validity(text, "cliff", tolerant=False)
            tolerant = check_validity(text, "cliff", tolerant=True)
            strict_ok += 1 if strict.ok else 0
            tolerant_ok += 1 if tolerant.ok else 0
            repairs += tolerant.repairs
            if not strict.ok and tolerant.ok:
                salvaged.append(row["file"])
            for warning in tolerant.warnings:
                if warning.category == "correction":
                    categories[_kind(warning.message)] += 1
        print(f"\n--- arm: {arm}  ({reread} answers re-read) ---")
        print(f"  strict   valid: {strict_ok}/{reread} = {100.0 * strict_ok / reread:.1f}%")
        print(f"  tolerant valid: {tolerant_ok}/{reread} = {100.0 * tolerant_ok / reread:.1f}%")
        print(f"  repairs made  : {repairs} ({repairs / reread:.2f} per answer)")
        print(f"  salvaged only by the tolerant reading: {len(salvaged)} "
              f"{sorted(set(salvaged))[:6]}")
        if categories:
            print("  repair kinds  :", dict(categories.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
