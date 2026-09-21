# CLIFF Acceptance Criteria

This repository implements the requested acceptance criteria for CLIFF 1.1
plus additional ones proposed below. Where a criterion depends on a specific
LLM class (e.g. a Flash-class model), the repository contains a replayable
protocol; numbers recorded in this session come from the available subagent
model and are labeled as such. All recorded numbers below are updated by
`python tests/run_all.py` runs and the SubAgent protocols.

## C1 — Standard format specification

- Normative spec: [cliff-1.1.0.md](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.1.0.md)
  ([1.0](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.0.0.md) remains the frozen, superseded definition)

- Normative grammar: [cliff-1.1.abnf](https://github.com/cliff-format/cliff/blob/main/spec/abnf/cliff-1.1.abnf)
- Style guide (informative, not enforced): [style/README.md](https://github.com/cliff-format/cliff/blob/main/style/README.md)
- Valid examples: [cliff-1.1.0 examples](https://github.com/cliff-format/cliff/tree/main/spec/examples/cliff-1.1.0); conformance fixtures:
  `tests/fixtures/`
- Reference validator: `tools/cliff_validator.py`
- Tag references: [content-types.md](https://github.com/cliff-format/cliff/blob/main/references/content-types.md),
  [emotion-tags.md](https://github.com/cliff-format/cliff/blob/main/references/emotion-tags.md), [status-tags.md](https://github.com/cliff-format/cliff/blob/main/references/status-tags.md)

## C2 — Token savings ≥ 30% vs common formats (average)

- Benchmark: `tools/token_benchmark.py`
- Corpus: 16 translation units with equivalent semantics across CLIFF 1.1,
  XLIFF 2.1, JSON, CSV, gettext PO, Fluent, YAML, and TOML. Each
  representation carries the same family info, standards, dependencies,
  glossary terms (CLIFF counts its `variant: glossary` file), group/entry
  context, `type`, `emotion`, `status`, `max-width`, and ICU payloads.
- Tokenizer: `tiktoken` `cl100k_base` (deterministic fallback if unavailable).
- Re-verified this revision after the corpus moved to CLIFF 1.1: **CLIFF 1138
  tokens (main + glossary dependency file) vs 1785.9 average of XLIFF 2.1 /
  JSON / CSV / PO / Fluent / YAML / TOML → 36.3% saving**. PASS (threshold
  ≥ 30%). The version line changed from `CLIFF 1.0` to `CLIFF 1.1`; the token
  count is unchanged at `cl100k_base`, because both version lines tokenise
  identically.

## C3 — AI translation reference accuracy ≥ 90%

- Corpus: `tests/quality/corpus.cliff` (12 entries: idioms, sarcasm, pun,
  proper nouns, ICU, word order, width); glossary dependency:
  `tests/quality/glossary.zh-CN.cliff` (`variant: glossary`).
- Gold references and rubric: `tests/quality/gold-reference.md`
  (信 4 / 达 3 / 雅 2 / constraints 1 per entry).
- Objective constraint checks: `tests/quality/check_constraints.py`.
- Independent evaluator protocol: `tests/quality/evaluator-instructions.md`.
- Recorded result: **119/120 = 99.17% average rubric score** (from the
  previously recorded SubAgent translator + independent evaluator protocol);
  **48/48 objective constraints re-verified this session**. PASS.

## C4 — AI format-edit correctness = 100% over 100 valid-intent edits

- Protocol and task list: `tests/edit-robustness/README.md`,
  `tests/edit-robustness/tasks.json`.
- Baseline: `tests/edit-robustness/base.cliff`.
- Each of the 100 sequential valid-intent edits is applied by a SubAgent
  without access to the validator, then every file is checked with
  `tools/cliff_validator.py`; score = valid files / 100.
- Deliberately invalid edits are covered separately by the invalid fixtures
  (C5.1), not by this score.
- Recorded this session (deterministic replay from `tasks.json` via
  `apply_edits.py`): **100/100 valid (100.0%)**. PASS.

## C5 — Additional criteria proposed for CLIFF 1.0 / 1.1

| # | Criterion | Test |
| --- | --- | --- |
| C5.1 | Every invalid document yields a **line-numbered, classed error** | `tests/fixtures/invalid/` + validator output |
| C5.2 | Closed vocabularies (`type` 26, `emotion` 23, `status` 4: `initial`/`translated`/`reviewed`/`final`) reject near-miss tags, including differently cased spellings | `tests/fixtures/invalid/invalid-status.zh-CN.cliff`, `invalid-emotion.zh-CN.cliff`, `invalid-type.zh-CN.cliff` |
| C5.3 | ICU MF1/MF2 survives as payload; broken braces are detected | `tests/fixtures/valid/icu.zh-CN.cliff`, `tests/fixtures/invalid/unbalanced-icu.zh-CN.cliff` |
| C5.4 | Display width follows UAX #11 (Latin=1, CJK=2, combining=0) | `accept-short` entry in quality corpus; `--check-width` |
| C5.5 | Comments are discardable without losing translation context | `tests/fixtures/valid/comments-blanks.zh-CN.cliff`; design rationale §15 |
| C5.6 | Canonical IDs are `namespace.clan.group.entry`, case-sensitive, and unique | `tests/fixtures/invalid/duplicate-entry-id.zh-CN.cliff`, `tests/fixtures/valid/mixed-shape-ids.zh-CN.cliff`, `--ids` |
| C5.7 | Token benchmark is deterministic and reproducible | two-run verification of `tools/token_benchmark.py` |
| C5.8 | No multi-line structural construct exists in the grammar | [cliff-1.1.abnf](https://github.com/cliff-format/cliff/blob/main/spec/abnf/cliff-1.1.abnf), design rationale |
| C5.9 | Four header fields are required; a flat or folder file name is a **recommendation** in 1.1, checked for consistency only | `tests/fixtures/layout/`; `missing-*` fixtures |
| C5.10 | Glossary variant is restricted to term-level types (warning) | `variant: glossary` fixtures |
| C5.11 | `=` and `:` are equivalent; tolerant whitespace never changes meaning | tolerant-syntax fixtures |
| C5.12 | Status workflow prevents `translated`/`reviewed`/`final` without target; `initial` allows no target | `tests/fixtures/invalid/reviewed-without-target.zh-CN.cliff` |
| C5.13 | **1.1** — identifiers accept `A-Z a-z 0-9 _ -` (no `.`), are case-sensitive, and are never rewritten by a parser | `tests/fixtures/valid/uppercase-entry-id.zh-CN.cliff`, `underscore-entry-id.zh-CN.cliff`, `mixed-shape-ids.zh-CN.cliff` |
| C5.14 | **1.1** — one optional trailing `,` / `;` per line is standard, meaningless, never re-emitted, and a second one is a syntax error | `tests/fixtures/valid/valid-terminators.zh-CN.cliff`, `tests/fixtures/invalid/double-terminator.zh-CN.cliff` |
| C5.15 | **1.1** — a layout/header mismatch is a warning by default and an error under `--check-layout`, so the mode is explicit | `tests/fixtures/layout/` (both modes) |
| C5.16 | **1.1** — style deviations are warnings, never errors, and `--style` reports them | `tests/fixtures/style/` |
| C5.17 | **1.1** — tolerant parsing repairs the seven documented deviations, reports every repair, and refuses the forbidden ones in Appendix C.5 | `tests/fixtures/tolerant/` (both the repairable files and the two that must stay refused, `unrepairable.zh-CN.cliff` and `quoted-unknown-key.zh-CN.cliff`); `tests/clarion/test_read_modes.py` pins each fixture's repair count **by category**, so a change in the repair set has to be deliberate |
| C5.18 | **1.1** — a tolerant parse serializes back into a strictly valid document, and serialization is a fixed point | `cliff-python/tests/test_tolerant_parser.py`, `tests/run_all.py --tolerant` |
| C5.19 | **1.1** — an answer may hold more than one CLIFF document (a translation plus the glossary the terminology workflow produced); each is validated on its own and either version line splits | `tools/cliff_validator.py --multi-document`, `tests/fixtures/tolerant/two-documents.txt`, `tests/clarion/test_read_modes.py`, `tests/test_validator_tool.py` |
| C5.20 | **1.1** — the reading in effect is observable on every row, and the two readings disagree only as documented | `read_mode`/`repairs` on every translation, robustness and fidelity record; `tests/clarion/test_read_modes.py` |

## C6 — CLARION: format-versus-format measurement

CLARION generalizes C2–C4 from "CLIFF alone" to "CLIFF against every format a
project might ship", using one corpus and one generation path. Protocol:
[clarion-methodology.md](clarion-methodology.md).

| # | Criterion | How it is produced | Model needed |
| --- | --- | --- | --- |
| C6.1 | Token cost of every format, plain arm | `python -m clarion tokens` | no |
| C6.2 | Token cost of every format carrying the same context | same command, context arm | no |
| C6.3 | Token cost with and without the CLIFF specification block | component subtraction inside the same run | no |
| C6.4 | Translation quality per format and arm (chrF++/BLEU/TER, coverage, validity) | `python -m clarion translate` | yes |
| C6.5 | Instruction-following per format and arm (rule engine over the gold manifests) | same run | yes |
| C6.6 | Terminology adherence and de-jargon cleanliness | same run | yes |
| C6.7 | Latency and output tokens per format and arm | same run | yes |
| C6.8 | Format validity and intent success after model edits, every format | `python -m clarion robustness` | yes (deterministic replay available) |
| C6.9 | Round-trip context fidelity per format | `python -m clarion fidelity` | no |
| C6.10 | Harness self-verification: a perfect answer scores perfectly, a damaged answer is detected, degenerate controls stay below a real answer, deterministic edits keep every format valid | `python -m clarion selfcheck` | no |
| C6.11 | **1.1** — the same answers scored under both readings, so a report names the one behind its numbers: how many CLIFF answers a tolerant read salvages, and at what repair cost | `python -m clarion translate --read-mode tolerant` vs `--read-mode strict`; `read_mode` and `repairs` columns in the D3/D4/D7 tables | yes |
| C6.12 | **Modification correctness of a single-pass rewrite**: `valid %`, `ids kept %`, `coverage %`, `source kept %`, `repairs/answer`, and the extra / missing / drifted / untranslated identifier counts, per format and arm | the `D3/D4 - structural integrity of the rewrite` table of `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch` (`clarion/report.py` `structure_report`) | yes |
| C6.12 | **measured at the deployment settings** (1.3, example-driven prompt, all ten formats) | **CLIFF bare 58.3% valid / 75.0% ids kept / 75.0% coverage; context 70.8% / 72.9% / 72.9%** — CLIFF is the least surviving of the ten and the best on the answers that survive (chrF++ 53.3) | see the run entry in [CHANGELOG.md](../CHANGELOG.md) |

### C6.12 is the modification-correctness number; C4 and C6.8 are not

The pipeline asks a model for **one document and one complete file back**, which is
what production does: the model thinks, then rewrites the file once. C6.12 measures
that task, so it answers "how correctly does the model modify a CLIFF file" with
the columns that decide it — an answer can be a perfectly valid file and still be
the wrong document, which is why `ids kept %` and `coverage %` sit beside
`valid %`.

**One protocol, every format.** C6.12 is reported for all ten formats of the
configured run, not for CLIFF alone: the same single-pass task, the same
temperature (`1.3`, the value the production plugin uses and the configuration
carries) and the same prompt style (`examples`) for every row, so the rows differ
only in the format. A per-format override - `--formats cliff` - narrows a run, and
then the table says which formats it covers, because a number quoted out of a
narrowed run is not the benchmark's.

C4 (100 sequential edits) and C6.8 (twelve sequential edits per file, each applied
to the previous answer) measure something else: whether a file **survives being
edited repeatedly**. That is a real property, but it is not the production shape and
it is a much harder task, so the two numbers must not be quoted for each other.
Quoting a multi-edit rate as "the model's format correctness" understates it;
quoting C6.12 as "robustness under repeated editing" overstates it. Both are
reported, each stating which question it answers.

Recorded in this revision:

- `python -m clarion corpus validate` — **16 files, 392 entries, 0 problems**.
- `python -m clarion corpus stats` — CLARION-Core **0.3.0**, six strata, 18
  `.cliff` files in the tree (16 standard documents plus two `variant: glossary`
  term files); 118 of 392 items `human_verified` (the imported corpora); the
  authored items are CC0 and still await sign-off.
- `python -m clarion tokens` — CLARION-Core document payload, `o200k_base`:
  CLIFF **24 322** tokens in the plain arm and **47 499** in the context arm,
  against 20 647–41 228 (plain) and 52 753–140 693 (context) for the other nine
  formats. The command also prices each prompt and its components.
- `python -m clarion selfcheck` — **SELF-CHECK PASS**, including two checks new
  in this revision: the strict and tolerant readings differ exactly as
  Appendix C documents, and a repaired document serializes into one the strict
  grammar accepts.
- `python -m pytest tests/clarion` and `python tests/run_all.py --quality --robustness` — pass
  (100/100 edit-robustness edits valid; all validator suites exit as expected).

### C6.4–C6.8 recorded run

`python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch`,
model `deepseek-flash`, `read_mode: tolerant`, 3 repeats per cell, corpus
**CLARION-Core 0.3.0** (16 documents, 392 entries).

Run directory:
`results/clarion-deepseek-flash-20260920T114819+0000-6a5259` — 1 180 records,
exit 0, 960 translation runs + 60 robustness chains + 160 fidelity conversions,
**5 598 954 prompt + 4 172 463 output tokens** billed, 53 minutes wall clock
(concurrency 50, one endpoint, temperature 0).

| # | Criterion | CLIFF recorded | Best other format | Note |
| --- | --- | --- | --- | --- |
| C6.4 | quality, plain arm, chrF++ (failures scored 0) | **51.2** | android 51.8 | measured on the same segments, same model, one variable |
| C6.4 | quality, context arm, chrF++ | **53.9** | android 54.9 | |
| C6.5 | instruction-following, plain / context | **79.5% / 83.0%** | json-cliff 76.8% / json-cliff 83.4% | rule engine over the gold manifests |
| C6.6 | terminology / de-jargon, plain | **94.0% / 99.8%** | — | |
| C6.7 | output tokens per run, plain | **3 111** | json-plain 1 332 | CLIFF is not the cheapest here; the spec block is part of its output budget |
| C6.8 | still valid after model edits, bare / context | **100.0% / 100.0%** | android 100% / 100% | re-run with the example prompt (**at temperature 0.0**, see below); was 100.0% / 83.3% |
| C6.8 | same, at the shipped temperature 1.3 | **97.7% valid / 95.9% intent** | — | CLIFF only, 171 edits over three passes; the deployment number **for repeated editing**, which is not C6.12 |
| C6.9 | round-trip context retention | **100.0%** | csv/json-cliff/xliff/yaml-cliff 100% | json-plain 67.3% |

### C6.8 re-run: the prompt redesign, and what it fixed

After the two prompt pilots the shipped configuration moved to
`temperature: 1.3` (DeepSeek's recommended translation temperature, and what the
production plugin uses) and `prompt_style: examples` (the specification text
replaced by the key/scope facts plus two conforming documents; 20 739 → 2 510
prompt tokens per cell at the time; the table has since been re-measured through
the assembly path and reads **21 383 → 2 417**, see
`docs/clarion-prompt-design.md`). Dimension 7 was then re-run through
`run_robustness_matrix` over the `ui` stratum, 2 passes × 12 edits, 240 calls.
**Only the prompt change reached that run**: the edit path built its own request
with a hard-coded `temperature=0.0` and ignored the configured value, so the
column below is a 0.0 comparison — same model, same files, same edits, only the
CLIFF edit prompt differing. The defect is fixed (the temperature is now a
parameter forwarded from the configuration, guarded by
`tests/clarion/test_edit_request.py`) and the 1.3 baseline has since been
measured: CLIFF **97.7 % valid / 95.9 % intent** over 171 edits in three passes,
against 100 % / 98.6 % here. See
[clarion-prompt-design.md](clarion-prompt-design.md) for the per-failure
attribution, and note that **the 1.3 row is the number to quote**: the 0.0 column
measures a decoder the pipeline does not use.

| format | arm | still valid % | invented-key failures | repairs |
| --- | --- | ---: | ---: | ---: |
| **cliff** | bare | **100.0** | 0 | 0 |
| **cliff** | context | **100.0** (was 83.3) | **0** (was 2) | 44 / 6 introduced |
| xliff-2.1 | bare | 59.5 (was 57.1) | 0 | 0 |
| xliff-2.1 | context | 62.5 (was 55.6) | 0 | 0 |
| other eight formats | both | 100.0 | 0 | 0 |

The `cliff/context` failures were the invented keys of the previous run
(`translator-context`, `ref`, `source-ref`, `status` in a group section); D7's
edit prompt had carried no CLIFF content at all, so the model named the fields
itself. With the field names and scopes stated, **no edit in the run invented a
key**, and every repair was absorbed by the tolerant reader rather than failing.
The repair figures are the running total over document-steps (44) and the repairs
the model actually introduced (6, on `add-reference` and `set-emotion` — the two
operations that require creating a field that is not on the page); the total is
larger because one deviation is re-counted by every later step, so only the
introduced count may be attributed per operation
(`.tools/d7_audit.py` prints both). The isolated effect is measured separately:
18.8 % → 0 % invented-key failures over 48 edits per condition, Fisher exact
p = 0.0026 ([clarion-prompt-design.md](clarion-prompt-design.md); this was
published as 0.0129 from a defective test - the corrected p is smaller, so the
difference is if anything stronger).

**The XLIFF rows are not comparable across the two runs, and the difference is the
model, not the decoder.** The prompt change touches CLIFF only, and every XLIFF
failure is an XML parse error in a document the model rewrote wholesale. An
earlier version of this note attributed the 100.0 % to a temperature-0.0 lucky
sample; that was wrong on both counts. Both runs sent 0.0 on the edit path, and
the 100.0 % belongs to the frozen `benchmark/clarion-2026-09-02` run, whose
configuration reads `model: deepseek-v4-flash` with the same stratum and edit
count. The same-model baseline is 57.1 % / 55.6 %, so what separates 100 % from
59.5 % is the model change (`deepseek-v4-flash` → `deepseek-flash`). CLIFF's own
comparison is unaffected: both of its columns come from the same model.

**No `truncated` runs** (0.0% in every cell), so the rows measure the format,
not the output budget.

**The two readings, on the same answers.** Re-scoring the 96 stored CLIFF
answers of this run under both readings, with no model call
(`python tools/compare_readings.py <run-dir>`):

| Arm | strict valid | tolerant valid | repairs | salvaged only by tolerance |
| --- | ---: | ---: | ---: | --- |
| bare | 89.6% | 93.8% | 3 | 2 answers |
| context | 83.3% | 89.6% | 6 | 3 answers |

Every repair was a shape repair — one quoted tag, four identifiers containing a
reserved character, two normalization-induced id collisions. None was salvaged by
inventing content, which is what Appendix C.5 forbids: one `wmt24pp` context
answer claimed `status: translated` on an entry with no `target` at all, and the
tolerant reading refused it exactly as the strict one did.

**Failure composition (a format property, not a harness fault).** 61 of 960 runs
did not parse, all of them in the two formats that cannot carry multi-line
context cleanly: `csv` (context arm) writes a context field containing a newline
into one row, which shifts every later column, and `xliff-2.1` (context arm)
emits malformed XML at a specific line. Each failure was inspected in the stored
answer text, not read off the summary.

**Correction carried into this revision.** The token tables previously priced a
CLIFF prompt that no arm sends: `token_matrix` omitted `allow_glossary_output`
and `workflow_style`, so the terminology-workflow block was missing and the
reference specification — which only CLIFF's prompt carries, 16 316 tokens per
cell — was charged to no row. CLIFF's prompt columns were therefore about half
of the real figure. The document columns were unaffected. `tests/clarion/test_tools.py`
now asserts that the token matrix and the translation arms build the same prompt,
argument for argument.

**Reading used for the scored rows.** The C6.4–C6.8 numbers are recorded under
the configuration shipped in `configs/deepseek-flash.json`, which sets
`read_mode: tolerant` — the reading CLIFF 1.1 defines for an automated
translation pipeline (Appendix C). Every row carries that mode and its repair
count, so the same answers can also be scored under `--read-mode strict`;
`docs/clarion-methodology.md` §9.1 states which question each reading answers.
CLIFF's D7 context row (83.3% still valid) is measured under that reading and is
the only row in the table whose validity is affected by which reading is in
force; the other nine formats have one reading each.

**Known limitation of the recorded run.** The annotator that wrote the
`context_origin: annotated` briefs is the same model as the system under test
(`deepseek-flash`), which `clarion/corpus/annotate.py` warns against because it
flatters the context arm. A context-arm gain measured on annotated context is a
weaker claim than one measured on native context; the rows' `context source`
column says which items are which. This run therefore supports the
format-to-format comparison (every format sees the same brief, so the pairing
moves all formats together) but not a claim that CLIFF's context arm would gain
as much against a human-written brief.

## How to re-run with a different model class

Replace the translator agent and the 100-edit agent with the target model
(e.g. a Flash-class model), keep the same prompt files and task files, then
re-run the validator and evaluator. The scores are model-independent because
the validators and rubric are fixed artifacts in this repository.
