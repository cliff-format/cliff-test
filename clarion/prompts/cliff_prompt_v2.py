"""Example-driven CLIFF prompt, scoped to what a tolerant reader cannot repair.

Design, and the measurements it comes from.

The recorded `deepseek-flash` run prices CLIFF's `format instructions` at about
46 400 tokens per arm, of which **16 316 tokens per cell is the full text of
`cliff-1.1.0.md`**. In the plain arm CLIFF's instructions cost more than twice the
document they describe. The redesign replaces that text with examples plus the
smallest set of stated facts that still prevents *failures*.

The fact set is bounded by an empirical probe of the repair boundary
(`../.tools/probe_repairs.py`, a working-copy script beside the checkouts and not
part of this repository), not by taste. The boundary it found is pinned **in-repo**
by `tests/fixtures/tolerant/` and `tests/clarion/test_prompt_v2.py`, which is what a
reader can check; the probe is the instrument that drew it. Under the tolerant
reading the harness uses:

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

So this module states three things and nothing else:

* ``KEYS_BY_SCOPE`` - the exact key names, and which scope each is legal in. This
  is what the recorded run's D7 failures violated, and Appendix C.5 forbids a
  parser from repairing it: "repair what I can infer you meant" is the guessing
  the appendix exists to prevent.
* ``VOCABULARIES`` - the closed tag sets, because a value outside them is
  reported as a vocabulary error in both readings.
* ``CLIFF_TASK_RULES`` - what we need back, as properties of the delivered file:
  the translation in ``target`` with ``status`` set, the source and every id and
  header value as they were, the keys of the table above, the file's own layout,
  and each text value as one quoted string.

Everything else - spacing, quoting, brackets, layout, style - is taught by
``EXAMPLES``, which are real conforming documents.

Two rules govern the wording, and ``tests/clarion/test_tools.py`` holds both.
Everything is stated **affirmatively**: a sentence that names the failure
("an unquoted text value cannot be repaired") describes a shape a model can
produce, so the failure lives in this file's fact table and in the test, not in the
prompt. And the prompt constrains **only what the specification requires and what
we need back**: no block here may fence *how* the model works, because reproducing
the file it was given and editing the text is a good way to arrive at the answer.
`docs/clarion-prompt-design.md` records the rule and what it removed.

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
#:
#: Phrased affirmatively throughout, and deliberately so. CLIFF is a format the
#: model has no prior for, so the prompt has to say what to write; a sentence that
#: names the failure ("do not invent a field") also describes it, and a description
#: of a failure is a thing a model can produce. Every line below is therefore a
#: statement of what the file contains, not of what to avoid.
CLIFF_FACTS = f"""CLIFF 1.1 — A LINE-ORIENTED TRANSLATION FILE

An entry starts with a line of the form <entry-id>; the `key: value` lines under
it are that entry's fields. A section starts with `[group.path]`, and its keys are
inherited by the entries below it.

KEYS AND THEIR SCOPE — each key belongs to the scope it is listed under

{_row("header", KEYS_BY_SCOPE["header"]["required"] + KEYS_BY_SCOPE["header"]["optional"])}
{_row("[group]", KEYS_BY_SCOPE["group"]["optional"])}
{_row("<entry>", KEYS_BY_SCOPE["entry"]["required"] + KEYS_BY_SCOPE["entry"]["optional"])}

Required: `namespace`, `clan`, `source-language`, `target-language` in the header;
`source` and `status` on every entry; `type` on the entry or inherited from its
group.

`status` is an entry key. A group carries `context`, `type`, `emotion` and
`max-width`.

CLOSED VOCABULARIES — write one of these values

  type
{_vocabulary("type")}

  emotion (a list of one or more)
{_vocabulary("emotion")}

  status (entry only)
{_vocabulary("status")}

  variant (header only)
{_vocabulary("variant")}
"""

#: What we need back. Every item is a property of the delivered file, so the list
#: states the product and leaves the working method to the model: reproducing the
#: file it was given and editing the text is a perfectly good way to arrive at it,
#: and a prompt that fenced that would be spending tokens on the model's process
#: instead of on the result. The earlier wording was imperative ("Write the source
#: text..., Follow the layout...") and read as instructions for how to work.
CLIFF_TASK_RULES = """WHAT WE NEED IN CLIFF

1. The translation of each entry, in that entry's `target` field, with the entry's
   `status` set to `translated`.
2. Every context, type, emotion, width and reference field, and every header
   value, exactly as they appear in the file you were given, escaping included.
3. The keys in the table above, each in the scope it is listed under, once per
   scope. (`reference` is spelled `reference`; context is spelled `context`.)
4. The layout and conventions of the file you were given; the examples below show
   the shape.
5. Each text value as one quoted string, with its final punctuation inside the
   quotes and the closing quote last on the line:
   `context: "Reviewed in the 2026 audit."`. Inside a list, each item is a quoted
   string: `reference: ["src/ui/panel.cpp:42"]`."""

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
