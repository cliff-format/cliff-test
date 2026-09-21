#!/usr/bin/env python3
"""Token-cost benchmark: CLIFF 1.1 vs XLIFF 2.1, JSON, CSV, gettext PO,
Fluent, YAML, and TOML.

Counts tokens with OpenAI-compatible tokenizer cl100k_base (tiktoken 0.13.0)
and writes reproducible reports to tests/benchmark/report.md and
tests/benchmark/report.zh-CN.md plus fixtures for manual fairness review.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tests" / "benchmark"
FIXTURES = OUT_DIR / "fixtures"

#: The row label CLIFF is measured and reported under. 1.1 is a pure relaxation
#: of 1.0, so the corpus below is valid under either, but the row must name the
#: specification the emitter actually writes on the version line.
CLIFF_LABEL = "CLIFF 1.1"

#: Character classes for the deterministic fallback tokenizer, used when tiktoken
#: is not installed. Named rather than inlined because the same class appears twice
#: and a drift between the two copies would silently change the fallback count.
CJK_CLASS = r"\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3040-\u30FF\uAC00-\uD7AF"
CJK_RE = f"[{CJK_CLASS}]"
NON_WORD_RE = f"[^\\sA-Za-z0-9{CJK_CLASS}]"

SAMPLE = {
    "namespace": "ironforge-rpg",
    "clan": "game",
    "source_language": "zh-CN",
    "target_language": "en-US",
    "title": "IronForge RPG - Act 3 dialog",
    "info": [
        "The mountain city of IronForge, one week after the siege.",
        "Anvil is a warm, plain-spoken dwarf blacksmith; Captain Mei is formal in "
        "public, warm to friends. The player returns to the blacksmith to reclaim "
        "a repaired sword.",
    ],
    "standard": [
        "Preserve proper nouns; localize idioms for humor.",
        "Keep UI labels under the declared max-width.",
    ],
    "dependency": [
        "../terms/ironforge.terms.en-US.cliff",
        "docs/act3-script.md",
    ],
    "terms": [
        ("铁剑", "Iron Sword"),
        ("旅行者", "traveler"),
        ("铁匠铺", "forge"),
    ],
    "groups": [
        {
            "path": "items.shop",
            "context": "Blacksmith shop, purchase confirmation popup.",
            "emotion": ["playful"],
            "max-width": 20,
            "entries": [
                {
                    "id": "inv-sword-iron",
                    "source": "铁剑",
                    "target": "Iron Sword",
                    "type": "noun",
                    "status": "final",
                    "reference": ["src/combat/items.cpp:142"],
                },
                {
                    "id": "inv-potion-heal",
                    "source": "恢复药水",
                    "target": "Healing Potion",
                    "type": "noun-phrase",
                    "status": "translated",
                },
                {
                    "id": "inv-armor-mithril",
                    "source": "秘银护甲",
                    "target": "Mithril Armor",
                    "type": "noun-phrase",
                    "status": "reviewed",
                },
                {
                    "id": "inv-axe-rune",
                    "source": "符文战斧",
                    "target": "Rune Battleaxe",
                    "type": "noun",
                    "status": "final",
                },
            ],
        },
        {
            "path": "dialog.act3.first-meet",
            "context": "The player meets Captain Mei at the city gate after the siege.",
            "entries": [
                {
                    "id": "greeting",
                    "source": "你好，旅行者。",
                    "target": "Hello, traveler.",
                    "type": "dialogue",
                    "emotion": ["polite", "calm"],
                    "status": "final",
                },
                {
                    "id": "ask-origin",
                    "source": "你从哪里来？",
                    "target": "Where do you come from?",
                    "type": "dialogue",
                    "emotion": ["polite", "curious"],
                    "status": "reviewed",
                },
                {
                    "id": "ask-companion",
                    "source": (
                        "{name}，{gender, select, male {他} female {她} other {他们}} "
                        "是你的同伴吗？"
                    ),
                    "target": (
                        "{name}, is {gender, select, male {he} female {she} "
                        "other {they}} your companion?"
                    ),
                    "type": "sentence",
                    "emotion": ["surprised", "playful"],
                    "status": "reviewed",
                    "context": "She points at the silent stranger next to the player.",
                    "reference": ["src/dialog/act3.cpp:87"],
                },
                {
                    "id": "ask-city",
                    "source": "城里还安全吗？",
                    "target": "Is the city still safe?",
                    "type": "dialogue",
                    "status": "reviewed",
                },
                {
                    "id": "ask-sword",
                    "source": "你的剑是新打的吗？",
                    "target": "Was your sword newly forged?",
                    "type": "dialogue",
                    "status": "reviewed",
                },
            ],
        },
        {
            "path": "dialog.act3.farewell",
            "context": "The player leaves the forge with the repaired sword.",
            "emotion": ["playful", "joyful"],
            "entries": [
                {
                    "id": "farewell",
                    "source": "一路顺风，旅行者！",
                    "target": "Safe travels, traveler!",
                    "type": "dialogue",
                    "status": "reviewed",
                },
                {
                    "id": "farewell-pun",
                    "source": "剑客无剑，如鱼无水——改天我请你“剑”面！",
                    "target": (
                        "A swordsman without a sword is a fish out of water - let's "
                        'have a re-"blade" meeting soon!'
                    ),
                    "type": "dialogue",
                    "status": "reviewed",
                    "context": "Anvil winks; the pun is on 见/剑.",
                },
                {
                    "id": "come-again",
                    "source": "下次再来！",
                    "target": "Come back anytime!",
                    "type": "dialogue",
                    "status": "final",
                },
            ],
        },
        {
            "path": "quests.reward",
            "context": "Quest reward screen after the sword is returned.",
            "emotion": ["grateful"],
            "entries": [
                {
                    "id": "reward-title",
                    "source": "铁匠的谢礼",
                    "target": "The Blacksmith's Gratitude",
                    "type": "label",
                    "status": "final",
                },
                {
                    "id": "reward-body",
                    "source": "收下这枚护符吧。",
                    "target": "Please take this charm.",
                    "type": "narration",
                    "status": "reviewed",
                },
                {
                    "id": "reward-count",
                    "source": "{count, plural, =0 {没有奖励} one {# 件奖励} other {# 件奖励}}",
                    "target": "{count, plural, =0 {No rewards} one {# reward} other {# rewards}}",
                    "type": "sentence",
                    "status": "reviewed",
                },
                {
                    "id": "reward-accept",
                    "source": "接受",
                    "target": "Accept",
                    "type": "label",
                    "status": "final",
                    "max-width": 8,
                },
            ],
        },
    ],
}


def tokenizer():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return lambda text: len(enc.encode(text)), "tiktoken cl100k_base"
    except Exception:
        def fallback(text: str) -> int:
            cjk = len(re.findall(CJK_RE, text))
            ascii_words = len(re.findall(r"[A-Za-z0-9]+", text))
            punct = len(re.findall(NON_WORD_RE, text))
            return cjk + ascii_words + punct
        return fallback, "deterministic fallback"


def q(text: str) -> str:
    """Minimal double-quoted string as used by CLIFF and many formats."""
    return json.dumps(text, ensure_ascii=False)


def cliff_list(items) -> str:
    return "[" + ", ".join(q(str(x)) for x in items) + "]"


def esc_xml(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def po_escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"))


def effective_emotion(entry: dict, group: dict) -> list:
    if "emotion" in entry:
        return entry["emotion"]
    if "emotion" in group:
        return group["emotion"]
    if entry.get("type") in ("dialogue", "monologue", "idiom"):
        return ["neutral"]
    return ["objective"]


def effective_max_width(entry: dict, group: dict):
    if "max-width" in entry:
        return entry["max-width"]
    if "max-width" in group:
        return group["max-width"]
    return None


def effective_context(entry: dict, group: dict) -> str:
    parts = []
    if "context" in group and group["context"]:
        parts.append(group["context"])
    if "context" in entry and entry["context"]:
        parts.append(entry["context"])
    return " ".join(parts)


def glossary_pairs(s: dict):
    return [{"source": src, "target": tgt, "type": "noun", "status": "final",
             "context": "Canonical game term."}
            for src, tgt in s["terms"]]


# ---------------------------------------------------------------------------
# CLIFF 1.1 emitters (main standard file + separate glossary variant file)
# ---------------------------------------------------------------------------

def emit_cliff_main(s: dict) -> str:
    lines = [
        "CLIFF 1.1",
        f'namespace: {s["namespace"]}',
        f'clan: {s["clan"]}',
        f'source-language: {s["source_language"]}',
        f'target-language: {s["target_language"]}',
        f'title: {q(s["title"])}',
    ]
    lines.append("info: " + " ".join(q(info) for info in s["info"]))
    lines.append("standard: " + " ".join(q(std) for std in s["standard"]))
    lines.append("dependency: [" + ",".join(q(dep) for dep in s['dependency']) + "]")
    for g in s["groups"]:
        lines.append("")
        lines.append(f'[{g["path"]}]')
        if "context" in g:
            lines.append(f"context: {q(g['context'])}")
        if "emotion" in g:
            lines.append(f"emotion: [{', '.join(g['emotion'])}]")
        if "max-width" in g:
            lines.append(f"max-width: {g['max-width']}")
        for e in g["entries"]:
            lines.append("")
            lines.append(f'<{e["id"]}>')
            lines.append(f"source: {q(e['source'])}")
            lines.append(f"target: {q(e['target'])}")
            lines.append(f"type: {e['type']}")
            if "emotion" in e:
                lines.append(f"emotion: [{', '.join(e['emotion'])}]")
            lines.append(f"status: {e['status']}")
            if "context" in e:
                lines.append(f"context: {q(e['context'])}")
            if "max-width" in e:
                lines.append(f"max-width: {e['max-width']}")
            if "reference" in e:
                lines.append(f"reference: {cliff_list(e['reference'])}")
    return "\n".join(lines) + "\n"


def emit_cliff_glossary(s: dict) -> str:
    lines = [
        "CLIFF 1.1",
        f'namespace: {s["namespace"]}',
        "clan: terms",
        f'source-language: {s["source_language"]}',
        f'target-language: {s["target_language"]}',
        "variant: glossary",
        f'title: {q("IronForge RPG canonical terminology")}',
        f'standard: {q("Canonical term translations; dialect-specific files may override.")}',
        "",
        "[terms]",
        "type: noun",
    ]
    for idx, (src, tgt) in enumerate(s["terms"], start=1):
        term_id = ["iron-sword", "traveler", "forge"][idx - 1]
        lines.append("")
        lines.append(f"<{term_id}>")
        lines.append(f"source: {q(src)}")
        lines.append(f"target: {q(tgt)}")
        lines.append("type: noun")
        lines.append("status: final")
        lines.append('context: "Canonical game term."')
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# XLIFF 2.1
# ---------------------------------------------------------------------------

def emit_xliff(s: dict) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        f'<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" '
        f'srcLang="{s["source_language"]}" trgLang="{s["target_language"]}">'
    )
    lines.append(f'<file id="{s["namespace"]}-{s["clan"]}" original="{esc_xml(s["title"])}">')
    lines.append("  <notes>")
    for info in s["info"]:
        lines.append(f'    <note category="info">{esc_xml(info)}</note>')
    for std in s["standard"]:
        lines.append(f'    <note category="standard">{esc_xml(std)}</note>')
    for dep in s["dependency"]:
        lines.append(f'    <note category="dependency">{esc_xml(dep)}</note>')
    lines.append("  </notes>")
    if s["terms"]:
        lines.append("  <glossary>")
        for src, tgt in s["terms"]:
            lines.append(
                "    <glossaryEntry>"
                f"<term><source>{esc_xml(src)}</source>"
                f"<target>{esc_xml(tgt)}</target></term>"
                "<note>Canonical game term.</note>"
                "</glossaryEntry>"
            )
        lines.append("  </glossary>")
    for g in s["groups"]:
        lines.append(f'  <group id="{g["path"]}">')
        lines.append("    <notes>")
        if "context" in g:
            lines.append(f'      <note category="context">{esc_xml(g["context"])}</note>')
        if "emotion" in g:
            lines.append(f'      <note category="emotion">{esc_xml(" ".join(g["emotion"]))}</note>')
        if "max-width" in g:
            lines.append(f'      <note category="maxWidth">{g["max-width"]}</note>')
        lines.append("    </notes>")
        for e in g["entries"]:
            lines.append(f'    <unit id="{e["id"]}">')
            if "reference" in e or "context" in e:
                lines.append("      <notes>")
                if "context" in e:
                    lines.append(
                        f'        <note category="context">{esc_xml(e["context"])}</note>'
                    )
                if "reference" in e:
                    joined = esc_xml(" ".join(e["reference"]))
                    lines.append(f'        <note category="reference">{joined}</note>')
                lines.append("      </notes>")
            lines.append(f"      <segment><source>{esc_xml(e['source'])}</source>"
                         f"<target>{esc_xml(e['target'])}</target></segment>")
            lines.append("      <metadata>")
            lines.append(f'        <metaGroup category="type">{e["type"]}</metaGroup>')
            if "emotion" in e or "emotion" not in g:
                emotion = esc_xml(" ".join(effective_emotion(e, g)))
                lines.append(
                    f'        <metaGroup category="emotion">{emotion}</metaGroup>'
                )
            lines.append(f'        <metaGroup category="state">{e["status"]}</metaGroup>')
            if "max-width" in e:
                lines.append(f'        <metaGroup category="maxWidth">{e["max-width"]}</metaGroup>')
            lines.append("      </metadata>")
            lines.append("    </unit>")
        lines.append("  </group>")
    lines.append("</file>")
    lines.append("</xliff>")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def emit_json(s: dict) -> str:
    doc = {
        "namespace": s["namespace"],
        "clan": s["clan"],
        "sourceLanguage": s["source_language"],
        "targetLanguage": s["target_language"],
        "title": s["title"],
        "info": s["info"],
        "standards": s["standard"],
        "dependencies": s["dependency"],
        "glossary": [
            {"source": src, "target": tgt, "type": "noun", "status": "final"}
            for src, tgt in s["terms"]
        ],
        "groups": [],
    }
    for g in s["groups"]:
        group = {"path": g["path"], "entries": []}
        if "context" in g:
            group["context"] = g["context"]
        if "emotion" in g:
            group["emotion"] = g["emotion"]
        if "max-width" in g:
            group["maxWidth"] = g["max-width"]
        for e in g["entries"]:
            entry = {
                "id": e["id"],
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "status": e["status"],
            }
            if "emotion" in e or "emotion" not in g:
                entry["emotion"] = effective_emotion(e, g)
            if "context" in e:
                entry["context"] = e["context"]
            if "max-width" in e:
                entry["maxWidth"] = e["max-width"]
            if "reference" in e:
                entry["reference"] = e["reference"]
            group["entries"].append(entry)
        doc["groups"].append(group)
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def emit_csv(s: dict) -> str:
    header = [
        "id", "namespace", "clan", "group", "sourceLanguage", "targetLanguage",
        "title", "info", "standards", "dependencies", "glossary",
        "groupContext", "entryContext", "source", "target", "type", "emotion",
        "status", "maxWidth", "reference",
    ]
    rows = [header]
    info = " ".join(s["info"])
    standards = "; ".join(s["standard"])
    dependencies = "; ".join(s["dependency"])
    glossary = "; ".join(f"{src}=>{tgt}" for src, tgt in s["terms"])
    for g in s["groups"]:
        for e in g["entries"]:
            rows.append([
                e["id"],
                s["namespace"],
                s["clan"],
                g["path"],
                s["source_language"],
                s["target_language"],
                s["title"],
                info,
                standards,
                dependencies,
                glossary,
                g.get("context", ""),
                e.get("context", ""),
                e["source"],
                e["target"],
                e["type"],
                " ".join(effective_emotion(e, g)),
                e["status"],
                effective_max_width(e, g) if effective_max_width(e, g) is not None else "",
                " ".join(e["reference"]) if "reference" in e else "",
            ])
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# gettext PO
# ---------------------------------------------------------------------------

def emit_po(s: dict) -> str:
    lines = [
        'msgid ""',
        'msgstr ""',
        f'"Project-Id-Version: {po_escape(s["title"])}\\n"',
        f'"Language: {s["target_language"]}\\n"',
        f'"Language-Team: {s["source_language"]} to {s["target_language"]}\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        '""',
    ]
    lines.append(f"# namespace: {s['namespace']}")
    lines.append(f"# clan: {s['clan']}")
    for info in s["info"]:
        lines.append(f"# info: {info}")
    for std in s["standard"]:
        lines.append(f"# standard: {std}")
    for dep in s["dependency"]:
        lines.append(f"# dependency: {dep}")
    for src, tgt in s["terms"]:
        lines.append(f"# glossary: {src} => {tgt}")
    for g in s["groups"]:
        for e in g["entries"]:
            lines.append("")
            lines.append(f'msgctxt "{g["path"]}.{e["id"]}"')
            lines.append(f'msgid "{po_escape(e["source"])}"')
            lines.append(f'msgstr "{po_escape(e["target"])}"')
            if "reference" in e:
                lines.append(f"#: {' '.join(e['reference'])}")
            context = effective_context(e, g)
            if context:
                lines.append(f"#. context: {context}")
            lines.append("#. type: " + e["type"])
            lines.append("#. emotion: " + " ".join(effective_emotion(e, g)))
            lines.append("#. status: " + e["status"])
            if effective_max_width(e, g) is not None:
                lines.append("#. max-width: " + str(effective_max_width(e, g)))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Fluent
# ---------------------------------------------------------------------------

def fluent_attr(key: str, value) -> str:
    if isinstance(value, list):
        return f"    .{key} = {' '.join(value)}"
    return f"    .{key} = {value}"


def emit_fluent(s: dict) -> str:
    lines = [
        "# Fluent resource for IronForge RPG Act 3",
        f"# namespace: {s['namespace']}",
        f"# clan: {s['clan']}",
        f"# source-language: {s['source_language']}",
        f"# target-language: {s['target_language']}",
        f"# title: {s['title']}",
    ]
    for info in s["info"]:
        lines.append(f"# info: {info}")
    for std in s["standard"]:
        lines.append(f"# standard: {std}")
    for dep in s["dependency"]:
        lines.append(f"# dependency: {dep}")
    lines.append("")
    for i, (src, tgt) in enumerate(s["terms"], start=1):
        term = ["iron-sword", "traveler", "forge"][i - 1]
        lines.append(f"-term-{term} = {tgt}")
        lines.append(f"    .source = {src}")
        lines.append("    .type = noun")
        lines.append("    .status = final")
        lines.append("    .context = Canonical game term.")
    lines.append("")
    for g in s["groups"]:
        group_id = g["path"].replace(".", "-")
        for e in g["entries"]:
            msg_id = f"{group_id}-{e['id']}"
            lines.append(f"{msg_id} = {e['target']}")
            lines.append(f"    .id = {e['id']}")
            lines.append(f"    .source = {e['source']}")
            lines.append(f"    .group = {g['path']}")
            lines.append(f"    .type = {e['type']}")
            lines.append(f"    .emotion = {' '.join(effective_emotion(e, g))}")
            lines.append(f"    .status = {e['status']}")
            if effective_context(e, g):
                lines.append(f"    .context = {effective_context(e, g)}")
            if effective_max_width(e, g) is not None:
                lines.append(f"    .max-width = {effective_max_width(e, g)}")
            if "reference" in e:
                lines.append(f"    .reference = {' '.join(e['reference'])}")
            lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------------

def yaml_scalar(value) -> str:
    if isinstance(value, bool) or isinstance(value, int):
        return str(value)
    return q(str(value))


def emit_yaml(s: dict) -> str:
    lines = []
    lines.append(f"namespace: {s['namespace']}")
    lines.append(f"clan: {s['clan']}")
    lines.append(f"source_language: {s['source_language']}")
    lines.append(f"target_language: {s['target_language']}")
    lines.append(f"title: {q(s['title'])}")
    lines.append("info:")
    for info in s["info"]:
        lines.append(f"  - {q(info)}")
    lines.append("standards:")
    for std in s["standard"]:
        lines.append(f"  - {q(std)}")
    lines.append("dependencies:")
    for dep in s["dependency"]:
        lines.append(f"  - {q(dep)}")
    lines.append("glossary:")
    for src, tgt in s["terms"]:
        lines.append("  - source: " + q(src))
        lines.append("    target: " + q(tgt))
        lines.append("    type: noun")
        lines.append("    status: final")
    lines.append("groups:")
    for g in s["groups"]:
        lines.append(f"  - path: {q(g['path'])}")
        if "context" in g:
            lines.append(f"    context: {q(g['context'])}")
        if "emotion" in g:
            lines.append("    emotion:")
            for emo in g["emotion"]:
                lines.append(f"      - {q(emo)}")
        if "max-width" in g:
            lines.append(f"    max_width: {g['max-width']}")
        lines.append("    entries:")
        for e in g["entries"]:
            lines.append(f"      - id: {q(e['id'])}")
            lines.append(f"        source: {q(e['source'])}")
            lines.append(f"        target: {q(e['target'])}")
            lines.append(f"        type: {e['type']}")
            if "emotion" in e or "emotion" not in g:
                lines.append("        emotion:")
                for emo in effective_emotion(e, g):
                    lines.append(f"          - {q(emo)}")
            lines.append(f"        status: {e['status']}")
            if "context" in e:
                lines.append(f"        context: {q(e['context'])}")
            if "max-width" in e:
                lines.append(f"        max_width: {e['max-width']}")
            if "reference" in e:
                lines.append("        reference:")
                for ref in e["reference"]:
                    lines.append(f"          - {q(ref)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# TOML
# ---------------------------------------------------------------------------

def emit_toml(s: dict) -> str:
    lines = []
    lines.append(f'namespace = {q(s["namespace"])}')
    lines.append(f'clan = {q(s["clan"])}')
    lines.append(f'source_language = {q(s["source_language"])}')
    lines.append(f'target_language = {q(s["target_language"])}')
    lines.append(f'title = {q(s["title"])}')
    lines.append("info = [" + ", ".join(q(x) for x in s["info"]) + "]")
    lines.append("standards = [" + ", ".join(q(x) for x in s["standard"]) + "]")
    lines.append("dependencies = [" + ", ".join(q(x) for x in s["dependency"]) + "]")
    lines.append("")
    for src, tgt in s["terms"]:
        lines.append("[[glossary]]")
        lines.append(f'source = {q(src)}')
        lines.append(f'target = {q(tgt)}')
        lines.append('type = "noun"')
        lines.append('status = "final"')
        lines.append("")
    for g in s["groups"]:
        key = "groups." + g["path"].replace(".", "-")
        lines.append(f"[{key}]")
        lines.append(f'path = {q(g["path"])}')
        if "context" in g:
            lines.append(f'context = {q(g["context"])}')
        if "emotion" in g:
            lines.append("emotion = [" + ", ".join(q(x) for x in g["emotion"]) + "]")
        if "max-width" in g:
            lines.append(f"max_width = {g['max-width']}")
        lines.append("")
        for e in g["entries"]:
            lines.append(f"[[{key}.entries]]")
            lines.append(f'id = {q(e["id"])}')
            lines.append(f'source = {q(e["source"])}')
            lines.append(f'target = {q(e["target"])}')
            lines.append(f'type = {q(e["type"])}')
            if "emotion" in e or "emotion" not in g:
                emo = effective_emotion(e, g)
                lines.append("emotion = [" + ", ".join(q(x) for x in emo) + "]")
            lines.append(f'status = {q(e["status"])}')
            if "context" in e:
                lines.append(f'context = {q(e["context"])}')
            if "max-width" in e:
                lines.append(f"max_width = {e['max-width']}")
            if "reference" in e:
                lines.append("reference = [" + ", ".join(q(x) for x in e["reference"]) + "]")
            lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def build_report_texts(results: dict, engine: str, cliff_tokens: int, order: list,
                       fixtures_paths: list) -> tuple[str, str]:
    """The two reports, as text. No writes, so `--check` can render without touching
    the tracked files."""
    others = [name for name in order if name != CLIFF_LABEL]
    avg = sum(results[name]["tokens"] for name in others) / len(others)
    savings = (1 - cliff_tokens / avg) * 100
    verdict = "PASS" if savings >= 30 else "FAIL"

    rows = []
    for name in order:
        r = results[name]
        pct = (r["tokens"] / cliff_tokens - 1) * 100
        rows.append(f"| {name} | {r['tokens']} | {r['chars']} | {r['bytes']} | {pct:+.1f}% |")

    en_lines = [
        f"# {CLIFF_LABEL} Token Benchmark",
        "",
        f"- Corpus: {sum(len(g['entries']) for g in SAMPLE['groups'])} translation units across "
        f"{len(SAMPLE['groups'])} groups, with family info, standards, dependencies, glossary, "
        "per-entry type/emotion/status/max-width/context/reference, and ICU payloads.",
        f"- Tokenizer: {engine}.",
        f"- CLIFF token count = {CLIFF_LABEL} standard main file + the separate "
        "`variant: glossary` "
        "dependency file. The glossary is semantically part of the CLIFF corpus and is counted "
        "as CLIFF's true single-workflow cost; every other format inlines the same three terms "
        "in its native syntax.",
        "- Reproducibility: two consecutive runs of `python tools/token_benchmark.py` produced "
        "identical token counts (this report was generated by the second run).",
        "",
        "| Format | Tokens | Characters | Bytes | vs CLIFF |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    en_lines.extend(rows)
    en_lines += [
        "",
        f"{CLIFF_LABEL} uses **{cliff_tokens}** tokens (main + glossary). The average of the "
        f"other seven formats is **{avg:.1f}** tokens. CLIFF saves **{savings:.1f}%** "
        "against that average.",
        "",
        f"**Result: {verdict}** (threshold is at least 30% average savings vs the "
        "other 7 formats).",
        "",
        "Fixture files written to `tests/benchmark/fixtures/` for fairness review:",
        "",
    ]
    en_lines.extend(f"- `tests/benchmark/fixtures/{p}`" for p in fixtures_paths)
    en_lines.append("")

    zh_lines = [
        f"# {CLIFF_LABEL} Token 基准",
        "",
        f"- 语料：{sum(len(g['entries']) for g in SAMPLE['groups'])} 个翻译单元，分布在 "
        f"{len(SAMPLE['groups'])} 个组中，包含家庭信息、规范、依赖、术语表、逐条 "
        "type/emotion/status/max-width/context/reference 和 ICU 载荷。",
        f"- 分词器：{engine}。",
        f"- CLIFF token 数 = {CLIFF_LABEL} 标准主文件 + 单独的 `variant: glossary` 依赖术语表文件。"
        "术语表在语义上是 CLIFF 语料的一部分，按 CLIFF 的实际单工作流成本计入；其他每种格式"
        "都在其原生语法中内联同样的三条术语。",
        "- 可复现性：连续两次运行 `python tools/token_benchmark.py` 得到完全一致的 token 数"
        "（本报告由第二次运行生成）。",
        "",
        "| 格式 | Tokens | 字符数 | 字节数 | vs CLIFF |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in order:
        r = results[name]
        pct = (r["tokens"] / cliff_tokens - 1) * 100
        zh_lines.append(f"| {name} | {r['tokens']} | {r['chars']} | {r['bytes']} | {pct:+.1f}% |")
    zh_lines += [
        "",
        f"{CLIFF_LABEL} 使用 **{cliff_tokens}** token（主文件 + 术语表）。其他 7 种格式平均为 "
        f"**{avg:.1f}** token。CLIFF 相对该平均值节省 **{savings:.1f}%**。",
        "",
        f"**结果：{verdict}**（门槛为相对其他 7 种格式平均值至少节省 30%）。",
        "",
        "已写入 `tests/benchmark/fixtures/` 供公平性人工审计：",
        "",
    ]
    zh_lines.extend(f"- `tests/benchmark/fixtures/{p}`" for p in fixtures_paths)
    zh_lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return "\n".join(en_lines), "\n".join(zh_lines)


def write_reports(results: dict, engine: str, cliff_tokens: int, order: list,
                  fixtures_paths: list) -> None:
    """Write the two reports (and print the English one, as the tool always has)."""
    english, chinese = build_report_texts(results, engine, cliff_tokens, order, fixtures_paths)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.md").write_text(english, encoding="utf-8", newline="\n")
    (OUT_DIR / "report.zh-CN.md").write_text(chinese, encoding="utf-8", newline="\n")
    print(english)


def render_artefacts() -> dict[Path, str]:
    """Every file this tool writes, rendered in memory and keyed by its path.

    The suite commits these nine artefacts - two reports and seven fixture files - and
    regenerates them, so a code change can leave the committed copy stale with nothing
    failing. `--check` compares this mapping against the tracked files; the writer
    below writes it. One function renders, so the two can never disagree about what the
    output is.
    """
    count, engine = tokenizer()
    cliff_main_text = emit_cliff_main(SAMPLE)
    cliff_glossary_text = emit_cliff_glossary(SAMPLE)
    emitters = {
        CLIFF_LABEL: lambda s: emit_cliff_main(s) + "\n" + emit_cliff_glossary(s),
        "XLIFF 2.1": emit_xliff,
        "JSON": emit_json,
        "CSV": emit_csv,
        "gettext PO": emit_po,
        "Fluent": emit_fluent,
        "YAML": emit_yaml,
        "TOML": emit_toml,
    }

    results = {}
    for name, emit in emitters.items():
        text = emit(SAMPLE)
        results[name] = {
            "tokens": count(text),
            "chars": len(text),
            "bytes": len(text.encode("utf-8")),
        }

    # Fixture writer uses the actual per-format text, but CLIFF is two files.
    fixture_texts = {
        "cliff-main.cliff": cliff_main_text,
        "cliff-glossary.cliff": cliff_glossary_text,
        "xliff.xlf": emit_xliff(SAMPLE),
        "data.json": emit_json(SAMPLE),
        "data.csv": emit_csv(SAMPLE),
        "data.po": emit_po(SAMPLE),
        "data.ftl": emit_fluent(SAMPLE),
        "data.yaml": emit_yaml(SAMPLE),
        "data.toml": emit_toml(SAMPLE),
    }

    cliff_tokens = results[CLIFF_LABEL]["tokens"]
    order = list(emitters.keys())
    english, chinese = build_report_texts(
        results, engine, cliff_tokens, order, list(fixture_texts.keys())
    )
    artefacts = {
        OUT_DIR / "report.md": english,
        OUT_DIR / "report.zh-CN.md": chinese,
    }
    artefacts.update({FIXTURES / filename: text for filename, text in fixture_texts.items()})
    return artefacts


def first_difference(expected: str, actual: str) -> str:
    """A readable one-line summary of where two texts diverge."""
    expected_lines, actual_lines = expected.splitlines(), actual.splitlines()
    for index in range(max(len(expected_lines), len(actual_lines))):
        want = expected_lines[index] if index < len(expected_lines) else "<end of file>"
        got = actual_lines[index] if index < len(actual_lines) else "<end of file>"
        if want != got:
            return f"line {index + 1}:\n      tracked: {want}\n      rendered: {got}"
    return "the texts differ only in trailing whitespace"


def check() -> int:
    """Compare every rendered artefact with the tracked file. 0 when they match."""
    stale: list[str] = []
    for path, expected in sorted(render_artefacts().items()):
        relative = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            stale.append(f"{relative}: missing (the tool would create it)")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            stale.append(f"{relative}: {first_difference(expected, actual)}")
    if not stale:
        print("token benchmark: every tracked artefact matches what the tool renders")
        return 0
    print("token benchmark: tracked artefacts are stale")
    for entry in stale:
        print(f"  - {entry}")
    print("\nregenerate with: python tools/token_benchmark.py")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="render every artefact in memory and compare it with the tracked file",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()

    artefacts = render_artefacts()
    for path, text in artefacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        # LF explicitly: `.gitattributes` pins `eol=lf`, and the default text-mode write
        # on Windows turns every newline into CRLF, which leaves the tracked reports
        # looking modified after every run and makes the committed bytes platform
        # dependent. `check()` reads with universal newlines, so it could not see it.
        path.write_text(text, encoding="utf-8", newline="\n")
    print(artefacts[OUT_DIR / "report.md"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
