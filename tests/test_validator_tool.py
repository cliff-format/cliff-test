"""The reference validator tool's modes and exit codes.

`tests/run_all.py` runs each fixture suite in the mode it is about, and this
module holds the tool itself to the same contract: a mode that reports the wrong
thing, or exits 0 on a bad document, would make every suite above it meaningless.

The multi-document mode is asserted here because it is the one mode whose
subject is not a single document: a translator following the terminology
workflow returns a translated file *plus* a glossary, and concatenating two
valid documents is not one valid document.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FIXTURES = ROOT / "tests" / "fixtures"


def _load_validator():
    """Import `cliff_validator` without running its `main()`."""
    spec = importlib.util.spec_from_file_location(
        "cliff_cliff_validator", TOOLS / "cliff_validator.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validator():
    pytest.importorskip("cliff_format", reason="cliff-python is not importable")
    return _load_validator()


def _issues(validator, text: str) -> list:
    return validator.multi_document_issues(text)


TWO_DOCUMENTS = (
    "CLIFF 1.0\nnamespace: demo\nclan: settings\n"
    "source-language: en-US\ntarget-language: zh-CN\n\n"
    '[main]\ntype: label\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n\n'
    "CLIFF 1.1\nnamespace: demo\nclan: settings-terms\n"
    "source-language: en-US\ntarget-language: zh-CN\nvariant: glossary\n\n"
    '[terms]\ntype: noun\n\n<a>\nsource: "A"\ntarget: "甲"\nstatus: final\n'
)


def test_a_two_document_answer_is_valid(validator) -> None:
    """The documented two-deliverable shape passes, in either version."""
    assert _issues(validator, TWO_DOCUMENTS) == []


def test_the_fixture_used_by_the_battery_is_valid(validator) -> None:
    """The fixture `run_all.py` points the mode at must stay valid."""
    text = (FIXTURES / "tolerant" / "two-documents.txt").read_text(encoding="utf-8")
    assert _issues(validator, text) == []


def test_a_single_document_is_not_a_multi_document_answer(validator) -> None:
    """The negative control: the mode must not pass a plain document.

    Otherwise a run could "pass" the splitting check without ever splitting.
    """
    single = TWO_DOCUMENTS.split("CLIFF 1.1")[0]
    issues = _issues(validator, single)
    assert len(issues) == 1
    assert "fewer than two" in issues[0].message


def test_each_document_is_checked_on_its_own(validator) -> None:
    """A defect in the second document must be reported, with its own line.

    Concatenation hides this: the second version line is a syntax error to a
    single-document parser, and the real defect behind it is never reached.
    """
    broken = TWO_DOCUMENTS.replace(
        '<a>\nsource: "A"\ntarget: "甲"\nstatus: final',
        '<a>\nsource: "A"\ntarget: "甲"',
    )
    issues = _issues(validator, broken)
    assert issues, "the missing status in the second document was not reported"
    assert any(issue.line > 10 for issue in issues), [i.line for i in issues]
    assert any("document 2 of 2" in issue.message for issue in issues), [
        i.message for i in issues
    ]


def test_multi_document_mode_rejects_a_document_it_cannot_split(validator) -> None:
    """A version line that is not a version line is a syntax error, not a pass."""
    issues = _issues(validator, "CLIFF 1.1\nnamespace: demo\n\n[a]\n<b>\nsource: x\n")
    assert len(issues) == 1
    assert "fewer than two" in issues[0].message
