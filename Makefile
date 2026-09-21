.PHONY: test check bench selfcheck quality robustness clean

# What CI runs, in the order it runs it. `make check` is the local gate: if it
# passes here it passes there, and every step is here rather than in the workflow
# so the two cannot drift.
#
# CLIFF_REQUIRE_SIBLINGS=1 is what the workflow sets for the test step: without it a
# failed sibling checkout or corpus turns the dependent suites into skips, and this
# gate would pass having checked nothing.
check:
	CLIFF_REQUIRE_SIBLINGS=1 python tests/run_all.py
	# `run_all.py` rewrites the token-benchmark report and its nine fixtures; this is
	# what notices when the committed copy and the generator have drifted apart. The
	# remaining tracked generated artefacts have no generator to re-render them, and
	# `tests/test_generated_artefacts.py` says which and what covers them instead.
	python tools/token_benchmark.py --check
	python tools/corpus_version.py
	ruff check .
	CLIFF_REQUIRE_SIBLINGS=1 pytest
	python -m clarion selfcheck
	python -m clarion secret-scan

test:
	python tests/run_all.py

# The two batteries the runner only runs on request. Each reads something produced
# rather than committed - the 100 edits, which are gitignored, and the stored quality
# translation, which `make clean` removes - so the inputs are produced first and the
# documented command works on a fresh clone.
quality robustness:
	python tests/edit-robustness/apply_edits.py
	@test -f tests/quality/translator-output.cliff || git checkout -- tests/quality/translator-output.cliff
	@test -f tests/quality/quality-report.md || git checkout -- tests/quality/quality-report.md
	python tests/run_all.py --quality --robustness

selfcheck:
	python -m clarion selfcheck

bench:
	python tools/token_benchmark.py

clean:
	rm -rf tests/edit-robustness/edits tests/edit-robustness/report.md tests/quality/translator-output.cliff tests/quality/quality-report.md tests/benchmark/report.md
