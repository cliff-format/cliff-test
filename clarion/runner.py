"""Experiment execution: expand the matrix, run it, and keep the evidence.

Three matrices exist, and each writes a JSONL evidence file plus a JSON
summary into the run directory:

translation   corpus file x format x arm x repeat  (dimensions 1 to 6)
fidelity      corpus file x format                 (round-trip context loss)
robustness    corpus file x format x arm           (dimension 7)

Isolation follows the configuration: with 'per-file' every corpus file gets a
fresh provider instance, so nothing from one file's conversation can leak into
another's - the file-level context pollution guard.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from .config import RunConfig
from .corpus.model import Corpus, CorpusFile
from .experiments.robustness import RobustnessResult, default_tasks, run_robustness
from .experiments.translate import run_translation_task
from .formats.arms import Arm
from .formats.registry import get_format
from .metrics.fidelity import FidelityReport, roundtrip_fidelity
from .metrics.terminology import JargonPolicy, load_policy
from .metrics.tokens import Tokenizer, get_tokenizer
from .paths import RESULTS_ROOT
from .providers import build_provider
from .providers.base import Provider
from .util import append_jsonl, dump_json, short_hash, utc_now, write_text


@dataclass
class RunPaths:
    """Where one run keeps its evidence."""

    root: Path
    records: Path
    summary: Path
    config: Path

    @staticmethod
    def create(name: str, base: Path | None = None) -> RunPaths:
        """Create a timestamped run directory."""
        stamp = utc_now().replace(":", "").replace("-", "")
        root = (base or RESULTS_ROOT) / f"{name}-{stamp}-{short_hash(name + stamp, 6)}"
        root.mkdir(parents=True, exist_ok=True)
        return RunPaths(
            root=root,
            records=root / "records.jsonl",
            summary=root / "summary.json",
            config=root / "config.json",
        )


@dataclass
class RunOutput:
    """Result of one execution."""

    kind: str
    paths: RunPaths
    records: list[dict[str, Any]] = field(default_factory=list)

    def count(self) -> int:
        """Number of records produced."""
        return len(self.records)


_PROVIDER_LOCK = Lock()


def _provider_for(config: RunConfig, cache: dict[str, Provider], key: str) -> Provider:
    """Pick the conversation boundary.

    per-task   a fresh conversation for every file, format and arm - nothing a
               model saw while translating one file can influence another, and
               nothing it learned about one format helps it with the next
    per-file   one conversation per file, shared across formats
    shared     one conversation for the whole run
    """
    if config.isolation == "per-task":
        return build_provider(config.provider)
    slot = key if config.isolation == "per-file" else "shared"
    with _PROVIDER_LOCK:
        if slot not in cache:
            cache[slot] = build_provider(config.provider)
        return cache[slot]


def run_translation_matrix(
    config: RunConfig,
    corpus: Corpus,
    *,
    tokenizer: Tokenizer | None = None,
    policy: JargonPolicy | None = None,
    paths: RunPaths | None = None,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> RunOutput:
    """Run every (file, format, arm, repeat) translation task."""
    tokenizer = tokenizer or get_tokenizer(config.tokenizer)
    policy = policy if policy is not None else load_policy(config.target_language)
    paths = paths or RunPaths.create(config.name)
    dump_json(paths.config, config.as_dict())
    providers: dict[str, Provider] = {}
    output = RunOutput(kind="translation", paths=paths)

    tasks: list[tuple[CorpusFile, str, str, int]] = []
    for corpus_file in corpus.files:
        for format_id in config.formats:
            spec = get_format(format_id)
            for arm in config.arms:
                if Arm(arm) is Arm.CONTEXT and not spec.context_capable:
                    continue
                for repeat in range(max(1, config.repeats)):
                    tasks.append((corpus_file, format_id, arm, repeat))

    def execute(task: tuple[CorpusFile, str, str, int]) -> dict[str, Any]:
        corpus_file, format_id, arm, repeat = task
        provider = _provider_for(
            config, providers, f"{corpus_file.id}:{format_id}:{arm}:{repeat}"
        )
        result = run_translation_task(
            corpus_file,
            format_id=format_id,
            arm=arm,
            provider=provider,
            tokenizer=tokenizer,
            config=config,
            policy=policy,
            repeat=repeat,
        )
        record = result.as_dict()
        record["kind"] = "translation"
        stem = f"{corpus_file.id}__{format_id}__{arm}__{repeat}"
        answers = paths.root / "answers"
        write_text(answers / f"{stem}.answer.txt", result.answer_text)
        write_text(answers / f"{stem}.prompt.txt", result.prompt_text)
        record["answer_file"] = f"answers/{stem}.answer.txt"
        return record

    workers = max(1, config.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, record in enumerate(pool.map(execute, tasks), start=1):
            append_jsonl(paths.records, record)
            output.records.append(record)
            if progress is not None:
                progress(index, len(tasks), record)
    return output


def rerun_failed(
    config: RunConfig,
    corpus: Corpus,
    records: list[dict[str, Any]],
    *,
    tokenizer: Tokenizer | None = None,
    policy: JargonPolicy | None = None,
    paths: RunPaths,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Re-run only the translation cells that failed.

    A successful cell costs money to produce and nothing to keep, so a repair
    run touches exactly the failures: the same file, format, arm and repeat,
    with the fixed harness.
    """
    tokenizer = tokenizer or get_tokenizer(config.tokenizer)
    policy = policy if policy is not None else load_policy(config.target_language)
    by_id = {item.id: item for item in corpus.files}
    targets = [
        record
        for record in records
        if record.get("kind") == "translation" and record.get("failed")
    ]
    providers: dict[str, Provider] = {}

    def execute(record: dict[str, Any]) -> dict[str, Any]:
        corpus_file = by_id[str(record["file"])]
        format_id = str(record["format"])
        arm = str(record["arm"])
        repeat = int(record.get("repeat", 0))
        provider = _provider_for(config, providers, f"{corpus_file.id}:{format_id}:{arm}:{repeat}")
        result = run_translation_task(
            corpus_file,
            format_id=format_id,
            arm=arm,
            provider=provider,
            tokenizer=tokenizer,
            config=config,
            policy=policy,
            repeat=repeat,
        )
        fresh = result.as_dict()
        fresh["kind"] = "translation"
        fresh["retried"] = True
        fresh["previous_outcome"] = record.get("outcome")
        stem = f"{corpus_file.id}__{format_id}__{arm}__{repeat}"
        write_text(paths.root / "answers-retry" / f"{stem}.answer.txt", result.answer_text)
        return fresh

    repaired: list[dict[str, Any]] = []
    workers = max(1, config.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, record in enumerate(pool.map(execute, targets), start=1):
            append_jsonl(paths.root / "records-retry.jsonl", record)
            repaired.append(record)
            if progress is not None:
                progress(index, len(targets), record)
    return repaired


def merge_records(
    original: list[dict[str, Any]], repaired: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Replace failed cells with their repaired versions, keep everything else."""
    index = {
        (str(r["file"]), str(r["format"]), str(r["arm"]), int(r.get("repeat", 0))): r
        for r in repaired
    }
    merged: list[dict[str, Any]] = []
    for record in original:
        if record.get("kind") != "translation":
            merged.append(record)
            continue
        key = (
            str(record["file"]),
            str(record["format"]),
            str(record["arm"]),
            int(record.get("repeat", 0)),
        )
        merged.append(index.get(key, record))
    return merged


def run_fidelity_matrix(
    config: RunConfig,
    corpus: Corpus,
    *,
    paths: RunPaths | None = None,
) -> RunOutput:
    """Measure round-trip context loss for every file and format."""
    paths = paths or RunPaths.create(f"{config.name}-fidelity")
    dump_json(paths.config, config.as_dict())
    output = RunOutput(kind="fidelity", paths=paths)
    for corpus_file in corpus.files:
        for format_id in config.formats:
            report: FidelityReport = roundtrip_fidelity(
                corpus_file.document,
                format_id,
                arm=Arm.CONTEXT,
                read_mode=config.read_mode,
            )
            record = report.as_dict()
            record["kind"] = "fidelity"
            record["file"] = corpus_file.id
            record["stratum"] = corpus_file.stratum
            append_jsonl(paths.records, record)
            output.records.append(record)
    return output


def run_robustness_matrix(
    config: RunConfig,
    corpus: Corpus,
    *,
    edits: int = 30,
    use_model: bool = True,
    paths: RunPaths | None = None,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> RunOutput:
    """Apply the same edit sequence to every format and validate every step."""
    paths = paths or RunPaths.create(f"{config.name}-robustness")
    dump_json(paths.config, config.as_dict())
    providers: dict[str, Provider] = {}
    output = RunOutput(kind="robustness", paths=paths)

    jobs: list[tuple[CorpusFile, str, str]] = []
    for corpus_file in corpus.files:
        for format_id in config.formats:
            spec = get_format(format_id)
            for arm in config.arms:
                if Arm(arm) is Arm.CONTEXT and not spec.context_capable:
                    continue
                jobs.append((corpus_file, format_id, arm))

    def execute(job: tuple[CorpusFile, str, str]) -> dict[str, Any]:
        corpus_file, format_id, arm = job
        tasks = default_tasks(corpus_file.document, count=edits)
        provider = _provider_for(config, providers, corpus_file.id) if use_model else None
        result: RobustnessResult = run_robustness(
            corpus_file.document,
            format_id=format_id,
            arm=arm,
            provider=provider,
            tasks=tasks,
            file_id=corpus_file.id,
            read_mode=config.read_mode,
            prompt_style=config.prompt_style,
            temperature=config.provider.temperature,
            max_output_tokens=config.provider.max_output_tokens,
            answer_dir=(
                paths.root
                / "answers-robustness"
                / f"{corpus_file.id}__{format_id}__{arm}"
            ) if provider is not None else None,
        )
        record = result.as_dict()
        record["kind"] = "robustness"
        record["stratum"] = corpus_file.stratum
        return record

    workers = max(1, config.concurrency)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, record in enumerate(pool.map(execute, jobs), start=1):
            append_jsonl(paths.records, record)
            output.records.append(record)
            if progress is not None:
                progress(index, len(jobs), record)
    return output


def token_matrix(
    config: RunConfig,
    corpus: Corpus,
    *,
    tokenizer: Tokenizer | None = None,
    policy: JargonPolicy | None = None,
) -> list[dict[str, Any]]:
    """Dimensions 1 and 2 without calling a model.

    Builds the exact prompt every translation task would send and reports its
    component-level token cost. Because the components are labelled, the report
    can state the cost with and without the CLIFF specification block by
    subtraction instead of by a second experiment.
    """
    from .formats.render import render_document
    from .prompts.assembly import build_translation_prompt

    tokenizer = tokenizer or get_tokenizer(config.tokenizer)
    policy = policy if policy is not None else load_policy(config.target_language)
    rows: list[dict[str, Any]] = []

    for corpus_file in corpus.files:
        for format_id in config.formats:
            spec = get_format(format_id)
            for arm in config.arms:
                arm_value = Arm(arm)
                if arm_value is Arm.CONTEXT and not spec.context_capable:
                    continue
                task_document = _blank(corpus_file, arm_value)
                document_text = render_document(task_document, format_id, arm=arm_value)
                glossary_text = ""
                if config.include_glossary and corpus_file.glossary_document is not None:
                    if arm_value is Arm.CONTEXT:
                        glossary_text = render_document(
                            corpus_file.glossary_document, format_id, arm=arm_value
                        )
                bundle = build_translation_prompt(
                    document_text=document_text,
                    format_id=format_id,
                    tokenizer=tokenizer,
                    source_language=corpus_file.source_language,
                    target_language=corpus_file.target_language,
                    arm=arm_value.value,
                    spec_location=config.spec_location,
                    spec_reference=config.spec_reference,
                    glossary_text=glossary_text,
                    policy_fragment=policy.prompt_fragment() if config.include_policy else "",
                    document=task_document,
                    # D1/D2 price the prompt the translation arms actually send.
                    # These two arguments are part of that prompt and of no other
                    # format's: the terminology-workflow block, and its placement
                    # (the ablation in docs/clarion-prompting.md shows placement
                    # changes whether the workflow is obeyed). Leaving them out
                    # understated the CLIFF row of the token tables by about half.
                    allow_glossary_output=config.allow_glossary_output,
                    workflow_style=config.workflow_style,
                    # Part of the prompt the arms send, so part of its price. This
                    # was omitted along with `prompt_style` in the translation path,
                    # which is why both were silently priced and sent as the default
                    # style while the configuration named `examples`.
                    prompt_style=config.prompt_style,
                )
                budget = bundle.budget
                rows.append(
                    {
                        "kind": "tokens",
                        "file": corpus_file.id,
                        "stratum": corpus_file.stratum,
                        "format": format_id,
                        "arm": arm_value.value,
                        "entries": corpus_file.entry_count,
                        "tokenizer": tokenizer.name,
                        "document_tokens": budget.tokens_of("document"),
                        "glossary_tokens": budget.tokens_of("glossary"),
                        "spec_tokens": budget.tokens_of("spec.digest"),
                        "format_notes_tokens": budget.tokens_of("format.notes"),
                        "instruction_tokens": budget.tokens_of(
                            "system.role", "task.rules", "policy.terminology", "context.hint"
                        ),
                        "prompt_tokens": budget.total,
                        "prompt_tokens_without_format_instructions": budget.without(
                            "spec.digest", "format.notes"
                        ),
                        "characters": sum(
                            item.characters for item in budget.components if item.id == "document"
                        ),
                    }
                )
    return rows


def _blank(corpus_file: CorpusFile, arm: Arm) -> Any:
    from .formats.arms import project

    return project(corpus_file.document, arm, blank=True)
