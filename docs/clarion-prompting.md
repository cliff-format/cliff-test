# Translating CLIFF with an LLM: the CLARION playbook

This is the practical companion to the benchmark: how to get good translations
out of a model when the working file is CLIFF. Everything here is implemented in
the harness, so the recommendations are executable rather than advisory.

## 1. Attach the format rules once

A model has never seen CLIFF, so the prompt has to say what the format is. How much
of the specification it sends is `prompt_style`, and the choice is priced rather
than argued: `python tools/prompt_cost.py` assembles every style through the same
call path a run uses and prints the components.

| Style | What is sent | One cell, `ui-console`, plain arm |
| --- | --- | ---: |
| `digest` | the whole specification text, plus a hand-written digest | 21 393 tokens |
| `examples` | our stated facts plus two conforming documents | 2 417 tokens |
| `spec` | the specification compressed to its rules, extracted at build time | 4 142 tokens |

`spec` is what the shipped configuration selects. It is the cheapest prompt that
still carries the format's rules, because it sends the rules and not the rationale:
of the specification's 16 838 tokens, only 2 492 are sentences that state a rule.

The parts that can go stale are the ones the machine reads: the closed vocabularies
come out of `cliff/references`, the field tables out of the specification's own
markdown, the grammar and the semantic constraints out of the ABNF — so a key added
to the specification appears in the prompt on the next build, and
`tests/clarion/test_spec_digest.py` fails if the prompt and the reference
implementation disagree. The paragraphs the module writes itself are named in
`cliff_rules.WRITTEN_HERE`, so a reviewer knows which ones to read by hand.

The cost is a separately measured prompt component, which is why the with/without
comparison needs no extra model run: `python tools/prompt_cost.py --decomposition`
prints the compressed block part by part.

Practical rule: `spec` for translation. Use `digest` only to reproduce a run
recorded before the prompt redesign — it is the style that still carries the full
specification text.

## 2. Build the glossary before translating, not after

CLIFF has a glossary variant; a project only benefits from it if the file
exists. When a document arrives without terminology, mine one:

    python -m clarion glossary bootstrap datasets/clarion-core/game/game-shard.zh-CN.cliff \
        --out datasets/clarion-core/game/glossary.zh-CN.cliff --propose --attach

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

The glossary is a CLIFF file with `variant: glossary`, so it is validated,
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
of the session. The harness therefore offers three boundaries and the shipped
configuration selects the strictest:

    "isolation": "per-task"   # what configs/deepseek-flash.json sets

`per-task` builds a fresh provider for every file, format and arm, so nothing a
model saw while translating one file can influence another, and nothing it learned
about one format helps it with the next — which is what makes a format-to-format
comparison a comparison. The dataclass default is the looser `per-file`, one
session per corpus file; `shared` is one session for the whole run.
`tests/clarion/test_cli.py` asserts that the shipped configuration's choice reaches
the wire.

The only state shared between files is the glossary - which is the point: shared
decisions travel as data, not as conversational memory.

When translating with an agent framework instead of a raw API, use the same
boundary: one subagent per file, the glossary and the specification digest in
its prompt, and the validator output as its feedback channel.

## 5. Batch by section, never split an entry

Send the version line, the header, the section line and its group metadata,
then the entries of that section. Every batch repeats the header and the
section context, because an entry without its group metadata has lost half its
brief. Never split an entry across batches.

## 6. Close the loop with the validator

CLIFF errors are line-numbered and categorized, so repair is local:

    python -m cliff_format validate translated.cliff
    python -m cliff_format validate --tolerant translated.cliff   # what a reader may repair

Feed only the failing lines back:

    The file failed validation. Fix only these lines:
    <validator output>

Do not ask for a reformat of the whole file. Line-local repair is the failure
model the format was designed for.

## 7. The prompt CLARION actually sends

With the shipped configuration (`prompt_style: spec`, an OpenAI-compatible
endpoint, `isolation: per-task`), one CLIFF cell is:

    system: professional localization translator and localization engineer
            the CLIFF specification compressed to its rules      <- the `spec` style
    user:   task rules (the whole file back, every identifier, placeholders
            character for character, meaning translated, the brief applied)
            the deliverable statement, and how many entries and sections follow
            terminology policy                                   <- from the de-jargon file
            context hint                                         <- context arm only
            glossary                                             <- rendered in the same format
            the answer-boundary reminder                         <- CLIFF only, last before the file
            the document

Every block is a labelled component of `PromptBudget`, so any of them can be
subtracted from a measured prompt to price the difference without a second model
call — that is how the specification block, the glossary workflow and the format
notes are costed in a report. The blocks live in `clarion/prompts/`; editing them is
the supported way to tune the prompt, and `tests/clarion/test_spec_digest.py` and
`tests/clarion/test_tools.py` hold the rules they have to obey: state things
affirmatively, constrain only what the specification requires and the deliverable
needs, and never let a CLIFF-only statement reach the other nine formats.
