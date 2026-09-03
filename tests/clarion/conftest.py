"""Shared fixtures: a small in-memory corpus that does not depend on CLARION-Core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clarion.paths import ensure_clif_format

ensure_clif_format()

SAMPLE_CLIF = """CLIF 1.0
namespace: clarion
clan: fixture
source-language: en-US
target-language: zh-CN
title: "Harness fixture"
info: "Two screens of an invented console product."
standard: "Use 默认 for default; keep Token in Latin script; no trailing period on labels."
dependency: ["fixture-terms.zh-CN.clif"]

[settings.video]
context: "Video settings screen of the console."
type: label
emotion: [objective]
max-width: 12

<resolution>
source: "Resolution"
target: "分辨率"
status: final

<restore-default>
source: "Restore Default"
target: "恢复默认"
status: final
context: "Button that resets the panel."

[notifications]
context: "Notification centre."
type: sentence

<unread-count>
source: "{count, plural, =0 {No unread alerts} other {# unread alerts}}"
target: "{count, plural, =0 {没有未读提醒} other {# 条未读提醒}}"
status: final

<token-hint>
source: "Paste your API Token to continue."
target: "粘贴你的 API Token 以继续。"
status: final
context: "Token must stay in Latin script."
"""

SAMPLE_GLOSSARY = """CLIF 1.0
namespace: clarion
clan: fixture-terms
source-language: en-US
target-language: zh-CN
variant: glossary
title: "Fixture glossary"

[terms]
type: noun

<default>
source: "Default"
target: "默认"
status: final

<token>
source: "Token"
target: "Token"
status: final
"""

GOLD = {
    "file": "fixture.zh-CN.clif",
    "stratum": "fixture",
    "provenance": {
        "source": "original text written for CLARION",
        "license": "CC0-1.0",
        "redistributable": True,
        "human_verified": False,
        "origin": "original",
    },
    "items": {
        "resolution": {
            "reference": "分辨率",
            "difficulty": "easy",
            "rules": [
                {"id": "res-width", "kind": "max-width", "params": {"cells": 12}},
                {
                    "id": "res-term",
                    "kind": "term",
                    "params": {
                        "source": "Resolution",
                        "target": ["分辨率"],
                        "forbidden": ["解析度"],
                    },
                },
            ],
        },
        "restore-default": {
            "reference": "恢复默认",
            "rules": [
                {
                    "id": "default-jargon",
                    "kind": "forbid",
                    "params": {"texts": ["缺省"]},
                },
                {"id": "label-no-period", "kind": "no-trailing-punctuation", "params": {}},
            ],
        },
        "unread-count": {
            "reference": "{count, plural, =0 {没有未读提醒} other {# 条未读提醒}}",
            "rules": [{"id": "icu", "kind": "icu-preserve", "params": {}}],
        },
        "token-hint": {
            "reference": "粘贴你的 API Token 以继续。",
            "rules": [
                {"id": "keep-token", "kind": "keep-verbatim", "params": {"text": "Token"}},
                {"id": "spacing", "kind": "cjk-latin-space", "params": {}},
            ],
        },
    },
}


@pytest.fixture(scope="session")
def sample_document():
    """The fixture document, parsed with clif_format."""
    import clif_format

    return clif_format.parse(SAMPLE_CLIF)


@pytest.fixture(scope="session")
def sample_glossary():
    """The fixture glossary document."""
    import clif_format

    return clif_format.parse(SAMPLE_GLOSSARY)


@pytest.fixture(scope="session")
def corpus_root() -> Path:
    """A one-stratum corpus on disk, ready for load_corpus.

    Written inside the repository rather than into a temporary directory: the
    harness runs under a file sandbox that only permits writes in the
    workspace, and the fixture is deterministic, so rewriting it is free.
    """
    root = Path(__file__).resolve().parent / "_fixture_corpus"
    stratum = root / "fixture"
    stratum.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "name": "fixture",
                "version": "0.0.1",
                "strata": [{"id": "fixture", "title": "harness fixture"}],
            }
        ),
        encoding="utf-8",
    )
    (stratum / "fixture.zh-CN.clif").write_text(SAMPLE_CLIF, encoding="utf-8")
    (stratum / "fixture-terms.zh-CN.clif").write_text(SAMPLE_GLOSSARY, encoding="utf-8")
    (stratum / "fixture.gold.json").write_text(
        json.dumps(GOLD, ensure_ascii=False), encoding="utf-8"
    )
    return root
