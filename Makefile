.PHONY: test check bench selfcheck clean

# What CI runs, in the order it runs it. `make check` is the local gate: if it
# passes here it passes there, and every step is here rather than in the workflow
# so the two cannot drift.
check:
	python tests/run_all.py
	python tools/corpus_version.py
	ruff check clarion tests/clarion
	pytest
	python -m clarion selfcheck

test:
	python tests/run_all.py

selfcheck:
	python -m clarion selfcheck

bench:
	python tools/token_benchmark.py

clean:
	rm -rf tests/edit-robustness/edits tests/edit-robustness/report.md tests/quality/translator-output.cliff tests/quality/quality-report.md tests/benchmark/report.md
