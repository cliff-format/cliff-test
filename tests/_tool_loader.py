"""Load an in-repo tool or driver module by path, for tests that exercise it.

Four test modules grew their own copy of this six-line dance: `test_validator_tool`,
`test_edit_robustness`, `test_compare_readings_tool` and `test_prompt_cost_tool`. The
tools are scripts rather than importable package members - they are run as
`python tools/<name>.py` and import their neighbours by adding their own directory to
`sys.path` - so a test that wants their functions has to load them by path, and a
helper keeps the four doing it the same way.

Import it as `from tests._tool_loader import load_module` (the suite's other shared
helper, `tests/_siblings.py`, is imported both ways; `tests/__init__.py` exists, so the
package-qualified form works from anywhere in the tree, including `tests/clarion/`).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_module(path: Path | str, name: str) -> ModuleType:
    """Import the module at *path* under *name* and return it.

    *name* only has to be unique within the run; it is what `importlib` registers the
    module as, so two tests loading the same file under different names do not collide
    with each other's `sys.modules` entry.
    """
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a module from {path}")
    module = importlib.util.module_from_spec(spec)
    # Registered before execution, the way the hand-written copies did it: a tool that
    # imports itself, or a module whose classes are later pickled or compared by
    # identity, needs its entry to exist while the body runs.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
