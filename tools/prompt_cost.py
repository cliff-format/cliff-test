"""Price the CLIFF prompt styles, per component and per pilot file.

This is the instrument behind the cost table in `docs/clarion-prompt-design.md`,
and it is in the repository because the table's numbers are quoted in the
changelog and in the acceptance criteria: a number a reader cannot reproduce is a
number they have to take on trust. (The pilot's own script stayed in the working
copy; this one did not, for the same reason `tools/compare_readings.py` moved.)

Both styles are assembled by `build_translation_prompt` - the call path a run
uses - so what is measured is what would be sent. The earlier version of this
measurement projected the example-driven side by subtracting component totals and
adding back the module strings; that silently drifted as soon as the assembly
changed (dropping `format.notes` for the example-driven style, for instance).

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

STYLES = ("digest", "examples")


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


def cell_table(file_id: str, arm: str, config_path: Path) -> int:
    tokenizer, bundles = build_bundles(file_id, arm, config_path)
    print(f"cell: {file_id} / cliff / {arm}   tokenizer: {tokenizer.name}")
    header = f"{'component':<22}{'role':<8}{'digest':>9}{'examples':>10}"
    print(header)
    print("-" * len(header))

    # A component is reported once per role it appears in, so a block that moves
    # between messages (the split digest does) cannot hide behind a merged row.
    rows: list[tuple[str, str]] = []
    for style in STYLES:
        for component in bundles[style].budget.components:
            key = (component.id, component.role)
            if key not in rows:
                rows.append(key)

    def count(style: str, name: str, role: str) -> int:
        return sum(
            c.tokens for c in bundles[style].budget.components if c.id == name and c.role == role
        )

    for name, role in rows:
        counts = [count(style, name, role) for style in STYLES]
        if not any(counts):
            continue
        print(f"{name:<22}{role:<8}{counts[0]:>9}{counts[1]:>10}")
    print("-" * len(header))
    totals = [bundles[style].budget.total for style in STYLES]
    print(f"{'TOTAL':<22}{'':<8}{totals[0]:>9}{totals[1]:>10}")
    saving = totals[0] - totals[1]
    print(f"\nsaving per call: {saving} tokens ({100.0 * saving / totals[0]:.1f}% of the prompt)")
    print(
        "each column adds up to its total: the rows are the blocks of that one message "
        "pair, not a selection of them."
    )
    return 0


def pilot_table(arm: str, config_path: Path) -> int:
    header = f"{'file':<18}{'digest':>9}{'examples':>10}{'saving':>9}{'%':>7}"
    print(f"the four pilot files, arm '{arm}', both styles")
    print(header)
    print("-" * len(header))
    totals = dict.fromkeys(STYLES, 0)
    for file_id in PILOT_FILES:
        _, bundles = build_bundles(file_id, arm, config_path)
        costs = {style: bundles[style].budget.total for style in STYLES}
        for style in STYLES:
            totals[style] += costs[style]
        saving = costs["digest"] - costs["examples"]
        print(
            f"{file_id:<18}{costs['digest']:>9}{costs['examples']:>10}"
            f"{saving:>9}{100.0 * saving / costs['digest']:>6.1f}%"
        )
    saving = totals["digest"] - totals["examples"]
    print("-" * len(header))
    print(
        f"{'TOTAL':<18}{totals['digest']:>9}{totals['examples']:>10}"
        f"{saving:>9}{100.0 * saving / totals['digest']:>6.1f}%"
    )
    print("\nrepeats add no prompt cost: the prompt is rebuilt per cell, not per sample.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/deepseek-flash.json")
    parser.add_argument("--file", default="ui-console")
    parser.add_argument("--arm", default="bare")
    parser.add_argument("--pilot", action="store_true", help="per-file saving, four pilot files")
    parser.add_argument(
        "--block-delta",
        action="store_true",
        help="per-block token delta against the last commit (working copy only)",
    )
    args = parser.parse_args(argv)
    config_path = ROOT / args.config

    if args.block_delta:
        from prompt_block_delta import main as delta_main

        return delta_main([])
    if args.pilot:
        return pilot_table(args.arm, config_path)
    return cell_table(args.file, args.arm, config_path)


if __name__ == "__main__":
    raise SystemExit(main())
