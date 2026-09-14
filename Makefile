.PHONY: test bench clean

test:
	python tests/run_all.py

bench:
	python tools/token_benchmark.py

clean:
	rm -rf tests/edit-robustness/edits tests/edit-robustness/report.md tests/quality/translator-output.cliff tests/quality/quality-report.md tests/benchmark/report.md
