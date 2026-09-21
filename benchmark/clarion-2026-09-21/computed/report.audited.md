# CLARION audit - clarion-deepseek-flash

- Run: clarion-deepseek-flash-20260921T211031+0000-de29a5
- Model: deepseek-flash (openai), temperature 1.3
- Records parsed: **1180** (translation 960, robustness 60, fidelity 160)
- **Audit method: no model call was made and nothing was regenerated.** Numbers below are recomputed from records.jsonl, answers/*.answer.txt, the corpus gold, and config/summary. Reproduce: node tools/audit_report.mjs results\clarion-deepseek-flash-20260921T211031+0000-de29a5

## 1. Corrected failure accounting

The run summary reports the pipeline-level gate, which counts only runs whose provider call failed. This table counts **record-level** failures (outcome != ok: parse-error / invalid / incomplete / degenerate / gold-leak) with Wilson 95% intervals, and beside them the share of runs that survived - the interval is on the *survivors*, which is the number a reader compares with a threshold. The real translation % column is the audit-recomputed share of entries that actually carry a non-empty translation (see section 2).

| format | arm | runs | failed | still valid % (95% CI) | recorded coverage % | real translation % |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| android | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| android | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| cliff | bare | 48 | 4 | 91.7 (80.4-96.7) | 91.7 | 91.7 |
| cliff | context | 48 | 4 | 91.7 (80.4-96.7) | 91.7 | 91.7 |
| csv | bare | 48 | 5 | 89.6 (77.8-95.5) | 89.6 | 85.4 |
| csv | context | 48 | 12 | 75.0 (61.2-85.1) | 78.9 | 82.4 |
| fluent | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| fluent | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| ios | bare | 48 | 1 | 97.9 (89.1-99.6) | 99.8 | 99.8 |
| ios | context | 48 | 2 | 95.8 (86.0-98.8) | 99.6 | 99.6 |
| json-cliff | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| json-cliff | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| json-plain | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| json-plain | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| po | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| po | context | 48 | 1 | 97.9 (89.1-99.6) | 100.0 | 100.0 |
| xliff-2.1 | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| xliff-2.1 | context | 48 | 10 | 79.2 (65.7-88.3) | 79.2 | 79.2 |
| yaml-cliff | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| yaml-cliff | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |

> Pipeline stage: 960 runs, 1 failed, 3993022 prompt + 11501757 output tokens billed Record-level failures are what the scores actually contain.

## 2. Measurement-integrity audit (every answer re-parsed)

The recorded structural checker accepts an answer as fully covered when the parser can fill a value from the **source** when no target slot exists (structure.py: value = entry.target or entry.source). That turns a target-less answer into coverage = 1.0 and scores the source text against the gold. This audit scans every stored answer for an actual non-empty translation slot.

| format | arm | recorded coverage % | real translation % | integrity |
| --- | --- | ---: | ---: | --- |
| android | bare | 100.0 | 100.0 | ok |
| android | context | 100.0 | 100.0 | ok |
| cliff | bare | 91.7 | 91.7 | ok |
| cliff | context | 91.7 | 91.7 | ok |
| csv | bare | 89.6 | 85.4 | low translation rate |
| csv | context | 78.9 | 82.4 | low translation rate |
| fluent | bare | 100.0 | 100.0 | ok |
| fluent | context | 100.0 | 100.0 | ok |
| ios | bare | 99.8 | 99.8 | ok |
| ios | context | 99.6 | 99.6 | ok |
| json-cliff | bare | 100.0 | 100.0 | ok |
| json-cliff | context | 100.0 | 100.0 | ok |
| json-plain | bare | 100.0 | 100.0 | ok |
| json-plain | context | 100.0 | 100.0 | ok |
| po | bare | 100.0 | 100.0 | ok |
| po | context | 100.0 | 100.0 | ok |
| xliff-2.1 | bare | 100.0 | 100.0 | ok |
| xliff-2.1 | context | 79.2 | 79.2 | low translation rate |
| yaml-cliff | bare | 100.0 | 100.0 | ok |
| yaml-cliff | context | 100.0 | 100.0 | ok |

**Strict reading (used here):** an answer the official parser reads back without a translation for an entry is a failed translation of that entry and scores 0 — exactly as an unparseable answer is a failed run. No answer is exempted because a second prompt could repair it: repair costs tokens, and permissive parsing is granted to no format. The rows flagged above are therefore counted, not excluded.

## 3. Strict quality (recorded vs audited)

Strict score = recorded chrF++ scaled by the real translation ratio: entries the official parser reads back without a translation score 0 (untranslated), unparseable runs score 0 (failed). No format gets credit for text it did not deliver in a parseable form.

| format | arm | recorded chrF++ (all) | audited chrF++ (all) | drop |
| --- | --- | ---: | ---: | ---: |
| android | bare | 51.77 | 51.77 | 0.00 |
| android | context | 54.02 | 54.02 | 0.00 |
| cliff | bare | 46.47 | 46.47 | 0.00 |
| cliff | context | 49.31 | 49.31 | 0.00 |
| csv | bare | 46.38 | 42.40 | 3.98 |
| csv | context | 41.76 | 35.49 | 6.27 |
| fluent | bare | 50.92 | 50.92 | 0.00 |
| fluent | context | 53.54 | 53.54 | 0.00 |
| ios | bare | 50.34 | 50.34 | 0.00 |
| ios | context | 52.50 | 52.50 | 0.00 |
| json-cliff | bare | 50.59 | 50.59 | 0.00 |
| json-cliff | context | 55.11 | 55.11 | 0.00 |
| json-plain | bare | 50.37 | 50.37 | 0.00 |
| json-plain | context | 53.39 | 53.39 | 0.00 |
| po | bare | 50.58 | 50.58 | 0.00 |
| po | context | 53.53 | 53.53 | 0.00 |
| xliff-2.1 | bare | 50.75 | 50.75 | 0.00 |
| xliff-2.1 | context | 42.21 | 42.21 | 0.00 |
| yaml-cliff | bare | 50.69 | 50.69 | 0.00 |
| yaml-cliff | context | 55.00 | 55.00 | 0.00 |

## 4. Breakdown by context origin (context arm)

| format | origin | runs | chrF++ (all) | failed % |
| --- | --- | ---: | ---: | ---: |
| android | annotated | 9 | 39.42 | 0.0 |
| android | native | 3 | 82.86 | 0.0 |
| android | original | 36 | 55.27 | 0.0 |
| cliff | annotated | 9 | 35.68 | 11.1 |
| cliff | native | 3 | 82.95 | 0.0 |
| cliff | original | 36 | 49.92 | 8.3 |
| csv | annotated | 9 | 17.21 | 55.6 |
| csv | native | 3 | 80.99 | 0.0 |
| csv | original | 36 | 44.62 | 19.4 |
| fluent | annotated | 9 | 38.83 | 0.0 |
| fluent | native | 3 | 82.66 | 0.0 |
| fluent | original | 36 | 54.79 | 0.0 |
| ios | annotated | 9 | 32.57 | 22.2 |
| ios | native | 3 | 82.62 | 0.0 |
| ios | original | 36 | 54.97 | 0.0 |
| json-cliff | annotated | 9 | 40.77 | 0.0 |
| json-cliff | native | 3 | 82.38 | 0.0 |
| json-cliff | original | 36 | 56.43 | 0.0 |
| json-plain | annotated | 9 | 38.94 | 0.0 |
| json-plain | native | 3 | 81.24 | 0.0 |
| json-plain | original | 36 | 54.69 | 0.0 |
| po | annotated | 9 | 36.02 | 11.1 |
| po | native | 3 | 83.97 | 0.0 |
| po | original | 36 | 55.37 | 0.0 |
| xliff-2.1 | annotated | 9 | 33.76 | 11.1 |
| xliff-2.1 | native | 3 | 84.95 | 0.0 |
| xliff-2.1 | original | 36 | 40.77 | 25.0 |
| yaml-cliff | annotated | 9 | 39.75 | 0.0 |
| yaml-cliff | native | 3 | 83.46 | 0.0 |
| yaml-cliff | original | 36 | 56.45 | 0.0 |

> **annotated** context was written by deepseek-flash (annotation pass, no human sign-off); **native** means the upstream project shipped it (here: Godot PO only). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

## 5. Breakdown by language direction

| direction | files | runs | chrF++ (all) | failed % |
| --- | ---: | ---: | ---: | ---: |
| en-US->zh-CN | 13 | 780 | 54.83 | 3.2 |
| zh-CN->en-US | 3 | 180 | 31.53 | 7.8 |

> The run mixes en-US->zh-CN (13 files) with zh-CN->en-US classical literature (3 files, gold from 1892/1925 translations) in one table; chrF++ is not comparable across directions.

## 6. Paired significance: CLIFF vs every other format

### Arm bare

Paired design (file, repeat); audited scores; paired bootstrap (10,000) + paired permutation (10,000); Holm-corrected across the nine comparisons per arm.

| vs | diff (cliff-other) | 95% CI | bootstrap p | permutation p | Holm p |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | -5.30 | -10.08--1.56 | 0.0004 | 0.0024 | 0.0036 (significant) |
| csv | 4.07 | -2.62-10.68 | 0.2288 | 0.2564 | 0.2288 (n.s.) |
| fluent | -4.45 | -9.05--0.80 | 0.0078 | 0.0294 | 0.0624 (n.s.) |
| ios | -3.86 | -8.65--0.26 | 0.0230 | 0.0659 | 0.1380 (n.s.) |
| json-cliff | -4.12 | -8.83--0.38 | 0.0294 | 0.0658 | 0.1380 (n.s.) |
| json-plain | -3.90 | -8.73--0.08 | 0.0436 | 0.0964 | 0.1380 (n.s.) |
| po | -4.11 | -8.87--0.36 | 0.0252 | 0.0721 | 0.1380 (n.s.) |
| xliff-2.1 | -4.28 | -8.96--0.56 | 0.0124 | 0.0442 | 0.0868 (n.s.) |
| yaml-cliff | -4.22 | -9.03--0.40 | 0.0250 | 0.0624 | 0.1380 (n.s.) |

> Statistical significance is not practical significance; no MT-Thresholds anchor is available.

### Arm context

Paired design (file, repeat); audited scores; paired bootstrap (10,000) + paired permutation (10,000); Holm-corrected across the nine comparisons per arm.

| vs | diff (cliff-other) | 95% CI | bootstrap p | permutation p | Holm p |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | -4.71 | -9.87--0.34 | 0.0322 | 0.0667 | 0.1932 (n.s.) |
| csv | 13.82 | 4.87-22.75 | 0.0034 | 0.0055 | 0.0272 (significant) |
| fluent | -4.22 | -9.52-0.25 | 0.0666 | 0.1049 | 0.3330 (n.s.) |
| ios | -3.19 | -8.61-1.67 | 0.2248 | 0.2540 | 0.3330 (n.s.) |
| json-cliff | -5.80 | -10.89--1.52 | 0.0026 | 0.0148 | 0.0234 (significant) |
| json-plain | -4.08 | -9.42-0.40 | 0.0806 | 0.1199 | 0.3330 (n.s.) |
| po | -4.21 | -9.40-0.30 | 0.0748 | 0.1161 | 0.3330 (n.s.) |
| xliff-2.1 | 7.10 | -2.50-17.06 | 0.1476 | 0.1651 | 0.3330 (n.s.) |
| yaml-cliff | -5.69 | -10.98--1.24 | 0.0070 | 0.0285 | 0.0490 (significant) |

> Statistical significance is not practical significance; no MT-Thresholds anchor is available.

## 7. Edit-robustness (D7) with Wilson intervals

| format | arm | chains | applicable edits | still valid % (95% CI) | intent applied % | checker |
| --- | --- | ---: | ---: | --- | ---: | --- |
| android | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | XML well-formedness |
| android | context | 3 | 36 | 100.0 (90.4-100.0) | 82.3 | XML well-formedness |
| cliff | bare | 3 | 36 | 100.0 (90.4-100.0) | 95.2 | strict CLIFF validator (cliff-python) |
| cliff | context | 3 | 36 | 86.1 (71.3-93.9) | 86.1 | strict CLIFF validator (cliff-python) |
| csv | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | strict CSV parse |
| csv | context | 3 | 36 | 94.4 (81.9-98.5) | 88.9 | strict CSV parse |
| fluent | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | identifier grammar |
| fluent | context | 3 | 36 | 97.2 (85.8-99.5) | 69.9 | identifier grammar |
| ios | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | quoted-assignment grammar |
| ios | context | 3 | 36 | 100.0 (90.4-100.0) | 88.1 | quoted-assignment grammar |
| json-cliff | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | strict JSON parse |
| json-cliff | context | 3 | 36 | 100.0 (90.4-100.0) | 86.1 | strict JSON parse |
| json-plain | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | strict JSON parse |
| json-plain | context | 3 | 36 | 100.0 (90.4-100.0) | 91.7 | strict JSON parse |
| po | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | msgid/msgstr grammar |
| po | context | 3 | 36 | 100.0 (90.4-100.0) | 80.6 | msgid/msgstr grammar |
| xliff-2.1 | bare | 3 | 36 | 72.2 (56.0-84.2) | 71.4 | lenient parse |
| xliff-2.1 | context | 3 | 36 | 77.8 (61.9-88.3) | 69.4 | lenient parse |
| yaml-cliff | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | strict YAML parse |
| yaml-cliff | context | 3 | 36 | 100.0 (90.4-100.0) | 86.1 | strict YAML parse |

> The validity checkers are **not of equal strictness**: CLIFF is validated by the official validator, while other formats only need to parse. still valid % is comparable only within a format row.

## 8. What this audit cannot fix without a re-run

1. **Context-arm fixtures with a missing target slot** (json-cliff context, csv context). No post-hoc analysis recovers a translation the model was never asked to produce; these cells need a renderer fix and a re-run.
2. **Human sign-off of corpus references.** human_verified is false for every authored item. A reference-free QE pass (WMT-QE class model) removes the dependency on reference quality for quality claims; chrF/BLEU against the current references remain reference-dependent. The audited scores above are still relative to those references.
3. **Non-CJK evaluation.** Only zh-CN (plus a small zh->en classical subset) was measured.
4. **Practical meaningfulness.** Statistical significance is reported as such, without an MT-Thresholds anchor.

## 9. Workflow comparison: CLIFF context arm (mandatory context payload) vs other formats (bare, shipped form)

This is the comparison CLIFF is designed for: thanks to mandatory `type`/inherited group metadata and a closed context schema, a CLIFF file **necessarily** carries its context payload (header info/standard, group metadata, per-entry context, type, emotion, max-width — the fields CLIFF makes mandatory or inherit), while the other formats in their shipped (bare) form carry nothing beyond identifier + source. The context arm of the competitors is a reference control only: it shows what happens when the same context payload is hand-injected into their non-mandatory channels — the fair apples-to-apples check that the quality differences collapse to ~0 once everyone carries the same context.

| vs | CLIFF context vs other bare: chrF++ diff | 95% CI | bootstrap p | Holm p |
| --- | ---: | ---: | ---: | ---: |
| android | -2.46 | -7.79-2.08 | 0.3336 | 1.0000 (n.s.) |
| csv | 6.91 | -0.16-13.79 | 0.0562 | 0.5057 (n.s.) |
| fluent | -1.61 | -6.76-2.75 | 0.5333 | 1.0000 (n.s.) |
| ios | -1.03 | -6.33-3.56 | 0.7191 | 1.0000 (n.s.) |
| json-cliff | -1.28 | -6.56-3.19 | 0.6459 | 1.0000 (n.s.) |
| json-plain | -1.06 | -6.21-3.32 | 0.6989 | 1.0000 (n.s.) |
| po | -1.27 | -6.55-3.19 | 0.6483 | 1.0000 (n.s.) |
| xliff-2.1 | -1.44 | -6.57-2.85 | 0.5863 | 1.0000 (n.s.) |
| yaml-cliff | -1.38 | -6.33-2.78 | 0.5845 | 1.0000 (n.s.) |

> D1/D2 show the same comparison on token cost: the CLIFF file carrying its mandatory context payload costs 47 499 document tokens per corpus (vs 8 065 in its bare arm), while the cheapest competitor in bare form is json-plain at 20 647 and the cheapest competitor carrying the same context payload is yaml-cliff at 52 753. The format does not trade quality for tokens at the workflow level: it delivers the context payload that produces the quality above, at a lower token cost than any competitor carrying the same context payload.
> **Strict-score note:** json-cliff context (real translation rate 25%) and csv context (85% parse failure) are counted, not excluded: per the strict reading they score 0 for the untranslated/unparseable part. Their quality advantage claim is thereby removed; the remaining competitive rows (android, ios, json-plain, po, yaml-cliff, fluent, xliff-2.1) are the valid comparisons.

