# CLIFF Benchmark — measured evidence (CLARION, 2026-09-21)

> **This is the benchmark of the shipped protocol.** `deepseek-flash`, reasoning
> **low**, temperature 1.3, the compressed CLIFF specification as the prompt
> (`prompt_style: spec`), answers read back **tolerantly** per CLIFF 1.1 Appendix C —
> which is what `configs/deepseek-flash.json` selects, so the numbers here describe
> the configuration a run started as documented produces. The raw evidence is the
> public bundle [`benchmark/clarion-2026-09-21`](benchmark/clarion-2026-09-21); the
> run directory is recorded in
> [CHANGELOG.md](CHANGELOG.md) and in [docs/acceptance-criteria.md](docs/acceptance-criteria.md).

CLIFF (Contextual Localization Integrated File Format) is a line-oriented, context-first working file for
the whole localization lifecycle — extraction, translation, review, delivery. One lossless file,
MIT-licensed, with:

- **Line-local syntax**: every construct is one line; no multi-line open/close pairs; deleting any
  line cannot unbalance the document (the AI-safety invariant the edit-robustness suite verifies).
- **Context as data, not comments**: family info and standards, inheritable group metadata, per-entry
  context, 26 closed content types, 23 closed emotion tags, max display width, glossary variant and
  dependency references, four-state status workflow (XLIFF-compatible).
- **ICU MessageFormat** MF1/MF2 verbatim inside strings, auto-detected, brace-validated.
- **Reference implementation**: cliff-python — MIT, zero runtime dependencies, bidirectional converters
  for XLIFF/PO/Fluent/JSON/YAML/CSV/Android/iOS, plus a normative ABNF.

## 1. What was measured

- **Same content, one source of truth**: every fixture in every format is generated from the same
  CLIFF corpus documents through the cliff-python converter — no format has a hand-tuned fixture.
- **Model**: `deepseek-flash`, **reasoning `low`**, temperature 1.3, 3 repeats per cell, one endpoint,
  2026-09-21, revision `b81d3e6`, prompt fingerprint `6ef59ba44d454294`. **Formats**: CLIFF,
  XLIFF 2.1, PO, Fluent, JSON-CLIFF, plain JSON, YAML-CLIFF, CSV, Android, iOS — exactly the formats
  cliff-python converts.
- **Corpus**: CLARION-Core 0.3.0, 16 standard documents plus 2 `variant: glossary` term files
  (18 `.cliff` files), 392 entries (UI, news, literature, legal, game, probe strata), mixed context
  origins (original / native / annotated), licensed CC0/MIT/Apache-2.0 with per-file SPDX headers.
- **Two arms**: `bare` (what a project ships today — identifier + source) vs `context` (the same
  content carrying the full context payload — info/standard/context/type/emotion/max-width — expressed
  in each format's own native channel: PO comments and msgctxt, XLIFF metadata/notes, Fluent comments,
  CSV columns, JSON/YAML fields; never hand-waved).
- **The reading the configuration declares**: `read_mode: tolerant`. An answer the reader can take back
  with a documented Appendix C repair is a valid answer and the repair is reported as a cost
  (`repairs/run`); an answer that needs a repair Appendix C.5 forbids scores 0. §11 reports the other
  reading on the same answers, so the two can be compared rather than confused.
- **Scale**: 960 translation runs (10 formats × 2 arms × 16 documents × 3 repeats), 60 robustness
  chains of 12 sequential edits each, 160 fidelity conversions. 3 993 022 prompt + 11 501 757 output
  tokens billed, ≈ 57 minutes wall clock at concurrency 50. **0 truncated answers in every cell**, so
  no row measures the output budget.
- **No QE pass.** The reference-free MetricX-23-QE scoring needs `unbabel-comet` and its weights, which
  were not available where this run was produced, so no reference-free quality figure is claimed
  anywhere in this document and the bundle carries no `qe_scores.jsonl`. Every quality statement below
  is chrF++/BLEU/TER against the corpus's gold references.

## 2. Token cost — plain form (per 392-entry corpus, tiktoken o200k_base)

| format | doc tokens | per entry | vs CLIFF | prompt (incl. CLIFF spec block) | prompt w/o spec block |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 41 228 | 105.2 | +69.5% | 50 710 | 50 054 |
| **cliff** | **24 322** | **62.0** | — | 81 455 | 34 655 |
| csv | 28 908 | 73.7 | +18.9% | 38 073 | 37 577 |
| fluent | 37 099 | 94.6 | +52.5% | 46 421 | 45 925 |
| ios | 38 794 | 99.0 | +59.5% | 48 164 | 47 620 |
| json-cliff | 26 388 | 67.3 | +8.5% | 35 537 | 35 057 |
| json-plain | 20 647 | 52.7 | **−15.1%** | 30 177 | 29 473 |
| po | 24 218 | 61.8 | −0.4% | 33 303 | 32 887 |
| xliff-2.1 | 29 848 | 76.1 | +22.7% | 39 205 | 38 517 |
| yaml-cliff | 23 492 | 59.9 | −3.4% | 32 641 | 32 161 |

Note on the CLIFF prompt column: the CLIFF specification block is priced as a separate component and
subtracted in the last column — the asymmetry is considered, never hidden. It is a **compressed**
specification: 2 925 tokens per cell, against 16 838 for the full specification text, and it is what
`prompt_style: spec` sends. In plain form a bare key/value JSON file is cheaper than CLIFF by 15 %: that
is the cost of the mandatory type/status fields, i.e. the minimum context CLIFF cannot go below — by
design. The command behind this table is `python -m clarion tokens`.

## 3. Token cost — same context payload carried (context form)

| format | doc tokens | per entry | vs CLIFF | prompt (incl. CLIFF spec) | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| **cliff** | **47 499** | **121.2** | — | 105 576 | 58 776 |
| yaml-cliff | 52 753 | 134.6 | +11.1% | 62 846 | 62 366 |
| json-cliff | 57 696 | 147.2 | +21.5% | 67 789 | 67 309 |
| po | 61 309 | 156.4 | +29.1% | 71 338 | 70 922 |
| json-plain | 61 805 | 157.7 | +30.1% | 72 279 | 71 575 |
| fluent | 74 341 | 189.6 | +56.5% | 84 607 | 84 111 |
| ios | 75 766 | 193.3 | +59.5% | 86 080 | 85 536 |
| android | 77 805 | 198.5 | +63.8% | 88 231 | 87 575 |
| xliff-2.1 | 106 156 | 270.8 | +123.5% | 116 457 | 115 769 |
| csv | 140 693 | 358.9 | +196.2% | 150 802 | 150 306 |

This is the scenario CLIFF exists for. When the same context payload travels in each format's native
channel, **CLIFF's document is the cheapest of the ten** — 11.1 % below yaml-cliff and 196.2 % below
csv. Its *prompt* is not: the prompt column includes the document plus the instructions, and CLIFF's
carries the 2 925-token specification block on every call, which puts it at 105 576 against
yaml-cliff's 62 846 and json-cliff's 67 789, behind only csv (150 802) and xliff-2.1 (116 457).

So the honest reading of this table is **two claims, not one**: the payload CLIFF has to send is the
smallest, and the instructions it has to send are the largest. Which of the two dominates depends on
the pipeline — a specification block is identical on every call and therefore cacheable, while the
context payload is not — and the last column prices the part that is CLIFF-specific, so a reader can
do that arithmetic with their own caching assumptions instead of ours.

## 4. Quality — plain form

| format | chrF++ (all runs) | chrF++ (survivors) | failed runs | BLEU | TER (lower better) | instruction % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| android | **51.8** | 51.8 | 0/48 | 45.3 | 63.3 | 78.5 |
| ios | 51.0 | 51.4 | 1/48 | 44.7 | 63.4 | 78.7 |
| fluent | 50.9 | 50.9 | 0/48 | 44.6 | 63.3 | 79.3 |
| xliff-2.1 | 50.8 | 50.8 | 0/48 | 44.4 | 63.0 | 78.2 |
| yaml-cliff | 50.7 | 50.7 | 0/48 | 44.2 | 61.7 | 78.3 |
| json-cliff | 50.6 | 50.6 | 0/48 | 44.2 | 61.5 | 77.8 |
| po | 50.6 | 50.6 | 0/48 | 44.2 | 62.6 | 78.9 |
| json-plain | 50.4 | 50.4 | 0/48 | 44.1 | 62.1 | 77.9 |
| csv | 46.4 | 51.8 | 5/48 | 42.5 | 43.9 | 76.1 |
| **cliff** | **46.5** | **50.7** | **4/48** | 41.4 | 53.4 | **78.7** |

Read `chrF++ (all runs)` with `chrF++ (survivors)`: the first counts every run once, at the score its
answer earned; the second averages only the runs that produced a usable file. **The gap between them is
the cost of format fragility**, and CLIFF's gap is 4.2 points. CLIFF's instruction-following (78.7 %) is
near the top of the band (76.1–79.3 %), and it is the only format that also answered with a glossary
(28 of 48 answers) — a second document the surface metrics do not credit.

**On the "[all runs]" convention.** A run whose answer did not parse usually earns 0, but not always: an
answer that parses far enough to be scored keeps that partial score, which happens in exactly four cells
(csv context 12.7, ios bare 30.4, ios context 30.8, po context 33.1 — all per failed run). The other
convention — every failure scored as zero — is what `report.audited.md` and the bundle's
`computed/investor-data.md` publish, and it differs in exactly those four cells: csv context 41.8, ios
50.3 bare / 52.5 context, po context 53.5. The generated report called this column
`chrF++ (all, failures=0)`, which the numbers never were; the label is corrected in
`clarion/report.py` and here.

## 5. Quality — same context payload carried (context form)

| format | chrF++ (all runs) | chrF++ (survivors) | failed runs | real translation % | instruction % |
| --- | ---: | ---: | ---: | ---: | ---: |
| yaml-cliff | **55.0** | 55.0 | 0/48 | 100.0 | 87.0 |
| json-cliff | 55.1 | 55.1 | 0/48 | 100.0 | 86.4 |
| po | 54.2 | 54.7 | 1/48 | 100.0 | 83.0 |
| android | 54.0 | 54.0 | 0/48 | 100.0 | 83.4 |
| ios | 53.8 | 54.8 | 2/48 | 99.6 | 82.1 |
| fluent | 53.5 | 53.5 | 0/48 | 100.0 | 82.8 |
| json-plain | 53.4 | 53.4 | 0/48 | 100.0 | 83.0 |
| **cliff** | **49.3** | **53.8** | **4/48** | **91.7** | 81.2 |
| csv | 45.6 | 55.7 | 12/48 | 82.4 | 76.8 |
| xliff-2.1 | 42.2 | 53.3 | 10/48 | 79.2 | 70.6 |

On the segments a format actually delivered (`chrF++ (survivors)`), the ten are within 2.5 points of each
other (53.3–55.7): **a format does not make a model translate better.** What a format changes is
delivery: xliff-2.1 loses 20.8 % of its context-arm runs to malformed output and csv loses 25.0 %, and
those failures are counted as zeros rather than excluded. CLIFF's 91.7 % sits below ios (95.8), po
(97.9) and the five formats at 100.0 %, and above csv and xliff-2.1, which lose 25.0 % and 20.8 % of
their context-arm runs; §11 describes exactly which CLIFF answers fail and why.

## 6. Latency — plain form (ms per run, output tokens billed)

| format | ms/run | output tokens | | format | ms/run | output tokens |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| fluent | 39 347 | 6 035 | | json-cliff | 62 042 | 9 723 |
| android | 49 277 | 6 286 | | ios | 64 725 | 7 949 |
| po | 50 312 | 7 791 | | **cliff** | **78 420** | **12 073** |
| json-plain | 53 266 | 7 770 | | yaml-cliff | 79 645 | 11 948 |
| xliff-2.1 | 57 298 | 8 849 | | csv | 100 184 | 16 281 |

## 7. Latency — context form

| format | ms/run | output tokens | vs CLIFF ms |
| --- | ---: | ---: | ---: |
| json-plain | 63 523 | 10 644 | −43.5% |
| fluent | 69 383 | 10 127 | −38.3% |
| po | 74 500 | 11 149 | −33.8% |
| android | 78 929 | 11 038 | −29.9% |
| ios | 84 751 | 12 199 | −24.7% |
| xliff-2.1 | 95 180 | 15 001 | −15.4% |
| yaml-cliff | 99 282 | 15 725 | −11.8% |
| json-cliff | 102 470 | 14 462 | −8.9% |
| **cliff** | **112 516** | **17 704** | — |
| csv | 161 886 | 26 866 | +43.9% |

**Read the output-token column as the decoder regime, not as the format.** With a reasoning tier
selected the vendor bills thinking tokens as output, and this run selected `reasoning: low`, so every
row carries its own thinking. CLIFF's row is the largest for two measurable reasons: thinking tokens
scale with the answer's length, and CLIFF is the only format in the comparison that may answer with a
**second document** (37 of 48 context-arm answers carried a glossary). A pipeline that wants the
glossary pays for it here; one that does not can ask for the translated file alone.

## 8. Format validity and edit success after LLM edits — all ten formats

Two different questions, two columns:

- **still valid %** — is the file still a valid file of its format after the edit? (checked with each
  format's authoritative parser — CLIFF uses the official validator; the others only need to parse).
- **intent applied %** — did the requested edit actually happen? The protocol applies 12 edit intents
  (set-target, set-context, set-status, set-type, set-emotion, set-max-width, add-reference, add-entry,
  delete-entry, rename-entry, move-entry, set-header-field) sequentially, each edit landing on the
  previous answer. A format survives an edit by ignoring it — so intent applied is the real check.

An edit a format cannot express is excluded from its denominator, so a format is never penalised for
lacking a field, only for breaking when it has one.

| format | arm | applicable edits | still valid % | intent applied % | repairs/edit |
| --- | --- | ---: | ---: | ---: | ---: |
| **cliff** | bare | 21 | **100.0** | **95.2** | 0.00 |
| **cliff** | context | 36 | **86.1** | **86.1** | 0.17 |
| android | bare | 15 | 100.0 | 100.0 | 0.00 |
| android | context | 34 | 100.0 | 82.3 | 0.00 |
| csv | bare | 21 | 100.0 | 100.0 | 0.00 |
| csv | context | 36 | 94.4 | 88.9 | 0.00 |
| fluent | bare | 15 | 100.0 | 100.0 | 0.00 |
| fluent | context | 34 | 97.0 | 69.9 | 0.00 |
| ios | bare | 15 | 100.0 | 100.0 | 0.00 |
| ios | context | 34 | 100.0 | 88.1 | 0.00 |
| json-cliff | bare | 21 | 100.0 | 100.0 | 0.00 |
| json-cliff | context | 36 | 100.0 | 86.1 | 0.00 |
| json-plain | bare | 17 | 100.0 | 100.0 | 0.00 |
| json-plain | context | 36 | 100.0 | 91.7 | 0.00 |
| po | bare | 17 | 100.0 | 100.0 | 0.00 |
| po | context | 36 | 100.0 | 80.6 | 0.00 |
| xliff-2.1 | bare | 21 | **71.4** | 71.4 | 0.00 |
| xliff-2.1 | context | 36 | 77.8 | 69.4 | 0.00 |
| yaml-cliff | bare | 21 | 100.0 | 100.0 | 0.00 |
| yaml-cliff | context | 36 | 100.0 | 86.1 | 0.00 |

Mean validity over the 60 chains: **96.3 %**. The four-state workflow, the closed vocabularies and the
line-local syntax are what this dimension measures, and they are why CLIFF's bare row is 100 % while
XLIFF's is 71.4 %: an XML edit that unbalances a tag corrupts past the edited line, and a CSV edit that
introduces a delimiter shifts every later column.

**Why is CLIFF's intent applied 95.2 % rather than 100 %?** Because CLIFF is the only format whose edits
are validated by a strict grammar, and the failed intents are the ones the model wrote in surface-syntax
error — each a single-line local fix, recorded honestly instead of silently accepted. The other formats
show the same model failing to apply edits at similar or higher rates (fluent context 69.9 %, po 80.6 %,
android 82.3 %); the difference is that their validators do not surface it. **Do not compare the
still-valid column across formats**: the checkers are not of equal strictness, and CLIFF's is the
strictest.

## 9. Structural integrity of the single-pass rewrite

The production shape: one document in, one complete file back. An answer can be a perfectly valid file
and still be the wrong document, which is why these columns sit beside validity.

| format | arm | valid % | ids kept % | coverage % | source kept % | repairs/answer | missing ids |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **cliff** | bare | **91.7** | **91.7** | **91.7** | **91.7** | 0.04 | 126 |
| **cliff** | context | **91.7** | **91.7** | **91.7** | 91.6 | 0.27 | 85 |
| android | bare | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| android | context | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| csv | bare | 89.6 | 89.6 | 89.6 | 89.3 | 0.00 | 98 |
| csv | context | 87.2 | 80.6 | 80.6 | 80.9 | 0.00 | 228 |
| fluent | bare | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| fluent | context | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| ios | bare | 97.9 | 99.8 | 99.8 | 100.0 | 0.00 | 2 |
| ios | context | 95.8 | 99.6 | 99.6 | 100.0 | 0.00 | 4 |
| json-cliff | bare | 100.0 | 100.0 | 100.0 | 99.9 | 0.00 | 0 |
| json-cliff | context | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| json-plain | bare | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| json-plain | context | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| po | bare | 100.0 | 100.0 | 100.0 | 99.9 | 0.00 | 0 |
| po | context | 97.9 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| xliff-2.1 | bare | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| xliff-2.1 | context | **79.2** | 79.2 | 79.2 | 79.2 | 0.00 | 270 |
| yaml-cliff | bare | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |
| yaml-cliff | context | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 |

CLIFF's 91.7 % is checked by the official validator, which is the strictest checker in the comparison —
the other nine only have to parse under theirs — so this column is comparable within a row, not across
formats, and the report prints the same warning. What the row does say is that CLIFF's eight failures
are real ones its own toolchain can see, and that csv and xliff-2.1's context arm scored below it under
those laxer checkers.

**A denominator note, because two published tables disagree on one cell.** This table divides by the
answers that came **back**, the way the generated report does; `report.audited.md` divides by the runs
**attempted**, which is the number a project experiences. They differ in one cell: csv's context arm is
87.2 % of the 47 answers that returned and **75.0 % of the 48 attempted** — one run failed at the
provider and never produced a structure to check, and the audit counts five further answers as failures
that the structure checker's own flag does not. CLIFF's rows are identical either way: all 96 of its
answers returned. Every missing id in the table is one a translation memory keyed on it would miss.

## 10. Round-trip context fidelity

| format | context facts | kept | retention % | most lost fields |
| --- | ---: | ---: | ---: | --- |
| **cliff** | 2 464 | 2 464 | **100.0** | — |
| csv, json-cliff, xliff-2.1, yaml-cliff | 2 464 | 2 464 | 100.0 | — |
| android, fluent, ios, po | 2 464 | 2 414 | 97.6 | header.title, header.info, header.standard (16 each) |
| json-plain | 2 464 | 1 709 | 67.3 | header.title, header.info, header.standard (16 each) |

The canonical CLIFF file is rendered with cliff-python itself and read back tolerantly, so a format that
claims to be lossless must find nothing to repair: repairs per round trip **0.00** for every row. PO
loses the header's title, info and standard because they live in comments and the round trip strips the
ones the model did not copy; plain JSON has nowhere to put them.

## 11. The two readings, on the same answers

CLIFF 1.1 Appendix C defines a tolerant reading, and the shipped configuration selects it. Re-scoring
the run's 96 stored CLIFF answers under both readings, with no model call
(`python tools/compare_readings.py <run-dir>`):

| arm | strict valid | tolerant valid | repairs | salvaged only by tolerance |
| --- | ---: | ---: | ---: | --- |
| bare | 87.5 % (42/48) | **91.7 % (44/48)** | 2 | 2 answers |
| context | 85.4 % (41/48) | **91.7 % (44/48)** | 13 | 3 answers |

Every repair was a **shape** repair: an identifier containing a reserved character (C.2.5 — 2 answers
bare, 12 context) and one repeated field (C.2.2). None was salvaged by inventing content, which is what
Appendix C.5 forbids.

**The eight answers that fail under both readings** (4 per arm) are all parse errors, and the reader's
own message says what they are:

| reader's rejection | answers | where |
| --- | ---: | --- |
| `expected 'key: value' or 'key = value' field` | 4 | godot-l10n bare, wmt24pp bare, lit-modern context, legal-terms context |
| `unknown group key 'status'; known keys: context, emotion, max-width, type` | 1 | ui-workbench context |
| `expected a quoted string` | 2 | sanguo-brewitt-taylor bare ×2 |
| `unterminated string` | 1 | sanguo-brewitt-taylor context |

Two things are worth reading off this table. The `status` case is the one Appendix C.5 forbids a parser
from repairing — a field written into the wrong scope — and it is the failure mode the CLIFF-specific
part of the prompt was written for; it survives at one answer in 96. And three of the eight are the same
document (`sanguo-brewitt-taylor`, classical Chinese whose values mix CJK curly quotes, which take no
backslash, with ASCII ones, which do), so the residual is **file-clustered rather than spread**: the
eight failures sit in six documents, and the other ten were clean in all six of their cells.

## 12. Why this matters

**Three audiences, one format.** Games are the worst-case market for the incumbent formats and the
sharpest test of CLIFF; web apps and general products are the everyday case. The format addresses both
with the same design:

- **Engine reality**: Godot ships CSV + gettext PO; Unreal ships PO + CSV (.locres runtime); Unity ships
  XLIFF + CSV — **three engines, three toolchains, no common interchange**. CLIFF converts
  bidirectionally to XLIFF/PO/Fluent/JSON/YAML/CSV/Android/iOS with the bundled zero-dependency
  converter, so it works as the interchange between all of them.
- **PO loss in practice**: 97.6 % context retention — the header title/info/standard vanish on
  round-trip (metadata lives in comments; several tools strip comments). For a game this means the
  family context (world, characters, style rules) is silently dropped between engine and translators.
- **CSV cost in practice**: the same payload costs 196 % more tokens (358.9 vs 121.2 per entry) and
  25.0 % of its context-arm runs come back malformed — a game UI with 3 000 strings pays that on every
  release cycle.
- **XLIFF in practice**: +123.5 % tokens in the context arm, and paired-tag XML is the worst shape for
  autoregressive editing: its bare-arm edit validity is 71.4 %, the lowest in the comparison.
- **What games need and no incumbent has**: closed-vocabulary content type (dialogue, monologue,
  narration, subtitle, accessibility-cue), emotion/register tags (23), display-width budgets per
  UAX #11 (UI overflow pre-check — critical for CJK localization), and the XLIFF-compatible four-state
  workflow (initial → translated → reviewed → final) so asset state is verifiable in-engine.

**The honest framing** (what the data supports and what it does not):

- Supported: CLIFF carries a full context payload in fewer document tokens than every other format in
  the comparison (47 499 against 52 753–140 693); the payload survives a round trip at 100 %; after
  repeated edits it holds at 100 % bare and 86.1 % context against xliff-2.1's 71.4 % and 77.8 %, and it
  is never the worst row; the four-state workflow and the closed vocabularies are engine-grade data; and
  it is the only format in the comparison that answered with a terminology glossary at all.
- Supported with a caveat: its single-pass validity is 91.7 % under the strictest checker in the
  comparison — the other nine are only checked for parse validity, so no row-for-row ranking is claimed
  — and that is the price of a format whose structure is positional. Its prompt is also the most
  expensive in the plain arm and the third most expensive in the context arm, because it is the only
  format that has to explain itself (2 925 tokens per call, identical every time and therefore cacheable
  in a way a context payload is not).
- Not supported: no format changes how well a model translates the same segment (the delivered-segment
  chrF++ band is 53.3–55.7 across all ten). CLIFF's advantage comes from the context payload being
  **structurally guaranteed** (mandatory type, inheritable group metadata) — the others must be
  hand-injected, and in shipped files usually are not.
- Not claimed: anything about reference-free quality. There is no QE pass in this bundle (§1).

## 13. Limits to state honestly

- **One model, one endpoint, one date** (`deepseek-flash`, 2026-09-21); re-measure per model family
  before citing. Temperature is recorded as 1.3 but is **nominal under a reasoning tier**: with
  `reasoning: low` the vendor controls sampling, so the decoder regime, not the temperature, is the
  variable this run fixed.
- **Target language dominant zh-CN** plus a small zh-to-en classical subset; re-measure at least one
  non-CJK pair.
- **The annotator is the model under test** for the `annotated` context origins, which flatters the
  context arm. Every format sees the same brief, so the format-to-format comparison stands; a claim
  that CLIFF's context arm would gain as much against a human-written brief does not.
- **CLIFF's validity is the tolerant reading** the configuration declares, and the strict column is in
  §11. The other nine formats have one reading each.
- **Edit-robustness rows are not cross-format comparable** (checker strictness differs); the CLIFF rows
  are the strictest-checker numbers. Latency is comparable only inside one run.

## 14. Reproduce everything

```
# run (costs API tokens): 960 translations + 60 edit chains + 160 fidelity conversions
python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch
# audit + unified computed metrics + review sheet
node tools/audit_report.mjs results/<run-dir>
# the two readings on the same answers
python tools/compare_readings.py results/<run-dir>
# token cost, no model calls
python -m clarion tokens
# package the public bundle
python tools/package_benchmark.py results/<run-dir>
# optional: the reference-free QE column (needs unbabel-comet), then re-run the audit
python tools/qe_score.py results/<run-dir>
```

Raw evidence: [`benchmark/clarion-2026-09-21/raw/`](benchmark/clarion-2026-09-21/raw) · Computed review
data: [`benchmark/clarion-2026-09-21/computed/`](benchmark/clarion-2026-09-21/computed) · Methodology:
[docs/clarion-methodology.md](docs/clarion-methodology.md) · Acceptance criteria:
[docs/acceptance-criteria.md](docs/acceptance-criteria.md).
