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
#: Skipped only in a project-tree scan. Test scratch that is *made* of
#: credential-shaped strings lives here on purpose - the suite that tests this
#: scanner writes them - so scanning the tree would otherwise always report the
#: test that tests the scan, and the pre-push gate could never pass. A caller who
#: passes an explicit root is asking about that directory and gets it scanned in
#: full, which is what lets the scanner's own tests plant a credential and watch it
#: be found.
GENERATED_DIR_NAMES = {"_secrets_sandbox"}


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
    """Find anything that looks like a credential in the working tree.

    With no ``root`` this is the pre-push gate over the project tree, so generated
    directories are skipped. With an explicit ``root`` the caller is asking about
    that directory specifically, and every file in it is read - which is how the
    scanner's own tests watch a planted credential be found.
    """
    base = root or CLIFF_TEST_ROOT
    generated = GENERATED_DIR_NAMES if root is None else set()
    findings: list[tuple[str, int]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(
            part in SKIP_DIRS or part in generated or part == ".secrets"
            for part in path.parts
        ):
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
