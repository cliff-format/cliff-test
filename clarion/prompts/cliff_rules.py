"""The CLIFF 1.1 specification, compressed to its normative content.

Why this exists, next to the hand-written example-driven prompt: the format's own
text is 16 803 tokens, of which only **2 492 are sentences that state a rule**
(MUST / SHOULD / MAY / REQUIRED). The rest is rationale, worked examples,
comparisons with other formats, migration notes and design discussion - material a
model reproducing a file has no use for, and material that costs tokens on every
call.

This module assembles the rules themselves and nothing else. Most of the block is
**read out of the specification repository at prompt-build time**:

* the normative ABNF, comments stripped (``grammar_only``);
* the ABNF's trailing semantic-constraint block, which is where the rules a
  grammar cannot express already live (``semantic_constraints``);
* the field tables of sections 7, 8 and 9, extracted from the specification's own
  markdown tables so the key names, required flags and inheritance cannot drift
  from the document;
* the closed vocabularies, read from the specification's reference tables;
* the specification's own quick example (section 3), not one of ours.

The rest - the framing and the rules that exist only because a *prompt* needs
them - is written here, and is named in ``WRITTEN_HERE`` with the section whose
rule it carries, so a reader knows which paragraphs to review by hand instead of
assuming a build-time extraction that does not cover them. They are the intro, the
marker rule, the framing line of the vocabularies, the group note, the escaping
paragraph and the glossary section. The two claims that
matter are held by tests: the extracted parts cannot drift from the specification
(the key tables are compared against the parser's key sets, the vocabularies
against the implementation's, the extraction is proven to read the specification
rather than a copy), and every section of the specification that states a rule is
either represented here or listed in ``SECTION_COVERAGE`` with the reason it is
not.
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
#: and need no further justification. The kind before the dash is a closed
#: vocabulary of its own - `abnf`, `table`, `vocab`, `prose`, `example`,
#: `informative`, `excluded` - and ``tests/clarion/test_spec_digest.py`` refuses a
#: reason that opens with anything else, so a mislabelled section is caught rather
#: than read.
SECTION_COVERAGE: dict[str, str] = {
    "1": "informative - motivation",
    "2": "informative - goals",
    "3": "example - the quick example is carried verbatim",
    "4": "abnf - conformance duties restated in the semantic constraints",
    "5": "abnf - lexical structure is the grammar itself, and 5.7 by the escape "
    "paragraph below",
    "6": "abnf - syntax is the grammar itself, and 6.2 by the escape paragraph below",
    "7": "table - header fields",
    "8": "table - entry fields",
    "9": "table - group inheritance",
    "10": "abnf - identifier rules are in the semantic constraints",
    "11": "excluded - file layout and naming are packaging, not file content",
    "12": "vocab - the closed sets, read from the reference tables",
    "13": "prose - the variant, its shape (13.2.1) and the two-document boundary "
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

#: The parts of the block that are **written here** rather than read from the
#: specification repository, keyed by a short name and valued with the section
#: whose rule the paragraph carries. Everything else in ``build_normative_rules``
#: is extracted from the specification at build time. These are the paragraphs a
#: reader has to review by hand - the module docstring used to claim there were
#: none, which is the kind of claim that stops a review from happening - and
#: ``tests/clarion/test_spec_digest.py`` asserts each named part is really in the
#: block, so a rename or a removal fails there instead of in a paid run.
WRITTEN_HERE: dict[str, str] = {
    "intro": "4 - what one `cliff-file` is, stated before the grammar",
    "marker": "6 - the single-line marker rule, as a reading instruction",
    "framing": "12 - the line that introduces the closed vocabularies",
    "group-note": "9 - what inherits and how the group and entry values combine",
    "escaping": "5.7 and 6.2 - the escape set and what stays an ordinary character",
    "glossary": "13.2 - the variant, its shape and the two-document boundary",
}

#: The field tables of sections 7 to 9, in the order they are rendered.
_TABLE_SECTIONS = ("7", "8", "9")

_KEY_RE = re.compile(r"`([^`]+)`")


#: The framing line above the closed vocabularies, and the vocabularies themselves.
VOCAB_FRAMING = "CLOSED VOCABULARIES (section 12; a value outside its set is an error)"

#: What the grammar below is for, in one sentence, before it is read.
INTRO = """The normative grammar, in ABNF (RFC 5234). It is the definition of the format, and
its first production is the whole of what an answer is: one `cliff-file`, from its
version line to its last field. The constraints after the grammar state the rules
a grammar cannot express."""


def group_note() -> str:
    """Section 9's inheritance rule, as the field tables can state it."""
    inherited = [key for key, _, _, flag in _table_rows("8") if flag == "inherited"]
    return (
        "GROUP FIELDS (the [section.path] line, before the section's first entry)\n"
        "  context  type  emotion  max-width\n"
        "  " + ", ".join(inherited) + " may be given on the group instead of on every "
        "entry: the entry value overrides the group value, lists do not merge, and at "
        "least one of the two provides type. context is joined, group value then entry "
        "value with one space. No other entry field is inherited."
    )


#: The escape rule of sections 5.7 and 6.2. Written here because the grammar states
#: the production and the model needs the rule: which characters take a backslash,
#: and which ones that look like they might - the CJK curly quotes - do not.
ESCAPE_PARAGRAPH = """ESCAPING (sections 5.7 and 6.2)

  A value is a C-style string literal. Five characters are written with a
  backslash inside it: the double quote (\\"), the backslash itself (\\\\), newline
  (\\n), carriage return (\\r) and tab (\\t) - those five are the whole escape set.
  So a value that contains a quote has \\" at that point, however long the value is,
  and the file you were given already spells it that way: the source text and every
  other value come through with their backslashes exactly as written. Chinese,
  Japanese and Korean curly quotes (\u201c \u201d \u300c \u300d) are ordinary characters and are
  written as they are, with no backslash."""


#: Section 13.2: the variant, its shape and the boundary between the two documents.
#: The boundary is the one rule here the specification does not state in a form a
#: prompt can use, which is why it is written out rather than pointed at.
GLOSSARY_SECTION = """VARIANT: glossary (section 13)

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
itself: the translated file is the first, the glossary is the second."""


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
    """The field tables of sections 7 to 9, and the inheritance rule of section 9.

    Rendered from the specification's markdown tables, so the key list cannot
    drift from the document: a key added to section 8 appears here on the next
    prompt build, and ``tests/clarion/test_spec_digest.py`` compares the result
    against the key sets the parser actually accepts.
    """
    lines: list[str] = []
    labels = {"7": "HEADER", "8": "ENTRY"}
    for section in _TABLE_SECTIONS[:-1]:
        lines.append(f"{labels[section]} FIELDS")
        for key, kind, required, inherited in _table_rows(section):
            flags = [flag for flag in (required, inherited) if flag]
            suffix = f"  ({', '.join(flags)})" if flags else ""
            lines.append(f"  {key:<16}{kind}{suffix}")
        lines.append("")

    # Section 9 is prose, not a table: the group keys and what inherits.
    lines.append(group_note())
    return "\n".join(lines)


@lru_cache(maxsize=1)
def quick_example() -> str:
    """The specification's own quick example (section 3), verbatim."""
    body = _sections().get("3", "")
    blocks = re.findall(r"```cliff\n(.*?)```", body, re.S)
    return blocks[0].strip() if blocks else ""


#: The rule the model breaks most stubbornly, injected repeatedly: at the top of the
#: block (primacy), again at its end, and in the user message immediately before the
#: document (recency - the last thing read before the answer starts). Stray closing
#: tags survived every single statement of it, so the next lever was position and
#: repetition, and the statement itself was rewritten to remove every markup cue the
#: prompt had been leaking: the specification's own words ("no closing tag exists"),
#: an XLIFF attribution for the status tags, and - worst of the three - the literal
#: `</terms>` the C.5 note used as its example, which put the very string in the
#: prompt that the model then emitted. What is left is a statement of what a marker
#: *is* and how far it runs.
MARKER_RULE = """SECTIONS AND ENTRIES ARE SINGLE LINES

  A section line `[group.path]` opens a section; an entry line `<id>` opens an entry.
  Each is a label on one line standing alone, and what it opens runs until the next
  such line or the end of the document. So the last thing in the answer is the last
  field of the last entry, and inside a string `<` and `>` are ordinary characters
  like any other."""


def block_parts() -> list[tuple[str, str]]:
    """The block, as labelled parts, in the order a reader meets them.

    The block is assembled from this list rather than from one f-string so that its
    decomposition is exact: the parts are the block, which is what lets
    ``docs/clarion-prompt-design.md`` publish a per-part cost that
    ``tests/clarion/test_spec_digest.py`` reproduces instead of trusting. The first
    and last parts are the same marker rule on purpose - see ``MARKER_RULE``.
    """
    types = ", ".join(type_tags())
    emotions = ", ".join(emotion_tags())
    status = ", ".join(STATUS_TAGS)
    vocabularies = (
        f"{VOCAB_FRAMING}\n\n"
        f"  type      {types}\n"
        f"  emotion   {emotions}\n"
        f"  status    {status}\n"
        f"  variant   standard, glossary"
    )
    return [
        ("title", "CLIFF 1.1 - THE SPECIFICATION, COMPRESSED TO ITS RULES"),
        ("marker-rule", MARKER_RULE),
        ("intro", INTRO),
        ("grammar", "--- GRAMMAR ---\n" + grammar_only() + "\n--- END GRAMMAR ---"),
        ("semantic-constraints", "SEMANTIC CONSTRAINTS (normative)\n" + semantic_constraints()),
        ("field-tables", field_tables()),
        ("vocabularies", vocabularies),
        (
            "quick-example",
            "A CONFORMING FILE (the specification's own quick example, section 3)\n\n"
            + quick_example(),
        ),
        ("escaping", ESCAPE_PARAGRAPH),
        ("glossary", GLOSSARY_SECTION),
        ("marker-rule-again", MARKER_RULE),
    ]


@lru_cache(maxsize=1)
def build_normative_rules() -> str:
    """The compressed CLIFF 1.1: the rules, and nothing but the rules."""
    return "\n\n".join(text for _, text in block_parts())


def block_decomposition(tokenizer) -> dict[str, int]:
    """The token cost of each part of the block under *tokenizer*.

    The published per-part breakdown, reproducible on demand. Each part is measured
    on its own, so the parts do not sum to the block exactly: a token boundary at a
    join is shared, and pretending otherwise would make the published rows add up by
    construction while being wrong about what one block costs.
    """
    return {label: tokenizer.count(text) for label, text in block_parts()}


def normative_rule_tokens(tokenizer) -> int:
    """The token cost of the compressed specification under *tokenizer*."""
    return tokenizer.count(build_normative_rules())
