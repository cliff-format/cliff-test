#!/usr/bin/env python3
"""Which CLARION modules can no test reach, directly or through an import?

`coverage.py` is not a dependency of this suite, so this answers the weaker but
still decidable question: following the import graph from every test module, which
modules of `clarion/` are never reached?

Substring matching is not good enough for this - `from clarion.prompts import
cliff_prompt_v2` does not contain the string `clarion.prompts.cliff_prompt_v2`, so a
text search reports phantom gaps and a gap finder that invents gaps gets ignored.
This parses every module with `ast` and resolves relative imports, then walks the
graph, so a module re-exported through a package `__init__` counts as reached.

A module nothing reaches is not automatically a defect: `clarion.cli`,
`clarion.pipeline` and `clarion.selfcheck` are entry points that are *run* rather
than imported, and the report says so instead of calling them untested.

Usage:
    python tools/coverage_audit.py             # report gaps
    python tools/coverage_audit.py --min 0     # include the small ones
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLARION = ROOT / "clarion"
TESTS = ROOT / "tests"

#: Modules that are meant to be executed rather than imported by a test. CI runs
#: all three, so "no test imports it" is not the same as "nothing checks it".
ENTRY_POINTS = ("clarion.cli", "clarion.pipeline", "clarion.selfcheck")


def _module_name(path: Path) -> str:
    """`clarion/metrics/judge.py` -> `clarion.metrics.judge`."""
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _package_of(path: Path, name: str) -> str:
    """The package a relative import resolves against."""
    if path.name == "__init__.py":
        return name
    return name.rsplit(".", 1)[0] if "." in name else ""


def _imports_of(path: Path, name: str) -> set[str]:
    """Every clarion module this file imports, including inside functions."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - a broken file is a different failure
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("clarion"):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = _package_of(path, name)
                for _ in range(node.level - 1):
                    package = package.rsplit(".", 1)[0] if "." in package else ""
                base = f"{package}.{base}" if base else package
            if not base.startswith("clarion"):
                continue
            found.add(base)
            found.update(f"{base}.{alias.name}" for alias in node.names)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min", type=int, default=2000, help="only report modules over this size")
    args = parser.parse_args(argv)

    graph: dict[str, set[str]] = {}
    sizes: dict[str, int] = {}
    for path in sorted(CLARION.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        name = _module_name(path)
        graph[name] = _imports_of(path, name)
        sizes[name] = path.stat().st_size

    # Seeds: whatever the suite imports, plus the packages they imply.
    reached: set[str] = set()
    frontier: list[str] = []
    for path in sorted(TESTS.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        for name in _imports_of(path, _module_name(path)):
            frontier.append(name)
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        reached.add(name)
        # A package is only reachable through its `__init__`, which is itself a
        # module in the graph and pulls in whatever it re-exports.
        frontier.extend(graph.get(name, ()))
        frontier.extend(child for child in graph if child.startswith(f"{name}."))

    covered = {name for name in sizes if name in reached}
    entry = {name for name in ENTRY_POINTS if name in sizes}
    gaps = sorted(
        (
            name
            for name, size in sizes.items()
            if name not in reached and size >= args.min and not name.endswith("__main__")
        ),
        key=lambda name: -sizes[name],
    )

    print(f"{len(sizes)} modules under clarion/, {len(covered)} reachable from the test suite")
    print(f"entry points, run rather than imported by a test: {', '.join(sorted(entry))}")
    print(f"\nunreachable modules over {args.min} bytes:")
    if not gaps:
        print("   (none)")
    for name in gaps:
        print(f"   {name:<38}{sizes[name]:>7} bytes")
    # Exit 0 either way: this is a report, and a fixed threshold in CI would turn a
    # new opt-in module into a build failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
