"""Example-driven CLIFF prompt, scoped to what a tolerant reader cannot repair.

Design, and the measurements it comes from.

The recorded `deepseek-flash` run prices CLIFF's `format instructions` at about
46 400 tokens per arm, of which **16 316 tokens per cell is the full text of
`cliff-1.1.0.md`**. In the plain arm CLIFF's instructions cost more than twice the
document they describe. The redesign replaces that text with examples plus the
smallest set of stated facts that still prevents *failures*.

The fact set is bounded by an empirical probe of the repair boundary
(`.tools/probe_repairs.py`), not by taste. Under the tolerant reading the harness
uses:

  repaired (so NOT worth prompt tokens)   unrepairable (must be stated)
  ------------------------------------   -------------------------------------
  C.2.3 quoted tag                       an unknown key, in any scope
  C.2.1 bare scalar in a list field      `status` in group scope
  C.2.4 quoted entry id                  a tag outside its closed vocabulary
  C.2.7 quoted key                       a missing `target` with `status: translated`
  C.2.2 repeated field                   an unbalanced ICU brace
  C.2.6 version-line spelling            an unquoted string
  C.2.5 identifier with reserved chars

Rule 5 of `CLIFF_TASK_RULES` states the last of those, and only that one: the
quoting of a *tag* is repairable (C.2.3) and the brackets around a list are
repairable (C.2.1), but an unquoted text value has no determinate end and is
refused, in a scalar and inside a list alike. The 1.3 edit run is what put it
there: two of its four invalid answers were a text value written without quotes.

C.2.7 is the case that shows why the boundary is drawn where it is: the repair
removes the quotes and then checks the word against the legal keys of its scope,
so a quoted *unknown* key is still refused. It cannot legalize anything, which is
what makes it safe to leave out of the prompt; see
`tests/fixtures/tolerant/quoted-unknown-key.zh-CN.cliff`.

A repair is still recorded and reported as a cost (`repairs` per row), which is
where shape untidiness belongs: it is priced, not prevented. Spending instruction
tokens on it would pay twice for something the reader already handles.

So this module states two things and nothing else:

* ``KEYS_BY_SCOPE`` - the exact key names, and which scope each is legal in. This
  is what the recorded run's D7 failures violated, and Appendix C.5 forbids a
  parser from repairing it: "repair what I can infer you meant" is the guessing
  the appendix exists to prevent.
* ``VOCABULARIES`` - the closed tag sets, because a value outside them is
  reported as a vocabulary error in both readings.

Everything else - spacing, quoting, brackets, layout, style - is taught by
``EXAMPLES``, which are real conforming documents.

Every claim here is checked against ``cliff_format`` by
``tests/clarion/test_prompt_v2.py``, because a wrong claim would teach a model to
write a file no validator accepts and no tolerant read can save.
"""

from __future__ import annotations

#: Legal keys per scope, with whether the scope requires them. Verified against
#: ``cliff_format.parser`` (HEADER_KEYS / GROUP_KEYS / ENTRY_KEYS) and the
#: required-field rules of specification 7 and 8.
KEYS_BY_SCOPE: dict[str, dict[str, tuple[str, ...]]] = {
    "header": {
        "required": ("namespace", "clan", "source-language", "target-language"),
        "optional": (
            "version",
            "variant",
            "title",
            "info",
            "standard",
            "dependency",
        ),
    },
    "group": {
        "required": (),
        "optional": ("context", "type", "emotion", "max-width"),
    },
    "entry": {
        "required": ("source", "status"),
        "optional": (
            "target",
            "type",
            "emotion",
            "context",
            "max-width",
            "reference",
            "reviewer",
        ),
    },
}

#: Closed vocabularies. A value outside these sets is a vocabulary error in both
#: readings, so these belong in the prompt.
VOCABULARIES: dict[str, tuple[str, ...]] = {
    "type": (
        "noun", "verb", "adjective", "adverb", "pronoun", "numeral",
        "preposition", "conjunction", "particle", "interjection", "proper-noun",
        "noun-phrase", "verb-phrase", "adjective-phrase", "adverb-phrase",
        "fixed-phrase", "idiom",
        "sentence", "description", "narration", "dialogue", "monologue",
        "prompt", "label", "subtitle", "accessibility-cue",
    ),
    "emotion": (
        "neutral", "objective", "mechanical", "joyful", "sad", "angry",
        "fearful", "surprised", "curious", "disgusted", "anxious", "calm",
        "playful", "serious", "urgent", "romantic", "hopeful", "grateful",
        "formal", "informal", "polite", "rude", "nostalgic",
    ),
    "status": ("initial", "translated", "reviewed", "final"),
    "variant": ("standard", "glossary"),
}

#: The list-typed fields. Their values are brackets in every example; the
#: tolerant reader also accepts a bare scalar and records a repair, so this is
#: stated as a fact about the field, not as a rule to obey.
LIST_TYPED = ("emotion", "dependency", "reference")


def _row(name: str, keys: tuple[str, ...]) -> str:
    return f"  {name:<9}{', '.join(keys) if keys else '(none)'}"


def _vocabulary(label: str) -> str:
    values = VOCABULARIES[label]
    lines: list[str] = []
    current = "          "
    for value in values:
        candidate = f"{current}{value}, "
        if len(candidate) > 78:
            lines.append(current.rstrip())
            current = "          "
            candidate = f"{current}{value}, "
        current = candidate
    lines.append(current.rstrip().rstrip(","))
    return "\n".join(lines)


#: The stated facts. Two jobs only: which key where, and which values exist.
CLIFF_FACTS = f"""CLIFF 1.1 — FIELD NAMES AND THEIR SCOPE

A field name is only legal in the scope listed below. Any other name, in any
scope, makes the file invalid; do not invent a field, and do not move one to
another scope.

{_row("header", KEYS_BY_SCOPE["header"]["required"] + KEYS_BY_SCOPE["header"]["optional"])}
{_row("[group]", KEYS_BY_SCOPE["group"]["optional"])}
{_row("<entry>", KEYS_BY_SCOPE["entry"]["optional"])}

Required: `namespace`, `clan`, `source-language`, `target-language` in the
header; `source` and `status` on every entry, plus `type` either on the entry or
inherited from its group.

Read the `status` row carefully: `status` exists on an **entry only**. A group
section accepts `context`, `type`, `emotion` and `max-width`, and nothing else.

CLOSED VOCABULARIES — these values exist, and no others

  type
{_vocabulary("type")}

  emotion (a list of one or more)
{_vocabulary("emotion")}

  status (entry only)
{_vocabulary("status")}

  variant (header only)
{_vocabulary("variant")}
"""

#: What the model does with the file. Verbs, not syntax.
CLIFF_TASK_RULES = """WHAT TO CHANGE

1. Write the translation of every entry into its `target` field, and set that
   entry's `status` to `translated`.
2. Everything else comes through unchanged and byte for byte: the source text,
   every id and group path, every context, type, emotion, width and reference,
   and every header value. Escaping included - a lost backslash changes the text.
3. Do not add, drop, reorder or rename a field. If an entry looks like it needs a
   field that is not in the table above, it does not: use the field that exists.
   (`reference` is spelled `reference`; context is spelled `context`.)
4. Keep the file's own layout and conventions. The examples below show the shape;
   follow the file you were given wherever it differs.
5. A text value is one quoted string, and the whole value is inside the quotes -
   final punctuation included. `context: "Reviewed in the 2026 audit."` is right;
   `context: Reviewed in the 2026 audit.` and `context: "Reviewed.".;` are not, and
   neither is text left after the closing quote. The same holds inside a list:
   `reference: ["src/ui/panel.cpp:42"]`. An unquoted text value is the one shape
   error nothing downstream can repair, so it is worth checking."""

#: Two conforming documents. The first shows every construct; the second shows the
#: only other document shape CLIFF has (a terminology glossary).
EXAMPLES = """EXAMPLES — THE SHAPE OF A CORRECT ANSWER

Content is invented; the shape is what matters.

--- a complete file ---
CLIFF 1.1
namespace: studio
clan: settings
source-language: en-US
target-language: zh-CN
version: "1.4.2"
title: "Settings strings"
info: "The end-user settings screens." "A second quoted string continues the value:"
  "adjacent strings are concatenated with nothing inserted between them."
standard: "Keep UI labels short."
dependency: ["settings-terms.zh-CN.cliff"]

[video]
context: "Video settings screen."
type: label
emotion: [objective]
max-width: 12

<resolution>
source: "Resolution"
target: "分辨率"
type: noun
status: translated
context: "Dropdown label above the resolution list."

<fullscreen>
source: "Fullscreen"
target: "全屏"
status: translated
emotion: [neutral, calm]

[notifications]
context: "Notification centre."
type: sentence

<unread-count>
source: "{count, plural, =0 {No unread alerts} other {# unread alerts}}"
target: "{count, plural, =0 {没有未读提醒} other {# 条未读提醒}}"
status: translated
context: "Placeholders stay character for character; only the words inside change."

<quoted-example>
source: "He said \\"yes\\" twice."
target: "他说了两遍\\"好\\"。"
status: translated

--- a terminology glossary, only when the task asks for one ---
CLIFF 1.1
namespace: studio
clan: settings-terms
source-language: en-US
target-language: zh-CN
variant: glossary
title: "Terms decided while translating settings"

[terms]
type: noun

<BlockOfGrass>
source: "草方块"
target: "The Block of Grass"
type: fixed-phrase
status: translated
context: "Product term; the article must be preserved."
"""
