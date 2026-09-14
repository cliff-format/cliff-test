# Token Benchmark

`python tools/token_benchmark.py` serializes one identical 16-unit CLIFF 1.0
corpus in CLIFF 1.0, XLIFF 2.1, JSON, CSV, gettext PO, Fluent, YAML, and TOML,
then counts tokens with `tiktoken` (`cl100k_base`, the OpenAI-compatible
tokenizer).

Counting convention:

- CLIFF 1.0 tokens = `cliff-main.cliff` + `cliff-glossary.cliff` (the dependency
  glossary file is counted as part of CLIFF's single-workflow cost).
- Every other format inlines the same glossary, family info, standards,
  dependencies, group/entry context, type, emotion, status, max-width,
  reference, and ICU payloads in its native syntax.
- Acceptance criterion: CLIFF must save at least 30% versus the average of the
  other seven formats.

Run:

```sh
cd D:\Projects\cliff-format\cliff-test
python tools\token_benchmark.py
```

Results are written to `tests/benchmark/report.md` and fixture snapshots under
`tests/benchmark/fixtures/`.
