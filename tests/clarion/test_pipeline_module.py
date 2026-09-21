"""The one-command pipeline: stage gating, and the evidence it leaves behind.

`clarion/pipeline.py` is what `clarion pipeline` runs end to end - fetch, secrets,
validate, licence, tokens, fidelity, translate, robustness, report - and it had no
test. The orchestrator is where a skipped stage silently becomes a stage that ran,
or a stage that failed still returns 0, so both are asserted here.

No model calls and no network: the provider is the mock, the import list is empty
(the "no imports configured" path), and the expensive stages are skipped. The run
directory is redirected into a sandbox inside the repository, because the file
sandbox denies the system temporary directory.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

import clarion.pipeline as pipeline_module
from clarion.config import PipelineConfig, ProviderConfig, RunConfig
from clarion.pipeline import Pipeline, run_pipeline
from clarion.runner import RunPaths

#: The scratch tree, scoped to this process. A fixed path is shared by every pytest
#: process pointed at this checkout, so two of them running at once left two run
#: directories behind and made "exactly one run directory" fail for a reason that has
#: nothing to do with the pipeline. `.gitignore` covers the parent, so the nested
#: per-process name is ignored too.
SANDBOX = Path(__file__).resolve().parent / "_pipeline_sandbox" / f"pid{os.getpid()}"


@pytest.fixture(autouse=True)
def _sandboxed_runs(monkeypatch):
    """Send every run directory into the sandbox, and clean up afterwards."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    original = RunPaths.create

    def create(name: str, base: Path | None = None) -> RunPaths:
        return original(name, base=SANDBOX)

    monkeypatch.setattr(pipeline_module.RunPaths, "create", staticmethod(create))
    yield
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)


def _config(**pipeline_overrides) -> RunConfig:
    """A pipeline that does everything offline, and nothing expensive."""
    skip = ["translate", "robustness", "fidelity"]
    skip.extend(pipeline_overrides.pop("skip", []))
    return RunConfig(
        name="pipeline-test",
        corpus="clarion-core",
        formats=["cliff"],
        arms=["bare"],
        repeats=1,
        concurrency=1,
        provider=ProviderConfig(kind="mock", model="mock-1", mode="perfect"),
        pipeline=PipelineConfig(fetch=[], skip=skip, **pipeline_overrides),
    )


def test_the_pipeline_reaches_the_report_and_leaves_its_evidence() -> None:
    code = run_pipeline(_config(), verbose=False)
    assert code == 0

    run_dirs = [path for path in SANDBOX.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1, f"expected exactly one run directory, got {run_dirs}"
    run_dir = run_dirs[0]

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "# CLARION run: pipeline-test" in report
    assert "D1 - token cost" in report, "the token tables belong in every report"
    assert "structural integrity" in report, "the modification-correctness table too"

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run"] == "pipeline-test"
    assert summary["model"] == "mock:mock-1"
    assert summary["records"] >= 0
    stages = {stage["stage"]: stage for stage in summary["stages"]}
    assert stages["secrets"]["ok"] is True, "a mock run needs no key and must not fail here"
    assert "validate" in stages


def test_a_skipped_stage_does_not_run_and_says_so() -> None:
    """The skip list is the difference between a 5-minute run and a 50-minute one."""
    code = run_pipeline(_config(skip=["tokens", "validate", "licence"]), verbose=False)
    assert code == 0
    run_dir = next(path for path in SANDBOX.iterdir() if path.is_dir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    names = [stage["stage"] for stage in summary["stages"]]
    for skipped in ("tokens", "validate", "licence"):
        assert skipped not in names, f"{skipped} was skipped but ran anyway"


def test_a_failing_stage_makes_the_run_fail() -> None:
    """A stage that reports not-ok must reach the exit code, not just the log."""
    config = _config()
    config.provider = ProviderConfig(
        kind="openai", model="not-reachable", api_key_env="NO_SUCH_KEY"
    )

    class Failing(Pipeline):
        def run_secrets(self) -> bool:
            self.stage("secrets", False, "planted failure", 0.0)
            return False

    assert Failing(config, verbose=False).run() == 1


def test_the_report_is_written_even_when_a_stage_fails() -> None:
    """The evidence of a failed run is the most valuable thing it produces."""
    config = _config()

    class Failing(Pipeline):
        def run_secrets(self) -> bool:
            self.stage("secrets", False, "planted failure", 0.0)
            return False

    assert Failing(config, verbose=False).run() == 1
    run_dir = next(path for path in SANDBOX.iterdir() if path.is_dir())
    assert (run_dir / "report.md").is_file()


def test_no_imports_configured_is_not_a_failure() -> None:
    """The fetch stage is skipped by configuration, not by absence of a recipe."""
    config = _config()
    pipeline = Pipeline(config, verbose=False)
    assert pipeline.run_fetch() is True
    assert pipeline.stages[-1].detail == "no imports configured"
