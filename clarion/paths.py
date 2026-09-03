"""Filesystem layout of the CLARION harness and the pyclif bootstrap.

CLARION depends on the official CLIF implementation (pyclif) for every CLIF
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
    "pyclif is required by CLARION. Either install it "
    "(pip install -e ../clif-python) or keep the clif-python checkout next to "
    "clif-test so that {src} exists."
)


def ensure_pyclif() -> None:
    """Make 'import pyclif' work, preferring an installed distribution.

    Falls back to the sibling clif-python/src checkout. Raises RuntimeError
    with an actionable message when neither is available.
    """
    try:
        import pyclif  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    src = str(CLIF_PYTHON_SRC)
    if CLIF_PYTHON_SRC.is_dir() and src not in sys.path:
        sys.path.insert(0, src)

    try:
        import pyclif  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - environment error
        raise RuntimeError(_PYCLIF_HINT.format(src=CLIF_PYTHON_SRC)) from exc


def pyclif_version() -> str:
    """Return the version of the pyclif implementation in use."""
    ensure_pyclif()
    import pyclif

    return str(pyclif.__version__)
