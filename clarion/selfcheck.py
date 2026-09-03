"""Offline end-to-end verification of the CLARION harness.

The benchmark must be able to prove that it works before it is allowed to
report a number about anyone else. The self-check runs the entire pipeline
without a network call, using the deterministic mock provider in two modes:

perfect  every metric must come out clean - anything else is a harness bug;
noisy    every metric must detect its planted failure - anything else means the
         metric is asleep.

It also renders, validates and reads back every format in every arm, measures
round-trip fidelity, builds the token tables, and applies the deterministic
edit sequence to every format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import ProviderConfig, RunConfig
from .corpus.store import load_corpus
from .formats.arms import Arm
from .formats.parse import parse_back
from .formats.registry import DEFAULT_FORMATS, get_format
from .formats.render import render
from .formats.validity import check_validity
from .metrics.fidelity import roundtrip_fidelity
from .metrics.terminology import load_policy
from .metrics.tokens import get_tokenizer
from .paths import ensure_clif_format, pyclif_version
from .runner import token_matrix


@dataclass
class CheckResult:
    """One self-check step."""

    name: str
    ok: bool
    detail: str = ""


@dataclass
class SelfCheckReport:
    """All self-check steps."""

    results: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        """Record one step."""
        self.results.append(CheckResult(name=name, ok=ok, detail=detail))

    @property
    def ok(self) -> bool:
        """True when every step passed."""
        return all(result.ok for result in self.results)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "ok": self.ok,
            "steps": [
                {"name": result.name, "ok": result.ok, "detail": result.detail}
                for result in self.results
            ],
        }


def _mock_config(mode: str, corpus_name: str) -> RunConfig:
    return RunConfig(
        name=f"selfcheck-{mode}",
        corpus=corpus_name,
        formats=list(DEFAULT_FORMATS),
        arms=["bare", "context"],
        repeats=1,
        provider=ProviderConfig(kind="mock", model="mock-1", mode=mode),
    )


def run_selfcheck(*, corpus_name: str = "clarion-core", verbose: bool = True) -> int:
    """Run every offline check and return a process exit code."""
    from .experiments.robustness import default_tasks, run_robustness
    from .experiments.translate import run_translation_task
    from .providers.mock import MockProvider

    report = SelfCheckReport()
    ensure_clif_format()
    report.add("clif-python available", True, f"version {pyclif_version()}")

    try:
        corpus = load_corpus(corpus_name)
    except FileNotFoundError as exc:
        report.add("corpus loads", False, str(exc))
        _print(report, verbose)
        return 1
    report.add(
        "corpus loads",
        bool(corpus.files),
        f"{len(corpus.files)} files, {corpus.entry_count()} entries, strata {corpus.strata()}",
    )
    if not corpus.files:
        _print(report, verbose)
        return 1

    import clif_format

    invalid: list[str] = []
    for corpus_file in corpus.files:
        issues = [
            issue
            for issue in clif_format.validate(corpus_file.path.read_text(encoding="utf-8"))
            if issue.category not in {"warning", "extension"}
        ]
        if issues:
            invalid.append(f"{corpus_file.path.name}:{issues[0].line} {issues[0].message}")
    report.add("corpus documents are valid CLIF", not invalid, "; ".join(invalid[:3]))

    missing_reference = [
        f"{corpus_file.id}/{entry_id}"
        for corpus_file in corpus.files
        for entry_id in corpus_file.sources()
        if not corpus_file.references().get(entry_id)
    ]
    report.add(
        "every entry has a reference translation",
        not missing_reference,
        "; ".join(missing_reference[:5]),
    )

    sample = corpus.files[0]
    render_failures: list[str] = []
    for format_id in DEFAULT_FORMATS:
        for arm in (Arm.BARE, Arm.CONTEXT):
            spec = get_format(format_id)
            if arm is Arm.CONTEXT and not spec.context_capable:
                continue
            try:
                text = render(sample.document, format_id, arm=arm, blank=True)
                validity = check_validity(text, format_id)
                parsed = parse_back(text, format_id)
                if not validity.ok:
                    render_failures.append(f"{format_id}/{arm.value}: invalid render")
                elif not parsed.ok:
                    render_failures.append(f"{format_id}/{arm.value}: {parsed.error}")
            except Exception as exc:  # noqa: BLE001 - report, do not crash
                render_failures.append(f"{format_id}/{arm.value}: {type(exc).__name__}: {exc}")
    report.add("every format renders, validates and reads back", not render_failures,
               "; ".join(render_failures[:3]))

    retention = {
        format_id: roundtrip_fidelity(sample.document, format_id, arm=Arm.CONTEXT)
        for format_id in DEFAULT_FORMATS
    }
    clif_retention = retention["clif"].retention
    report.add(
        "CLIF round-trips losslessly",
        clif_retention >= 0.999,
        f"retention {clif_retention:.3f}",
    )
    others = {key: value.retention for key, value in retention.items() if key != "clif"}
    report.add(
        "round-trip fidelity measured for every format",
        all(report_item.ok for report_item in retention.values()),
        ", ".join(f"{key} {value:.2f}" for key, value in sorted(others.items())),
    )

    tokenizer = get_tokenizer("o200k_base")
    policy = load_policy("zh-CN")
    config = _mock_config("perfect", corpus_name)
    token_rows = token_matrix(config, corpus, tokenizer=tokenizer, policy=policy)
    clif_bare = [row for row in token_rows if row["format"] == "clif" and row["arm"] == "bare"]
    report.add(
        "token matrix produced",
        bool(token_rows) and bool(clif_bare),
        f"{len(token_rows)} cells, tokenizer {tokenizer.name}",
    )

    perfect_provider = MockProvider(mode="perfect")
    perfect = run_translation_task(
        sample,
        format_id="clif",
        arm=Arm.CONTEXT,
        provider=perfect_provider,
        tokenizer=tokenizer,
        config=config,
        policy=policy,
    )
    report.add(
        "perfect answer scores perfectly",
        perfect.structure.get("valid") is True
        and perfect.structure.get("coverage") == 1.0
        and perfect.quality.get("chrf", 0) > 99.0,
        f"valid={perfect.structure.get('valid')} coverage={perfect.structure.get('coverage')} "
        f"chrf={perfect.quality.get('chrf')} instruction={perfect.instruction.get('score')}",
    )

    noisy_config = _mock_config("noisy", corpus_name)
    noisy = run_translation_task(
        sample,
        format_id="clif",
        arm=Arm.CONTEXT,
        provider=MockProvider(mode="noisy"),
        tokenizer=tokenizer,
        config=noisy_config,
        policy=policy,
    )
    detected = (
        noisy.quality.get("chrf", 100.0) < perfect.quality.get("chrf", 100.0)
        or noisy.structure.get("coverage", 1.0) < 1.0
    )
    report.add(
        "planted failures are detected",
        detected,
        f"coverage={noisy.structure.get('coverage')} chrf={noisy.quality.get('chrf')} "
        f"jargon_hits={noisy.jargon.get('hit_count')} unwrapped={noisy.structure.get('unwrapped')}",
    )
    report.add(
        "markdown fences are unwrapped, not counted as failures",
        bool(noisy.structure.get("unwrapped")),
        "the noisy mock wraps its answer in a code fence",
    )

    from .metrics.controls import evaluate_controls

    control_report = evaluate_controls(
        file_id=sample.id,
        sources=sample.sources(),
        references=sample.references(),
        system=sample.references(),
    )
    worst_name, worst_score = control_report.worst_control
    report.add(
        "degenerate controls score below a real answer",
        control_report.sane,
        f"system {control_report.system_score:.1f} vs {worst_name} {worst_score:.1f} "
        f"(all controls: "
        + ", ".join(f"{key} {value:.1f}" for key, value in control_report.controls.items())
        + ")",
    )

    tasks = default_tasks(sample.document, count=12)
    deterministic_failures: list[str] = []
    for format_id in DEFAULT_FORMATS:
        result = run_robustness(
            sample.document,
            format_id=format_id,
            arm=Arm.CONTEXT,
            provider=None,
            tasks=tasks,
            file_id=sample.id,
        )
        if result.validity_rate < 100.0:
            deterministic_failures.append(f"{format_id} {result.validity_rate:.0f}%")
    report.add(
        "deterministic edits keep every format valid",
        not deterministic_failures,
        "; ".join(deterministic_failures[:5]) or f"{len(tasks)} edits per format",
    )

    _print(report, verbose)
    return 0 if report.ok else 1


def _print(report: SelfCheckReport, verbose: bool) -> None:
    if not verbose:
        return
    for result in report.results:
        mark = "PASS" if result.ok else "FAIL"
        detail = f" - {result.detail}" if result.detail else ""
        print(f"[{mark}] {result.name}{detail}")
    print()
    print("SELF-CHECK PASS" if report.ok else "SELF-CHECK FAIL")
