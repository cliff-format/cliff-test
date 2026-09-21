"""Price the CLIFF prompt styles, per component and per pilot file.

This is the instrument behind the cost table in `docs/clarion-prompt-design.md`,
and it is in the repository because the table's numbers are quoted in the
changelog and in the acceptance criteria: a number a reader cannot reproduce is a
number they have to take on trust. (The pilot's own script stayed in the working
copy; this one did not, for the same reason `tools/compare_readings.py` moved.)

All three styles are assembled by `build_translation_prompt` - the call path a run
uses - so what is measured is what would be sent. That includes `spec`, the style
the shipped configuration selects: a table that priced the two styles the run does
*not* send was the one gap in this project's rule that every published token
number comes from an in-repo tool. The earlier version of this measurement
projected the example-driven side by subtracting component totals and adding back
the module strings; that silently drifted as soon as the assembly changed
(dropping `format.notes` for the example-driven style, for instance).

Usage:
    python tools/prompt_cost.py                              # the published cell
    python tools/prompt_cost.py --file wmt24pp --arm context
    python tools/prompt_cost.py --pilot                      # per-file saving
    python tools/prompt_cost.py --block-delta                # vs the last commit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cliff-python" / "src"))
sys.path.insert(0, str(ROOT))

#: The files the prompt pilots ran over, in the order the pilot documents them.
PILOT_FILES = ("ui-console", "ui-workbench", "wmt24pp", "probe-ambiguity")

STYLES = ("digest", "examples", "spec")


def build_bundles(file_id: str, arm: str, config_path: Path):
    """Assemble both prompt styles for one cell, through the run's own call path."""
    from clarion.config import load_config
    from clarion.corpus.store import load_corpus
    from clarion.formats.arms import Arm
    from clarion.formats.render import render_document
    from clarion.metrics.terminology import load_policy
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts.assembly import build_translation_prompt
    from clarion.runner import _blank

    config = load_config(config_path)
    corpus = load_corpus(config.corpus)
    corpus_file = next(item for item in corpus.files if item.id == file_id)
    arm_value = Arm(arm)
    tokenizer = get_tokenizer(config.tokenizer)
    policy = load_policy(config.target_language)
    document = _blank(corpus_file, arm_value)
    document_text = render_document(document, "cliff", arm=arm_value)

    bundles = {}
    for style in STYLES:
        bundles[style] = build_translation_prompt(
            document_text=document_text,
            format_id="cliff",
            tokenizer=tokenizer,
            source_language=corpus_file.source_language,
            target_language=corpus_file.target_language,
            arm=arm_value.value,
            spec_location=config.spec_location,
            spec_reference=config.spec_reference,
            glossary_text="",
            policy_fragment=policy.prompt_fragment() if config.include_policy else "",
            document=document,
            allow_glossary_output=config.allow_glossary_output,
            workflow_style=config.workflow_style,
            prompt_style=style,
        )
    return tokenizer, bundles


def cell_table(file_id: str, arm: str, config_path: Path, styles: tuple[str, ...]) -> int:
    tokenizer, bundles = build_bundles(file_id, arm, config_path)
    print(f"cell: {file_id} / cliff / {arm}   tokenizer: {tokenizer.name}")
    header = f"{'component':<22}{'role':<8}" + "".join(f"{style:>11}" for style in styles)
    print(header)
    print("-" * len(header))

    # A component is reported once per role it appears in, so a block that moves
    # between messages (the split digest does) cannot hide behind a merged row.
    rows: list[tuple[str, str]] = []
    for style in styles:
        for component in bundles[style].budget.components:
            key = (component.id, component.role)
            if key not in rows:
                rows.append(key)

    def count(style: str, name: str, role: str) -> int:
        return sum(
            c.tokens for c in bundles[style].budget.components if c.id == name and c.role == role
        )

    for name, role in rows:
        counts = [count(style, name, role) for style in styles]
        if not any(counts):
            continue
        print(f"{name:<22}{role:<8}" + "".join(f"{value:>11}" for value in counts))
    print("-" * len(header))
    totals = [bundles[style].budget.total for style in styles]
    print(f"{'TOTAL':<22}{'':<8}" + "".join(f"{value:>11}" for value in totals))
    if "digest" in styles and "examples" in styles:
        saving = totals[styles.index("digest")] - totals[styles.index("examples")]
        share = 100.0 * saving / totals[0]
        print(f"\nsaving per call: {saving} tokens ({share:.1f}% of the prompt)")
    print(
        "each column adds up to its total: the rows are the blocks of that one message "
        "pair, not a selection of them."
    )
    return 0


def pilot_table(arm: str, config_path: Path, styles: tuple[str, ...]) -> int:
    columns = "".join(f"{style:>11}" for style in styles)
    header = f"{'file':<18}{columns}{'saving':>9}{'%':>7}"
    print(f"the four pilot files, arm '{arm}', every prompt style")
    print(header)
    print("-" * len(header))
    totals = dict.fromkeys(styles, 0)
    for file_id in PILOT_FILES:
        _, bundles = build_bundles(file_id, arm, config_path)
        costs = {style: bundles[style].budget.total for style in styles}
        for style in styles:
            totals[style] += costs[style]
        saving = costs["digest"] - costs["examples"]
        print(
            f"{file_id:<18}"
            + "".join(f"{costs[style]:>11}" for style in styles)
            + f"{saving:>9}{100.0 * saving / costs['digest']:>6.1f}%"
        )
    saving = totals["digest"] - totals["examples"]
    print("-" * len(header))
    print(
        f"{'TOTAL':<18}"
        + "".join(f"{totals[style]:>11}" for style in styles)
        + f"{saving:>9}{100.0 * saving / totals['digest']:>6.1f}%"
    )
    print(
        "\nthe saving column compares the two styles the redesign replaces; repeats add no "
        "prompt cost, because the prompt is rebuilt per cell, not per sample."
    )
    return 0


def decomposition_table(config_path: Path) -> int:
    """The compressed block, part by part, as the design document publishes it."""
    from clarion.config import load_config
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts import cliff_rules

    config = load_config(config_path)
    tokenizer = get_tokenizer(config.tokenizer)
    parts = cliff_rules.block_decomposition(tokenizer)
    block = tokenizer.count(cliff_rules.build_normative_rules())
    print(f"the `spec` block, per part   tokenizer: {tokenizer.name}")
    print(f"{'part':<24}{'tokens':>9}")
    print("-" * 33)
    for label, cost in parts.items():
        print(f"{label:<24}{cost:>9}")
    print("-" * 33)
    print(f"{'sum of the parts':<24}{sum(parts.values()):>9}")
    print(f"{'the block as sent':<24}{block:>9}")
    print(
        "\neach part is measured on its own, so the parts do not sum to the block: a token "
        "boundary at a join is shared."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/deepseek-flash.json")
    parser.add_argument("--file", default="ui-console")
    parser.add_argument("--arm", default="bare")
    parser.add_argument("--pilot", action="store_true", help="per-file saving, four pilot files")
    parser.add_argument(
        "--decomposition",
        action="store_true",
        help="the compressed specification block, part by part",
    )
    parser.add_argument(
        "--styles",
        default=",".join(STYLES),
        help=f"comma-separated styles to price (default: {','.join(STYLES)})",
    )
    parser.add_argument(
        "--block-delta",
        action="store_true",
        help="per-block token delta against the previous revision in git",
    )
    args = parser.parse_args(argv)
    config_path = ROOT / args.config
    styles = tuple(part.strip() for part in args.styles.split(",") if part.strip())
    unknown = [style for style in styles if style not in STYLES]
    if unknown:
        parser.error(f"unknown prompt style(s) {', '.join(unknown)}; known: {', '.join(STYLES)}")

    if args.block_delta:
        from prompt_block_delta import main as delta_main

        return delta_main([])
    if args.decomposition:
        return decomposition_table(config_path)
    if args.pilot:
        return pilot_table(args.arm, config_path, styles)
    return cell_table(args.file, args.arm, config_path, styles)


if __name__ == "__main__":
    raise SystemExit(main())
