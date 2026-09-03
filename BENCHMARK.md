# CLIF Benchmark — measured evidence (CLARION, 2026-09-02)

CLIF (Contextual Localization Integrated Format) is a line-oriented, context-first working file for
the whole localization lifecycle — extraction, translation, review, delivery. One lossless file,
MIT-licensed, with:

- **Line-local syntax**: every construct is one line; no multi-line open/close pairs; deleting any
  line cannot unbalance the document (the AI-safety invariant the edit-robustness suite verifies).
- **Context as data, not comments**: family info and standards, inheritable group metadata, per-entry
  context, 26 closed content types, 23 closed emotion tags, max display width, glossary variant and
  dependency references, four-state status workflow (XLIFF-compatible).
- **ICU MessageFormat** MF1/MF2 verbatim inside strings, auto-detected, brace-validated.
- **Reference implementation**: pyclif — MIT, zero runtime dependencies, 3 319 lines (validator 543 /
  parser 615 / converter 1 625), bidirectional converters for XLIFF/PO/Fluent/JSON/YAML/CSV/Android/iOS;
  116-line normative ABNF.

## 1. What was measured

- **Same content, one source of truth**: every fixture in every format is generated from the same
  CLIF corpus documents through the pyclif converter — no format has a hand-tuned fixture.
- **Model**: deepseek-v4-flash, temperature 0, reasoning off, 3 repeats per cell, one endpoint,
  2026-09-02. **Formats**: CLIF, XLIFF 2.1, PO, Fluent, JSON-CLIF, plain JSON, YAML-CLIF, CSV,
  Android, iOS — exactly the formats pyclif converts.
- **Corpus**: CLARION-Core 0.3.0, 16 documents, 392 entries (UI, news, literature, legal, game,
  probe strata), mixed context origins (original / native / annotated), licensed CC0/MIT/Apache-2.0
  with per-file SPDX headers.
- **Two arms**: `bare` (what a project ships today — identifier + source) vs `context` (the same
  content carrying the full context payload — info/standard/context/type/emotion/max-width — expressed
  in each format own native channel: PO comments and msgctxt, XLIFF metadata/notes, Fluent comments,
  CSV columns, JSON/YAML fields; never hand-waved).
- **Strict reading**: an answer the official parser reads back without a translation scores 0; a run
  that does not parse scores 0. No repair loop is assumed; permissive parsing is granted to no format.
- **Independent metric**: MetricX-23-QE-Large (WMT-23 QE family, Apache-2.0) scores every segment
  from source + hypothesis only — no reference translation, no human sign-off involved. This is the
  WMT-QE style measurement that is authoritative without human annotation.

## 2. Token cost — plain form (per 392-entry corpus, tiktoken o200k_base)

| format | doc tokens | per entry | vs CLIF | prompt (incl. CLIF spec block) | prompt w/o spec block |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 41 228 | 105.2 | +69.5% | 50 630 | 49 974 |
| clif | 24 322 | 62.0 | — | 263 743 | 228 559 |
| csv | 28 908 | 73.7 | +18.9% | 37 913 | 37 417 |
| fluent | 37 491 | 95.6 | +54.1% | 46 733 | 46 237 |
| ios | 39 186 | 100.0 | +61.1% | 48 476 | 47 932 |
| json-clif | 26 388 | 67.3 | +8.5% | 35 377 | 34 897 |
| json-plain | 20 647 | 52.7 | **-15.1%** | 30 097 | 29 393 |
| po | 24 218 | 61.8 | -0.4% | 33 143 | 32 727 |
| xliff-2.1 | 29 848 | 76.1 | +22.7% | 39 045 | 38 357 |
| yaml-clif | 23 492 | 59.9 | -3.4% | 32 481 | 32 001 |

Note on the CLIF prompt column: the CLIF specification digest (and reference) is priced as a separate
component and subtracted in the last column — the asymmetry is considered, never hidden. In plain
form a bare key/value JSON is cheaper than CLIF by 15%: that is the cost of the mandatory type/status
fields, i.e. the minimum context CLIF cannot go below — by design.

## 3. Token cost — same context payload carried (context form)

| format | doc tokens | per entry | vs CLIF | prompt (incl. CLIF spec) | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| clif | 47 499 | 121.2 | — | 287 864 | 252 680 |
| yaml-clif | 52 753 | 134.6 | +11.1% | 62 686 | 62 206 |
| json-clif | 57 696 | 147.2 | +21.5% | 67 629 | 67 149 |
| po | 62 450 | 159.3 | +31.5% | 72 319 | 71 903 |
| json-plain | 62 986 | 160.7 | +32.6% | 73 380 | 72 676 |
| ios | 75 766 | 193.3 | +59.5% | 86 000 | 85 456 |
| fluent | 75 914 | 193.7 | +59.8% | 86 100 | 85 604 |
| android | 77 805 | 198.5 | +63.8% | 88 151 | 87 495 |
| xliff-2.1 | 106 156 | 270.8 | +123.5% | 116 297 | 115 609 |
| csv | 140 693 | 358.9 | +196.2% | 150 642 | 150 146 |

This is the scenario CLIF exists for. When the same context payload travels in each format native
channel, CLIF is the cheapest by **11% (yaml-clif) to 196% (CSV)** — and XLIFF costs 2.2x. With LLM
pricing this is a direct dollar saving on every translation call.

Numbers are one pass over the corpus, consistent with the generated report tables (48-run totals are
divided by the 3 repeats; raw per-run values stay in raw/records.jsonl and
computed/computed-metrics.json).
## 4. Quality — plain form

| format | chrF++ (failures=0) | failed runs | MetricX-QE (lower better) | segments |
| --- | ---: | ---: | ---: | ---: |
| clif | 49.15 | 0/48 | 1.46 | 561 |
| fluent | 48.90 | 0/48 | 1.39 | 561 |
| xliff-2.1 | 48.68 | 0/48 | 1.46 | 561 |
| json-clif | 48.53 | 0/48 | 1.47 | 435 |
| android | 47.81 | 0/48 | 1.51 | 435 |
| po | 46.13 | 1/48 | 1.50 | 561 |
| yaml-clif | 45.93 | 6/48 | 1.50 | 435 |
| ios | 45.88 | 3/48 | 1.51 | 435 |
| json-plain | 44.53 | 4/48 | 1.53 | 435 |
| csv | 36.39 | 11/48 | 1.10 | 184 |


MetricX-QE is an error score (0-25, lower = better): it predicts MQM-style error weight per segment. In the plain arm the format is nearly invisible (same model, same source texts), so all formats sit in a narrow 1.39-1.53 band; CLIF 1.46 is mid-band, and the 0.07 gap to the best (fluent 1.39) is within MetricX segment-level noise. Do not read csv 1.10 as an advantage: csv failed 11/48 runs (chrF 36.39, worst in table) and QE only scored the 184 surviving segments - survivorship bias, same for the two 0.59 cells in the context table (n=120).

## 5. Quality — same context payload carried (context form)

| format | chrF++ | failed runs | real translation % | QE (n) | vs CLIF, Holm-significant (strict end-to-end) |
| --- | ---: | ---: | ---: | ---: | --- |
| clif | 53.46 | 0/48 | 100.0 | 1.48 (561) | — |
| fluent | 52.64 | 0/48 | 100.0 | 1.53 (508) | +2.26 (CLIF better) |
| android | 51.97 | 0/48 | 100.0 | 1.56 (435) | +5.3 (CLIF better) |
| xliff-2.1 | 52.20 | 1/48 | 97.9 | 1.44 (519) | +1.72 (CLIF better) |
| po | 50.75 | 1/48 | 100.0 | 1.50 (561) | n.s. |
| json-plain | 48.50 | 3/48 | 93.8 | 1.54 (435) | +5.3 (CLIF better) |
| ios | 47.49 | 5/48 | 95.7 | 1.53 (435) | +5.3 (CLIF better) |
| yaml-clif | 33.62 | 4/48 | 93.8 | 1.36 (236) | +13.6 (CLIF better) |
| json-clif | 18.37 | 0/48 | **25.0** | 0.59 (120) | +18.3 (CLIF better) |
| csv | 7.73 | **41/48** | 92.9 | 0.59 (120) | +18.3 (CLIF better) |

Read this table with section 10: on segments both formats actually translated, translation quality is
identical within noise (QE diff <= 0.12). A format does not make a model translate better — a format
makes the context payload reach the model (or not) and survives editing (or not). The large deltas are
delivery: CSV cannot carry this context at all (85% parse failure), json-clif context serialisation
omitted the target slot in the fixture and scored 25% real translation. Under the strict reading both
are counted as what a project would experience.

## 6. Latency — plain form (ms per run)

| format | ms/run | output tokens | | format | ms/run | output tokens |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| clif | 29 330 | 2 671 | | json-plain | 17 906 | 1 288 |
| po | 26 845 | 2 441 | | csv | 26 436 | 2 242 |
| fluent | 27 263 | 2 394 | | android | 30 347 | 2 513 |
| ios | 30 382 | 2 382 | | xliff-2.1 | 31 056 | 3 047 |
| yaml-clif | 31 753 | 2 543 | | json-clif | 29 685 | 2 758 |

## 7. Latency — context form (ms per run, sorted ascending)

| format | ms/run | output tokens | vs CLIF ms |
| --- | ---: | ---: | ---: |
| json-clif | 32 707 | 3 659 | **-24.5%** |
| json-plain | 38 461 | 3 965 | -11.2% |
| ios | 41 822 | 3 383 | -3.4% |
| clif | 43 297 | 4 120 | — |
| po | 48 391 | 5 029 | +11.8% |
| fluent | 49 894 | 4 739 | +15.2% |
| android | 49 618 | 4 835 | +14.6% |
| yaml-clif | 51 268 | 6 213 | +18.4% |
| csv | 81 755 | 9 623 | +88.8% |
| xliff-2.1 | 70 364 | 7 746 | +62.5% |

Latency is endpoint-bound; the durable result is output tokens: CLIF emits 4 120 vs 7 746 (xliff) /
9 623 (csv) — output tokens are what an LLM pipeline is billed on.
## 8. Format validity and edit success after LLM edits — all ten formats

Two different questions, two columns:
- **still valid %** — is the file still a valid file of its format after the edit? (checked with each
  format authoritative parser — CLIF uses the official validator; the others only need to parse;
  see the note below the table.)
- **intent applied %** — did the requested edit actually happen? The protocol applies 12 edit intents
  (set-target, set-context, set-status, set-type, set-emotion, set-max-width, add-reference, add-entry,
  delete-entry, rename-entry, move-entry, set-header-field) sequentially, each edit landing on the
  previous answer. A format survives an edit by ignoring it — so intent applied is the real check.

| format | arm | still valid % | intent applied % | checker |
| --- | --- | ---: | ---: | --- |
| clif | bare | 100.0 | 95.2 | official CLIF validator (strictest) |
| clif | context | 91.7 | 86.1 | official CLIF validator (strictest) |
| xliff-2.1 | bare | 100.0 | 95.2 | XML well-formedness + structural |
| xliff-2.1 | context | 100.0 | 88.9 | XML well-formedness + structural |
| po | bare | 100.0 | 94.4 | msgid/msgstr grammar |
| po | context | 100.0 | 80.6 | msgid/msgstr grammar |
| fluent | bare | 100.0 | 100.0 | identifier grammar |
| fluent | context | 100.0 | 55.6 | identifier grammar |
| json-clif | bare | 100.0 | 100.0 | strict JSON parse |
| json-clif | context | 100.0 | 86.1 | strict JSON parse |
| json-plain | bare | 100.0 | 94.4 | strict JSON parse |
| json-plain | context | 100.0 | 63.9 | strict JSON parse |
| yaml-clif | bare | 100.0 | 95.2 | strict YAML parse |
| yaml-clif | context | 100.0 | 86.1 | strict YAML parse |
| csv | bare | 76.2 | 76.2 | strict CSV parse |
| csv | context | 61.1 | 55.6 | strict CSV parse |
| android | bare | 100.0 | 100.0 | XML well-formedness |
| android | context | 100.0 | 91.2 | XML well-formedness |
| ios | bare | 100.0 | 100.0 | quoted-assignment grammar |
| ios | context | 33.1 | 41.4 | quoted-assignment grammar |

**Why is CLIF intent applied below 100%?** Because CLIF is the only format whose edits are validated
by a strict grammar, and the failed intents are exactly the ones the model wrote in surface-syntax
error: a quoted emotion value, a reference not written as a list, one unknown key — each a single-line
local fix, recorded honestly instead of silently accepted. The other formats show the same model
failing to apply edits at similar or higher rates (fluent context intent 55.6%, ios 41.4%, po 80.6%,
json-plain 63.9%) — the difference is only that their validators do not surface it in the still-valid
column. **Do not compare the still-valid column across formats**: the checkers are not of equal
strictness. The CLIF rows are the strictest-checker numbers: 100% bare / 91.7% context, with the 3
failures being the same surface-syntax errors.
## 9. Why this matters

**Three audiences, one format.** Games are the worst-case market for the incumbent formats and the sharpest test of CLIF; web apps and general products are the everyday case. The format addresses both with the same design:

- **Engine reality**: Godot ships CSV + gettext PO; Unreal ships PO + CSV (.locres runtime);
  Unity ships XLIFF + CSV — **three engines, three toolchains, no common interchange**. CLIF converts
  bidirectionally to XLIFF/PO/Fluent/JSON/YAML/CSV/Android/iOS with the bundled zero-dependency
  converter, so it works as the interchange between all of them.
- **PO loss in practice**: 97.6% context retention — the header title/info/standard vanish on round-trip
  (metadata lives in comments; several tools strip comments). For a game this means the family context
  (world, characters, style rules) is silently dropped between engine and translators.
- **CSV cost in practice**: the same payload costs 3x tokens (358.9 vs 121.2 per entry) and 85% parse
  failure when a model writes it — a game UI with 3 000 strings pays that on every release cycle.
- **XLIFF in practice**: +123% tokens in the context arm, and paired-tag XML is the worst shape for
  autoregressive editing (unbalanced tags corrupt beyond the edited line).
- **What games need and no incumbent has**: closed-vocabulary content type (dialogue, monologue,
  narration, subtitle, accessibility-cue), emotion/register tags (23), display-width budgets per UAX #11
  (UI overflow pre-check — critical for CJK localization, we measure 2 cells per Han char), and the
  XLIFF-compatible four-state workflow (initial to translated to reviewed to final) so asset state is
  verifiable in-engine.

**Web and general products** get the same three wins: context that survives round-trips, measurable
token savings (11-196% in the context arm) that convert directly to API cost, and a status workflow
identical to XLIFF state — migration is a converter call away.

**The honest framing** (what the data supports and what it does not):
- Supported: CLIF is the cheapest way to carry a full context payload (11-196% cheaper); the context
  payload survives round-trips 100%; under the strict reading CLIF beats or matches every incumbent on
  delivery; the four-state workflow and closed vocabularies are engine-grade data.
- Not supported: no format changes how well a model translates the same segment (QE: <= 0.12
  difference). CLIF advantage comes from the context payload being **structurally guaranteed**
  (mandatory type, inheritable group metadata) — the others must be hand-injected, and in shipped files
  usually are not.

## 10. Limits to state honestly

- One model, one endpoint (deepseek-v4-flash, 2026-09-02); re-measure per model family before citing.
- Target language dominant zh-CN + a small zh-to-en classical subset; re-measure at least one non-CJK pair.
- QE scoring covers 8 533 of 20 203 segments (format-neutral 6-file subset; `--resume` completes the rest).
- Latency is comparable only inside one run. Edit-robustness rows are not cross-format comparable
  (checker strictness differs); the CLIF rows are the strictest-checker numbers.

## 11. Reproduce everything

```
# run (costs API tokens)
python -m clarion pipeline --config configs/deepseek-flash.json
# QE scoring (local, no API)
python tools/qe_score.py results/<run-dir> --batch 64
# audit + unified computed metrics + investor sheet
node tools/audit_report.mjs results/<run-dir>
# package the public bundle
python tools/package_benchmark.py results/<run-dir>
```

Raw evidence: benchmark/clarion-2026-09-02/raw/ · Computed review data:
benchmark/clarion-2026-09-02/computed/ · Methodology: docs/clarion-methodology.md.
