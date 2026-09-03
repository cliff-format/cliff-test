# CLARION benchmark bundle - clarion-2026-09-02

Source run: results/clarion-deepseek-v4-flash-20260902T040228+0000-91f21a, packed by
tools/package_benchmark.py. Raw evidence is kept as-is; the computed review data is the
program output of tools/audit_report.mjs (regenerated, never hand-written).

## raw/
| File | Contents |
| --- | --- |
| config.json | resolved run configuration (model, formats, arms, seed) |
| summary.json | per-stage run summary |
| records.jsonl | one JSON line per measured task (960 translation, 60 robustness, 160 fidelity) |
| answers/ | raw model answers + the exact prompt that produced them (one .answer.txt and .prompt.txt per task) |
| qe_scores.jsonl | per-segment MetricX-23-QE scores (reference-free) |
| tokens.json | per-format token-cost measurements (tiktoken o200k_base) |

## computed/
| File | Contents |
| --- | --- |
| computed-metrics.json | **unified review data**: token cost, quality, latency, validity, significance, fidelity, QE per format/arm |
| (QE aggregates are inside computed-metrics.json) |
| report.md | the original generated report (dimensions D1-D7) |
| report.audited.md | audit report: corrected failures, strict reading, significance, QE pairing |
| investor-data.md | the 7 review tables as a compact sheet |

## Reproduce
| Step | Command |
| --- | --- |
| run the benchmark | python -m clarion pipeline --config configs/deepseek-flash.json |
| audit + computed metrics | node tools/audit_report.mjs <run-dir> |
| QE scoring | python tools/qe_score.py <run-dir> (MetricX-23-QE-Large, Apache-2.0, reference-free) |
| pack this bundle | python tools/package_benchmark.py <run-dir> |

## License
The harness is MIT. Corpus documents carry their own SPDX headers (CC0 for authored text, MIT
for Godot, Apache-2.0 for WMT24++, public domain for the classical translations); model answers
are derived from those licensed sources and inherit their terms. See
`datasets/clarion-core/DATA-LICENSES.md` in clif-test.
