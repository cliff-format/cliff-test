"""The one-command pipeline: download, brief, measure, report.

    python -m clarion pipeline --config configs/deepseek-flash.json

Eight stages, each of which fails loudly instead of silently degrading:

1. secrets      load the API key from outside the repository and prove the
                working tree contains no credential
2. fetch        import every configured corpus: convert through pyclif, derive
                context deterministically, optionally have a second model write
                the brief, route by licence tier and write attribution
3. validate     the official CLIF validator over every corpus document
4. licence      attribution, SPDX headers and tier routing must be complete
5. tokens       dimensions 1 and 2, no model calls
6. fidelity     round-trip context retention per format
7. translate    dimensions 3 to 6 against the configured model
8. robustness   dimension 7, the same edit sequence in every format

The report and every raw record land in one run directory.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RunConfig
from .corpus.annotate import AnnotationConfig
from .corpus.fetchers import fetch
from .corpus.licensing import license_check
from .corpus.store import load_corpus
from .metrics.terminology import load_policy
from .metrics.tokens import get_tokenizer
from .paths import ensure_pyclif, pyclif_version
from .providers import build_provider
from .report import build_report
from .runner import (
    RunPaths,
    run_fidelity_matrix,
    run_robustness_matrix,
    run_translation_matrix,
    token_matrix,
)
from .secrets import install_key, scan_tree
from .util import dump_json, mean, utc_now, write_text


@dataclass
class StageResult:
    """Outcome of one pipeline stage."""

    name: str
    ok: bool
    detail: str = ""
    seconds: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "stage": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "seconds": round(self.seconds, 2),
            "data": self.data,
        }


class Pipeline:
    """Runs the stages and keeps the evidence together."""

    def __init__(self, config: RunConfig, *, verbose: bool = True) -> None:
        self.config = config
        self.verbose = verbose
        self.paths = RunPaths.create(config.name)
        self.stages: list[StageResult] = []
        self.token_rows: list[dict[str, Any]] = []
        self.records: list[dict[str, Any]] = []

    def log(self, message: str) -> None:
        """Print progress, because a paid run must never look stalled."""
        if self.verbose:
            print(f"[{utc_now()}] {message}", flush=True)

    def stage(self, name: str, ok: bool, detail: str, seconds: float, **data: Any) -> StageResult:
        """Record a finished stage."""
        result = StageResult(name=name, ok=ok, detail=detail, seconds=seconds, data=data)
        self.stages.append(result)
        self.log(f"{'OK ' if ok else 'FAIL'} {name}: {detail} ({seconds:.1f}s)")
        return result

    # ---------------------------------------------------------------- stages
    def run_secrets(self) -> bool:
        started = time.perf_counter()
        needs_key = self.config.provider.kind != "mock"
        installed = install_key(self.config.provider.api_key_env) if needs_key else True
        findings = scan_tree()
        ok = installed and not findings
        detail = (
            f"key {'loaded' if installed else 'MISSING'}, "
            f"{len(findings)} credential-looking strings in the tree"
        )
        self.stage("secrets", ok, detail, time.perf_counter() - started,
                   findings=[f"{path}:{line}" for path, line in findings[:10]])
        return ok

    def run_fetch(self) -> bool:
        started = time.perf_counter()
        steps = self.config.pipeline.fetch
        if not steps:
            self.stage("fetch", True, "no imports configured", time.perf_counter() - started)
            return True
        summaries: list[dict[str, Any]] = []
        ok = True
        for step in steps:
            step_started = time.perf_counter()
            annotator = None
            annotation_config = None
            if step.annotate:
                from dataclasses import replace

                # The annotator writes JSON, not prose: reasoning tokens would
                # eat the output budget and return an empty answer.
                provider_config = replace(
                    self.config.provider,
                    reasoning="off",
                    max_output_tokens=max(8192, self.config.provider.max_output_tokens),
                )
                if step.annotator_model:
                    provider_config = replace(provider_config, model=step.annotator_model)
                annotator = build_provider(provider_config)
                annotation_config = AnnotationConfig(propose_width=step.propose_width)
            try:
                result = fetch(
                    step.recipe,
                    stratum=step.stratum,
                    limit=step.limit,
                    annotator=annotator,
                    annotation_config=annotation_config,
                    revision=step.revision,
                )
            except Exception as exc:  # noqa: BLE001 - an import failure is a result
                ok = False
                summaries.append({"recipe": step.recipe, "error": f"{type(exc).__name__}: {exc}"})
                self.log(f"     import {step.recipe} failed: {exc}")
                continue
            summaries.append(result.as_dict())
            self.log(
                f"     {step.recipe}: {result.entries} entries, context {result.context_origin}"
                f"{' (cached)' if result.cached else ''}, "
                f"{time.perf_counter() - step_started:.1f}s"
            )
        self.stage("fetch", ok, f"{len(summaries)} imports", time.perf_counter() - started,
                   imports=summaries)
        return ok

    def run_validate(self) -> bool:
        started = time.perf_counter()
        ensure_pyclif()
        import pyclif

        corpus = load_corpus(self.config.corpus, strata=self.config.strata or None)
        problems: list[str] = []
        for corpus_file in corpus.files:
            issues = [
                issue
                for issue in pyclif.validate(corpus_file.path.read_text(encoding="utf-8"))
                if issue.category not in {"warning", "extension"}
            ]
            problems.extend(
                f"{corpus_file.path.name}:{issue.line} {issue.message}" for issue in issues
            )
        ok = not problems
        self.stage(
            "validate",
            ok,
            f"{len(corpus.files)} files, {corpus.entry_count()} entries, {len(problems)} problems",
            time.perf_counter() - started,
            problems=problems[:10],
        )
        return ok

    def run_licence(self) -> bool:
        started = time.perf_counter()
        problems = license_check()
        ok = not problems
        self.stage("licence", ok, f"{len(problems)} problems", time.perf_counter() - started,
                   problems=[problem.as_dict() for problem in problems][:10])
        return ok

    def run_tokens(self) -> bool:
        started = time.perf_counter()
        corpus = load_corpus(self.config.corpus, strata=self.config.strata or None)
        tokenizer = get_tokenizer(self.config.tokenizer)
        policy = load_policy(self.config.target_language)
        self.token_rows = token_matrix(self.config, corpus, tokenizer=tokenizer, policy=policy)
        dump_json(self.paths.root / "tokens.json", self.token_rows)
        self.stage("tokens", True, f"{len(self.token_rows)} cells", time.perf_counter() - started)
        return True

    def run_fidelity(self) -> bool:
        started = time.perf_counter()
        corpus = load_corpus(self.config.corpus, strata=self.config.strata or None)
        output = run_fidelity_matrix(self.config, corpus, paths=self.paths)
        self.records.extend(output.records)
        retention = mean([float(record["retention"]) for record in output.records]) * 100
        self.stage("fidelity", True, f"{len(output.records)} conversions, mean retention "
                   f"{retention:.1f}%", time.perf_counter() - started)
        return True

    def run_translate(self) -> bool:
        started = time.perf_counter()
        corpus = load_corpus(self.config.corpus, strata=self.config.strata or None)
        tokenizer = get_tokenizer(self.config.tokenizer)
        issue_count = 0

        def progress(done: int, total: int, record: dict[str, Any]) -> None:
            nonlocal issue_count
            has_issue = record.get("outcome") != "ok"
            if has_issue:
                issue_count += 1
            marker = f" [{issue_count} issue(s)]" if issue_count else ""
            if done % 10 == 0 or done == total or has_issue:
                self.log(
                    f"     translate {done}/{total} "
                    f"({record.get('format')}/{record.get('arm')} on {record.get('file')}){marker}"
                )
                if has_issue:
                    detail = record.get("error") or record.get("outcome")
                    self.log(f"       issue: {detail}")

        output = run_translation_matrix(
            self.config, corpus, tokenizer=tokenizer, paths=self.paths, progress=progress
        )
        self.records.extend(output.records)
        failed = [record for record in output.records if record.get("error")]
        prompt_tokens = sum(int(r["tokens"]["prompt_reported"] or 0) for r in output.records)
        output_tokens = sum(int(r["tokens"]["output_reported"] or 0) for r in output.records)
        ok = len(failed) < max(1, len(output.records) // 10)
        self.stage(
            "translate",
            ok,
            f"{len(output.records)} runs, {len(failed)} failed, "
            f"{prompt_tokens} prompt + {output_tokens} output tokens billed",
            time.perf_counter() - started,
            failed=[record.get("error") for record in failed][:5],
        )
        return ok

    def run_robustness(self) -> bool:
        started = time.perf_counter()
        strata = self.config.pipeline.robustness_strata or self.config.strata or None
        corpus = load_corpus(self.config.corpus, strata=strata)
        def progress(done: int, total: int, record: dict[str, Any]) -> None:
            self.log(
                f"     robustness {done}/{total} "
                f"({record.get('format')}/{record.get('arm')}: "
                f"{record.get('validity_rate')}% valid, {record.get('intent_rate')}% applied)"
            )

        output = run_robustness_matrix(
            self.config,
            corpus,
            edits=self.config.pipeline.robustness_edits,
            use_model=True,
            paths=self.paths,
            progress=progress,
        )
        self.records.extend(output.records)
        validity = mean([float(record["validity_rate"]) for record in output.records])
        self.stage(
            "robustness",
            True,
            f"{len(output.records)} format/arm chains, mean validity {validity:.1f}%",
            time.perf_counter() - started,
        )
        return True

    def run_report(self) -> Path:
        report = build_report(
            title=f"CLARION run: {self.config.name}",
            config=self.config.as_dict(),
            token_rows=self.token_rows,
            records=self.records,
        )
        path = self.paths.root / "report.md"
        write_text(path, report)
        dump_json(
            self.paths.summary,
            {
                "run": self.config.name,
                "finished": utc_now(),
                "pyclif": pyclif_version(),
                "model": f"{self.config.provider.kind}:{self.config.provider.model}",
                "reasoning": self.config.provider.reasoning,
                "records": len(self.records),
                "stages": [stage.as_dict() for stage in self.stages],
            },
        )
        return path

    def run(self) -> int:
        """Run every stage that is not skipped; return a process exit code."""
        skip = set(self.config.pipeline.skip)
        self.log(f"run directory: {self.paths.root}")
        if "secrets" not in skip and not self.run_secrets():
            self.run_report()
            return 1
        if "fetch" not in skip:
            self.run_fetch()
        if "validate" not in skip and not self.run_validate():
            self.run_report()
            return 1
        if "licence" not in skip and not self.run_licence():
            self.run_report()
            return 1
        if "tokens" not in skip:
            self.run_tokens()
        if "fidelity" not in skip:
            self.run_fidelity()
        if "translate" not in skip:
            self.run_translate()
        if "robustness" not in skip:
            self.run_robustness()
        path = self.run_report()
        self.log(f"report: {path}")
        return 0 if all(stage.ok for stage in self.stages) else 1


def run_pipeline(config: RunConfig, *, verbose: bool = True) -> int:
    """Entry point used by the CLI."""
    return Pipeline(config, verbose=verbose).run()
