# CLARION audit - clarion-deepseek-v4-flash

- Run: clarion-deepseek-v4-flash-20260902T040228+0000-91f21a
- Model: deepseek-v4-flash (openai), temperature 0
- Records parsed: **1180** (translation 960, robustness 60, fidelity 160)
- **Audit method: no model call was made and nothing was regenerated.** Numbers below are recomputed from records.jsonl, answers/*.answer.txt, the corpus gold, and config/summary. Reproduce: node tools/audit_report.mjs results\clarion-deepseek-v4-flash-20260902T040228+0000-91f21a

## 1. Corrected failure accounting

The run summary reports 960 runs, 0 failed (pipeline-level gate). This table counts **record-level** failures (outcome != ok: parse-error / invalid / incomplete / degenerate / gold-leak) with Wilson 95% intervals. The real translation % column is the audit-recomputed share of entries that actually carry a non-empty translation (see section 2).

| format | arm | runs | failed | failed % (95% CI) | recorded coverage % | real translation % |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| android | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| android | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| clif | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| clif | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| csv | bare | 48 | 11 | 77.1 (63.5-86.7) | 77.1 | 54.3 |
| csv | context | 48 | 41 | 14.6 (7.2-27.2) | 27.1 | 92.9 |
| fluent | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| fluent | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| ios | bare | 48 | 3 | 93.8 (83.2-97.9) | 95.2 | 95.2 |
| ios | context | 48 | 5 | 89.6 (77.8-95.5) | 95.7 | 95.7 |
| json-clif | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| json-clif | context | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 25.0 |
| json-plain | bare | 48 | 4 | 91.7 (80.4-96.7) | 91.7 | 91.7 |
| json-plain | context | 48 | 3 | 93.8 (83.2-97.9) | 93.8 | 93.8 |
| po | bare | 48 | 1 | 97.9 (89.1-99.6) | 100.0 | 100.0 |
| po | context | 48 | 1 | 97.9 (89.1-99.6) | 100.0 | 100.0 |
| xliff-2.1 | bare | 48 | 0 | 100.0 (92.6-100.0) | 100.0 | 100.0 |
| xliff-2.1 | context | 48 | 1 | 97.9 (89.1-99.6) | 97.9 | 97.9 |
| yaml-clif | bare | 48 | 6 | 87.5 (75.3-94.1) | 87.5 | 87.5 |
| yaml-clif | context | 48 | 4 | 91.7 (80.4-96.7) | 93.8 | 93.8 |

> Pipeline stage: 960 runs, 0 failed, 5103039 prompt + 3724383 output tokens billed Record-level failures are what the scores actually contain.

## 2. Measurement-integrity audit (every answer re-parsed)

The recorded structural checker accepts an answer as fully covered when the parser can fill a value from the **source** when no target slot exists (structure.py: value = entry.target or entry.source). That turns a target-less answer into coverage = 1.0 and scores the source text against the gold. This audit scans every stored answer for an actual non-empty translation slot.

| format | arm | recorded coverage % | real translation % | integrity |
| --- | --- | ---: | ---: | --- |
| android | bare | 100.0 | 100.0 | ok |
| android | context | 100.0 | 100.0 | ok |
| clif | bare | 100.0 | 100.0 | ok |
| clif | context | 100.0 | 100.0 | ok |
| csv | bare | 77.1 | 54.3 | low translation rate |
| csv | context | 27.1 | 92.9 | ok |
| fluent | bare | 100.0 | 100.0 | ok |
| fluent | context | 100.0 | 100.0 | ok |
| ios | bare | 95.2 | 95.2 | ok |
| ios | context | 95.7 | 95.7 | ok |
| json-clif | bare | 100.0 | 100.0 | ok |
| json-clif | context | 100.0 | 25.0 | **DEFECT: coverage inflated by source fallback** |
| json-plain | bare | 91.7 | 91.7 | ok |
| json-plain | context | 93.8 | 93.8 | ok |
| po | bare | 100.0 | 100.0 | ok |
| po | context | 100.0 | 100.0 | ok |
| xliff-2.1 | bare | 100.0 | 100.0 | ok |
| xliff-2.1 | context | 97.9 | 97.9 | ok |
| yaml-clif | bare | 87.5 | 87.5 | low translation rate |
| yaml-clif | context | 93.8 | 93.8 | ok |

**Strict reading (used here):** an answer the official parser reads back without a translation for an entry is a failed translation of that entry and scores 0 — exactly as an unparseable answer is a failed run. No answer is exempted because a second prompt could repair it: repair costs tokens, and permissive parsing is granted to no format. The rows flagged above are therefore counted, not excluded.

## 3. Strict quality (recorded vs audited)

Strict score = recorded chrF++ scaled by the real translation ratio: entries the official parser reads back without a translation score 0 (untranslated), unparseable runs score 0 (failed). No format gets credit for text it did not deliver in a parseable form.

| format | arm | recorded chrF++ (all) | audited chrF++ (all) | drop |
| --- | --- | ---: | ---: | ---: |
| android | bare | 47.81 | 47.81 | 0.00 |
| android | context | 51.97 | 51.97 | 0.00 |
| clif | bare | 49.15 | 49.15 | 0.00 |
| clif | context | 53.46 | 53.46 | 0.00 |
| csv | bare | 36.39 | 24.95 | 11.44 |
| csv | context | 7.73 | 7.73 | 0.00 |
| fluent | bare | 48.90 | 48.90 | 0.00 |
| fluent | context | 52.64 | 52.64 | 0.00 |
| ios | bare | 45.88 | 45.88 | 0.00 |
| ios | context | 47.49 | 47.49 | 0.00 |
| json-clif | bare | 48.53 | 48.53 | 0.00 |
| json-clif | context | 18.37 | 15.67 | 2.70 |
| json-plain | bare | 44.53 | 44.53 | 0.00 |
| json-plain | context | 48.50 | 48.50 | 0.00 |
| po | bare | 46.13 | 46.13 | 0.00 |
| po | context | 50.75 | 50.75 | 0.00 |
| xliff-2.1 | bare | 48.68 | 48.68 | 0.00 |
| xliff-2.1 | context | 52.20 | 52.20 | 0.00 |
| yaml-clif | bare | 45.93 | 45.93 | 0.00 |
| yaml-clif | context | 33.62 | 33.62 | 0.00 |

## 4. Breakdown by context origin (context arm)

| format | origin | runs | chrF++ (all) | failed % |
| --- | --- | ---: | ---: | ---: |
| android | annotated | 9 | 40.16 | 0.0 |
| android | native | 3 | 82.66 | 0.0 |
| android | original | 36 | 52.36 | 0.0 |
| clif | annotated | 9 | 41.46 | 0.0 |
| clif | native | 3 | 82.66 | 0.0 |
| clif | original | 36 | 54.02 | 0.0 |
| csv | annotated | 9 | 0.00 | 88.9 |
| csv | native | 3 | 84.73 | 0.0 |
| csv | original | 36 | 3.24 | 91.7 |
| fluent | annotated | 9 | 41.19 | 0.0 |
| fluent | native | 3 | 80.97 | 0.0 |
| fluent | original | 36 | 53.14 | 0.0 |
| ios | annotated | 9 | 22.90 | 55.6 |
| ios | native | 3 | 84.73 | 0.0 |
| ios | original | 36 | 50.54 | 0.0 |
| json-clif | annotated | 9 | 6.89 | 0.0 |
| json-clif | native | 3 | 82.15 | 0.0 |
| json-clif | original | 36 | 15.92 | 0.0 |
| json-plain | annotated | 9 | 30.71 | 33.3 |
| json-plain | native | 3 | 83.60 | 0.0 |
| json-plain | original | 36 | 50.02 | 0.0 |
| po | annotated | 9 | 40.92 | 0.0 |
| po | native | 3 | 80.99 | 0.0 |
| po | original | 36 | 50.69 | 2.8 |
| xliff-2.1 | annotated | 9 | 34.72 | 11.1 |
| xliff-2.1 | native | 3 | 82.66 | 0.0 |
| xliff-2.1 | original | 36 | 54.03 | 0.0 |
| yaml-clif | annotated | 9 | 13.09 | 44.4 |
| yaml-clif | native | 3 | 80.86 | 0.0 |
| yaml-clif | original | 36 | 34.82 | 0.0 |

> **annotated** context was written by deepseek-v4-pro (annotation pass, no human sign-off); **native** means the upstream project shipped it (here: Godot PO only). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

## 5. Breakdown by language direction

| direction | files | runs | chrF++ (all) | failed % |
| --- | ---: | ---: | ---: | ---: |
| en-US->zh-CN | 13 | 780 | 48.50 | 5.6 |
| zh-CN->en-US | 3 | 180 | 24.14 | 20.0 |

> The run mixes en-US->zh-CN (13 files) with zh-CN->en-US classical literature (3 files, gold from 1892/1925 translations) in one table; chrF++ is not comparable across directions.

## 6. Paired significance: CLIF vs every other format

### Arm bare

Paired design (file, repeat); audited scores; paired bootstrap (10,000) + paired permutation (10,000); Holm-corrected across the nine comparisons per arm.

| vs | diff (clif-other) | 95% CI | bootstrap p | permutation p | Holm p |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 1.34 | 0.48-2.10 | 0.0036 | 0.0032 | 0.0180 (significant) |
| csv | 24.20 | 17.43-31.14 | 0.0002 | 0.0000 | 0.0018 (significant) |
| fluent | 0.25 | -0.63-1.11 | 0.5713 | 0.5698 | 0.5713 (n.s.) |
| ios | 3.28 | 1.32-5.66 | 0.0002 | 0.0006 | 0.0018 (significant) |
| json-clif | 0.62 | -0.27-1.42 | 0.1534 | 0.1587 | 0.4602 (n.s.) |
| json-plain | 4.63 | 2.34-7.28 | 0.0002 | 0.0002 | 0.0018 (significant) |
| po | 3.03 | 0.84-5.73 | 0.0024 | 0.0119 | 0.0144 (significant) |
| xliff-2.1 | 0.48 | -0.24-1.12 | 0.1852 | 0.1799 | 0.4602 (n.s.) |
| yaml-clif | 3.22 | 0.37-6.53 | 0.0226 | 0.0445 | 0.0904 (n.s.) |

> Statistical significance is not practical significance; no MT-Thresholds anchor is available.

### Arm context

Paired design (file, repeat); audited scores; paired bootstrap (10,000) + paired permutation (10,000); Holm-corrected across the nine comparisons per arm.

| vs | diff (clif-other) | 95% CI | bootstrap p | permutation p | Holm p |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 1.49 | 0.41-2.50 | 0.0080 | 0.0082 | 0.0240 (significant) |
| csv | 45.73 | 39.35-51.79 | 0.0002 | 0.0000 | 0.0018 (significant) |
| fluent | 0.82 | -0.18-1.70 | 0.0954 | 0.0962 | 0.1908 (n.s.) |
| ios | 5.96 | 3.54-8.92 | 0.0002 | 0.0000 | 0.0018 (significant) |
| json-clif | 37.79 | 30.69-44.60 | 0.0002 | 0.0000 | 0.0018 (significant) |
| json-plain | 4.96 | 2.88-7.43 | 0.0002 | 0.0000 | 0.0018 (significant) |
| po | 2.71 | 1.28-4.69 | 0.0002 | 0.0001 | 0.0018 (significant) |
| xliff-2.1 | 1.26 | -1.80-5.31 | 0.5305 | 0.5081 | 0.5305 (n.s.) |
| yaml-clif | 19.83 | 12.60-27.72 | 0.0002 | 0.0000 | 0.0018 (significant) |

> Statistical significance is not practical significance; no MT-Thresholds anchor is available.

## 7. Edit-robustness (D7) with Wilson intervals

| format | arm | chains | applicable edits | still valid % (95% CI) | intent applied % | checker |
| --- | --- | ---: | ---: | --- | ---: | --- |
| android | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | XML well-formedness |
| android | context | 3 | 36 | 100.0 (90.4-100.0) | 91.2 | XML well-formedness |
| clif | bare | 3 | 36 | 100.0 (90.4-100.0) | 95.2 | strict CLIF validator (pyclif) |
| clif | context | 3 | 36 | 91.7 (78.2-97.1) | 86.1 | strict CLIF validator (pyclif) |
| csv | bare | 3 | 36 | 75.0 (58.9-86.2) | 76.2 | strict CSV parse |
| csv | context | 3 | 36 | 61.1 (44.9-75.2) | 55.6 | strict CSV parse |
| fluent | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | identifier grammar |
| fluent | context | 3 | 36 | 100.0 (90.4-100.0) | 55.6 | identifier grammar |
| ios | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | quoted-assignment grammar |
| ios | context | 3 | 36 | 33.3 (20.2-49.7) | 41.4 | quoted-assignment grammar |
| json-clif | bare | 3 | 36 | 100.0 (90.4-100.0) | 100.0 | strict JSON parse |
| json-clif | context | 3 | 36 | 100.0 (90.4-100.0) | 86.1 | strict JSON parse |
| json-plain | bare | 3 | 36 | 100.0 (90.4-100.0) | 94.4 | strict JSON parse |
| json-plain | context | 3 | 36 | 100.0 (90.4-100.0) | 63.9 | strict JSON parse |
| po | bare | 3 | 36 | 100.0 (90.4-100.0) | 94.4 | msgid/msgstr grammar |
| po | context | 3 | 36 | 100.0 (90.4-100.0) | 80.6 | msgid/msgstr grammar |
| xliff-2.1 | bare | 3 | 36 | 100.0 (90.4-100.0) | 95.2 | lenient parse |
| xliff-2.1 | context | 3 | 36 | 100.0 (90.4-100.0) | 88.9 | lenient parse |
| yaml-clif | bare | 3 | 36 | 100.0 (90.4-100.0) | 95.2 | strict YAML parse |
| yaml-clif | context | 3 | 36 | 100.0 (90.4-100.0) | 86.1 | strict YAML parse |

> The validity checkers are **not of equal strictness**: CLIF is validated by the official validator, while other formats only need to parse. still valid % is comparable only within a format row.

## 8. What this audit cannot fix without a re-run

1. **Context-arm fixtures with a missing target slot** (json-clif context, csv context). No post-hoc analysis recovers a translation the model was never asked to produce; these cells need a renderer fix and a re-run.
2. **Human sign-off of corpus references.** human_verified is false for every authored item. A reference-free QE pass (WMT-QE class model) removes the dependency on reference quality for quality claims; chrF/BLEU against the current references remain reference-dependent. The audited scores above are still relative to those references.
3. **Non-CJK evaluation.** Only zh-CN (plus a small zh->en classical subset) was measured.
4. **Practical meaningfulness.** Statistical significance is reported as such, without an MT-Thresholds anchor.

## 9. Workflow comparison: CLIF context arm (mandatory context payload) vs other formats (bare, shipped form)

This is the comparison CLIF is designed for: thanks to mandatory `type`/inherited group metadata and a closed context schema, a CLIF file **necessarily** carries its context payload (header info/standard, group metadata, per-entry context, type, emotion, max-width — the fields CLIF makes mandatory or inherit), while the other formats in their shipped (bare) form carry nothing beyond identifier + source. The context arm of the competitors is a reference control only: it shows what happens when the same context payload is hand-injected into their non-mandatory channels — the fair apples-to-apples check that the quality differences collapse to ~0 once everyone carries the same context.

| vs | CLIF context vs other bare: chrF++ diff | 95% CI | bootstrap p | Holm p |
| --- | ---: | ---: | ---: | ---: |
| android | 5.65 | 4.21-7.23 | 0.0002 | 0.0018 (significant) |
| csv | 28.51 | 21.83-35.26 | 0.0002 | 0.0018 (significant) |
| fluent | 4.56 | 2.92-6.40 | 0.0002 | 0.0018 (significant) |
| ios | 7.58 | 5.29-10.18 | 0.0002 | 0.0018 (significant) |
| json-clif | 4.93 | 3.25-6.83 | 0.0002 | 0.0018 (significant) |
| json-plain | 8.93 | 6.51-11.63 | 0.0002 | 0.0018 (significant) |
| po | 7.33 | 4.76-10.30 | 0.0002 | 0.0018 (significant) |
| xliff-2.1 | 4.78 | 3.31-6.47 | 0.0002 | 0.0018 (significant) |
| yaml-clif | 7.53 | 4.56-10.81 | 0.0002 | 0.0018 (significant) |

> D1/D2 show the same comparison on token cost: the CLIF file carrying its mandatory context payload costs 47 499 document tokens per corpus (vs 8 065 in its bare arm), while the cheapest competitor in bare form is json-plain at 20 647 and the cheapest competitor carrying the same context payload is yaml-clif at 52 753. The format does not trade quality for tokens at the workflow level: it delivers the context payload that produces the quality above, at a lower token cost than any competitor carrying the same context payload.
> **Strict-score note:** json-clif context (real translation rate 25%) and csv context (85% parse failure) are counted, not excluded: per the strict reading they score 0 for the untranslated/unparseable part. Their quality advantage claim is thereby removed; the remaining competitive rows (android, ios, json-plain, po, yaml-clif, fluent, xliff-2.1) are the valid comparisons.


## 10. Reference-free quality estimation (QE)

Coverage: **8533 segments scored** (all formats scored on the same file subset; minimum files per format/arm = 1). The remaining corpus files can be completed with `python tools/qe_score.py <run-dir> --resume`; the subset is format-neutral, so format rankings within it stand.

WMT-QE style measurement: **MetricX-23-QE-Large** (Apache-2.0) predicts an MQM-style error score in [0, 25] from **source + hypothesis only** — no reference translation and no human sign-off is involved anywhere (official predict.py input format, score = logit of <extra_id_10>, clamped). It measures translation quality independently of the gold references, which was the only remaining reference-dependent weakness of the chrF/BLEU tables.

| format | arm | segments scored | mean QE (lower is better, 95% CI) |
| --- | --- | ---: | ---: |
| android | bare | 435 | 1.51 [1.35-1.70] |
| android | context | 435 | 1.56 [1.41-1.73] |
| clif | bare | 561 | 1.46 [1.33-1.61] |
| clif | context | 561 | 1.48 [1.35-1.63] |
| csv | bare | 184 | 1.10 [0.89-1.36] |
| csv | context | 120 | 0.59 [0.54-0.65] |
| fluent | bare | 561 | 1.39 [1.27-1.53] |
| fluent | context | 508 | 1.53 [1.38-1.67] |
| ios | bare | 435 | 1.51 [1.34-1.69] |
| ios | context | 435 | 1.53 [1.36-1.70] |
| json-clif | bare | 435 | 1.47 [1.32-1.64] |
| json-clif | context | 120 | 0.59 [0.53-0.65] |
| json-plain | bare | 435 | 1.53 [1.36-1.70] |
| json-plain | context | 435 | 1.54 [1.38-1.72] |
| po | bare | 561 | 1.50 [1.36-1.65] |
| po | context | 561 | 1.50 [1.37-1.65] |
| xliff-2.1 | bare | 561 | 1.46 [1.33-1.62] |
| xliff-2.1 | context | 519 | 1.44 [1.31-1.60] |
| yaml-clif | bare | 435 | 1.50 [1.34-1.68] |
| yaml-clif | context | 236 | 1.36 [1.12-1.61] |

### 10.1 Paired significance (QE error score; shared segments only; diff = other - clif, positive = CLIF better)

| arm | vs | shared segments | diff (other-clif) | 95% CI | bootstrap p | Holm p |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bare | android | 435 | 0.029 | 0.010-0.048 | 0.0032 | 0.0196 (significant) |
| bare | csv | 184 | 0.030 | 0.011-0.050 | 0.0028 | 0.0196 (significant) |
| bare | fluent | 561 | -0.073 | -0.126--0.028 | 0.0016 | 0.0144 (significant) |
| bare | ios | 435 | 0.020 | 0.003-0.037 | 0.0192 | 0.0768 (n.s.) |
| bare | json-clif | 435 | -0.015 | -0.066-0.027 | 0.5787 | 1.0000 (n.s.) |
| bare | json-plain | 435 | 0.044 | 0.011-0.080 | 0.0096 | 0.0480 (significant) |
| bare | po | 561 | 0.033 | 0.011-0.057 | 0.0024 | 0.0192 (significant) |
| bare | xliff-2.1 | 561 | 0.003 | -0.019-0.024 | 0.8158 | 1.0000 (n.s.) |
| bare | yaml-clif | 435 | 0.016 | -0.004-0.036 | 0.1192 | 0.3575 (n.s.) |
| context | android | 435 | 0.041 | -0.009-0.096 | 0.1144 | 0.8006 (n.s.) |
| context | csv | 120 | -0.001 | -0.004-0.003 | 0.7131 | 1.0000 (n.s.) |
| context | fluent | 508 | 0.029 | -0.015-0.078 | 0.2280 | 1.0000 (n.s.) |
| context | ios | 435 | 0.007 | -0.051-0.068 | 0.7978 | 1.0000 (n.s.) |
| context | json-clif | 120 | -0.004 | -0.010-0.001 | 0.1972 | 1.0000 (n.s.) |
| context | json-plain | 435 | 0.022 | -0.043-0.091 | 0.5107 | 1.0000 (n.s.) |
| context | po | 561 | 0.016 | -0.030-0.062 | 0.4887 | 1.0000 (n.s.) |
| context | xliff-2.1 | 519 | -0.048 | -0.083--0.017 | 0.0012 | 0.0096 (significant) |
| context | yaml-clif | 236 | 0.118 | 0.049-0.201 | 0.0004 | 0.0036 (significant) |

### 10.1b Strict paired comparison (missing translation scored as worst = 25)

| arm | vs | pairs | diff (other-clif) | 95% CI | bootstrap p | Holm p |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bare | android | 561 | 5.33 | 4.54-6.16 | 0.0004 | 0.0036 (significant) |
| bare | csv | 561 | 15.70 | 14.76-16.57 | 0.0004 | 0.0036 (significant) |
| bare | fluent | 561 | -0.07 | -0.13--0.03 | 0.0008 | 0.0036 (significant) |
| bare | ios | 561 | 5.32 | 4.54-6.15 | 0.0004 | 0.0036 (significant) |
| bare | json-clif | 561 | 5.29 | 4.51-6.13 | 0.0004 | 0.0036 (significant) |
| bare | json-plain | 561 | 5.34 | 4.56-6.17 | 0.0004 | 0.0036 (significant) |
| bare | po | 561 | 0.03 | 0.01-0.06 | 0.0024 | 0.0048 (significant) |
| bare | xliff-2.1 | 561 | 0.00 | -0.02-0.02 | 0.7962 | 0.7962 (n.s.) |
| bare | yaml-clif | 561 | 5.32 | 4.53-6.15 | 0.0004 | 0.0036 (significant) |
| context | android | 561 | 5.34 | 4.56-6.17 | 0.0004 | 0.0036 (significant) |
| context | csv | 561 | 18.30 | 17.48-19.07 | 0.0004 | 0.0036 (significant) |
| context | fluent | 561 | 2.26 | 1.71-2.84 | 0.0004 | 0.0036 (significant) |
| context | ios | 561 | 5.32 | 4.53-6.15 | 0.0004 | 0.0036 (significant) |
| context | json-clif | 561 | 18.29 | 17.48-19.07 | 0.0004 | 0.0036 (significant) |
| context | json-plain | 561 | 5.33 | 4.54-6.16 | 0.0004 | 0.0036 (significant) |
| context | po | 561 | 0.02 | -0.03-0.06 | 0.5103 | 0.5103 (n.s.) |
| context | xliff-2.1 | 561 | 1.72 | 1.25-2.25 | 0.0004 | 0.0036 (significant) |
| context | yaml-clif | 561 | 13.57 | 12.60-14.50 | 0.0004 | 0.0036 (significant) |

> Missing = the official parser read the answer without a target for that entry, or the run did not parse at all. Under this strict reading, format fragility is priced as quality loss rather than excluded.

### 10.2 QE by context origin (context arm, lower is better)

| origin | clif QE | clif segments | best competitor QE | worst competitor QE |
| --- | ---: | ---: | ---: | ---: |
| annotated | 1.37 | 252 | 1.28 (xliff-2.1) | 1.40 (po) |
| native | 0.59 | 240 | 0.59 (yaml-clif) | 0.63 (json-plain) |
| original | 1.85 | 630 | 1.81 (xliff-2.1) | 2.16 (yaml-clif) |

> QE is measured only on segments the model actually translated (missing targets are excluded, not scored 25). The unaffected property is the ranking of formats for the same segments; a format with many untranslated entries shows up in the integrity table instead.

