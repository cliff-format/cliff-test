"""The CLIFF 1.1 specification, compressed to its normative content.

Why this exists, next to the hand-written example-driven prompt: the format's own
text is 16 656 tokens, of which only **2 467 are sentences that state a rule**
(MUST / SHOULD / MAY / REQUIRED). The rest is rationale, worked examples,
comparisons with other formats, migration notes and design discussion - material a
model reproducing a file has no use for, and material that costs tokens on every
call.

This module assembles the rules themselves and nothing else, **derived from the
specification repository at prompt-build time**:

* the normative ABNF, comments stripped (``grammar_only``);
* the ABNF's trailing semantic-constraint block, which is where the rules a
  grammar cannot express already live (``semantic_constraints``);
* the field tables of sections 7, 8 and 9, extracted from the specification's own
  markdown tables so the key names, required flags and inheritance cannot drift
  from the document;
* the closed vocabularies, read from the specification's reference tables;
* the specification's own quick example (section 3), not one of ours.

Nothing here is written by hand, which is the point: a compressed restatement
somebody maintains by hand is a second source of truth, and the second source of
truth is the one that goes stale. Everything a reader sees in the prompt can be
traced to a line of the specification, and ``tests/clarion/test_spec_digest.py``
holds that trace: the key tables are compared against the parser's key sets, the
vocabularies against the implementation's, and every section of the specification
that states a rule is either represented here or listed in ``SECTION_COVERAGE``
with the reason it is not.
"""

from __future__ import annotations

import re
from functools import lru_cache

from ..paths import SPEC_FILE
from ..util import read_text
from .spec_digest import (
    STATUS_TAGS,
    emotion_tags,
    grammar_only,
    semantic_constraints,
    type_tags,
)

#: Where each specification section's rules end up in this digest. A section that
#: states a rule (MUST / SHOULD / MAY) and is not represented has to say why not,
#: so a new normative section cannot be dropped silently by a compression pass.
#: Sections that only explain, motivate or illustrate are marked "informative"
#: and need no further justification.
SECTION_COVERAGE: dict[str, str] = {
    "1": "informative - motivation",
    "2": "informative - goals",
    "3": "example - the quick example is carried verbatim",
    "4": "abnf - conformance duties restated in the semantic constraints",
    "5": "abnf - lexical structure is the grammar itself",
    "6": "abnf - syntax is the grammar itself",
    "7": "table - header fields",
    "8": "table - entry fields",
    "9": "table - group inheritance",
    "10": "abnf - identifier rules are in the semantic constraints",
    "11": "excluded - file layout and naming are packaging, not file content",
    "12": "vocab - the closed sets, read from the reference tables",
    "13": "table - the variant, its shape (13.2.1) and the two-document boundary "
    "(13.2.2.2) are all stated; the glossary ablation in the design document is why "
    "the boundary is spelled out rather than implied",
    "14": "abnf - ICU is payload; brace balance is in the semantic constraints",
    "15": "table - max-width is an entry and group field",
    "16": "table - dependency is a header field",
    "17": "excluded - canonical serialization is a writer/reader tool concern, not "
    "something the answer has to satisfy",
    "18": "informative - interoperability with other formats",
    "19": "excluded - resource limits are an implementation duty, not a file rule",
    "20": "abnf - extension fields are ordinary keys with an x- prefix",
    "21": "abnf - the version rule is in the grammar and the semantic constraints",
    "C": "excluded - tolerant parsing describes what a reader may repair, and the "
    "design deliberately spends no prompt token on repairable shapes",
}

#: The specification's field tables, by section number, in the order they appear.
_TABLE_SECTIONS = ("7", "8", "9")

_KEY_RE = re.compile(r"`([^`]+)`")


@lru_cache(maxsize=1)
def _sections() -> dict[str, str]:
    """The specification's sections, keyed by their number as a string."""
    text = read_text(SPEC_FILE) if SPEC_FILE.exists() else ""
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        heading = re.match(r"^## (\d+)\.", line)
        appendix = re.match(r"^## Appendix ([A-Z])\.", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
        elif appendix:
            current = appendix.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {key: "\n".join(value) for key, value in sections.items()}


def _cells(line: str) -> list[str]:
    """The cells of a markdown table row, without the outer pipes."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _required(value: str) -> str:
    cleaned = value.replace("**", "").strip()
    if cleaned.lower().startswith("required"):
        # "required (direct or inherited)" is still required; the parenthetical is
        # the inheritance note, which the inherited column states separately.
        return "required"
    return ""


def _table_rows(section: str) -> list[tuple[str, str, str, str]]:
    """The (key, type, required, inherited) rows of one section's field table.

    The inherited flag is read from the section-8 column named "Inherited from
    group", not from a substring match on the whole row: a substring match caught
    only `type` (whose *required* cell happens to say "direct or inherited") and
    silently dropped `emotion`, `context` and `max-width`, which inherit too.
    """
    body = _sections().get(section, "")
    rows: list[tuple[str, str, str, str]] = []
    header: list[str] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if not header:
            header = [cell.lower() for cell in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        keys = _KEY_RE.findall(cells[0])
        if not keys:
            continue
        inherited = ""
        for name, value in zip(header, cells, strict=False):
            if name.startswith("inherit") and value.replace("**", "").strip().lower() == "yes":
                inherited = "inherited"
        required = _required(cells[2]) if len(cells) > 2 else ""
        rows.append((keys[0], cells[1].replace("**", "").strip(), required, inherited))
    return rows


@lru_cache(maxsize=1)
def field_tables() -> str:
    """The field tables of sections 7 and 8, and the inheritance rule of section 9.

    Rendered from the specification's markdown tables, so the key list cannot
    drift from the document: a key added to section 8 appears here on the next
    prompt build, and ``tests/clarion/test_spec_digest.py`` compares the result
    against the key sets the parser actually accepts.
    """
    lines: list[str] = []
    for section, label in (("7", "HEADER"), ("8", "ENTRY")):
        lines.append(f"{label} FIELDS")
        for key, kind, required, inherited in _table_rows(section):
            flags = [flag for flag in (required, inherited) if flag]
            suffix = f"  ({', '.join(flags)})" if flags else ""
            lines.append(f"  {key:<16}{kind}{suffix}")
        lines.append("")

    # Section 9 is prose, not a table: the group keys and what inherits.
    inherited = [key for key, _, _, flag in _table_rows("8") if flag == "inherited"]
    lines.append("GROUP FIELDS (the [section.path] line, before the section's first entry)")
    lines.append("  context  type  emotion  max-width")
    lines.append(
        "  " + ", ".join(inherited) + " may be given on the group instead of on every "
        "entry: the entry value overrides the group value, lists do not merge, and at "
        "least one of the two provides type. context is joined, group value then entry "
        "value with one space. No other entry field is inherited."
    )
    return "\n".join(lines)


@lru_cache(maxsize=1)
def quick_example() -> str:
    """The specification's own quick example (section 3), verbatim."""
    body = _sections().get("3", "")
    blocks = re.findall(r"```cliff\n(.*?)```", body, re.S)
    return blocks[0].strip() if blocks else ""


#: The rule the model breaks most stubbornly, quoted from the specification and
#: injected repeatedly: at the top of the block (primacy), again at its end, and in
#: the user message immediately before the document (recency - the last thing read
#: before the answer starts). Stray closing tags survived every single statement of
#: this rule (2-5 of 48 answers under every prompt variant measured here), so the
#: next lever is position and repetition rather than another sentence. The ABNF's own
#: words are quoted because they are the specification's statement of it, and because
#: that comment is one of the comments ``grammar_only()`` strips.
MARKER_RULE = """SECTIONS AND ENTRIES ARE SINGLE LINES - nothing in a CLIFF file is closed

  A section line `[group.path]` opens a section; an entry line `<id>` opens an entry.
  Each is one line standing alone, and what it opens runs until the next such line or
  the end of the document. The specification states it of an entry line in exactly
  these words: "single-line marker; no closing tag exists". So the last thing in the
  answer is the last field of the last entry, `<` and `>` inside a string are ordinary
  text, and no line of a CLIFF file exists to close anything."""


@lru_cache(maxsize=1)
def build_normative_rules() -> str:
    """The compressed CLIFF 1.1: the rules, and nothing but the rules."""
    types = ", ".join(type_tags())
    emotions = ", ".join(emotion_tags())
    status = ", ".join(STATUS_TAGS)
    return f"""CLIFF 1.1 - THE SPECIFICATION, COMPRESSED TO ITS RULES

{MARKER_RULE}

The normative grammar, in ABNF (RFC 5234). It is the definition of the format, and
its first production is the whole of what an answer is: one `cliff-file`, from its
version line to its last field. The constraints after the grammar state the rules
a grammar cannot express.

--- GRAMMAR ---
{grammar_only()}
--- END GRAMMAR ---

SEMANTIC CONSTRAINTS (normative)
{semantic_constraints()}

{field_tables()}

CLOSED VOCABULARIES (section 12; a value outside its set is an error)
  type      {types}
  emotion   {emotions}
  status    {status}
  variant   standard, glossary

A CONFORMING FILE (the specification's own quick example, section 3)

{quick_example()}

ESCAPING (sections 5.7 and 6.2)

  A value is a C-style string literal. Five characters are written with a
  backslash inside it: the double quote (\\"), the backslash itself (\\\\), newline
  (\\n), carriage return (\\r) and tab (\\t) - those five are the whole escape set.
  So a value that contains a quote has \\" at that point, however long the value is,
  and the file you were given already spells it that way: the source text and every
  other value come through with their backslashes exactly as written. Chinese,
  Japanese and Korean curly quotes (\u201c \u201d \u300c \u300d) are ordinary characters and are
  written as they are, with no backslash.

VARIANT: glossary (section 13)

A glossary is the same grammar with variant: glossary: one term per entry, unique
ids, source the term and target its canonical rendering. It is a deliverable of
translation as well as an input, so a term decided while translating is recorded in
one. Section 13.2.2 states the criterion: add the document when the brief asks for
terminology consistency or a naming policy, when a term recurs across entries, or
when a naming judgement would otherwise be re-made differently. The rendering
recorded is the rendering used in the translated file.

Its shape, from section 13.2.1: the header carries variant: glossary, and the clan
of the glossary is the clan it serves with the suffix -terms (settings becomes
settings-terms; a glossary shared by a whole project uses the clan terms). The
entries sit in a section, by convention [terms], one term per entry, each carrying
source (the term), target (the rendering used), type (a term-level tag from the
closed set above), status, and context saying why that rendering was chosen.

Two documents are then one answer. A second document is recognised by its own
version line, so the glossary begins with its own CLIFF 1.1 line placed immediately
after the last field of the translated file, and each document is complete in
itself: the translated file is the first, the glossary is the second.

{MARKER_RULE}"""


def normative_rule_tokens(tokenizer) -> int:
    """The token cost of the compressed specification under *tokenizer*."""
    return tokenizer.count(build_normative_rules())
