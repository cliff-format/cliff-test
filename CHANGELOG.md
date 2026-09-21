# cliff-test Changelog

cliff-test is versioned with CLIFF 1.1.0. See the Git history for the complete record of changes.

## 1.1.0 — 2026

The suite follows CLIFF 1.1, which is a pure relaxation of 1.0: every 1.0
fixture still passes, and the checks below answer the 1.1 questions.

### Recorded

- **The CLIFF edit baseline at the shipped temperature 1.3**, which no earlier
  D7 number could be: `python .tools/d7_cliff_13.py --passes 3`, CLIFF only, the
  `ui` stratum, the same 12 edits, 171 applicable edits, every answer kept
  (`results/d7-cliff-13/`). **97.7 % still valid / 95.9 % intent applied**, per
  pass 96.5 / 93.0 / 98.2 on intent and 1.0 point of standard deviation on
  validity. Against the 0.0 rows (100 % / 98.6 %) the difference is the decoder.
  All seven failures are attributed from the stored answers in
  [docs/clarion-prompt-design.md](docs/clarion-prompt-design.md): four answers were
  not CLIFF (an unquoted text value, a period outside the closing quote, an
  unquoted string as a list value, and one 32-byte `<support>...invalid...</support>`
  stub), three were valid but did not apply the instruction (a reproducible no-op
  on `set-emotion`, an invented target value, and a rename applied to a group
  rather than to an entry of the same name). Repairs the model introduced were
  confined to `add-reference` (5) and `set-emotion` (2).
- **The first benchmark run on the 1.1 corpus and the current model name**:
  `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch`,
  model `deepseek-flash`, `read_mode: tolerant`, 3 repeats per cell over
  CLARION-Core 0.3.0 (16 documents, 392 entries). Run
  `results/clarion-deepseek-flash-20260920T114819+0000-6a5259`: 1 180 records,
  exit 0, 960 translation runs + 60 robustness chains + 160 fidelity
  conversions, 5 598 954 prompt + 4 172 463 output tokens, 53 minutes, no
  truncated run.
  - CLIFF **chrF++ 51.2 plain / 53.9 context**, instruction-following
    79.5% / 83.0%, round-trip context retention **100%**, still valid after
    edits **100.0% bare / 83.3% context**.
  - `--skip fetch` is deliberate and recorded in
    [docs/acceptance-criteria.md](docs/acceptance-criteria.md): the fetch cache
    was empty, so importing again would have rewritten the committed corpus —
    the 118 `human_verified` items, their checksums and their attribution — and
    spent several hundred extra annotation calls on the same model as the system
    under test, which `clarion/corpus/annotate.py` warns against.
  - **The two readings measured on the same answers**: re-scoring the 96 stored
    CLIFF answers with no model call gives strict valid 89.6% / 83.3% against
    tolerant valid 93.8% / 89.6%, at 0.06 / 0.12 repairs per answer. All six
    repairs were shape repairs; one `wmt24pp` answer claimed
    `status: translated` on an entry with no `target`, which both readings
    refuse (Appendix C.5). This is the number that makes the tolerant mode worth
    having, and it could not be produced before this revision.
  - 61 of 960 runs failed to parse, all in the two formats that cannot carry
    multi-line context cleanly (`csv` context writes a newline into one row and
    shifts every later column; `xliff-2.1` context emits malformed XML). Each
    was inspected in the stored answer text rather than read off the summary.
  - Correction: the D1/D2 prompt columns of [BENCHMARK.md](BENCHMARK.md) are
    restated from the regenerated tables, because `token_matrix` had been
    pricing a CLIFF prompt no arm sends.

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
- **`tests/clarion/test_edit_request.py`**: the temperature contract for the edit
  dimension — the request carries the value it is given (0.0 / 0.7 / 1.3), the
  matrix forwards `provider.temperature`, and the CLIFF field table is present
  under `examples` and absent under `digest`.
- **The temperature a request was actually sent at** is recorded per row
  (`RobustnessResult.temperature`, `TaskResult.temperature`), not only in the run
  directory's `config.json`. A record that carries the configuration alone cannot
  show a divergence between the two, which is exactly how D7 spent its whole
  history sending 0.0 while its `config.json` said 1.3.
- **A CLIFF intent assertion in `clarion/selfcheck.py`**: the deterministic
  reference application must not merely keep the file valid, it must apply the
  edit (100 % on both arms). The validity-only check could not see the silent
  failure shape this dimension exists to detect — a legal file whose instruction
  never landed. Scoped to CLIFF deliberately: json-plain fails it for a codec
  reason (a `|` used both inside a list value and between fields, so a
  multi-valued `reference` or `emotion` loses every element after the first on
  read-back), which is a defect of a format outside the question this benchmark
  now answers.
- **`docs/clarion-prompt-design.md`** records the temperature defect, the XLIFF
  attribution correction and the repair-attribution correction alongside the
  existing metric-error note, so the method's own mistakes are readable rather
  than only their fixed results.
- Appendix C.4 behaviour documented from what the implementation actually does,
  after the recorded run contradicted the first draft of the note: a collision
  that normalization *creates* is disambiguated (`-2`, `-3`, …) and reported as
  an `id-collision` repair, while a duplicate id the author wrote twice is still
  rejected in both readings (10.2). The two cases are distinguished by whether
  the ids became equal through normalization.
- `docs/clarion-methodology.md` §9.1 states what each reading answers, which
  repairs exist, what a terminator is not, and which C.5 refusals hold.

### Fixed

- **The edit dimension ignored the configured temperature.** `run_robustness`
  built its own `CompletionRequest` with a hard-coded `temperature=0.0`, and
  `build_provider` never passes a temperature to the provider at all, so
  `provider.temperature` reached the wire only through the translation path. Two
  consequences: **every D7 number published so far is a 0.0 number**, including the
  rows labelled as the deployment settings, and `d7_pilot.py --temperature 1.3`
  was a no-op that changed a `ProviderConfig` field nothing reads. The controlled
  CLIFF comparison survives (both its columns are the same model, the same `ui`
  stratum, the same 12 edits and an unedited `EDIT_SYSTEM`, so only the prompt
  differed), but no claim about D7 at 1.3 was ever supported, and a 1.3
  measurement is now owed. The temperature is a parameter of `run_robustness`,
  forwarded from the configuration, and
  `tests/clarion/test_edit_request.py` fails with `{0.0} == {1.3}` if the
  forward is dropped. Related corrections recorded in
  [docs/clarion-prompt-design.md](docs/clarion-prompt-design.md): the D7 pilot
  table's "temperature 1.3" heading, the "re-run at the shipped settings"
  section, and the attribution of the XLIFF row — the 100.0 % it was compared
  against belongs to the frozen `deepseek-v4-flash` benchmark, not to this model,
  whose same-run baseline is 57.1 %, so that difference is a model change rather
  than a temperature or prompt effect.
- **The published repair attribution for D7 counted re-counts as repairs.** A
  record's repair count is the count for the whole document at that step, and the
  answer text carries forward, so one deviation is counted again by every later
  step: the six CLIFF context cells sum to 44 per-step repair counts but the model
  introduced only **6** (`add-reference` 4, `set-emotion` 2). Attributing the sum
  per operation charged early operations for deviations introduced later.
  `.tools/d7_audit.py` now prints both figures and warns if the counts are not
  monotone within a cell.
- **`clarion/experiments/robustness.py` annotated `answer_dir` with `Path`
  without importing it.** It survived only because
  `from __future__ import annotations` defers evaluation; ruff's F821 reports it
  now that the annotated name is resolved.
- **`tests/clarion/test_prompt_v2.py`** had its first-party import in the
  third-party block, so `ruff check` failed on the file that guards the prompt.

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


