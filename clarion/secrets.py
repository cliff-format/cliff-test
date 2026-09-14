"""Credential loading that cannot end up in a commit.

A key is looked up in this order:

1. the environment variable named by the provider configuration;
2. a file next to the workspace, outside every git repository:
   <workspace>/.clarion-secrets/<name>.key  - the recommended location;
3. a gitignored file inside this repository: cliff-test/.secrets/<name>.key.

Nothing here ever writes a key, prints a key, or puts a key into a run record.
'clarion secret-scan' proves the working tree is clean before a push.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .paths import CLIFF_TEST_ROOT, WORKSPACE_ROOT

EXTERNAL_SECRETS = WORKSPACE_ROOT / ".clarion-secrets"
INTERNAL_SECRETS = CLIFF_TEST_ROOT / ".secrets"
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{24,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
SKIP_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".clarion-cache", "results"}


def load_key(env_var: str, *, name: str = "deepseek") -> str:
    """Return an API key, or an empty string when none is configured."""
    value = os.environ.get(env_var, "").strip()
    if value:
        return value
    for directory in (EXTERNAL_SECRETS, INTERNAL_SECRETS):
        candidate = directory / f"{name}.key"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return ""


def install_key(env_var: str, *, name: str = "deepseek") -> bool:
    """Put a stored key into the environment for the current process only."""
    if os.environ.get(env_var):
        return True
    key = load_key(env_var, name=name)
    if key:
        os.environ[env_var] = key
        return True
    return False


def scan_tree(root: Path | None = None) -> list[tuple[str, int]]:
    """Find anything that looks like a credential in the working tree."""
    base = root or CLIFF_TEST_ROOT
    findings: list[tuple[str, int]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part == ".secrets" for part in path.parts):
            continue
        if path.suffix in {".png", ".jpg", ".webp", ".gif", ".db", ".pyc", ".key"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                findings.append((str(path.relative_to(base)), number))
    return findings
