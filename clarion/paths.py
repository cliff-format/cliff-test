"""Filesystem layout of the CLARION harness and the clif-python bootstrap.

CLARION depends on the official CLIF implementation (clif-python) for every CLIF
parse, serialize, validate and convert operation. The sibling clif-python
checkout is used automatically when the package is not installed, so a fresh
clone of the three repositories works with no installation step.
"""

from __future__ import annotations

import sys
from pathlib import Path

CLIF_TEST_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CLIF_TEST_ROOT.parent

CLIF_SPEC_ROOT = WORKSPACE_ROOT / "clif"
SPEC_FILE = CLIF_SPEC_ROOT / "spec" / "clif-1.0.0.md"
ABNF_FILE = CLIF_SPEC_ROOT / "spec" / "abnf" / "clif-1.0.abnf"
REFERENCES_DIR = CLIF_SPEC_ROOT / "references"
SPEC_EXAMPLES_DIR = CLIF_SPEC_ROOT / "spec" / "examples" / "clif-1.0.0"

CLIF_PYTHON_ROOT = WORKSPACE_ROOT / "clif-python"
CLIF_PYTHON_SRC = CLIF_PYTHON_ROOT / "src"

DATASETS_ROOT = CLIF_TEST_ROOT / "datasets"
CORE_CORPUS_ROOT = DATASETS_ROOT / "clarion-core"
CONFIG_ROOT = CLIF_TEST_ROOT / "configs"
RESULTS_ROOT = CLIF_TEST_ROOT / "results"
DOCS_ROOT = CLIF_TEST_ROOT / "docs"
POLICY_ROOT = CLIF_TEST_ROOT / "clarion" / "policy"

_PYCLIF_HINT = (
    "clif-python is required by CLARION. Either install it "
    "(pip install -e git+https://github.com/clif-format/clif-python.git) or keep the clif-python checkout next to "
    "clif-test so that {src} exists."
)


def ensure_clif_format() -> None:
    """Make 'import clif_format' work, preferring an installed distribution.

    Falls back to the sibling clif-python/src checkout. Raises RuntimeError
    with an actionable message when neither is available.
    """
    try:
        import clif_format  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    src = str(CLIF_PYTHON_SRC)
    if CLIF_PYTHON_SRC.is_dir() and src not in sys.path:
        sys.path.insert(0, src)

    try:
        import clif_format  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - environment error
        raise RuntimeError(_PYCLIF_HINT.format(src=CLIF_PYTHON_SRC)) from exc


def pyclif_version() -> str:
    """Return the version of the clif-python implementation in use."""
    ensure_clif_format()
    import clif_format

    return str(clif_format.__version__)
