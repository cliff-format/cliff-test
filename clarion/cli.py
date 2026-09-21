"""Command line interface for CLARION.

    python -m clarion corpus validate
    python -m clarion corpus stats
    python -m clarion tokens --out results/tokens.md
    python -m clarion fidelity
    python -m clarion translate --config configs/deepseek-flash.json
    python -m clarion robustness --deterministic
    python -m clarion glossary bootstrap path/to/file.cliff
    python -m clarion selfcheck
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import FULL_NAME, NAME, __version__
from .config import RunConfig, load_config
from .corpus.lint import lint_file
from .corpus.store import load_corpus
from .formats.read_mode import READ_MODES
from .formats.registry import FORMATS
from .metrics.terminology import load_policy
from .metrics.tokens import get_tokenizer
from .paths import RESULTS_ROOT, ensure_cliff_format, pycliff_version
from .prompts.assembly import PROMPT_STYLES
from .report import build_report, fidelity_report, token_report
from .runner import (
    RunPaths,
    run_fidelity_matrix,
    run_robustness_matrix,
    run_translation_matrix,
    token_matrix,
)
from .selfcheck import run_selfcheck
from .util import dump_json, write_text


def _config_from_args(args: argparse.Namespace) -> RunConfig:
    overrides: dict[str, Any] = {}
    if getattr(args, "formats", None):
        overrides["formats"] = list(args.formats)
    if getattr(args, "arms", None):
        overrides["arms"] = list(args.arms)
    if getattr(args, "strata", None):
        overrides["strata"] = list(args.strata)
    if getattr(args, "corpus", None):
        overrides["corpus"] = args.corpus
    if getattr(args, "tokenizer", None):
        overrides["tokenizer"] = args.tokenizer
    if getattr(args, "repeats", None):
        overrides["repeats"] = args.repeats
    if getattr(args, "read_mode", None):
        overrides["read_mode"] = args.read_mode
    if getattr(args, "prompt_style", None):
        # A prompt style is an experimental condition, and the configuration file is
        # the wrong place to switch one: a run directory records the configuration it
        # was started with, so an override here is what keeps two styles comparable
        # within one session. The run still records the value it used.
        overrides["prompt_style"] = args.prompt_style
    provider_override: dict[str, Any] = {}
    if getattr(args, "temperature", None) is not None:
        # Same reason, and it is the variable that has to be separated from the
        # prompt content: every run recorded before this flag existed changed both
        # at once (0.0 always came with the full specification text), so a
        # temperature claim could not be tested against them.
        provider_override["temperature"] = args.temperature
    if getattr(args, "reasoning", None):
        # The decoder regime as a whole: with a thinking tier selected the vendor
        # controls sampling itself, so this is the lever that is left when prompt
        # content and temperature have both been shown not to move a number.
        provider_override["reasoning"] = args.reasoning
    if provider_override:
        overrides["provider"] = provider_override
    return load_config(getattr(args, "config", None), **overrides)


def cmd_corpus_validate(args: argparse.Namespace) -> int:
    """Validate every corpus document with the official CLIFF validator."""
    ensure_cliff_format()
    import cliff_format

    corpus = load_corpus(args.corpus, strata=args.strata or None)
    failures = 0
    for corpus_file in corpus.files:
        issues = cliff_format.validate(corpus_file.path.read_text(encoding="utf-8"))
        errors = [issue for issue in issues if issue.category not in {"warning", "extension"}]
        missing_gold = [
            entry_id
            for entry_id in corpus_file.sources()
            if entry_id not in corpus_file.gold and not corpus_file.references().get(entry_id)
        ]
        known = corpus_file.sources()
        stray_gold = [entry_id for entry_id in corpus_file.gold if entry_id not in known]
        state = "VALID" if not errors else "INVALID"
        print(f"{corpus_file.path.name}: {state} ({corpus_file.entry_count} entries)")
        for issue in errors:
            print(f"  {issue.line}: [{issue.category}] {issue.message}")
        for entry_id in stray_gold:
            print(f"  gold manifest references unknown entry '{entry_id}'")
        for entry_id in missing_gold:
            print(f"  entry '{entry_id}' has no reference translation")
        lint = lint_file(corpus_file)
        for finding in lint:
            print(f"  [{finding.kind}] {finding.entry}: {finding.detail[:110]}")
        failures += len(errors) + len(stray_gold) + len(missing_gold) + len(lint)
    print(f"\n{len(corpus.files)} files, {corpus.entry_count()} entries, {failures} problems")
    return 0 if failures == 0 else 1


def cmd_corpus_stats(args: argparse.Namespace) -> int:
    """Summarize the corpus: size, licences, human verification, contamination."""
    corpus = load_corpus(args.corpus, strata=args.strata or None)
    print(
        f"{corpus.name} {corpus.version}: "
        f"{len(corpus.files)} files, {corpus.entry_count()} entries"
    )
    print()
    print(
        f"{'stratum':<10}{'file':<28}{'entries':>8}{'verified':>9}  "
        f"{'origin':<10}{'context':<11}license"
    )
    for corpus_file in corpus.files:
        verified = sum(
            1
            for gold in corpus_file.gold.values()
            if gold.provenance and gold.provenance.human_verified
        )
        blocks = [gold.provenance for gold in corpus_file.gold.values() if gold.provenance]
        if corpus_file.provenance:
            blocks.append(corpus_file.provenance)
        origin_text = "/".join(sorted({block.origin for block in blocks})) or "-"
        context_text = "/".join(sorted({block.context_origin for block in blocks})) or "-"
        license_text = "/".join(sorted({block.license for block in blocks})) or "-"
        print(
            f"{corpus_file.stratum:<10}{corpus_file.path.name:<28}{corpus_file.entry_count:>8}"
            f"{verified:>9}  {origin_text:<10}{context_text:<11}{license_text}"
        )
    return 0


def cmd_corpus_recipes(args: argparse.Namespace) -> int:
    """List the external corpora CLARION knows how to import."""
    from .corpus.fetchers import load_recipes

    print(f"{'id':<20}{'tier':<13}{'context':<10}{'licence':<26}strata")
    for recipe in load_recipes():
        print(
            f"{recipe.id:<20}{recipe.tier:<13}{recipe.context_origin:<10}"
            f"{recipe.license[:24]:<26}{', '.join(recipe.strata)}"
        )
    print(
        "\ntier vendor: may be committed with attribution; sharealike: segregated under its own "
        "licence; fetch-only: never committed."
    )
    print(
        "context native: the upstream project wrote the translator brief; derived: computed "
        "deterministically from document ids, domains and neighbouring segments; none: no "
        "context, plain arm only. Add --annotate to have a model write a brief for a derived "
        "source (marked as annotated until a human signs it off)."
    )
    return 0


def cmd_corpus_fetch(args: argparse.Namespace) -> int:
    """Import an external corpus through its recipe.

    A sentence-pair corpus becomes a CLARION corpus here: pairs to CLIFF,
    deterministic enrichment, an optional annotation pass, then the licence
    header, checksums and attribution that make it publishable.
    """
    from .corpus.annotate import AnnotationConfig
    from .corpus.fetchers import fetch
    from .providers import build_provider

    config = _config_from_args(args)
    annotator = None
    annotation_config = None
    if args.annotate:
        provider_config = replace(
            config.provider,
            reasoning="off",
            max_output_tokens=max(8192, config.provider.max_output_tokens),
        )
        if args.annotator_model:
            provider_config = replace(provider_config, model=args.annotator_model)
        annotator = build_provider(provider_config)
        annotation_config = AnnotationConfig(
            summarize=not args.no_summary,
            propose_width=args.propose_width,
            batch_size=args.batch_size,
        )
        if provider_config.model == config.provider.model and config.provider.kind != "mock":
            print(
                "warning: the annotator and the system under test are the same model; "
                "prefer --annotator-model with a different one, and report the pairing"
            )
    try:
        result = fetch(
            args.recipe,
            stratum=args.stratum,
            limit=args.limit,
            annotator=annotator,
            annotation_config=annotation_config,
            revision=args.revision or "",
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001 - report the reason, do not traceback
        print(f"fetch failed: {type(exc).__name__}: {exc}")
        return 1
    print(f"{result.recipe_id}: {result.entries} entries -> {result.cliff_path}")
    print(f"tier {result.tier}; committed to the repository: {result.committed}")
    print(f"context origin: {result.context_origin}{' (cached)' if result.cached else ''}")
    if result.cached:
        print("nothing was downloaded or paid for; pass --force to rebuild")
        return 0
    if result.enrichment:
        data = result.enrichment.as_dict()
        print(
            f"enrichment: {data['group_context']} group contexts, "
            f"{data['entry_context']} entry contexts, {data['types_assigned']} types, "
            f"{data['icu_detected']} placeholder notes"
        )
    if result.annotation:
        data = result.annotation.as_dict()
        print(
            f"annotation by {data['model']}: {data['annotated']}/{data['requested']} entries, "
            f"family brief {data['wrote_family_brief']}, {data['summarized_groups']} group briefs"
        )
        print(
            f"rejected: {data['rejected_leak']} leaky contexts, "
            f"{data['rejected_type']} bad types, {data['rejected_emotion']} bad emotions, "
            f"{data['rejected_width']} impossible widths"
        )
        print("annotated context is a hypothesis: run 'clarion corpus review' before publishing")
    return 0


def cmd_corpus_license_check(args: argparse.Namespace) -> int:
    """Verify that everything committed under datasets/ may be committed."""
    from .corpus.licensing import license_check

    problems = license_check()
    for problem in problems:
        print(f"{problem.path}: {problem.problem}")
    print(f"\n{len(problems)} licence problems")
    return 0 if not problems else 1


def cmd_corpus_review(args: argparse.Namespace) -> int:
    """Export a human review sheet for a corpus (CSV)."""
    import csv
    import io

    from .corpus.annotate import review_rows

    corpus = load_corpus(args.corpus, strata=args.strata or None)
    buffer = io.StringIO()
    writer: csv.DictWriter[str] | None = None
    count = 0
    for corpus_file in corpus.files:
        for row in review_rows(corpus_file.document):
            row["file"] = corpus_file.path.name
            provenance = corpus_file.provenance
            row["context_origin"] = provenance.context_origin if provenance else "original"
            if writer is None:
                writer = csv.DictWriter(buffer, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            count += 1
    output = Path(args.out or "results/clarion-review.csv")
    write_text(output, buffer.getvalue())
    print(f"{count} rows written to {output}")
    print("Fill in 'approved' and 'reviewer', then set human_verified in the gold manifests.")
    return 0


def cmd_tokens(args: argparse.Namespace) -> int:
    """Dimensions 1 and 2: token cost per format, with no model calls."""
    config = _config_from_args(args)
    corpus = load_corpus(config.corpus, strata=config.strata or None)
    tokenizer = get_tokenizer(config.tokenizer)
    policy = load_policy(config.target_language)
    rows = token_matrix(config, corpus, tokenizer=tokenizer, policy=policy)
    text = "\n".join(
        [
            f"# {NAME} token cost",
            "",
            f"Corpus: {corpus.name} {corpus.version} ({len(corpus.files)} files, "
            f"{corpus.entry_count()} entries). Tokenizer: {tokenizer.name}.",
            "",
            token_report(rows, arm="bare", title="D1 - token cost, plain formats"),
            token_report(rows, arm="context", title="D2 - token cost, context-carrying formats"),
        ]
    )
    print(text)
    if args.out:
        write_text(Path(args.out), text)
        dump_json(Path(args.out).with_suffix(".json"), rows)
        print(f"written: {args.out}")
    return 0


def cmd_fidelity(args: argparse.Namespace) -> int:
    """Round-trip context retention per format."""
    config = _config_from_args(args)
    corpus = load_corpus(config.corpus, strata=config.strata or None)
    output = run_fidelity_matrix(config, corpus)
    print(fidelity_report(output.records))
    print(f"evidence: {output.paths.records}")
    return 0


def cmd_translate(args: argparse.Namespace) -> int:
    """Run the translation matrix (dimensions 1 to 6)."""
    config = _config_from_args(args)
    corpus = load_corpus(config.corpus, strata=config.strata or None)
    tokenizer = get_tokenizer(config.tokenizer)
    paths = RunPaths.create(config.name)
    tokens = token_matrix(config, corpus, tokenizer=tokenizer)
    output = run_translation_matrix(config, corpus, tokenizer=tokenizer, paths=paths)
    report = build_report(
        title=f"{NAME} run: {config.name}",
        config=config.as_dict(),
        token_rows=tokens,
        records=output.records,
    )
    write_text(paths.root / "report.md", report)
    dump_json(paths.root / "tokens.json", tokens)
    dump_json(
        paths.summary,
        {
            "corpus": corpus.name,
            "files": len(corpus.files),
            "entries": corpus.entry_count(),
            "records": output.count(),
            "cliff-python": pycliff_version(),
        },
    )
    print(report)
    print(f"evidence: {paths.records}")
    return 0


def cmd_robustness(args: argparse.Namespace) -> int:
    """Dimension 7: apply the same edits to every format and validate."""
    config = _config_from_args(args)
    corpus = load_corpus(config.corpus, strata=config.strata or None)
    output = run_robustness_matrix(
        config, corpus, edits=args.edits, use_model=not args.deterministic
    )
    from .report import robustness_report

    print(robustness_report(output.records))
    print(f"evidence: {output.paths.records}")
    return 0


def cmd_glossary(args: argparse.Namespace) -> int:
    """Mine, propose and merge a CLIFF glossary for a file."""
    ensure_cliff_format()
    import cliff_format

    from .providers import build_provider
    from .tools.glossary import attach_dependency, bootstrap

    config = _config_from_args(args)
    provider = build_provider(config.provider) if args.propose else None
    policy = load_policy(config.target_language)
    source_path = Path(args.file)
    glossary_path = Path(args.out) if args.out else source_path.with_name(
        source_path.name.split(".")[0] + "-terms." + config.target_language + ".cliff"
    )
    document, report, candidates = bootstrap(
        source_path,
        glossary_path=glossary_path,
        provider=provider,
        policy=policy,
        min_count=args.min_count,
    )
    write_text(glossary_path, cliff_format.serialize(document))
    print(f"terms mined: {len(candidates)}; added: {len(report.added)}; kept: {len(report.kept)}")
    for conflict in report.conflicts:
        print(f"  conflict: {conflict['term']} locked as {conflict['locked']}")
    print(f"glossary written: {glossary_path}")
    if args.attach:
        source_document = attach_dependency(cliff_format.load(source_path), glossary_path.name)
        write_text(source_path, cliff_format.serialize(source_document))
        print(f"dependency attached to {source_path.name}")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Download, brief, measure and report in one command."""
    from .pipeline import run_pipeline

    config = _config_from_args(args)
    if args.skip:
        config.pipeline.skip = list(args.skip)
    if args.edits is not None:
        config.pipeline.robustness_edits = args.edits
    return run_pipeline(config, verbose=not args.quiet)


def cmd_retry(args: argparse.Namespace) -> int:
    """Re-run only the failed cells of an existing run and rebuild its report."""
    from .config import from_dict
    from .runner import RunPaths, merge_records, rerun_failed
    from .util import load_json, read_jsonl

    run_dir = Path(args.run)
    config = from_dict(load_json(run_dir / "config.json"))
    records = read_jsonl(run_dir / "records.jsonl")
    failed = [r for r in records if r.get("kind") == "translation" and r.get("failed")]
    if not failed:
        print("nothing failed in that run")
        return 0
    print(f"re-running {len(failed)} failed cells of {run_dir.name}")

    corpus = load_corpus(config.corpus, strata=config.strata or None)
    paths = RunPaths(
        root=run_dir,
        records=run_dir / "records.jsonl",
        summary=run_dir / "summary.json",
        config=run_dir / "config.json",
    )

    def progress(done: int, total: int, record: dict[str, Any]) -> None:
        state = record.get("outcome")
        print(
            f"  {done}/{total} {record.get('file')}/{record.get('format')}/{record.get('arm')}"
            f": {record.get('previous_outcome')} -> {state}",
            flush=True,
        )

    repaired = rerun_failed(config, corpus, records, paths=paths, progress=progress)
    merged = merge_records(records, repaired)
    tokens = load_json(run_dir / "tokens.json") if (run_dir / "tokens.json").exists() else []
    report = build_report(
        title=f"{NAME} run (repaired): {config.name}",
        config=config.as_dict(),
        token_rows=tokens,
        records=merged,
    )
    write_text(run_dir / "report-retry.md", report)
    still_failing = [r for r in repaired if r.get("failed")]
    print(f"\nrepaired {len(repaired) - len(still_failing)} of {len(repaired)}")
    print(f"report: {run_dir / 'report-retry.md'}")
    return 0


def cmd_secret_scan(args: argparse.Namespace) -> int:
    """Prove the working tree carries no credential before a push."""
    from .secrets import scan_tree

    findings = scan_tree()
    for path, line in findings:
        print(f"{path}:{line}: credential-looking string")
    print(f"\n{len(findings)} findings")
    return 0 if not findings else 1


def cmd_selfcheck(args: argparse.Namespace) -> int:
    """Verify the whole harness offline with the deterministic mock provider."""
    return run_selfcheck(corpus_name=args.corpus, verbose=not args.quiet)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLARION argument parser."""
    parser = argparse.ArgumentParser(prog="clarion", description=f"{NAME}: {FULL_NAME}")
    parser.add_argument("--version", action="version", version=f"{NAME} {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--config", help="JSON or YAML run configuration")
        target.add_argument("--corpus", default="clarion-core")
        target.add_argument("--strata", nargs="*", help="restrict to these strata")
        target.add_argument("--formats", nargs="*", choices=sorted(FORMATS), default=None)
        target.add_argument("--arms", nargs="*", choices=["bare", "context"], default=None)
        target.add_argument("--tokenizer", default=None)
        target.add_argument("--repeats", type=int, default=None)
        target.add_argument(
            "--read-mode",
            dest="read_mode",
            choices=list(READ_MODES),
            default=None,
            help=(
                "how a CLIFF answer is read back: 'tolerant' applies the documented "
                "relaxations of specification Appendix C and counts each repair "
                "(default); 'strict' is the reference-toolchain reading"
            ),
        )
        target.add_argument(
            "--prompt-style",
            dest="prompt_style",
            choices=list(PROMPT_STYLES),
            default=None,
            help=(
                "how much CLIFF specification the prompt carries: 'digest' adds the "
                "full specification text, 'examples' states the repairable boundary "
                "with two conforming files, 'spec' carries the specification "
                "compressed to its normative content (ABNF, constraints, field "
                "tables, vocabularies). Defaults to the configuration's value."
            ),
        )
        target.add_argument(
            "--temperature",
            type=float,
            default=None,
            help=(
                "decoder temperature for this run, overriding the configuration. Use "
                "it to vary one variable at a time: the recorded runs did not, so "
                "their 0.0 conditions also carried a different prompt."
            ),
        )
        target.add_argument(
            "--reasoning",
            choices=("off", "low", "medium", "high"),
            default=None,
            help=(
                "thinking tier for this run, overriding the configuration: 'off' "
                "disables reasoning tokens, the others select an effort tier the "
                "vendor maps onto its own switch. With a tier selected the vendor "
                "controls sampling itself, so temperature stops being the variable "
                "that decides the output."
            ),
        )

    corpus_parser = subparsers.add_parser("corpus", help="corpus inspection")
    corpus_sub = corpus_parser.add_subparsers(dest="corpus_command", required=True)
    validate_parser = corpus_sub.add_parser("validate", help="validate every corpus document")
    validate_parser.add_argument("--corpus", default="clarion-core")
    validate_parser.add_argument("--strata", nargs="*")
    validate_parser.set_defaults(func=cmd_corpus_validate)
    stats_parser = corpus_sub.add_parser("stats", help="corpus size, licences and provenance")
    stats_parser.add_argument("--corpus", default="clarion-core")
    stats_parser.add_argument("--strata", nargs="*")
    stats_parser.set_defaults(func=cmd_corpus_stats)
    recipes_parser = corpus_sub.add_parser("recipes", help="list importable external corpora")
    recipes_parser.set_defaults(func=cmd_corpus_recipes)
    fetch_parser = corpus_sub.add_parser("fetch", help="import an external corpus by recipe id")
    add_common(fetch_parser)
    fetch_parser.add_argument("recipe")
    fetch_parser.add_argument("--stratum", default=None)
    fetch_parser.add_argument("--limit", type=int, default=200)
    fetch_parser.add_argument("--revision", default="", help="upstream commit or release to record")
    fetch_parser.add_argument(
        "--force", action="store_true", help="re-download and re-brief even when cached"
    )
    fetch_parser.add_argument(
        "--annotate",
        action="store_true",
        help="run the model annotation pass (writes context/type/emotion, never targets)",
    )
    fetch_parser.add_argument(
        "--annotator-model",
        dest="annotator_model",
        default=None,
        help="model that writes the brief; use a different one from the system under test",
    )
    fetch_parser.add_argument("--no-summary", dest="no_summary", action="store_true")
    fetch_parser.add_argument("--propose-width", dest="propose_width", action="store_true")
    fetch_parser.add_argument("--batch-size", dest="batch_size", type=int, default=12)
    fetch_parser.set_defaults(func=cmd_corpus_fetch)
    license_parser = corpus_sub.add_parser(
        "license-check", help="verify licences, attribution and tier routing"
    )
    license_parser.set_defaults(func=cmd_corpus_license_check)
    review_parser = corpus_sub.add_parser("review", help="export a human review sheet")
    review_parser.add_argument("--corpus", default="clarion-core")
    review_parser.add_argument("--strata", nargs="*")
    review_parser.add_argument("--out", default=None)
    review_parser.set_defaults(func=cmd_corpus_review)

    tokens_parser = subparsers.add_parser("tokens", help="dimensions 1 and 2 (no model calls)")
    add_common(tokens_parser)
    tokens_parser.add_argument("--out", help="write the Markdown report here")
    tokens_parser.set_defaults(func=cmd_tokens)

    fidelity_parser = subparsers.add_parser("fidelity", help="round-trip context retention")
    add_common(fidelity_parser)
    fidelity_parser.set_defaults(func=cmd_fidelity)

    translate_parser = subparsers.add_parser("translate", help="dimensions 1 to 6")
    add_common(translate_parser)
    translate_parser.set_defaults(func=cmd_translate)

    robustness_parser = subparsers.add_parser("robustness", help="dimension 7")
    add_common(robustness_parser)
    robustness_parser.add_argument("--edits", type=int, default=30)
    robustness_parser.add_argument(
        "--deterministic",
        action="store_true",
        help="apply edits with the reference implementation instead of a model",
    )
    robustness_parser.set_defaults(func=cmd_robustness)

    glossary_parser = subparsers.add_parser("glossary", help="glossary tooling")
    glossary_sub = glossary_parser.add_subparsers(dest="glossary_command", required=True)
    bootstrap_parser = glossary_sub.add_parser(
        "bootstrap", help="mine a glossary from a CLIFF file"
    )
    add_common(bootstrap_parser)
    bootstrap_parser.add_argument("file", help="CLIFF document to mine")
    bootstrap_parser.add_argument("--out", help="glossary path to write or merge into")
    bootstrap_parser.add_argument("--min-count", type=int, default=2, dest="min_count")
    bootstrap_parser.add_argument("--propose", action="store_true", help="ask for renderings")
    bootstrap_parser.add_argument("--attach", action="store_true", help="add a dependency line")
    bootstrap_parser.set_defaults(func=cmd_glossary)

    pipeline_parser = subparsers.add_parser(
        "pipeline", help="one command: fetch, brief, validate, measure, report"
    )
    add_common(pipeline_parser)
    pipeline_parser.add_argument("--skip", nargs="*", default=None)
    pipeline_parser.add_argument("--edits", type=int, default=None)
    pipeline_parser.add_argument("--quiet", action="store_true")
    pipeline_parser.set_defaults(func=cmd_pipeline)

    retry_parser = subparsers.add_parser("retry", help="re-run only the failed cells of a run")
    retry_parser.add_argument("--run", required=True, help="run directory to repair")
    retry_parser.set_defaults(func=cmd_retry)

    secret_parser = subparsers.add_parser("secret-scan", help="check the tree for credentials")
    secret_parser.set_defaults(func=cmd_secret_scan)

    selfcheck_parser = subparsers.add_parser("selfcheck", help="offline end-to-end verification")
    selfcheck_parser.add_argument("--corpus", default="clarion-core")
    selfcheck_parser.add_argument("--quiet", action="store_true")
    selfcheck_parser.set_defaults(func=cmd_selfcheck)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
