# cliff-test Changelog

cliff-test is versioned with CLIFF 1.1.0. See the Git history for the complete record of changes.

## 1.1.0 — 2026

The suite follows CLIFF 1.1, which is a pure relaxation of 1.0: every 1.0
fixture still passes, and the checks below answer the 1.1 questions.

### Changed

- **`tools/cliff_validator.py` follows the relaxed `name` production**
  (`A-Z a-z 0-9 _ -`, never `.`) and keeps tags narrow via a separate
  `TAG_NAME_RE`. A near-miss tag is reported as a `vocabulary` error listing the
  allowed values, and a quoted tag is a shape error in strict mode.
- **Strict mode is strict again.** The validator previously accepted a bare
  scalar in a list-typed field (`emotion: neutral`) and a quoted tag. Both are
  errors under specification 6.1; the relaxations exist only in `--tolerant`.
- **Layout mismatches are warnings by default** (`layout` category), because
  1.1 recommends a layout rather than requiring it. `--check-layout` reports
  them as errors for a project that enforces the convention.
- Tolerant reading of the version line accepts `CLIFF 1.0` and `CLIFF 1.1`; an
  unimplemented version is rejected with the supported versions named.
- **CLARION reads model answers in the tolerant mode CLIFF 1.1 defines for a
  translation pipeline** (specification Appendix C), and can be switched to the
  strict, reference-toolchain reading with `read_mode` / `--read-mode`. Every
  translation, robustness and fidelity row records the mode and the number of
  repairs it took, and the D3/D4/D7 tables carry both, so a row can always state
  which question its number answers. Until this change the Appendix C path was
  unreachable from CLARION: `check_validity` and `parse_back` were always called
  in strict mode, so an answer a model punctuated the way models punctuate was
  scored as a format failure.
- **The CLARION-Core corpus declares CLIFF 1.1.** All 18 documents moved from
  `CLIFF 1.0` to `CLIFF 1.1`, and the manifest version moved to `0.3.0` to match
  the version the benchmark documents and the dataset card already carried. The
  documents' content is unchanged, field for field: a version-line move is not a
  rewrite, and the corpus is deliberately *not* in canonical serialized form
  (field order, adjacent-string continuation lines and the licence comment blocks
  are author choices that a serializer would normalise away). `tools/corpus_version.py`
  is the guard: it changes the version line and nothing else, and proves it with
  a semantic fingerprint of every field plus the gold manifests' provenance
  digests.
- 1.0-era labels replaced where they named the current specification: the format
  registry label, the token benchmark's emitters, result keys and report titles,
  the edit-robustness and quality prompts and their reports, and the corpus
  authoring specification.
- **Token-cost prompt columns corrected.** `token_matrix` built its prompt
  without `allow_glossary_output` and `workflow_style`, and never accounted for
  the reference specification that only the CLIFF prompt carries (16 316 tokens
  per cell). CLIFF's D1/D2 prompt totals were therefore roughly half of what the
  translation arms actually send; the other nine formats were correct, and the
  document-token columns were never affected.

### Added

- **`--check-layout`**, **`--style`**, and **`--tolerant`** modes, each with its
  own fixture suite: `tests/fixtures/layout/`, `style/`, `tolerant/`.
- **Optional line terminator** support (`CLIFF 1.1` §5.6) in the strict parser,
  with `tests/fixtures/valid/valid-terminators.zh-CN.cliff` and
  `tests/fixtures/invalid/double-terminator.zh-CN.cliff`.
- **`tests/run_all.py`** now states the mode and the expected exit code of
  every suite, checks both spec example directories, and warns when the
  tolerant refusal set (Appendix C.5) is empty.
- `--tolerant` delegates to `cliff_format`, so the tolerant contract has exactly
  one implementation in the ecosystem.
- **`--read-mode {strict,tolerant}`** on the CLARION commands, plus the
  `read_mode` run-configuration key.
- **`read_mode` and `repairs`** on every translation row, robustness outcome and
  fidelity record; `repairs/run`, `repairs/edit` and a `read mode` column in the
  report tables.
- **`--multi-document`** on the validator: an answer may hold a translated file
  *plus* the glossary the terminology workflow produced, and each document is
  validated on its own (concatenating two valid documents is not one valid
  document). Fixture: `tests/fixtures/tolerant/two-documents.txt`.
- **Three tolerant fixtures** pinning the repair set by category, including one
  whose every line ends with `,` / `;` to assert that a line terminator is
  syntax and not a repair: `terminators-and-quoted-tags.zh-CN.cliff`,
  `quoted-id-and-bare-list.zh-CN.cliff`, `two-documents.txt`.
- **`tools/corpus_version.py`**: the corpus version-line guard and migration,
  with a semantic fingerprint that makes "only the version line changed" a
  checkable claim.
- **Tests**: `tests/clarion/test_read_modes.py` (the two readings, per-category
  repair counts, Appendix C.5 refusals, document splitting, comment lines that
  mention a version), `tests/clarion/test_corpus_1_1.py` (the corpus's declared
  version, strict validity, zero repairs, provenance digests, gold agreement),
  `tests/test_validator_tool.py` (the validation modes, including the
  multi-document contract), and a prompt-parity test in
  `tests/clarion/test_tools.py`.
- Appendix C.4 behaviour decided and documented: a collision is rejected, not
  renamed, because §10.2 makes a duplicate canonical ID a validity error in both
  readings.
- `docs/clarion-methodology.md` §9.1 states what each reading answers, which
  repairs exist, what a terminator is not, and which C.5 refusals hold.

### Fixed

- **`split_cliff_documents` only recognised `CLIFF 1.0`.** An answer holding a
  1.1 translation plus a glossary was handed to a single-document parser as one
  blob, which failed and was scored as a parse error against the format. The
  splitter now matches either version line and requires the line to hold nothing
  but the version, so a licence comment that mentions "CLIFF 1.1" in prose is
  never mistaken for a document start.
- **Every tolerant repair was reported twice.** `_check_cliff` appended one
  `correction` warning per repair on top of the ones `validate_document` already
  emits, which would have inflated the repair column of any report.
- **`corpus_version.py`'s guard replaced a wrong assumption.** The first plan for
  the 1.1 migration used `serialize(parse(text)) == text` as the safety gate; all
  18 files fail it, because the corpus intentionally keeps author field order,
  continuation lines and comment blocks. The guard now checks a semantic
  fingerprint plus a strict line-level diff instead, which is the property that
  actually matters and which the old gate would have "fixed" by destroying
  readability and attribution.
- The corpus authoring specification described the stratum glossary as
  `glossary.<lang>.cliff` and as loaded by file name; the loader keys on the
  `variant: glossary` header, and the real files are named after the clan they
  serve (`ui-console-terms.zh-CN.cliff`), as the specification recommends. The
  document now matches the implementation.
- Stale corpus figures in the README, the acceptance criteria and the
  methodology (6 files / 111 entries from version 0.1.0) replaced with the
  measured 16 files / 392 entries of 0.3.0, and the published
  `results/clarion-core-tokens.md` regenerated.

### Moved

- `tests/fixtures/invalid/uppercase-entry-id.zh-CN.cliff` and
  `underscore-entry-id.zh-CN.cliff` → `tests/fixtures/valid/`: 1.1 accepts both.
- `tests/fixtures/invalid/filename-mismatch.zh-CN.cliff` and the three
  `invalid/ja-JP/` fixtures → `tests/fixtures/layout/`: their finding is a
  warning in 1.1.


