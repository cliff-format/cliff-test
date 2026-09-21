"""One policy for the trees this suite reads but does not own.

Two things a checkout can be missing: a sibling repository (`cliff` for the
specification examples, `cliff-python` for the reference implementation) and an
optional in-repo tree (the CLARION-Core corpus). Absent, the dependent tests skip -
which is right on a developer's machine and wrong in CI, where a failed checkout
must not turn into a green build that tested nothing. `CLIFF_REQUIRE_SIBLINGS=1` is
the switch CI sets, and this module is the one place that reads it.

Ported from `cliff-python/tests/conftest.py`, so both repositories answer the
question the same way; the two are separate distributions, so the code is
duplicated deliberately rather than shared through an import.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import pytest

#: The switch CI sets. `run_all.py` reads it too, for the batteries that run through
#: the validator rather than through pytest.
ENV_VAR = "CLIFF_REQUIRE_SIBLINGS"


def required() -> bool:
    """Whether this run demands its sibling trees (the CI setting)."""
    return os.environ.get(ENV_VAR) == "1"


def require_directory(directory: Path, name: str, *, pattern: str = "*.cliff") -> list[Path]:
    """Return the paths under *directory*, or skip - which becomes a failure on demand.

    With the directory present the matching paths come back sorted. Without it the
    caller is expected to skip, unless `CLIFF_REQUIRE_SIBLINGS=1`, in which case this
    fails instead: a suite that collects zero cases passes for the wrong reason, and
    that is exactly what the variable exists to prevent.
    """
    if directory.is_dir():
        return sorted(directory.rglob(pattern))
    message = f"{name} not found at {directory}"
    if required():
        pytest.fail(message)
    return []


def require_sibling(directory: Path, name: str, *, pattern: str = "*.cliff") -> list[Path]:
    """The same policy for a sibling repository checkout."""
    return require_directory(directory, f"sibling checkout {name}", pattern=pattern)


def skip_if_missing(paths: Sequence[Path], name: str) -> None:
    """Skip when a `require_*` call came back empty without being demanded."""
    if not paths:
        pytest.skip(f"sibling checkout {name} is not available")
