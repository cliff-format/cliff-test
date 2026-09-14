"""Package the CLARION run into the public benchmark bundle.

Layout (raw evidence stays as-is; computed review data is the program output):

    cliff-test/benchmark/clarion-2026-09-02/
        README.md
        raw/       answers/ records.jsonl qe_scores.jsonl tokens.json config.json summary.json
        computed/  computed-metrics.json qe_summary.json report.md
                   report.audited.md investor-data.md

Usage: python tools/package_benchmark.py results/<run-id>
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.exit("usage: python tools/package_benchmark.py results/<run-id>")
    run_dir = Path(args[0])
    if not (run_dir / "records.jsonl").exists():
        sys.exit("not a run dir: " + str(run_dir))

    out = ROOT / "benchmark" / "clarion-2026-09-02"
    raw = out / "raw"
    comp = out / "computed"
    raw.mkdir(parents=True, exist_ok=True)
    comp.mkdir(parents=True, exist_ok=True)

    raw_names = ["config.json", "summary.json", "records.jsonl", "qe_scores.jsonl", "tokens.json"]
    comp_names = ["computed-metrics.json", "report.md", "report.audited.md", "investor-data.md"]
    for name in raw_names:
        src = run_dir / name
        if src.exists():
            shutil.copyfile(src, raw / name)
            print("raw/ " + name)
    for name in comp_names:
        src = run_dir / name
        if src.exists():
            shutil.copyfile(src, comp / name)
            print("computed/ " + name)
    answers_src = run_dir / "answers"
    if answers_src.exists():
        shutil.copytree(answers_src, raw / "answers", dirs_exist_ok=True)
        n = len(list(answers_src.glob("*.answer.txt")))
        print("raw/ answers/ (" + str(n) + " tasks)")

    # README
    readme_lines = ["# CLARION benchmark bundle - clarion-2026-09-02","","Source run: results/clarion-deepseek-v4-flash-20260902T040228+0000-91f21a, packed by","tools/package_benchmark.py. Raw evidence is kept as-is; the computed review data is the","program output of tools/audit_report.mjs (regenerated, never hand-written).","","## raw/","| File | Contents |","| --- | --- |","| config.json | resolved run configuration (model, formats, arms, seed) |","| summary.json | per-stage run summary |","| records.jsonl | one JSON line per measured task (960 translation, 60 robustness, 160 fidelity) |","| answers/ | raw model answers + the exact prompt that produced them (one .answer.txt and .prompt.txt per task) |","| qe_scores.jsonl | per-segment MetricX-23-QE scores (reference-free) |","| tokens.json | per-format token-cost measurements (tiktoken o200k_base) |","","## computed/","| File | Contents |","| --- | --- |","| computed-metrics.json | **unified review data**: token cost, quality, latency, validity, significance, fidelity, QE per format/arm |","| (QE aggregates are inside computed-metrics.json) |","| report.md | the original generated report (dimensions D1-D7) |","| report.audited.md | audit report: corrected failures, strict reading, significance, QE pairing |","| investor-data.md | the 7 review tables as a compact sheet |","","## Reproduce","| Step | Command |","| --- | --- |","| run the benchmark | python -m clarion pipeline --config configs/deepseek-flash.json |","| audit + computed metrics | node tools/audit_report.mjs <run-dir> |","| QE scoring | python tools/qe_score.py <run-dir> (MetricX-23-QE-Large, Apache-2.0, reference-free) |","| pack this bundle | python tools/package_benchmark.py <run-dir> |","","## License","The harness is MIT. Corpus documents carry their own SPDX headers (CC0 for authored text, MIT","for Godot, Apache-2.0 for WMT24++, public domain for the classical translations); model answers","are derived from those licensed sources and inherit their terms. See","`datasets/clarion-core/DATA-LICENSES.md` in cliff-test.",""]
    (out / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    print("wrote " + str(out / "README.md"))
    print("bundle complete at " + str(out))


if __name__ == "__main__":
    main()
