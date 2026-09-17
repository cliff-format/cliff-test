# Contributing to cliff-test

This project owns the verification story for the CLIFF specification in the
sibling `cliff` repository.

## What we need

1. **Conformance fixtures** — one directory per question, under
   `tests/fixtures/`: `valid/`, `invalid/`, `layout/`, `style/`, `tolerant/`.
   Each suite is checked in the mode it is about, so put a fixture in the suite
   whose mode proves it: a document that is valid CLIFF but written in a shape
   the style guide discourages belongs in `style/`, not in `invalid/`.
2. **Validator changes** — keep `tools/cliff_validator.py` in lockstep with
   [cliff-1.1.0.md](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.1.0.md).
3. **Benchmark improvements** — new format emitters or corpora in
   `tools/token_benchmark.py`, with fairness notes.
4. **Quality corpus growth** — difficult translation cases plus gold
   references in `tests/quality/`.
5. **Robustness tasks** — realistic model-style edits in
   `tests/edit-robustness/tasks.json`.

## Before submitting

```bash
python tests/run_all.py
python tests/run_all.py --quality --robustness
```

`tests/run_all.py` prints the mode and the expected exit code of every suite.
The expectations are:

| Suite | Expectation |
| --- | --- |
| `valid/` | exit 0, zero errors |
| `invalid/` | non-zero exit, at least one error |
| `layout/` | exit 0 by default (the finding is a warning in 1.1), non-zero under `--check-layout` |
| `style/` | exit 0 with `--style`, and at least one `STYLE` warning |
| `tolerant/` | exit 0 under `--tolerant` for the repairable files; non-zero for the ones Appendix C.5 forbids repairing |

Two rules about what a fixture may assert:

- **A style deviation is never an error.** A document with `snake_case` ids or a
  trailing `;` is valid CLIFF 1.1; only `--style` may complain, and only as a
  warning.
- **A tolerant fixture must be paired with its refusal.** If you add a document
  the tolerant parser should repair, also add one it must refuse, so Appendix
  C.5 stays covered (`tests/run_all.py` warns when the refusal set is empty).

## License

All contributions are under the MIT License.
