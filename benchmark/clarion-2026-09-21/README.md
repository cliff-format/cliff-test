# CLARION benchmark bundle - clarion-2026-09-21

Source run: `results/clarion-deepseek-flash-20260921T211031+0000-de29a5`, packed by `tools/package_benchmark.py`. Raw
evidence is kept as-is; the computed review data is the program output of
`tools/audit_report.mjs` (regenerated, never hand-written).

## Protocol

| | |
| --- | --- |
| model | `deepseek-flash` |
| reasoning | `low` |
| temperature | 1.3 |
| prompt style (CLIFF) | `spec` |
| read mode (CLIFF) | `tolerant` |
| formats | 10 (cliff, xliff-2.1, po, fluent, json-cliff, json-plain, yaml-cliff, csv, android, ios) |
| arms | bare, context |
| repeats | 3 |
| corpus | clarion-core |
| translation runs | 960 |
| robustness chains | 60 (12 edits each) |
| fidelity conversions | 160 |

## raw/

| File | Contents |
| --- | --- |
| config.json | resolved run configuration (model, formats, arms, seed) |
| summary.json | per-stage run summary |
| records.jsonl | one JSON line per measured task (960 translation, 60 robustness, 160 fidelity) |
| answers/ | raw model answers + the exact prompt that produced them (one .answer.txt and .prompt.txt per task) |
| qe_scores.jsonl | per-segment MetricX-23-QE scores (reference-free), when the optional QE pass was run |
| tokens.json | per-format token-cost measurements (tiktoken o200k_base) |

## computed/

| File | Contents |
| --- | --- |
| computed-metrics.json | **unified review data**: token cost, quality, latency, validity, significance, fidelity per format/arm |
| report.md | the original generated report (dimensions D1-D7) |
| report.audited.md | audit report: corrected failures, strict reading, significance |
| investor-data.md | the review tables as one compact sheet |

## Reproduce

| Step | Command |
| --- | --- |
| run the benchmark | `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch` |
| audit + computed metrics | `node tools/audit_report.mjs <run-dir>` |
| pack this bundle | `python tools/package_benchmark.py <run-dir>` |
| two readings (CLIFF) | `python tools/compare_readings.py <run-dir>` |
| QE scoring (optional) | `python tools/qe_score.py <run-dir>` (MetricX-23-QE-Large, Apache-2.0, reference-free) |

## License

The harness is MIT. Corpus documents carry their own SPDX headers (CC0 for
authored text, MIT for Godot, Apache-2.0 for WMT24++, public domain for the
classical translations); model answers are derived from those licensed sources and
inherit their terms.
