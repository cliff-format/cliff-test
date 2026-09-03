# CLARION methodology

**CLARION** - *Contextual Localization Accuracy, Robustness, Instruction-following
and Overhead beNchmark* - measures a **localization file format**, not a model.

The question it answers is narrow and testable: *when the same content and the
same translation brief are delivered to the same model in different file
formats, what changes?*

## 1. The seven dimensions

| # | Dimension | Arm | Needs a model |
| --- | --- | --- | --- |
| D1 | Token cost of CLIF against other formats in their plain form | bare | no |
| D2 | Token cost when the other formats carry the same context in their own metadata channels | context | no |
| D3 | Translation quality, plain formats | bare | yes |
| D4 | Translation quality, context-carrying formats | context | yes |
| D5 | Translation wall-clock cost, plain formats | bare | yes |
| D6 | Translation wall-clock cost, context-carrying formats | context | yes |
| D7 | Format validity after model edits | both | yes (a deterministic replay exists) |

Two supporting measurements are always reported with them:

- **Round-trip context fidelity** - convert a CLIF document into a format and
  back, then count how many context facts survived. This is the objective
  version of the claim "CLIF carries context losslessly".
- **Parse and validity rate** - reported separately from quality, because a
  reference metric will happily score the fragment of a file that survived a
  broken parse.

## 2. The fairness rules

1. **One source of truth.** Every fixture in every format and arm is generated
   from the same CLIF corpus document through clif-python (or, for the two plain
   key/value dialects, through code written against the same data model). No
   format has a hand-tuned fixture.
2. **Identical instructions.** All formats receive the same system role, the
   same task rules and the same terminology policy. Only two blocks differ:
   the per-format notes (where the translation goes in this format) and, for
   CLIF alone, the specification digest.
3. **The asymmetry is priced, not hidden.** A model has seen XLIFF and PO
   thousands of times and has never seen CLIF, so CLIF must pay for a
   specification block. That block is a separately measured prompt component,
   and D1/D2 report the totals with and without it.
4. **The context arm favours the competitor.** clif-python writes the complete CLIF
   context payload into each format's documented channel: PO extracted
   comments and msgctxt, XLIFF metadata and notes, Fluent comments, Android
   and iOS comments, CSV columns, JSON and YAML fields. If CLIF still wins the
   context arm, it is not winning because the other formats were starved.
5. **Nothing is scored that was not asked for.** An edit a format cannot
   express is excluded from that format's denominator in D7 and reported as
   "applicable edits", so a format is never punished for lacking a field, only
   for breaking when it has one.

## 3. Arms

**bare** is what a project normally ships: identifiers and source text.
Family information, translation standards, group metadata, per-entry context,
emotion, width limits, references and workflow status are all removed. CLIF
cannot go below its own required minimum (every entry keeps a type and a
status), and that floor is reported rather than hidden.

**context** adds the full brief. For CLIF this is the file itself; for the
others it is their native metadata channel.

The difference between the two arms is the honest measurement of what context
is worth: same model, same content, same instructions, one variable.

## 4. Token accounting (D1, D2)

Every prompt is built from labelled components and every component is measured
separately:

    system.role, task.rules, format.notes, spec.digest,
    policy.terminology, context.hint, glossary, document

Because the components are additive, any subset can be priced arithmetically.
The "with and without the CLIF specification" comparison therefore costs
nothing: subtract `spec.digest` and `format.notes` from the measured total.
The tokenizer is named in every table (tiktoken `o200k_base` by default, with
a documented heuristic fallback that is labelled as such and never mixed into
the same table).

Reported per format: document tokens, tokens per entry, glossary tokens,
format-instruction tokens, prompt total, prompt total without format
instructions, and the percentage difference against CLIF.

## 5. Quality (D3, D4)

Three tiers, of which only the first is enabled by default:

**Tier 1 - deterministic, dependency free.** chrF++ (chrF with word bigrams,
the metric that behaves sensibly on Chinese without a word segmenter), BLEU and
TER for continuity with older reports, plus the structural, instruction,
terminology and de-jargon metrics below. Multi-reference is supported: gold
alternatives count as additional references.

**Tier 2 - LLM judge (optional, costs tokens).** A GEMBA-MQM style prompt asks
for error spans with an MQM category and severity; the score is
100 - (25 x critical + 5 x major + 1 x minor). Explainable and comparable
across formats. Never enabled by default, and never the only quality number.

**Tier 3 - neural metrics (optional, needs torch).** COMET-style models. Note
the licences before using them in a published comparison: MetricX-24 is
Apache-2.0, CometKiwi is CC-BY-NC-SA-4.0, and several XCOMET checkpoints are
gated.

Surface metrics are computed only over entries that came back; coverage,
identifier preservation and source fidelity are reported alongside so that a
high score on three surviving entries can never be mistaken for a good run.

### 5.1 Metric hygiene

Five rules, each from a published failure of MT evaluation practice:

1. **Degenerate controls are scored in every run.** WMT24's analysis of COMET
   showed that an empty translation can outscore a real system and that a
   sentence-shuffled hypothesis scores about as well as an empty one. CLARION
   scores four controls per file - empty, copy-source, shuffled and truncated -
   and disqualifies any metric that ranks a control at or above the real
   system. This matters here more than anywhere else, because broken format
   round-trips produce exactly those shapes.
2. **Never select and evaluate with the same metric.** Filtering or choosing
   data with a metric and then reporting that metric inflates the result.
3. **Aggregate at the segment level.** Every metric is computed per entry and
   averaged over entries, which is also what makes the paired significance
   tests possible.
4. **Label the direction and the scale.** chrF++, BLEU and COMET are
   higher-is-better; TER and MetricX are lower-is-better. COMET scores are not
   comparable across language pairs, so a single column may never mix them.
5. **Pin and print the metric signature.** Tokenizer, metric version, model
   checkpoint and revision go into the report. Scores have changed between
   library versions before.

If a neural metric is enabled, prefer permissively licensed, offline-runnable
checkpoints: COMET-22 (`Unbabel/wmt22-comet-da`, Apache-2.0, CPU-runnable) and
MetricX-24-hybrid (Apache-2.0, lower is better). CometKiwi is CC-BY-NC-SA and
the Tower judge family is CC-BY-NC; neither may be used in a commercial or
redistributable evaluation. Our MQM judge prompt is written for CLARION - the
GEMBA repository's code and prompts are CC-BY-SA-4.0, so they are referenced as
prior art but never vendored.

When surface metrics are compared against an external tool, use sacreBLEU with
`--tokenize zh` for Chinese (`ja-mecab` for Japanese, `13a` for Latin-script
targets): scoring Chinese with the default tokenizer measures whitespace, not
translation.

## 6. Instruction following

A fluent sentence that ignores the brief is a failed translation. CLARION
attaches machine-checkable rules to corpus items and scores the share that
passed. The rule kinds are listed in
[clarion-corpus-spec.md](clarion-corpus-spec.md#5-rule-kinds); the ones that
matter most are the ones that contradict a model's default habit:

- a character name the brief says to translate semantically rather than
  transliterate (Ash as 余烬, never 艾什);
- a term whose textbook rendering dominates training data but reads badly
  (default as 默认, never 缺省; robust as 健壮, never 鲁棒; token kept as Token);
- typographic conventions: a space between Han text and Latin or digits,
  fullwidth punctuation, no trailing full stop in UI labels;
- a display-width budget that forces a shorter wording;
- ICU and placeholder integrity;
- one term rendered identically everywhere it occurs.

This is the dimension the whole benchmark exists for: context is only valuable
if it changes the output. A format that carries the brief but does not get it
obeyed scores no better than a format that never carried it.

## 7. Terminology and the de-jargon policy

Glossary adherence counts, for every glossary term that actually occurs in a
source segment, whether the canonical rendering appears in the translation.
The de-jargon policy (`clarion/policy/dejargon.zh-CN.json`) is editable project
data with a confidence level per rule; only medium and high confidence rules
are enforced by default, and the whole policy is also emitted as a prompt
fragment so the model is told the rule before being measured against it.

## 8. Latency (D5, D6)

Latency is measured per request and reported per entry. It is dominated by
output tokens and by provider load, so it is only comparable inside one run
against one endpoint, and every table says so. Output tokens are reported next
to it, because a format that forces the model to re-emit metadata pays twice:
once in prompt tokens and once in generation time.

## 9. Edit robustness (D7)

The same edit intents are applied to every format:

    set-target, set-context, set-status, set-type, set-emotion, set-max-width,
    add-reference, add-entry, delete-entry, rename-entry, move-entry,
    set-header-field, add-comment

Each intent is rendered as one natural-language instruction, applied
sequentially (each edit lands on the previous answer), and after every step the
file is validated with a checker of comparable strictness: the official CLIF
validator for CLIF, XML well-formedness plus structural requirements for XLIFF
and Android, the msgid/msgstr grammar for PO, the identifier grammar for
Fluent, strict JSON, YAML and CSV parsing, and the quoted-assignment grammar
for iOS.

Two rates are reported together:

- **still valid** - the file is a valid file of that format;
- **intent applied** - the requested change actually happened.

A format that survives by ignoring instructions is not robust. A deterministic
replay (the reference edit applied to the data model) runs the same protocol
with no model, which is how the harness proves its own validators agree with
its own renderers.

## 10. Statistics

- The design is paired: identical segments, identical model, one variable.
  Differences are therefore tested with a **paired bootstrap** and an
  **approximate randomisation (paired permutation)** test over items.
- Pass rates use **Wilson intervals**; paired pass/fail comparisons use
  **McNemar's exact test**.
- With ten formats there are dozens of pairwise comparisons, so p-values are
  corrected (Holm or Benjamini-Hochberg) before any claim is made.
- Temperature 0 is not determinism: at least three repeats per cell, reported
  as mean with a confidence interval.
- A metric difference is only called meaningful when it exceeds the accepted
  threshold for that metric and language pair, not because it is positive.
  There is no published "magic N" of segments; MT-Thresholds is the right
  instrument, and its anchor is sobering: an improvement of about 1 BLEU buys
  only roughly 65 percent agreement with human preference. Report the interval
  and the converted accuracy, never a self-invented threshold.
- CLARION-Core is deliberately small (about 111 entries in version 0.1.0),
  which is the small end of the studied regime. Treat a single-run difference
  as a hypothesis, and widen the corpus through the recipes before publishing
  a claim.

## 11. Contamination control

Public benchmarks released before a model's training cut-off may already be in
its training data. Every corpus item therefore records an `origin`:

- `original` - text written for CLARION, unavailable to any crawler before
  publication;
- `public` - text imported from an external corpus.

Reports compare the two groups. Contamination inflates absolute scores; it is
much less harmful to the *ranking of formats*, which is what CLARION claims.

## 12. Corpus

[CLARION-Core](../datasets/clarion-core/) covers five strata - UI strings,
news and social text, classical and modern literature, legal and academic
text, and game dialogue and screenplay. Version 0.1.0 is entirely original
CC0 text, which makes it redistributable and contamination-free; external
corpora are added through [recipes](../datasets/recipes/recipes.json) with
their licences and vendoring tier attached. See
[DATA-LICENSES.md](../datasets/clarion-core/DATA-LICENSES.md).

## 12.1 Importing an external corpus

Every established machine-translation corpus - FLORES, WMT24++, NTREX, the WMT
test sets - is a list of sentence pairs. They were built to measure a *model*,
so they carry no translator brief at all: no situation, no content type, no
tone, no width budget, no terminology. Dropping such a corpus into CLARION
unchanged would make the context arm identical to the plain arm, and the
benchmark would measure nothing.

An imported corpus therefore passes through a pipeline before it is usable, and
every item records where its context came from:

| context_origin | Meaning | Used for |
| --- | --- | --- |
| `native` | the upstream project wrote it: gettext `#.` comments, `#:` references, `msgctxt`, Fluent comment levels, MASSIVE intents | the strongest material for the context arm |
| `derived` | computed deterministically from metadata the corpus already ships: document ids become groups, domain labels become group context, neighbouring segments become document context, placeholder detection adds an integrity note | safe, reproducible, publishable |
| `annotated` | written by a model in a separate annotation pass | opt-in, marked, and a hypothesis until a human signs it off |
| `original` | written by hand together with the text, as in CLARION-Core 0.1.0 | the reference standard |

### The annotation pass

Because `derived` context can only restate what a corpus already contains, the
fields that decide translation quality - what a string is, who says it, how it
must sound, how wide it may be - can only be obtained by writing them. CLARION
does it in the two passes a real localization brief is written in:

1. **summarize** - read the whole document, write the family brief (`info`) and
   the translation standards (`standard`), plus one context line per group;
2. **annotate** - read each segment with that brief in hand and write its
   `context`, `type`, `emotion` and, optionally, a `max-width` budget.

Five guards keep the pass from turning the benchmark into a self-fulfilling
prophecy, and each of them is enforced in code and pinned by a test:

| Guard | Rule |
| --- | --- |
| No target exposure | The annotator receives source text and upstream metadata only. A test asserts that no reference translation ever appears in an annotation prompt. |
| Leak detection | Every produced context is compared against the reference translation; reproducing a six-character Han span or a four-word Latin sequence rejects the context. A brief that contains the answer would win the context arm without the format doing anything. |
| Closed vocabularies | `type` and `emotion` must be CLIF tags. Invalid tags are rejected and counted, never coerced into something valid. |
| Reference-consistent constraints | A proposed `max-width` that the human reference itself violates is rejected. A brief may not demand what the gold translation does not do. |
| Different annotator | The annotator should not be the model under test; using one model for both phrases the brief the way that model likes to read it. The model id is recorded, the CLI warns when they match, and every report prints it. |

Three rules keep this from contaminating the measurement:

1. **The annotator never sees or writes a target.** It reads source text and
   upstream metadata only, and it may only write context, type, emotion and
   max-width; tags are validated against the closed CLIF vocabularies before
   they are accepted.
2. **Context is generated once, into the CLIF document.** Every other format is
   converted from that same document, so the quality of the context can never
   favour one format over another - it moves all formats together.
3. **Results are broken down by `context_origin`.** A context-arm gain measured
   on annotated context is a weaker claim than one measured on native context,
   and the report must not hide the difference.

Practical consequence: prefer `native` sources (Godot, Firefox, Unciv, MASSIVE)
for the context arm, and use flat corpora (WMT24++, FLORES+) for volume,
translation difficulty and the plain arm.

### Two comparisons, and the difference between them

"CLIF carrying a full brief" against "a JSON file carrying nothing" is a
legitimate and important comparison - it is the real choice a project makes -
but it is a **workflow** claim, not a **format** claim, and CLARION never
reports it alone:

| Comparison | What it shows | Where it appears |
| --- | --- | --- |
| CLIF context arm vs other formats' **context** arm | a format property: the same brief costs fewer tokens and survives editing better in CLIF | D2, D4, D6, D7 - the apples-to-apples result |
| CLIF context arm vs other formats' **plain** arm | a workflow property: what a project gains by moving from a bare resource file to a context-carrying working file | reported separately and always labelled as a workflow comparison |

Publishing only the second would be a rigged headline; publishing only the
first would hide the reason the format exists. Both are produced by the same
run, because every format is measured in both arms.

## 12.2 Publishing an imported corpus

The harness is MIT; imported text is not ours to relicense. Three mechanisms,
all machine-checked by `clarion corpus license-check`:

1. **Tier routing.** Permissive output (MIT, Apache-2.0, CC-BY, CC0) joins
   `datasets/clarion-core/`; file-level copyleft goes to `datasets/mpl-2.0/`;
   ShareAlike output goes to `datasets/cc-by-sa/` with its own LICENSE, because
   our segmentation is an adaptation; anything that may not be redistributed is
   written to a gitignored cache and never committed.
2. **In-file attribution.** Every generated file starts with CLIF comment lines
   naming the upstream project, its licence, its SPDX identifier and the exact
   revision. CLIF comments are inert developer notes, so this can never leak
   into a prompt or a translation.
3. **Per-item checksums.** The gold manifest stores a SHA-256 of the source and
   of the reference, so an imported corpus can be verified against upstream
   without republishing anything else.

## 12.3 The one-command run

```bash
python -m clarion pipeline --config configs/deepseek-flash.json
```

Eight stages, each recorded in the run summary with its duration and outcome:

| Stage | What it does | Fails the run |
| --- | --- | --- |
| secrets | loads the key from outside the repository and scans the tree for credentials | yes |
| fetch | imports every configured corpus: convert, annotate, enrich, route by licence, attribute | no (records the failure) |
| validate | the official CLIF validator over every corpus document | yes |
| licence | attribution, SPDX headers and tier routing | yes |
| tokens | dimensions 1 and 2 | no |
| fidelity | round-trip context retention | no |
| translate | dimensions 3 to 6 | when more than a tenth of the runs fail |
| robustness | dimension 7 | no |

Two settings matter for cost and honesty:

- **The annotator runs with reasoning disabled** and a larger output budget. It
  writes JSON, and a reasoning budget consumed the whole answer in testing -
  the failure looked like an empty response with `finish_reason: length`.
  Unparsable batches are halved and retried before being given up.
- **The annotator should be a different model** from the system under test.
  The shipped configuration annotates with `deepseek-v4-pro` and measures
  `deepseek-v4-flash`.

## 13. Reproducibility

Every run writes a directory containing the resolved configuration, a JSONL
record per task (including the prompt component costs, the raw metrics and the
provider usage), a JSON summary with the clif-python version, and the Markdown
report. A number in a report can always be traced back to the exact request
that produced it.

## 14. Threats to validity

1. **Model familiarity.** Models know XLIFF and PO and do not know CLIF. The
   specification digest reduces the gap but does not erase it; a result should
   be read as "CLIF plus a one-screen digest" versus "a format the model
   already knows".
2. **Converter quality.** All non-CLIF fixtures are produced by clif-python. A bug
   there is a bug in the benchmark; the round-trip fidelity check is the guard.
3. **Reference bias.** The reference translations were written by the same
   kind of system that is being evaluated. Human sign-off is tracked per item
   (`human_verified`) and is required before publishing quality claims.
4. **One language pair.** Most of CLARION-Core is English to Simplified
   Chinese. Format effects should be re-measured for at least one non-CJK pair
   before generalising.
5. **Latency portability.** Wall-clock numbers do not transfer between
   endpoints, regions or days.
