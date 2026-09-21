"""Token delta of every prompt block, working copy against a git revision.

The prompt is priced per block, not per prompt: a block that grows by 80 tokens
costs 80 tokens on every call of every format it reaches, and the important blocks
are shared - ``SYSTEM_ROLE`` and ``TASK_RULES`` reach all ten formats. Without this
the cost of a prompt edit is invisible until a run is paid for.

Usage: python tools/prompt_block_delta.py [<git-ref>]     # default HEAD
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cliff-python" / "src"))
sys.path.insert(0, str(ROOT))

#: Every module-level prompt string that reaches a model, by module. A new block
#: belongs here: an unpriced block is a block whose growth nobody sees.
BLOCKS = {
    "templates": (
        "SYSTEM_ROLE",
        "TASK_RULES",
        "OUTPUT_RULES_BILINGUAL",
        "OUTPUT_RULES_MONOLINGUAL",
        "CONTEXT_HINT",
        "GLOSSARY_DELIVERABLE",
        "GLOSSARY_WORKFLOW",
        "CLIFF_EDIT_SAFETY",
    ),
    "cliff_prompt_v2": ("CLIFF_FACTS", "CLIFF_TASK_RULES", "EXAMPLES"),
}


def block(source: str, name: str) -> str:
    """The literal body of a triple-quoted module-level string, or ""."""
    match = re.search(rf'^{name} = (?:f)?"""(.*?)"""', source, re.M | re.S)
    return match.group(1) if match else ""


def rendered(module_source: str, name: str) -> str:
    """The *value* of a module-level string, with f-string placeholders filled in.

    Reading the source text instead compares a template against a rendered string:
    ``CLIFF_FACTS`` holds ``{_row(...)}`` calls that the source spells out and the
    value does not, so the source-text comparison reported a 107-token difference
    where the rendered difference was zero. Executing the revision is what makes the
    number the number.
    """
    namespace: dict[str, object] = {}
    try:
        exec(compile(module_source, "<previous revision>", "exec"), namespace)  # noqa: S102
    except Exception:  # pragma: no cover - a revision with imports or side effects
        return block(module_source, name)
    value = namespace.get(name)
    return value if isinstance(value, str) else block(module_source, name)


def main(argv: list[str]) -> int:
    ref = argv[0] if argv else "HEAD"
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts import cliff_prompt_v2, templates

    tokenizer = get_tokenizer("o200k_base")
    print(f"{'block':<26}{'before':>8}{'after':>8}{'delta':>8}")
    print("-" * 50)
    net = 0
    for module_name, names in BLOCKS.items():
        current = templates if module_name == "templates" else cliff_prompt_v2
        previous = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{ref}:clarion/prompts/{module_name}.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
        for name in names:
            before = tokenizer.count(rendered(previous, name)) if previous else 0
            after = tokenizer.count(getattr(current, name))
            net += after - before
            marker = "" if before == after else "  <-- changed"
            print(f"{name:<26}{before:>8}{after:>8}{after - before:>+8}{marker}")
    print("-" * 50)
    print(f"{'net, per call':<26}{'':<8}{'':<8}{net:>+8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
