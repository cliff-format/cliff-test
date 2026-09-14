# Contributing to cliff-test

This project owns the verification story for the CLIFF specification in the
sibling `cliff` repository.

## What we need

1. **Conformance fixtures** — valid and invalid `.cliff` files under
   `tests/fixtures/`.
2. **Validator changes** — keep `tools/cliff_validator.py` in lockstep with
   [cliff-1.0.0.md](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.0.0.md).
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

Invalid fixtures must make the validator exit non-zero; valid fixtures must
pass with zero errors.

## License

All contributions are under the MIT License.
