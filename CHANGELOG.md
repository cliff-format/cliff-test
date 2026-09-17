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

### Moved

- `tests/fixtures/invalid/uppercase-entry-id.zh-CN.cliff` and
  `underscore-entry-id.zh-CN.cliff` → `tests/fixtures/valid/`: 1.1 accepts both.
- `tests/fixtures/invalid/filename-mismatch.zh-CN.cliff` and the three
  `invalid/ja-JP/` fixtures → `tests/fixtures/layout/`: their finding is a
  warning in 1.1.

