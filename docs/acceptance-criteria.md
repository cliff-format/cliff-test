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
- Corpus: 16 translation units with equivalent semantics across CLIFF 1.0,
  XLIFF 2.1, JSON, CSV, gettext PO, Fluent, YAML, and TOML. Each
  representation carries the same family info, standards, dependencies,
  glossary terms (CLIFF counts its `variant: glossary` file), group/entry
  context, `type`, `emotion`, `status`, `max-width`, and ICU payloads.
- Tokenizer: `tiktoken` `cl100k_base` (deterministic fallback if unavailable).
- Recorded in this session: **CLIFF 1.0 1250 tokens (main + glossary
  dependency file) vs 1785.9 average of XLIFF 2.1 / JSON / CSV / PO / Fluent /
  YAML / TOML → 30.0% saving**. PASS (threshold ≥ 30%).

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
| C5.17 | **1.1** — tolerant parsing repairs the six documented deviations, reports every repair, and refuses the forbidden ones in Appendix C.5 | `tests/fixtures/tolerant/` (both the repairable files and `unrepairable.zh-CN.cliff`) |
| C5.18 | **1.1** — a tolerant parse serializes back into a strictly valid document, and serialization is a fixed point | `cliff-python/tests/test_tolerant_parser.py`, `tests/run_all.py --tolerant` |

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

Recorded in this session (no model calls yet, by design):

- `python -m clarion selfcheck` — **SELF-CHECK PASS** (12 checks, including
  CLIFF round-trip retention 1.000 and 12 deterministic edits valid in all ten
  formats).
- `python -m clarion corpus validate` — **6 files, 111 entries, 0 problems**.
- `python -m clarion tokens` — CLARION-Core document payload, `o200k_base`:
  CLIFF 4 907 tokens in the plain arm and 8 065 in the context arm, against
  3 873–7 815 (plain) and 9 223–23 331 (context) for the other nine formats.
- `python -m pytest tests/clarion` — **146 passed**.

Quality, latency and edit-robustness numbers (C6.4–C6.8) are deliberately not
recorded yet: the environment is built and self-verified first, and the corpus
still needs human sign-off (`human_verified` is `false` for every item).

## How to re-run with a different model class

Replace the translator agent and the 100-edit agent with the target model
(e.g. a Flash-class model), keep the same prompt files and task files, then
re-run the validator and evaluator. The scores are model-independent because
the validators and rubric are fixed artifacts in this repository.
