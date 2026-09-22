"""Make the sibling reference implementation importable for the whole suite.

`cliff-format`'s own tools import `cliff_format` (the harness compares the prompt's
key tables, vocabularies and required fields against the implementation that
validates the answers), and `cliff-python` is a **sibling checkout, not a dependency
of this package**: the conformance job installs `cliff-test`, not `cliff-python`.

Nothing put the sibling on the path, so the modules that import `cliff_format` failed
to collect in CI - a pytest collection error, exit 2 - while passing by hand, where
the caller had set `PYTHONPATH` already. This applies the same fallback the harness
uses (`clarion.paths.ensure_cliff_format`), once, before any test module is
imported, and it fails with the same actionable message when there is no sibling and
no installed package.
"""

from __future__ import annotations

from clarion.paths import ensure_cliff_format

ensure_cliff_format()
