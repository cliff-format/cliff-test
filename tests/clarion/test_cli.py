"""The command surface: every subcommand parses, and the offline ones run.

`clarion/cli.py` is a quarter of the harness by size and had no test, so a broken
`add_argument`, a renamed subcommand or a dispatch typo would only be found by
running the tool by hand. Two things are asserted here:

* **the surface** - every top-level command answers `--help` with exit 0, and the
  list of commands is compared against a written-down set, so adding one is a
  deliberate act rather than a silent gap in coverage;
* **the offline commands** - `corpus validate`, `corpus stats` and `secret-scan`
  run end to end with no model and no network, which also exercises the corpus
  lint and the credential scan behind them.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from clarion.cli import build_parser, main
from clarion.prompts import cliff_rules

#: The top-level commands. Adding one without adding it here fails the surface
#: test below, which is the point: a command nobody tests is a command nobody
#: notices is broken.
COMMANDS = (
    "corpus",
    "fidelity",
    "glossary",
    "pipeline",
    "retry",
    "robustness",
    "secret-scan",
    "selfcheck",
    "tokens",
    "translate",
)

METAVAR_RE = re.compile(r"\{([a-z0-9_,-]+)\}")


def test_the_command_list_is_the_one_this_suite_covers() -> None:
    parser = build_parser()
    match = METAVAR_RE.search(parser.format_help())
    assert match is not None, "the root parser no longer lists its subcommands"
    listed = tuple(sorted(match.group(1).split(",")))
    assert listed == tuple(sorted(COMMANDS)), (
        f"the CLI offers {listed}; this suite covers {tuple(sorted(COMMANDS))}. "
        "Add the command to COMMANDS (and test it) or remove it from the CLI."
    )


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_answers_help(command: str, capsys) -> None:
    """A subcommand whose arguments cannot be built is a broken release."""
    with pytest.raises(SystemExit) as exit_info:
        main([command, "--help"])
    assert exit_info.value.code == 0
    assert command in capsys.readouterr().out


def test_corpus_subcommands_are_reachable() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["corpus", "--help"])
    assert exit_info.value.code == 0


def test_an_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["translat"])  # a plausible typo for 'translate'
    assert exit_info.value.code != 0


def test_no_command_is_an_error_rather_than_a_silent_success() -> None:
    """`required=True` on the subparsers: a bare `clarion` must not exit 0."""
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code != 0


def test_corpus_validate_runs_offline_and_reports_the_whole_corpus(capsys) -> None:
    """The strictest offline command: every document, with lint and gold checks."""
    code = main(["corpus", "validate"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "files," in out and "problems" in out, out
    # The summary is the claim: 16 documents, 392 entries, no problems.
    assert "0 problems" in out, out


def test_corpus_stats_runs_offline(capsys) -> None:
    code = main(["corpus", "stats"])
    out = capsys.readouterr().out
    assert code == 0, out
    # The manifest's display name and the corpus figures, which the summary line
    # states together: 'CLARION-Core 0.3.0: 16 files, 392 entries'.
    assert "CLARION-Core" in out, out
    assert "16 files, 392 entries" in out, out


def test_secret_scan_reports_a_clean_tree(capsys) -> None:
    """The gate the project runs before a push, exercised as the user runs it."""
    code = main(["secret-scan"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "0 findings" in out, out


def test_selfcheck_runs_the_whole_chain_offline() -> None:
    """The project's own end-to-end gate, through the CLI, with no model calls.

    It is the only check that exercises the corpus, the formats, the metrics and
    the report together, and CI runs it as `python -m clarion selfcheck`. Having it
    here as well means a developer who runs `pytest` finds out before pushing.
    """
    assert main(["selfcheck", "--quiet"]) == 0


def test_the_final_measurement_command_runs_end_to_end(monkeypatch) -> None:
    """`translate --formats cliff` is the command the final measurement uses.

    It is run here against a recording provider, so the paid run cannot fail on
    plumbing - the argument override, the matrix, the report - and so the two
    settings that decide what the number *means* are asserted rather than assumed:
    the temperature that reaches the wire, and the prompt style in the system
    message. Both have been wrong before: the edit path sent 0.0 for its whole
    history while the configuration said 1.3, and the run directory could not show
    it.
    """
    import clarion.cli as cli_module
    import clarion.runner as runner_module
    from clarion.config import ProviderConfig, RunConfig
    from clarion.providers.base import Completion, CompletionRequest
    from clarion.providers.mock import MockProvider
    from clarion.runner import RunPaths

    sandbox = Path(__file__).resolve().parent / "_cli_run_sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True, exist_ok=True)
    original_create = RunPaths.create
    monkeypatch.setattr(
        cli_module.RunPaths,
        "create",
        staticmethod(lambda name, base=None: original_create(name, base=sandbox)),
    )

    class Recording:
        name = "recording"
        model = "mock-1"

        def __init__(self) -> None:
            self.inner = MockProvider(mode="perfect", model="mock-1")
            self.requests: list[CompletionRequest] = []

        def complete(self, request: CompletionRequest) -> Completion:
            self.requests.append(request)
            return self.inner.complete(request)

    provider = Recording()
    config = RunConfig(
        name="final-dry-run",
        corpus="clarion-core",
        formats=["cliff"],
        arms=["bare", "context"],
        repeats=1,
        isolation="per-task",
        concurrency=1,
        prompt_style="spec",
        provider=ProviderConfig(
            kind="openai",
            model="deepseek-flash",
            temperature=1.3,
            api_key_env="TEST_API_KEY",
        ),
    )
    monkeypatch.setattr(cli_module, "load_config", lambda *_a, **_k: config)
    monkeypatch.setattr(runner_module, "build_provider", lambda _config: provider)

    try:
        assert main(["translate", "--formats", "cliff"]) == 0

        # The override took effect: one format, both arms, one repeat.
        assert len(provider.requests) == 32, f"{len(provider.requests)} calls, expected 16 x 2"
        assert {request.temperature for request in provider.requests} == {1.3}, (
            "the temperature the configuration names must be the one on the wire"
        )
        # Marked by the specification block's own title line, read from the module: a
        # literal heading here went stale when the block was retitled, and a stale
        # literal in an assertion is worse than no assertion (it was "FIELD NAMES AND
        # THEIR SCOPE" and the block now opens "KEYS AND THEIR SCOPE").
        digest_title = cliff_rules.build_normative_rules().splitlines()[0]
        assert all(
            digest_title in request.messages[0].content
            for request in provider.requests
        ), "prompt_style=spec must put the compressed specification in every system message"

        run_dir = next(path for path in sandbox.iterdir() if path.is_dir())
        report = (run_dir / "report.md").read_text(encoding="utf-8")
        assert "- Formats: cliff" in report, "the report must name the formats that ran"
        assert "xliff" not in report, "a format that was not run must not appear"
        assert "structural integrity" in report, (
            "the modification-correctness table is the point of this run"
        )
        assert (run_dir / "records.jsonl").is_file()
        # The header has to name the regime that produced the numbers. It said
        # "production digest" for every run, including this one, whose
        # configuration - and whose prompts - are the compressed specification.
        assert "- CLIFF specification injection: spec" in report, report[:400]
    finally:
        if sandbox.exists():
            shutil.rmtree(sandbox)


def test_one_variable_can_be_overridden_without_editing_a_configuration() -> None:
    """`--prompt-style` and `--temperature` exist to separate confounded variables.

    Every run recorded before these flags existed changed temperature and prompt
    content together - each 0.0 condition also carried the full specification text -
    so no temperature claim could be tested against them. Switching one variable
    meant writing a new configuration file, and a run directory records the file it
    was started with, so two conditions could not be shown to differ in one thing.
    """
    from clarion.cli import _config_from_args, build_parser

    parser = build_parser()
    base = parser.parse_args(["pipeline", "--config", "configs/deepseek-flash.json"])
    baseline = _config_from_args(base)
    assert baseline.provider.temperature == 1.3  # what the shipped config names
    assert baseline.provider.reasoning == "low"  # the shipped decoder regime
    assert baseline.prompt_style == "spec"

    args = parser.parse_args(
        [
            "pipeline",
            "--config",
            "configs/deepseek-flash.json",
            "--prompt-style",
            "examples",
            "--temperature",
            "0.0",
            "--reasoning",
            "off",
        ]
    )
    overridden = _config_from_args(args)
    assert overridden.prompt_style == "examples"
    assert overridden.provider.temperature == 0.0
    assert overridden.provider.reasoning == "off"
    # One variable at a time means the rest of the provider block survives.
    assert overridden.provider.model == baseline.provider.model
    assert overridden.provider.max_output_tokens == baseline.provider.max_output_tokens
    assert overridden.formats == baseline.formats


def test_the_reasoning_tier_reaches_the_vendor_payload() -> None:
    """The switch has to become the field DeepSeek understands, not a comment."""
    from clarion.providers.openai_compat import reasoning_body

    assert reasoning_body("off", "deepseek-flash") == {"thinking": {"type": "disabled"}}
    assert reasoning_body("low", "deepseek-flash") == {
        "thinking": {"type": "enabled", "effort": "low"}
    }
    assert reasoning_body("medium", "deepseek-flash") == {
        "thinking": {"type": "enabled", "effort": "medium"}
    }
    # Other vendors take an effort field with their own spelling of "none".
    assert reasoning_body("low", "gpt-5") == {"reasoning_effort": "low"}
    assert reasoning_body("off", "gpt-5") == {"reasoning_effort": "none"}
    # "auto" leaves the decision to the endpoint rather than guessing.
    assert reasoning_body("auto", "deepseek-flash") == {}
