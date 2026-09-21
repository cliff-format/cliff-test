"""Token delta of every prompt block, working copy against a git revision.

The prompt is priced per block, not per prompt: a block that grows by 80 tokens
costs 80 tokens on every call of every format it reaches, and the important blocks
are shared - ``SYSTEM_ROLE`` and ``TASK_RULES`` reach all ten formats. Without this
the cost of a prompt edit is invisible until a run is paid for.

Three kinds of block are priced, and every one of them can reach a model:

* module-level strings (``templates``, ``cliff_prompt_v2``, ``cliff_rules``);
* strings assembled by a function, named with a trailing ``()`` - the compressed
  specification is the one that matters, and it is the block whose growth this tool
  exists to catch;
* prompt material that lives in a file rather than in a module, priced by content.

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

#: Every prompt block that reaches a model, by module. A new block belongs here: an
#: unpriced block is a block whose growth nobody sees. A name ending in ``()`` is
#: called rather than read.
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
        "CLIFF_ANSWER_REMINDER",
    ),
    "cliff_prompt_v2": ("CLIFF_FACTS", "CLIFF_TASK_RULES", "EXAMPLES"),
    "cliff_rules": (
        "build_normative_rules()",
        "MARKER_RULE",
        "INTRO",
        "VOCAB_FRAMING",
        "ESCAPE_PARAGRAPH",
        "GLOSSARY_SECTION",
    ),
}

#: Blocks that are *parts of* another block in the same table. They are printed
#: because a reader wants to see which part moved, and they are left out of the net
#: because counting a paragraph and the block that contains it twice is how a cost
#: report comes to overstate an edit.
PARTS_ONLY = (
    "MARKER_RULE",
    "INTRO",
    "VOCAB_FRAMING",
    "ESCAPE_PARAGRAPH",
    "GLOSSARY_SECTION",
)

#: Prompt material that is a file rather than a module string, by repository path.
FILE_BLOCKS = ("clarion/prompts/cliff-spec-supplement.md",)


def block(source: str, name: str) -> str:
    """The literal body of a triple-quoted module-level string, or ""."""
    match = re.search(rf'^{name} = (?:f)?"""(.*?)"""', source, re.M | re.S)
    return match.group(1) if match else ""


def rendered(module, previous_source: str, name: str, *, call: bool = False) -> str:
    """The *value* of a block in the previous revision, with its helpers available.

    Reading the source text instead compares a template against a rendered string:
    ``CLIFF_FACTS`` holds ``{_row(...)}`` calls that the source spells out and the
    value does not, so the source-text comparison reported a 107-token difference
    where the rendered difference was zero. Executing the revision is what makes the
    number the number.

    The previous revision is executed with this revision's imports and helpers
    already in its namespace, because the relative imports that make the module
    loadable also make it un-exec-able from a string. Two things keep that seeding
    from hiding a change: a name the revision does not define is treated as absent
    (a block added since the revision must show its whole cost, not a zero delta),
    and a block assembled by a function is *called* rather than read.
    """
    if name not in _defined_names(previous_source):
        return ""
    namespace: dict[str, object] = {
        name: value for name, value in vars(module).items() if not name.startswith("__")
    }
    try:
        exec(compile(_without_imports(previous_source), "<previous revision>", "exec"), namespace)  # noqa: S102
    except Exception:  # pragma: no cover - a revision that cannot be executed
        return block(previous_source, name)
    value = namespace.get(name)
    if call and callable(value):
        value = value()
    return value if isinstance(value, str) else block(previous_source, name)


def _defined_names(source: str) -> set[str]:
    """The names the revision's source defines at module level."""
    import ast

    names: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _without_imports(source: str) -> str:
    """The revision's source with its import statements removed, as an AST.

    Slicing the lines instead is what a first attempt did, and a multi-line
    ``from .spec_digest import (`` left its continuation lines behind, which made the
    exec fail and the tool report the whole block as new. An AST drop cannot have
    that failure mode.
    """
    import ast

    tree = ast.parse(source)
    tree.body = [
        node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def main(argv: list[str]) -> int:
    ref = argv[0] if argv else "HEAD"
    import importlib

    from clarion.metrics.tokens import get_tokenizer

    tokenizer = get_tokenizer("o200k_base")

    def show(previous: str) -> int:
        net = 0
        for module_name, names in BLOCKS.items():
            module = importlib.import_module(f"clarion.prompts.{module_name}")
            source = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{ref}:clarion/prompts/{module_name}.py"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout
            for name in names:
                attribute = name[:-2] if name.endswith("()") else name
                is_call = name.endswith("()")
                before_text = rendered(module, source, attribute, call=is_call) if source else ""
                current = getattr(module, attribute)
                after_text = current() if is_call else current
                before = tokenizer.count(before_text)
                after = tokenizer.count(after_text)
                if name not in PARTS_ONLY:
                    net += after - before
                marker = "" if before == after else "  <-- changed"
                print(f"{name:<26}{before:>8}{after:>8}{after - before:>+8}{marker}")
        for path in FILE_BLOCKS:
            source = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{ref}:{path}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout
            after_text = (ROOT / path).read_text(encoding="utf-8")
            before, after = tokenizer.count(source), tokenizer.count(after_text)
            net += after - before
            marker = "" if before == after else "  <-- changed"
            print(f"{Path(path).name:<26}{before:>8}{after:>8}{after - before:>+8}{marker}")
        return net

    print(f"prompt blocks, working copy against {ref}   tokenizer: {tokenizer.name}")
    print(f"{'block':<26}{'before':>8}{'after':>8}{'delta':>8}")
    print("-" * 50)
    net = show(ref)
    print("-" * 50)
    print(f"{'net, per call':<26}{'':<8}{'':<8}{net:>+8}")
    print(
        "\nnet counts each block once: the rows marked as parts (the paragraphs inside the "
        "compressed block) are shown but not added, because the composed row already "
        "carries them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
