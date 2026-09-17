"""CLIFF specification injection for prompts.

The only supported injection is the production CLIFF digest: ABNF plus the
writer-facing supplement. Helper functions here read the closed vocabularies
and the ABNF from the specification repository.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from ..paths import ABNF_FILE, REFERENCES_DIR
from ..util import read_text

_SUPPLEMENT_FILE = Path(__file__).resolve().parent / "cliff-spec-supplement.md"

_TABLE_TAG_RE = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|")

FALLBACK_TYPES = (
    "noun verb adjective adverb pronoun numeral preposition conjunction particle "
    "interjection proper-noun noun-phrase verb-phrase adjective-phrase adverb-phrase "
    "fixed-phrase idiom sentence description narration dialogue monologue prompt label "
    "subtitle accessibility-cue"
).split()
FALLBACK_EMOTIONS = (
    "neutral objective mechanical joyful sad angry fearful surprised curious disgusted "
    "anxious calm playful serious urgent romantic hopeful grateful formal informal polite "
    "rude nostalgic"
).split()
STATUS_TAGS = ("initial", "translated", "reviewed", "final")


def _tags_from_reference(filename: str, fallback: tuple[str, ...] | list[str]) -> list[str]:
    path = REFERENCES_DIR / filename
    if not path.exists():
        return list(fallback)
    tags: list[str] = []
    for line in read_text(path).split("\n"):
        match = _TABLE_TAG_RE.match(line)
        if match:
            tag = match.group(1)
            if tag not in tags:
                tags.append(tag)
    return tags or list(fallback)


@lru_cache(maxsize=1)
def type_tags() -> tuple[str, ...]:
    """The closed set of CLIFF content types, read from the specification."""
    return tuple(_tags_from_reference("content-types.md", FALLBACK_TYPES))


@lru_cache(maxsize=1)
def emotion_tags() -> tuple[str, ...]:
    """The closed set of CLIFF emotion tags, read from the specification."""
    return tuple(_tags_from_reference("emotion-tags.md", FALLBACK_EMOTIONS))


_ABNF_COMMENT = re.compile(r"^\s*;")
_SEMANTIC_MARKER = "Semantic constraints"


@lru_cache(maxsize=1)
def grammar_only() -> str:
    """The normative ABNF, stripped of prose comments.

    A formal grammar states in 40 lines what a specification needs pages of
    English for, and a model reads it more reliably than a paraphrase. This is
    the backbone of the injected rules; natural language is only added where a
    grammar cannot express the rule.
    """
    if not ABNF_FILE.exists():
        return ""
    lines = [
        line.rstrip()
        for line in read_text(ABNF_FILE).split("\n")
        if line.strip() and not _ABNF_COMMENT.match(line)
    ]
    return "\n".join(lines)


@lru_cache(maxsize=1)
def semantic_constraints() -> str:
    """The constraint list the ABNF carries as its trailing comment block."""
    if not ABNF_FILE.exists():
        return ""
    text = read_text(ABNF_FILE)
    index = text.find(_SEMANTIC_MARKER)
    if index < 0:
        return ""
    block = text[index:]
    lines = [re.sub(r"^\s*;\s?", "", line).rstrip() for line in block.split("\n")]
    return "\n".join(line for line in lines if line.strip())


@lru_cache(maxsize=1)
def spec_supplement() -> str:
    """A concise writer-side digest of the normative specification.

    ABNF states what is legal; this markdown states the generation choices
    models need when producing or editing CLIFF (safe ids, field cardinality,
    quoting, glossary shape).
    """
    if not _SUPPLEMENT_FILE.exists():
        return ""
    return read_text(_SUPPLEMENT_FILE).strip()


@lru_cache(maxsize=1)
def build_grammar_plus() -> str:
    """The grammar-plus rules: ABNF plus answer shape and counted triggers.

    This is the production CLIFF injection. The ABNF stays the backbone; the
    extra prose is limited to what ABNF cannot state: how to stop the answer
    and how to decide a countable glossary.
    """
    types = ", ".join(type_tags())
    emotions = ", ".join(emotion_tags())
    status = ", ".join(STATUS_TAGS)
    return f"""You are editing CLIFF 1.1. Its normative grammar follows, in ABNF (RFC 5234).
The grammar is the definition of the format; the notes after it state the
things a grammar leaves open.

--- GRAMMAR ---
{grammar_only()}
--- END GRAMMAR ---

RULES THE GRAMMAR LEAVES TO THE WRITER
{semantic_constraints()}

CLOSED VOCABULARIES
type:    {types}
emotion: {emotions}
status:  {status}

WRITER SAFETY RULES
Identifiers may use uppercase letters, lowercase letters, digits, "_" and "-",
and never ".". They are case-sensitive and must be copied exactly as written:
do not recapitalize an entry id and do not add or remove underscores, because
the id is the translation match key. The recommended shapes are lowercase
kebab-case (editors-note) or PascalCase (EditorsNote), one shape per file.
Fixed tags (type, emotion, status, variant) are the exception and are not
flexible: they are lowercase kebab-case words from the closed vocabularies
above, written bare — never quoted. Glossary ids follow the same identifier
rule and are unique; one entry per term. Text values are quoted strings; escape
inner double quotes as \", newlines as \n, and tabs as \t, so the whole value
stays one quoted string.

A CONFORMING FILE, FOR SHAPE

CLIFF 1.1
namespace: demo
clan: settings
source-language: en-US
target-language: zh-CN
title: "Demo application settings"
standard: "Keep UI terms short."
dependency: ["settings-terms.zh-CN.cliff"]

[video]
context: "Video settings screen."
type: label
emotion: [objective]
max-width: 12

<resolution>
source: "Resolution"
target: "分辨率"
status: final
reference: ["src/ui/video.cpp:42"]

<hdr-toggle>
source: "Enable HDR"
target: "启用 HDR"
type: label
emotion: [objective, calm]
status: final
context: "Toggle beside the resolution dropdown."

The shape of a value declares its type: brackets hold a list, quotes hold text,
a bare lowercase word is a tag or an identifier. emotion, dependency and
reference are the list-typed fields, so their values sit inside brackets at
every length. Inside a string, an escaped quote stays escaped: source,
context and every other field come through exactly as received.

max-width counts display cells: Latin and digits 1, Han and fullwidth 2.

THE SHAPE OF YOUR ANSWER
Your answer is one CLIFF document with the same structure as the file you
received: the same version line, the same header keys, the same section paths
in the same order, and the same entry markers in the same order. Each entry
marker appears once. Each field of an entry appears once. The answer ends
after the last field of the last entry.
Your work goes into the target field of each entry, and into status.

TERMINOLOGY (specification 13.2)
A file with 'variant: glossary' holds terms rather than sentences, and it is a
deliverable of translation as well as an input. Append one when terminology is
widespread or highly repeated: a naming policy, many repeated product or domain
terms, or renderings that must stay consistent across the file. A concise
glossary contains one entry per such term and ends after the last one. Each
entry carries the source term and the rendering you used.

--- SPEC SUPPLEMENT ---
{spec_supplement()}"""
