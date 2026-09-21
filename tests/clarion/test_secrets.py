"""Credential loading, and the scan that proves a tree is clean before a push.

`clarion/secrets.py` had no test at all, which is the wrong module to leave
unguarded: it is the only code in the harness that reads an API key, and the only
code that claims a working tree contains no credential. Both claims are cheap to
check and expensive to get wrong.

The sandbox directory is written inside the repository rather than through
`tmp_path`, because the file sandbox denies the system temporary directory - the
same reason `conftest.py` writes its fixture corpus here. `.gitignore` covers it.
"""

from __future__ import annotations

import os
from pathlib import Path

from clarion import secrets

SANDBOX = Path(__file__).resolve().parent / "_secrets_sandbox"


def _sandbox(name: str) -> Path:
    """An empty directory for one test, inside the repository."""
    path = SANDBOX / name
    if path.exists():
        for child in path.rglob("*"):
            if child.is_file():
                child.unlink()
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_the_environment_wins_over_a_stored_file(monkeypatch) -> None:
    """A key in the environment is used as-is, without touching the disk."""
    external = _sandbox("env-wins")
    (external / "deepseek.key").write_text("sk-fromfile0000000000000000", encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.setenv("TEST_API_KEY", "sk-fromenv00000000000000000")
    assert secrets.load_key("TEST_API_KEY") == "sk-fromenv00000000000000000"


def test_a_stored_key_is_read_from_the_external_directory(monkeypatch) -> None:
    """With no environment variable, the recommended location is the fallback."""
    external = _sandbox("file-fallback")
    (external / "deepseek.key").write_text("  sk-stored0000000000000000000\n", encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("file-fallback-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.load_key("TEST_API_KEY") == "sk-stored0000000000000000000"


def test_no_key_configured_returns_empty_rather_than_raising(monkeypatch) -> None:
    """Absence is reported, not raised: the caller decides whether it is fatal."""
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", _sandbox("no-key-external"))
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("no-key-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.load_key("TEST_API_KEY") == ""


def test_install_key_puts_a_stored_key_into_the_environment(monkeypatch) -> None:
    """The provider reads the environment, so the loader has to reach it."""
    external = _sandbox("install")
    (external / "deepseek.key").write_text("sk-installed000000000000000000", encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.install_key("TEST_API_KEY") is True
    assert os.environ["TEST_API_KEY"] == "sk-installed000000000000000000"
    # A second call is a no-op rather than an overwrite.
    assert secrets.install_key("TEST_API_KEY") is True
    assert os.environ["TEST_API_KEY"] == "sk-installed000000000000000000"


def test_install_key_reports_failure_when_nothing_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", _sandbox("install-none-external"))
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("install-none-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.install_key("TEST_API_KEY") is False


def test_scan_tree_finds_a_planted_credential() -> None:
    """The guard has to fire on the shape it is looking for."""
    root = _sandbox("scan-finds")
    (root / "leak.txt").write_text(
        "nothing on this line\nkey = sk-abcdefghijklmnopqrstuvwx\n", encoding="utf-8"
    )
    (root / "clean.py").write_text("token = 'not-a-credential'\n", encoding="utf-8")
    findings = secrets.scan_tree(root)
    assert [Path(name).name for name, _ in findings] == ["leak.txt"]
    assert findings[0][1] == 2, "the scan must report the line the credential is on"


#: The shapes the scanner promises to catch, one per pattern in `SECRET_PATTERNS`.
CREDENTIAL_SHAPES = (
    "sk-abcdefghijklmnopqrstuvwx",
    "hf_abcdefghijklmnopqrst",
    "AKIAIOSFODNN7EXAMPLE",
)


def test_scan_tree_catches_every_credential_shape_it_claims_to() -> None:
    root = _sandbox("scan-shapes")
    for index, shape in enumerate(CREDENTIAL_SHAPES):
        (root / f"shape{index}.txt").write_text(f"value: {shape}\n", encoding="utf-8")
    found = {Path(name).name for name, _ in secrets.scan_tree(root)}
    assert found == {f"shape{i}.txt" for i in range(len(CREDENTIAL_SHAPES))}


def test_scan_tree_skips_the_places_a_key_is_supposed_to_live() -> None:
    """A scan that flagged the secret store or a run directory would always fail."""
    root = _sandbox("scan-skips")
    for skipped in (".secrets", "results"):
        directory = root / skipped
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "deepseek.key").write_text("sk-abcdefghijklmnopqrstuvwx\n", encoding="utf-8")
    (root / "kept.txt").write_text("sk-abcdefghijklmnopqrstuvwx\n", encoding="utf-8")
    found = {Path(name).name for name, _ in secrets.scan_tree(root)}
    assert found == {"kept.txt"}, f"the scan should only report the tracked file, got {found}"
