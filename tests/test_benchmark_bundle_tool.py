"""The tools that produce the published bundle are checked, not trusted.

Two tools turn a run directory into the evidence a reader is handed:

* `tools/audit_report.mjs` computes `computed-metrics.json`, `report.audited.md` and
  `investor-data.md` — the bundle's `computed/` payload, and a second implementation
  of statistics (`wilson()`) that the Python side guards in
  `tests/clarion/test_stats.py`;
* `tools/package_benchmark.py` assembles `benchmark/<bundle>/` and writes the README
  whose "Reproduce" table names the exact commands a reader is told to follow.

Neither had a single test reference, and both carried a defect that only a guard can
catch: the run id was a literal in each of them, so auditing or packing a *new* run
reproduced the *old* run's provenance — the one string a reader checks first, in the
one place nobody re-reads. The guards here are about provenance being derived, and
about the commands a reader is told to run actually existing.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGER = ROOT / "tools" / "package_benchmark.py"
AUDITOR = ROOT / "tools" / "audit_report.mjs"
SANDBOX = Path(__file__).resolve().parent / "clarion" / "_bundle_sandbox"

#: A run id in the shape the runner mints: name, timestamp, short hash.
RUN_ID = "clarion-deepseek-flash-20260922T031500+0000-ab12cd"

#: The commands the bundle README tells a reader to run, and what has to exist for
#: each to be runnable. The point is that the table is a promise: this project has
#: already shipped a documented command for a flag that no longer existed
#: (`--spec-mode cheatsheet`), so the strings are checked rather than trusted.
REPRODUCE = {
    "python -m clarion pipeline": "clarion.cli",
    "node tools/audit_report.mjs": "tools/audit_report.mjs",
    "python tools/package_benchmark.py": "tools/package_benchmark.py",
    "python tools/compare_readings.py": "tools/compare_readings.py",
    "python tools/qe_score.py": "tools/qe_score.py",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_run() -> Path:
    """A run directory with only what the packager reads."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)
    (SANDBOX / "config.json").write_text(
        json.dumps(
            {
                "corpus": "clarion-core",
                "formats": ["cliff", "po"],
                "arms": ["bare", "context"],
                "repeats": 3,
                "tokenizer": "o200k_base",
                "read_mode": "tolerant",
                "prompt_style": "spec",
                "provider": {"model": "deepseek-flash", "reasoning": "low", "temperature": 1.3},
                "pipeline": {"robustness_edits": 12},
            }
        ),
        encoding="utf-8",
    )
    records = [
        {"kind": "translation"},
        {"kind": "translation"},
        {"kind": "robustness"},
        {"kind": "fidelity"},
    ]
    (SANDBOX / "records.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    return SANDBOX


def teardown_module() -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)


def test_the_bundle_name_comes_from_the_run_id() -> None:
    """A packer that names its output from a literal overwrites the previous bundle."""
    packager = _load(PACKAGER, "package_benchmark")
    assert packager._bundle_name(RUN_ID) == "clarion-2026-09-22"
    assert packager._bundle_name("clarion-deepseek-v4-flash-20260228T235959+0000-000000") == (
        "clarion-2026-02-28"
    )
    with pytest.raises(SystemExit):
        packager._bundle_name("results-without-a-timestamp")


def test_the_bundle_readme_describes_the_run_it_packs() -> None:
    """The provenance line, the protocol and the counts are read from the run.

    This is the defect the packer had: the README named one particular run id and
    one particular set of counts, so packing a different run produced evidence whose
    first paragraph was about another run.
    """
    packager = _load(PACKAGER, "package_benchmark")
    run = _fake_run()
    readme = packager._readme(run, RUN_ID, "clarion-2026-09-22")

    assert f"`results/{RUN_ID}`" in readme, "the README must name the run it packs"
    assert "clarion-deepseek-v4-flash-20260902" not in readme
    # Counts come from records.jsonl, not from prose.
    assert "| translation runs | 2 |" in readme
    assert "| robustness chains | 1 (12 edits each) |" in readme
    assert "| fidelity conversions | 1 |" in readme
    # The protocol is the run's own configuration.
    assert "| reasoning | `low` |" in readme
    assert "| prompt style (CLIFF) | `spec` |" in readme
    assert "| temperature | 1.3 |" in readme
    assert "| corpus | clarion-core |" in readme
    assert "2 (cliff, po)" in readme


def test_the_reproduce_commands_in_the_bundle_readme_exist() -> None:
    """Every command the README tells a reader to run is a command that exists."""
    packager = _load(PACKAGER, "package_benchmark")
    readme = packager.README_HEADER.format(
        bundle="clarion-2026-09-22",
        run_id=RUN_ID,
        model="m",
        reasoning="low",
        temperature=1.3,
        prompt_style="spec",
        read_mode="tolerant",
        formats="2 (cliff, po)",
        arms="bare, context",
        repeats=3,
        corpus="clarion-core",
        translations=2,
        robustness=1,
        fidelity=1,
        edits=12,
        tokenizer="o200k_base",
    )
    for command, target in REPRODUCE.items():
        assert command in readme, f"the README no longer documents {command!r}; update this test"
        if target.startswith("tools/"):
            assert (ROOT / target).is_file(), f"{command!r} names a file that does not exist"
        else:
            from clarion.cli import build_parser

            assert build_parser() is not None, target


def test_the_audit_tool_derives_the_run_it_audits() -> None:
    """No run id may be a literal in the audit tool.

    It had one, in the generated `investor-data.md` header: auditing a new run wrote
    the *old* run's id into the published provenance line.
    """
    source = AUDITOR.read_text(encoding="utf-8")
    literal = re.findall(r"clarion-[\w.+-]*-\d{8}T\d{6}[+\-]\d{4}-[0-9a-f]{6,}", source)
    assert literal == [], (
        f"tools/audit_report.mjs hard-codes the run id(s) {literal}; the run being audited "
        "is the directory passed as argv[2]"
    )
    assert "path.basename(path.resolve(runDir))" in source, (
        "the audited run's id is no longer derived from its directory"
    )


def _committed_bundle() -> Path | None:
    """The packed bundle's `raw/` directory, which has a run directory's shape."""
    bundles = sorted((ROOT / "benchmark").glob("*/raw/records.jsonl"))
    return bundles[0].parent if bundles else None


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_audit_tool_audits_a_run_and_names_it() -> None:
    """End to end, on the shape of records the tool actually meets.

    The provenance line is the one string a reader checks first, and both defects this
    file guards lived there: a hard-coded run id, and a corpus count that read 18 files
    and 414 entries because the two `variant: glossary` term files were filtered by
    **file name** (`*-terms.*.cliff`) instead of by their variant header. The counts
    below are the corpus's own, and they are what the line has to say.
    """
    bundle = _committed_bundle()
    if bundle is None:
        pytest.skip("no packed bundle on disk to take records from")
    run = SANDBOX
    if run.exists():
        shutil.rmtree(run)
    (run / "answers").mkdir(parents=True)
    for name in ("config.json", "summary.json", "tokens.json"):
        shutil.copyfile(bundle / name, run / name)
    records = (bundle / "records.jsonl").read_text(encoding="utf-8").splitlines()
    # One record per (format, arm): the sheet reports the whole matrix, so a partial one
    # is not the shape this tool meets in production. Sampling the first five lines
    # instead gave a run with a single format and arm, which the tool used to reject with
    # a TypeError rather than a report - the guards for that are in the tool now.
    seen: set[tuple[str, str]] = set()
    sampled: list[str] = []
    for line in records:
        if '"translation"' not in line:
            continue
        record = json.loads(line)
        key = (str(record.get("format")), str(record.get("arm")))
        if key in seen:
            continue
        seen.add(key)
        sampled.append(line)
    assert len(sampled) == len({(json.loads(line).get("format"), json.loads(line).get("arm"))
                                for line in records if '"translation"' in line})
    (run / "records.jsonl").write_text("\n".join(sampled) + "\n", encoding="utf-8")

    result = subprocess.run(
        ["node", str(AUDITOR), str(run)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    sheet = (run / "investor-data.md").read_text(encoding="utf-8")
    assert f"Source: run {run.name} (" in sheet, sheet.splitlines()[:4]
    assert "16 corpus files, 392 entries" in sheet, (
        "the corpus counts in the provenance line are wrong again; they are read out of "
        "the corpus index, which must exclude `variant: glossary` files by their header"
    )
    assert f"{len(sampled)} translation runs" in sheet, (
        "the run line no longer counts the records it read"
    )


def test_the_packer_derives_the_run_it_packs() -> None:
    """The same guard on the Python side, where the literal was the source run id."""
    source = PACKAGER.read_text(encoding="utf-8")
    literal = re.findall(r"clarion-[\w.+-]*-\d{8}T\d{6}[+\-]\d{4}-[0-9a-f]{6,}", source)
    assert literal == [], f"tools/package_benchmark.py hard-codes the run id(s) {literal}"
    assert "run_dir.resolve().name" in source, "the source run id is no longer derived"
