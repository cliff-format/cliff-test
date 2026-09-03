# Translating CLIF with an LLM: the CLARION playbook

This is the practical companion to the benchmark: how to get good translations
out of a model when the working file is CLIF. Everything here is implemented in
the harness, so the recommendations are executable rather than advisory.

## 1. Attach the format rules once

A model has never seen CLIF. Inject the rules at one of three levels:

| Level | What is sent | Roughly |
| --- | --- | --- |
| `none` | nothing | 0 tokens |
| `cheatsheet` | the generated one-screen digest | a few hundred tokens |
| `full` | the complete normative specification | several thousand tokens |

    python -m clarion tokens --spec-mode cheatsheet

The digest is **generated from the specification repository**, not copied: the
closed vocabularies are read out of the reference tables in `clif/references`,
so it can never drift from the normative text. The cost is a separately
measured prompt component, which is why the with/without comparison needs no
extra model run.

Practical rule: use `cheatsheet` for translation, `full` only when the model
must also restructure a document.

## 2. Build the glossary before translating, not after

CLIF has a glossary variant; a project only benefits from it if the file
exists. When a document arrives without terminology, mine one:

    python -m clarion glossary bootstrap datasets/clarion-core/game/game-shard.zh-CN.clif \
        --out datasets/clarion-core/game/glossary.zh-CN.clif --propose --attach

What it does:

1. **Mines candidates** - entries typed as proper-noun, fixed-phrase, idiom or
   noun-phrase; brand-like tokens (CamelCase, ALL CAPS); capitalized multi-word
   names; repeated Han runs; short repeated UI labels.
2. **Proposes renderings** (with `--propose`) in one batched call, under the
   de-jargon policy, so every term is decided once instead of drifting across
   files.
3. **Merges** into an existing glossary without ever overwriting a term whose
   status is `reviewed` or `final`; conflicts are reported, not applied.
4. **Attaches** the glossary to the source file's `dependency` list with
   `--attach`, so every later prompt carries it automatically.

The glossary is a CLIF file with `variant: glossary`, so it is validated,
diffed and reviewed like any other translation asset.

## 3. Say what the project means, not what the textbook says

Some renderings dominate training data and read badly to a normal reader:
`default` as 缺省, `robust` as 鲁棒, `token` as 词元, `resolution` as 解析度.
The policy file `clarion/policy/dejargon.zh-CN.json` records the discouraged
rendering, the accepted ones, a confidence level and a note. It is used twice:

- as a **prompt fragment**, so the model is told before it is measured;
- as a **checker**, so a violation is caught with a line-level report.

Extend it per project; it is data, not code. Terms that should stay in Latin
script (Token, API, SDK, Cookie, Wi-Fi) live in the same file.

## 4. One file, one context

Translating several files in one conversation lets terminology and tone from
one file leak into another, and a mistake made early is repeated for the rest
of the session. The harness therefore defaults to

    "isolation": "per-file"

which gives every corpus file its own provider session. The only state shared
between files is the glossary - which is the point: shared decisions travel as
data, not as conversational memory.

When translating with an agent framework instead of a raw API, use the same
boundary: one subagent per file, the glossary and the specification digest in
its prompt, and the validator output as its feedback channel.

## 5. Batch by section, never split an entry

Send the version line, the header, the section line and its group metadata,
then the entries of that section. Every batch repeats the header and the
section context, because an entry without its group metadata has lost half its
brief. Never split an entry across batches.

## 6. Close the loop with the validator

CLIF errors are line-numbered and categorized, so repair is local:

    python -m pyclif validate translated.clif

Feed only the failing lines back:

    The file failed validation. Fix only these lines:
    <validator output>

Do not ask for a reformat of the whole file. Line-local repair is the failure
model the format was designed for.

## 7. The prompt CLARION actually sends

    system: professional localization translator and localization engineer
    user:   task rules (return the whole file, keep identifiers, preserve
            placeholders, translate meaning not words)
            format notes (where the translation goes in this format)
            CLIF cheat sheet            <- CLIF only
            terminology policy          <- from the de-jargon file
            context hint                <- context arm only
            glossary                    <- rendered in the same format
            the document

Each block is measured separately, so any experiment can be re-priced without
re-running it. The blocks live in `clarion/prompts/templates.py`; editing them
is the supported way to tune the prompt.
