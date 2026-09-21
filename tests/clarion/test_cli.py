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

import pytest

from clarion.cli import build_parser, main

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
