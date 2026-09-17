"""Filesystem layout of the CLARION harness and the cliff-python bootstrap.

CLARION depends on the official CLIFF implementation (cliff-python) for every CLIFF
parse, serialize, validate and convert operation. The sibling cliff-python
checkout is used automatically when the package is not installed, so a fresh
clone of the three repositories works with no installation step.
"""

from __future__ import annotations

import sys
from pathlib import Path

CLIFF_TEST_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CLIFF_TEST_ROOT.parent

CLIFF_SPEC_ROOT = WORKSPACE_ROOT / "cliff"
# The current specification. CLIFF 1.1 is a pure relaxation of 1.0, so a prompt
# built from the 1.1 grammar also describes a 1.0 document correctly; the 1.0
# files remain in the repository as the frozen definition.
SPEC_FILE = CLIFF_SPEC_ROOT / "spec" / "cliff-1.1.0.md"
ABNF_FILE = CLIFF_SPEC_ROOT / "spec" / "abnf" / "cliff-1.1.abnf"
REFERENCES_DIR = CLIFF_SPEC_ROOT / "references"
SPEC_EXAMPLES_DIR = CLIFF_SPEC_ROOT / "spec" / "examples" / "cliff-1.1.0"

CLIFF_PYTHON_ROOT = WORKSPACE_ROOT / "cliff-python"
CLIFF_PYTHON_SRC = CLIFF_PYTHON_ROOT / "src"

DATASETS_ROOT = CLIFF_TEST_ROOT / "datasets"
CORE_CORPUS_ROOT = DATASETS_ROOT / "clarion-core"
CONFIG_ROOT = CLIFF_TEST_ROOT / "configs"
RESULTS_ROOT = CLIFF_TEST_ROOT / "results"
DOCS_ROOT = CLIFF_TEST_ROOT / "docs"
POLICY_ROOT = CLIFF_TEST_ROOT / "clarion" / "policy"

_PYCLIFF_HINT = (
    "cliff-python is required by CLARION. Either install it "
    "(pip install -e git+https://github.com/cliff-format/cliff-python.git) or keep the cliff-python checkout next to "
    "cliff-test so that {src} exists."
)


def ensure_cliff_format() -> None:
    """Make 'import cliff_format' work, preferring an installed distribution.

    Falls back to the sibling cliff-python/src checkout. Raises RuntimeError
    with an actionable message when neither is available.
    """
    try:
        import cliff_format  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    src = str(CLIFF_PYTHON_SRC)
    if CLIFF_PYTHON_SRC.is_dir() and src not in sys.path:
        sys.path.insert(0, src)

    try:
        import cliff_format  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - environment error
        raise RuntimeError(_PYCLIFF_HINT.format(src=CLIFF_PYTHON_SRC)) from exc


def pycliff_version() -> str:
    """Return the version of the cliff-python implementation in use."""
    ensure_cliff_format()
    import cliff_format

    return str(cliff_format.__version__)
