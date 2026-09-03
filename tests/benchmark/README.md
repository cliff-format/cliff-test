# Token Benchmark

`python tools/token_benchmark.py` serializes one identical 16-unit CLIF 1.0
corpus in CLIF 1.0, XLIFF 2.1, JSON, CSV, gettext PO, Fluent, YAML, and TOML,
then counts tokens with `tiktoken` (`cl100k_base`, the OpenAI-compatible
tokenizer).

Counting convention:

- CLIF 1.0 tokens = `clif-main.clif` + `clif-glossary.clif` (the dependency
  glossary file is counted as part of CLIF's single-workflow cost).
- Every other format inlines the same glossary, family info, standards,
  dependencies, group/entry context, type, emotion, status, max-width,
  reference, and ICU payloads in its native syntax.
- Acceptance criterion: CLIF must save at least 30% versus the average of the
  other seven formats.

Run:

```sh
cd D:\Projects\clif-format\clif-test
python tools\token_benchmark.py
```

Results are written to `tests/benchmark/report.md` and fixture snapshots under
`tests/benchmark/fixtures/`.
