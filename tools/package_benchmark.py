"""Package the CLARION run into the public benchmark bundle.

Layout (raw evidence stays as-is; computed review data is the program output):

    cliff-test/benchmark/<bundle>/
        README.md
        raw/       answers/ records.jsonl qe_scores.jsonl tokens.json config.json summary.json
        computed/  computed-metrics.json report.md report.audited.md investor-data.md

Usage: python tools/package_benchmark.py results/<run-id> [--name clarion-YYYY-MM-DD]

The bundle name defaults to `clarion-<date>`, read from the run id's own timestamp,
and the README's provenance line, format list and task counts are read from the run
it packs. Both used to be literals naming one particular run, which meant that
packing a *new* run wrote it into the *old* bundle and described it with the *old*
run's id and counts - a silently wrong provenance line in the published evidence,
the one string a reader trusts first.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: A run id is `clarion-<model>-<YYYYMMDD>T<hhmmss><tz>-<hash>`; the bundle name is
#: `clarion-<YYYY>-<MM>-<DD>`, read out of that timestamp. The example is written as
#: a placeholder rather than as a real id on purpose: `tests/test_benchmark_bundle_tool.py`
#: fails the build when a run id appears as a literal in this file, because the one
#: that used to be here is what made packing a new run describe the old one.
_RUN_DATE = re.compile(r"-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T\d{6}")

README_HEADER = """# CLARION benchmark bundle - {bundle}

Source run: `results/{run_id}`, packed by `tools/package_benchmark.py`. Raw
evidence is kept as-is; the computed review data is the program output of
`tools/audit_report.mjs` (regenerated, never hand-written).

## Protocol

| | |
| --- | --- |
| model | `{model}` |
| reasoning | `{reasoning}` |
| temperature | {temperature} |
| prompt style (CLIFF) | `{prompt_style}` |
| read mode (CLIFF) | `{read_mode}` |
| formats | {formats} |
| arms | {arms} |
| repeats | {repeats} |
| corpus | {corpus} |
| translation runs | {translations} |
| robustness chains | {robustness} ({edits} edits each) |
| fidelity conversions | {fidelity} |

## raw/

| File | Contents |
| --- | --- |
| config.json | resolved run configuration (model, formats, arms, seed) |
| summary.json | per-stage run summary |
| records.jsonl | one JSON line per measured task ({translations} translation, {robustness} robustness, {fidelity} fidelity) |
| answers/ | raw model answers + the exact prompt that produced them (one .answer.txt and .prompt.txt per task) |
| qe_scores.jsonl | per-segment MetricX-23-QE scores (reference-free), when the optional QE pass was run |
| tokens.json | per-format token-cost measurements (tiktoken {tokenizer}) |

## computed/

| File | Contents |
| --- | --- |
| computed-metrics.json | **unified review data**: token cost, quality, latency, validity, significance, fidelity per format/arm |
| report.md | the original generated report (dimensions D1-D7) |
| report.audited.md | audit report: corrected failures, strict reading, significance |
| investor-data.md | the review tables as one compact sheet |

## Reproduce

| Step | Command |
| --- | --- |
| run the benchmark | `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch` |
| audit + computed metrics | `node tools/audit_report.mjs <run-dir>` |
| pack this bundle | `python tools/package_benchmark.py <run-dir>` |
| two readings (CLIFF) | `python tools/compare_readings.py <run-dir>` |
| QE scoring (optional) | `python tools/qe_score.py <run-dir>` (MetricX-23-QE-Large, Apache-2.0, reference-free) |

## License

The harness is MIT. Corpus documents carry their own SPDX headers (CC0 for
authored text, MIT for Godot, Apache-2.0 for WMT24++, public domain for the
classical translations); model answers are derived from those licensed sources and
inherit their terms.
"""


def _records(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _bundle_name(run_id: str) -> str:
    """The bundle name, from the run id's own timestamp."""
    match = _RUN_DATE.search(run_id)
    if not match:
        raise SystemExit(f"cannot read a date out of the run id {run_id!r}; pass --name")
    return f"clarion-{match['year']}-{match['month']}-{match['day']}"


def _readme(run_dir: Path, run_id: str, bundle: str) -> str:
    """The bundle README, every figure read from the run it packs."""
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    records = _records(run_dir)
    counts = {"translation": 0, "robustness": 0, "fidelity": 0}
    for record in records:
        kind = record.get("kind")
        if kind in counts:
            counts[kind] += 1
    provider = config.get("provider", {})
    edits = config.get("pipeline", {}).get("robustness_edits", 0)
    formats = config.get("formats", [])
    return README_HEADER.format(
        bundle=bundle,
        run_id=run_id,
        model=provider.get("model", "?"),
        reasoning=provider.get("reasoning", "?"),
        temperature=provider.get("temperature", "?"),
        prompt_style=config.get("prompt_style", "?"),
        read_mode=config.get("read_mode", "?"),
        formats=f"{len(formats)} ({', '.join(formats)})",
        arms=", ".join(config.get("arms", [])),
        repeats=config.get("repeats", "?"),
        corpus=config.get("corpus", "?"),
        translations=counts["translation"],
        robustness=counts["robustness"],
        fidelity=counts["fidelity"],
        edits=edits,
        tokenizer=config.get("tokenizer", "?"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="the run directory to pack, e.g. results/<run-id>")
    parser.add_argument("--name", default="", help="bundle directory name (default: from the run id)")
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    if not (run_dir / "records.jsonl").exists():
        raise SystemExit("not a run dir: " + str(run_dir))
    run_id = run_dir.resolve().name
    bundle = args.name or _bundle_name(run_id)

    out = ROOT / "benchmark" / bundle
    raw = out / "raw"
    comp = out / "computed"
    raw.mkdir(parents=True, exist_ok=True)
    comp.mkdir(parents=True, exist_ok=True)

    for name in ("config.json", "summary.json", "records.jsonl", "qe_scores.jsonl", "tokens.json"):
        src = run_dir / name
        if src.exists():
            shutil.copyfile(src, raw / name)
            print("raw/ " + name)
    for name in ("computed-metrics.json", "report.md", "report.audited.md", "investor-data.md"):
        src = run_dir / name
        if src.exists():
            shutil.copyfile(src, comp / name)
            print("computed/ " + name)
    answers_src = run_dir / "answers"
    if answers_src.exists():
        shutil.copytree(answers_src, raw / "answers", dirs_exist_ok=True)
        print(f"raw/ answers/ ({len(list(answers_src.glob('*.answer.txt')))} tasks)")

    (out / "README.md").write_text(_readme(run_dir, run_id, bundle), encoding="utf-8")
    print("wrote " + str(out / "README.md"))
    print("bundle complete at " + str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
