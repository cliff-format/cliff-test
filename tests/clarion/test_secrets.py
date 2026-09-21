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
import shutil
from pathlib import Path

import pytest

from clarion import secrets

SANDBOX = Path(__file__).resolve().parent / "_secrets_sandbox"


def _shape(prefix: str, body: str = "abcdefghijklmnopqrstuvwx") -> str:
    """A credential-shaped string, assembled when the test runs.

    It must never appear as a literal in this file: `clarion secret-scan` walks the
    tree, so writing one here would trip the project's own pre-push gate on the test
    that tests the scanner. The sandbox directory is skipped for the same reason,
    which is why both halves of that arrangement are needed.
    """
    return prefix + body


SK_SHAPED = _shape("sk-")
HF_SHAPED = _shape("hf_", "abcdefghijklmnopqrst")
AWS_SHAPED = "AKIA" + "IOSFODNN7EXAMPLE"


@pytest.fixture(autouse=True)
def _clean_sandbox():
    """Leave no scratch behind: a generated tree is a dirty tree."""
    yield
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)


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
    (external / "deepseek.key").write_text(_shape("sk-", "fromfile" + "0" * 16), encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.setenv("TEST_API_KEY", _shape("sk-", "fromenv" + "0" * 17))
    assert secrets.load_key("TEST_API_KEY") == _shape("sk-", "fromenv" + "0" * 17)


def test_a_stored_key_is_read_from_the_external_directory(monkeypatch) -> None:
    """With no environment variable, the recommended location is the fallback."""
    expected = _shape("sk-", "stored" + "0" * 19)
    external = _sandbox("file-fallback")
    (external / "deepseek.key").write_text(f"  {expected}\n", encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("file-fallback-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.load_key("TEST_API_KEY") == expected


def test_no_key_configured_returns_empty_rather_than_raising(monkeypatch) -> None:
    """Absence is reported, not raised: the caller decides whether it is fatal."""
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", _sandbox("no-key-external"))
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("no-key-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.load_key("TEST_API_KEY") == ""


def test_install_key_puts_a_stored_key_into_the_environment(monkeypatch) -> None:
    """The provider reads the environment, so the loader has to reach it."""
    expected = _shape("sk-", "installed" + "0" * 16)
    external = _sandbox("install")
    (external / "deepseek.key").write_text(expected, encoding="utf-8")
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", external)
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.install_key("TEST_API_KEY") is True
    assert os.environ["TEST_API_KEY"] == expected
    # A second call is a no-op rather than an overwrite.
    assert secrets.install_key("TEST_API_KEY") is True
    assert os.environ["TEST_API_KEY"] == expected


def test_install_key_reports_failure_when_nothing_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "EXTERNAL_SECRETS", _sandbox("install-none-external"))
    monkeypatch.setattr(secrets, "INTERNAL_SECRETS", _sandbox("install-none-internal"))
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    assert secrets.install_key("TEST_API_KEY") is False


def test_scan_tree_finds_a_planted_credential() -> None:
    """The guard has to fire on the shape it is looking for."""
    root = _sandbox("scan-finds")
    (root / "leak.txt").write_text(
        f"nothing on this line\nkey = {SK_SHAPED}\n", encoding="utf-8"
    )
    (root / "clean.py").write_text("token = 'not-a-credential'\n", encoding="utf-8")
    findings = secrets.scan_tree(root)
    assert [Path(name).name for name, _ in findings] == ["leak.txt"]
    assert findings[0][1] == 2, "the scan must report the line the credential is on"


#: The shapes the scanner promises to catch, one per pattern in `SECRET_PATTERNS`.
CREDENTIAL_SHAPES = (SK_SHAPED, HF_SHAPED, AWS_SHAPED)


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
        (directory / "deepseek.key").write_text(f"{SK_SHAPED}\n", encoding="utf-8")
    (root / "kept.txt").write_text(f"{SK_SHAPED}\n", encoding="utf-8")
    found = {Path(name).name for name, _ in secrets.scan_tree(root)}
    assert found == {"kept.txt"}, f"the scan should only report the tracked file, got {found}"


def test_scan_tree_skips_its_own_test_scratch() -> None:
    """The suite writes credential shapes on purpose, so the tree scan skips them.

    Without this the project's own pre-push gate could never pass: `secret-scan`
    would always find the fixtures of the test that tests `secret-scan`. An explicit
    root is still scanned in full, which is what the tests above rely on.
    """
    root = _sandbox("scan-scratch")
    scratch = root / "_secrets_sandbox"
    scratch.mkdir(parents=True, exist_ok=True)
    # Not a `.key` file: that suffix is skipped on its own, and this test is about
    # the directory name, so the file has to be one the scanner would otherwise read.
    (scratch / "fake.txt").write_text(f"{SK_SHAPED}\n", encoding="utf-8")
    # An explicit root scans everything under it, including the generated name.
    assert [Path(name).name for name, _ in secrets.scan_tree(root)] == ["fake.txt"]
    # A project-tree scan skips it.
    assert secrets.scan_tree() == [], "the project tree must scan clean"
