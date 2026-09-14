# CLARION-Core authoring specification

This is the contract every corpus file must satisfy. It is written for whoever
adds a stratum, human or agent.

## 1. What a corpus item is

One item is one translation entry: a source text, a human-quality reference
translation, the context a translator legitimately needs, and zero or more
machine-checkable instructions the translation must obey.

Two files carry it:

| File | Role |
| --- | --- |
| `<file-id>.<target-language>.cliff` | A specification-valid CLIFF 1.0 document. Its `target` fields are the reference translations. |
| `<file-id>.gold.json` | Provenance, licence, verification state, alternative references, difficulty, tags and instruction rules. |

The harness blanks every `target` before it builds a prompt, so the corpus and
the gold can never drift apart.

Optional per stratum: `glossary.<target-language>.cliff`, a CLIFF file with
`variant: glossary`. Any file whose name contains `glossary` is loaded as the
stratum glossary and is attached to prompts in the context arm.

## 2. Directory layout

```
datasets/clarion-core/
  manifest.json              already exists, do not rewrite it
  DATA-LICENSES.md           already exists
  ui/    ui-console.zh-CN.cliff    ui-console.gold.json    glossary.zh-CN.cliff
  news/  news-wire.zh-CN.cliff     news-wire.gold.json
  lit/   lit-classical.en-US.cliff lit-classical.gold.json
  legal/ legal-terms.zh-CN.cliff   legal-terms.gold.json
  game/  game-shard.zh-CN.cliff    game-shard.gold.json    glossary.zh-CN.cliff
```

The gold manifest name is the CLIFF file name up to the first dot, plus
`.gold.json`. `ui-console.zh-CN.cliff` therefore pairs with
`ui-console.gold.json`.

## 3. CLIFF rules you must follow

```cliff
CLIFF 1.0
namespace: clarion
clan: ui-console
source-language: en-US
target-language: zh-CN
title: "Short description of the family"
info: "Who the audience is, what the product is, anything the whole file needs."
standard: "Translation policy lines: naming, register, punctuation, spacing."
dependency: ["glossary.zh-CN.cliff"]

[settings.video]
context: "Where these strings appear and what the user is doing."
type: label
emotion: [objective]
max-width: 12

<resolution>
source: "Resolution"
target: "分辨率"
status: final
context: "Dropdown label above the resolution list."
```

Hard requirements:

1. First line is exactly `CLIFF 1.0`.
2. `namespace`, `clan`, `source-language`, `target-language` are required.
   `namespace` is `clarion`; `clan` is the file id (`ui-console`).
3. The file name must agree with the header: `<clan>.<target-language>.cliff`.
4. An entry starts with `<entry-id>` on its own line. Entry ids are lowercase
   kebab-case and unique in the file. There is no closing tag.
5. Every entry needs `source`, a `type` (directly or inherited from its
   section) and `status`. Corpus entries carry a reference translation, so
   `status: final`.
6. Strings are quoted and single-line. A long string continues on the next
   physical line as another quoted string; the fragments are concatenated
   **verbatim**, so put the space at the end of a fragment yourself.
7. Lists are single-line: `emotion: [calm, hopeful]`. List-typed fields are
   always lists, even with one item.
8. `type` must be one of the 26 tags: noun, verb, adjective, adverb, pronoun,
   numeral, preposition, conjunction, particle, interjection, proper-noun,
   noun-phrase, verb-phrase, adjective-phrase, adverb-phrase, fixed-phrase,
   idiom, sentence, description, narration, dialogue, monologue, prompt, label,
   subtitle, accessibility-cue.
9. `emotion` tags: neutral, objective, mechanical, joyful, sad, angry, fearful,
   surprised, curious, disgusted, anxious, calm, playful, serious, urgent,
   romantic, hopeful, grateful, formal, informal, polite, rude, nostalgic.
10. `max-width` counts display cells: Latin and digits 1, CJK and fullwidth 2.
    Only declare it when it is a real constraint, and make sure the reference
    translation actually fits.
11. `#` starts a full-line comment. Comments are developer notes; never put
    translator-relevant information in them.

Validate with:

```
python -m clarion corpus validate --strata <stratum>
```

## 4. The gold manifest

```json
{
  "file": "ui-console.zh-CN.cliff",
  "stratum": "ui",
  "notes": "What this file is for and which failure modes it probes.",
  "provenance": {
    "source": "original text written for CLARION",
    "url": "",
    "license": "CC0-1.0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "redistributable": true,
    "human_verified": false,
    "verifier": "",
    "retrieved": "2026-01-01",
    "origin": "original",
    "notes": "Original text, therefore free of training-data contamination."
  },
  "items": {
    "resolution": {
      "reference": "分辨率",
      "alternatives": ["屏幕分辨率"],
      "difficulty": "easy",
      "tags": ["ui-label", "width-limited"],
      "rules": [
        { "id": "resolution-width", "kind": "max-width", "params": { "cells": 12 } },
        { "id": "resolution-term", "kind": "term",
          "params": { "source": "Resolution", "target": ["分辨率"], "forbidden": ["解析度"] } }
      ]
    }
  }
}
```

`reference` may be omitted when it is identical to the `target` in the CLIFF
file; state it anyway when you want the manifest to be self-contained.
`alternatives` are additional acceptable renderings and are used by the surface
metrics as extra references.

`origin` is `original` for text written for this benchmark and `public` for
text taken from an external source; the report uses it as the contamination
control group.

## 5. Rule kinds

| kind | params | Checks |
| --- | --- | --- |
| `require` | `text` or `texts`, `any_of` | the rendering contains the required text |
| `forbid` | `text` or `texts` | the rendering avoids a wording |
| `term` | `source`, `target` (list), `forbidden` (list) | glossary adherence when the term occurs in the source |
| `keep-verbatim` | `text` | a brand or identifier survives untranslated |
| `name-policy` | `expected` (list), `rejected` (list), `mode` | semantic versus phonetic rendering of a name |
| `cjk-latin-space` | `exempt` | a space between Han text and Latin or digits |
| `punctuation` | `style` (`fullwidth`) | fullwidth punctuation in Han text |
| `no-trailing-punctuation` | `chars` | UI labels do not end in a full stop |
| `max-width` | `cells` | rendered width fits the budget |
| `icu-preserve` | none | ICU arguments and dialect markers survive |
| `placeholder-preserve` | `patterns` | %s, {0}, {name}, tags survive |
| `consistency` | `source`, `target` (list) | one term is rendered the same way everywhere |
| `numerals` | none | numbers of the source appear in the target |
| `length-ratio` | `min`, `max` | the target is not truncated or padded |
| `regex` | `pattern`, `mode` (`match`/`forbid`), `ignore_case` | anything else that is checkable |
| `translated` | `allow_identical` | the target is not a copy of the source |
| `script` | `script` (`Han`), `min_ratio` | the target is really in the target script |

Rules are the point of the benchmark: they encode instructions that a model
would otherwise get wrong by default. A rule must be objectively checkable
against the reference translation - write the reference first, then a rule that
the reference passes.

## 6. Content requirements

- 20 to 24 entries per file, in 3 to 5 sections.
- Difficulty mix: about one third `easy`, one third `normal`, one third `hard`.
- At least 8 entries carry rules, and at least 4 of those rules encode an
  instruction that contradicts the default habit of a translation model
  (a name that must be translated semantically rather than transliterated, a
  term the training data usually renders with textbook jargon, a spacing or
  punctuation convention, a width budget that forces a shorter wording).
- At least 2 entries carry an ICU MessageFormat payload where the stratum
  makes that plausible.
- Context must be genuine translator context, never a hint that gives the
  answer away. Write what a project would really record.
- Chinese references follow the house style: a space between Han text and
  Latin or digits, fullwidth punctuation inside Han sentences, no textbook
  jargon (see `clarion/policy/dejargon.zh-CN.json`).
- **Only original text.** Do not copy sentences from books, films, websites,
  existing benchmarks or product user interfaces, even public-domain ones, in
  this version of the corpus. Write new text in the register of the stratum.
