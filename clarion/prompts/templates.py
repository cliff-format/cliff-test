"""Prompt building blocks.

Editing these strings is the supported way to tune CLARION's prompting. Each
block is measured separately in the token budget, so a report can always say
how many tokens the instructions cost versus the document itself.
"""

from __future__ import annotations

# The last sentence states the deliverable and nothing about the method. It used
# to read "You always return a complete file, never a diff and never a commentary",
# which fenced how the model may work (reproducing the file and editing it is a
# perfectly good way to produce the answer) and did it in the negative - and a
# sentence that names a failure shape is a sentence a model can act on. What we
# need from the model is the translated file; how it gets there is its own business.
SYSTEM_ROLE = """You are a professional localization translator and localization engineer.
You translate product, literary, legal and game content between languages, and you
edit localization resource files without breaking their structure.
We need the translated file itself, complete: the file we gave you, with its text
in the target language and its structure intact."""

TASK_RULES = """Translate the localization file below from {source_language} into {target_language}.

WHAT WE NEED
1. The translated file, complete: the file that appears under "FILE TO TRANSLATE",
   in the format you received it, opening with that file's first line and closing
   with its last. Reference material such as a glossary is context for your
   reading.
2. Every identifier, key, group path and structural element of that file, as it
   appears in the file you were given.
3. The source text verbatim; your work goes into the translation.
4. Every placeholder and ICU MessageFormat construct character for character -
   {{count, plural, ...}}, {{name}}, %s, %1$s, {{{{...}}}}, and any tag-like payload a
   string happens to carry - with the human-readable text inside them translated.
5. Meaning translated: register, tone and wordplay natural in {target_language}.
6. The brief the file carries - context, terminology, tone, width - applied as
   written."""

OUTPUT_RULES_BILINGUAL = """Fill in the translation for every entry, in the field this format uses
for the target text; the source field keeps the source text as it is."""

OUTPUT_RULES_MONOLINGUAL = """This file is a resource file in the source language: each key maps to
its source text. Return the same file with every value replaced by its
{target_language} translation, keeping every key unchanged."""

FORMAT_NOTES = {
    "cliff": """This file is CLIFF 1.1, a line-oriented localization format.
Each entry starts with a line of the form <entry-id>. Fields are flat
key: value lines that belong to the entry above them. Write the translation as
the target field of each entry and set status: translated.
Every string is quoted, and a double quote INSIDE a string must stay escaped as
\\" exactly as it appears in the file you received. Copy context, source and
every other field through unchanged, escaping included - dropping one backslash
invalidates the whole file.""",
    "xliff-2.1": """This file is XLIFF 2.1. Each translation unit is a unit element with a
segment containing source and target. Add or fill the target element of every
segment and set state to translated.""",
    "xliff-2.2": """This file is XLIFF 2.2. Each translation unit is a unit element with a
segment containing source and target. Add or fill the target element of every
segment and set state to translated.""",
    "po": """This file is a gettext PO catalogue. Fill msgstr for every msgid.
Keep msgctxt and every comment line unchanged.""",
    "fluent": """This file is a Fluent (FTL) resource. Each line is identifier = value.
Replace the value with the translation and keep the identifier and comments.""",
    "json-cliff": """This file is JSON holding the CLIFF data model: groups contain entries with
source, target and metadata. Fill the target field of every entry.""",
    "json-plain": """This file is a plain i18n JSON resource. Replace every string value with its
translation and keep every key. Where a key maps to an object with message and
description, translate message and leave description unchanged.""",
    "yaml-cliff": """This file is YAML holding the CLIFF data model: groups contain entries with
source, target and metadata. Fill the target field of every entry.""",
    "yaml-plain": """This file is a plain YAML resource of key: value pairs. Replace every value
with its translation, keep every key, and keep the comment lines unchanged.""",
    "csv": """This file is CSV with a header row. Fill the target column of every data row
and change nothing else. Quote fields that contain commas or quotes.""",
    "android": """This file is an Android strings.xml resource. Replace the text of every
string element with its translation and keep the name attribute and the
comments unchanged. Escape apostrophes as \\' as Android requires.""",
    "ios": """This file is an iOS Localizable.strings resource of "key" = "value"; lines.
Replace every value with its translation and keep every key and comment.""",
}

GLOSSARY_HEADER = """===== REFERENCE GLOSSARY - CONTEXT FOR YOUR READING =====
Project glossary. These renderings are canonical: use them exactly whenever the
term appears in the file you translate. This block is reference material that
stays here; your answer contains the translated file itself."""

GLOSSARY_FOOTER = """===== END OF REFERENCE GLOSSARY ====="""

DOCUMENT_HEADER = """===== FILE TO TRANSLATE - RETURN THIS FILE, COMPLETE ====="""

# CLIFF only, and placed immediately before the file so it is the last instruction
# read before the answer starts. The same rule is stated at the top and the end of
# the CLIFF specification block; this is the third injection, and the reason for
# three is that one statement never held: the model closes what it opens
# (`</terms>` after a glossary, and in one measured answer a closing line for every
# entry it had written), in every prompt variant this project has measured. Position
# and repetition are the untried lever, so the rule is put where primacy and recency
# both apply. It is deliberately not shared with the other nine formats, where
# closing tags are part of the syntax.
CLIFF_ANSWER_REMINDER = """The file below already has its structure. Each `<id>` and
`[group.path]` is one line standing alone, nothing in a CLIFF file is closed, and the
answer ends after the last field of the last entry - of the translated file, and then
of the glossary if you append one."""

CLIFF_EDIT_SAFETY = """CLIFF EDIT SAFETY
Every entry id and group path is there as written: identifiers may use upper- and
lowercase letters, digits, "_" and "-", they are case-sensitive, and
recapitalizing one or adding an underscore renames the translation key. Glossary
ids are unique; one entry per term. Fixed tags (type, emotion, status) are the
exception: they are lowercase kebab-case words from the closed vocabulary,
written bare. Every text value is one quoted string; inner double quotes are
escaped as \\" and newlines as \\n."""


# CLIFF is the only format in the comparison with a glossary variant, so it is
# the only one that may answer with a second document. That is not a violation
# of the one-file rule: it is the format's terminology workflow, and the
# benchmark measures whether a model actually uses it.
GLOSSARY_DELIVERABLE = """This task has one required deliverable, the translated file, and one
optional deliverable: a CLIFF glossary for the term decisions the translation
makes."""

GLOSSARY_WORKFLOW = """Terminology workflow.

Specification 13.2.2 is the criterion: a glossary is warranted when the brief
asks for terminology consistency or a naming policy, a term recurs across
entries, or a naming judgement would otherwise be re-made differently. A term
belongs in it when it recurs, names something (product, feature, character,
place, faction), is a fixed phrase or idiom, or was a judgement call; the
rendering it records is the one used in the translated file.

One CLIFF document, after the translated file:

CLIFF 1.1
namespace: <same namespace>
clan: <clan>-terms
source-language: <same>
target-language: <same>
variant: glossary
title: "Terms decided while translating <clan>"

[terms]
type: noun

<term-id>
source: "<source term>"
target: "<the rendering you used>"
type: <a CLIFF type tag>
status: translated
context: "<why this rendering, in one line>"

Each entry holds one term, carries the rendering you used, and satisfies CLIFF."""

CONTEXT_HINT = """The file carries a translation brief: family information, translation
standards, group context and per-entry context, content type, emotion, and
maximum display width in cells (Latin and digits count 1 cell, CJK and
fullwidth characters count 2). Follow all of it."""

JUDGE_SYSTEM = """You are a strict professional translation quality evaluator. You apply the MQM
error typology and you never reward fluent text that misses the brief."""

JUDGE_TASK = """Evaluate the translation below.

Report every error you find as a JSON object with these fields:
  category: one of accuracy, fluency, terminology, style, locale-convention, design
  severity: one of critical, major, minor
  span: the offending text
  note: one short sentence

Return ONLY a JSON object of the form:
{{"errors": [ ... ], "comment": "one sentence overall"}}
An empty error list means a flawless translation."""
