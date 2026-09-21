#!/usr/bin/env python3
"""Objective constraint checks for the CLIFF translation-quality test.

Does NOT score translation elegance; an evaluator agent scores that with
gold-reference.md. This script verifies the mechanical constraints that any
correct translation must satisfy.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import cliff_validator as cv  # noqa: E402

CORPUS = ROOT / "tests" / "quality" / "corpus.cliff"
OUTPUT = ROOT / "tests" / "quality" / "translator-output.cliff"

TERMS = {
    "Captain Zephyr": "泽费尔舰长",
    "the Aurelia": "奥蕾莉亚号",
    "Starbase 7": "七号星港",
}

BANNED = {
    "table-this": ["桌子"],
    "break-a-leg": ["断腿", "摔断腿"],
    "kick-bucket": ["水桶", "桶"],
    "cats-dogs": ["猫", "狗"],
}


def display_cells(text: str) -> int:
    total = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def fields(doc: cv.Document):
    out = {}
    for e in doc.entries:
        vals = {}
        for key, items in e.fields.items():
            vals[key] = " ".join(str(v) for _, v, _ in items)
        out[e.entry_id] = vals
    return out


def main() -> int:
    if not OUTPUT.exists():
        print("FAIL: translator-output.cliff does not exist")
        return 1

    checks: list[tuple[bool, str]] = []

    src_doc = cv.Document(CORPUS)
    src_doc.load(CORPUS.read_text(encoding="utf-8"))
    src_doc.validate()
    out_doc, ok = cv.validate_file(OUTPUT, check_width=False)
    checks.append((ok, f"validator: {'VALID' if ok else 'INVALID'}"))

    src = fields(src_doc)
    trg = fields(out_doc)
    checks.append((set(src) == set(trg), "entry id set unchanged"))

    for eid, s in src.items():
        if "source" not in trg[eid]:
            checks.append((False, f"{eid}: source missing"))
            continue
        checks.append((s.get("source") == trg[eid].get("source"), f"{eid}: source text unchanged"))
        checks.append(("target" in trg[eid] and trg[eid]["target"], f"{eid}: target present"))
        checks.append((trg[eid].get("status") == "translated", f"{eid}: status translated"))

    icu = trg.get("icu-count", {}).get("target", "")
    checks.append(("{" in icu and "}" in icu and icu.count("{") == icu.count("}"),
                   "icu-count: ICU braces balanced"))
    checks.append((icu.startswith("{count, plural,") and "=0" in icu and "other" in icu,
                   "icu-count: ICU plural structure preserved"))

    pn = trg.get("proper-nouns", {}).get("target", "")
    for src_term, tgt_term in TERMS.items():
        if src_term in src.get("proper-nouns", {}).get("source", ""):
            checks.append((tgt_term in pn, f"proper-nouns: glossary term '{tgt_term}' present"))

    for eid, bad in BANNED.items():
        t = trg.get(eid, {}).get("target", "")
        checks.append((not any(b in t for b in bad), f"{eid}: no banned literal '{'/'.join(bad)}'"))

    short = trg.get("accept-short", {}).get("target", "")
    checks.append((display_cells(short) <= 6, f"accept-short: {display_cells(short)} cells <= 6"))

    passed = sum(1 for okk, _ in checks if okk)
    total = len(checks)
    for okk, name in checks:
        print(("PASS" if okk else "FAIL") + f"  {name}")
    print(f"\nObjective constraints: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
