# CLARION methodology

**CLARION** - *Contextual Localization Accuracy, Robustness, Instruction-following
and Overhead beNchmark* - measures a **localization file format**, not a model.

The question it answers is narrow and testable: *when the same content and the
same translation brief are delivered to the same model in different file
formats, what changes?*

## 1. The seven dimensions

| # | Dimension | Arm | Needs a model |
| --- | --- | --- | --- |
| D1 | Token cost of CLIFF against other formats in their plain form | bare | no |
| D2 | Token cost when the other formats carry the same context in their own metadata channels | context | no |
| D3 | Translation quality, plain formats | bare | yes |
| D4 | Translation quality, context-carrying formats | context | yes |
| D5 | Translation wall-clock cost, plain formats | bare | yes |
| D6 | Translation wall-clock cost, context-carrying formats | context | yes |
| D7 | Format validity after model edits | both | yes (a deterministic replay exists) |

Two supporting measurements are always reported with them:

- **Round-trip context fidelity** - convert a CLIFF document into a format and
  back, then count how many context facts survived. This is the objective
  version of the claim "CLIFF carries context losslessly".
- **Parse and validity rate** - reported separately from quality, because a
  reference metric will happily score the fragment of a file that survived a
  broken parse.

## 2. The fairness rules

1. **One source of truth.** Every fixture in every format and arm is generated
   from the same CLIFF corpus document through cliff-python (or, for the two plain
   key/value dialects, through code written against the same data model). No
   format has a hand-tuned fixture.
2. **Identical instructions.** All formats receive the same system role, the
   same task rules and the same terminology policy. Only two blocks differ:
   the per-format notes (where the translation goes in this format) and, for
   CLIFF alone, the specification digest.
3. **The asymmetry is priced, not hidden.** A model has seen XLIFF and PO
   thousands of times and has never seen CLIFF, so CLIFF must pay for a
   specification block. That block is a separately measured prompt component,
   and D1/D2 report the totals with and without it.
4. **The context arm favours the competitor.** cliff-python writes the complete CLIFF
   context payload into each format's documented channel: PO extracted
   comments and msgctxt, XLIFF metadata and notes, Fluent comments, Android
   and iOS comments, CSV columns, JSON and YAML fields. If CLIFF still wins the
   context arm, it is not winning because the other formats were starved.
5. **Nothing is scored that was not asked for.** An edit a format cannot
   express is excluded from that format's denominator in D7 and reported as
   "applicable edits", so a format is never punished for lacking a field, only
   for breaking when it has one.

## 3. Arms

**bare** is what a project normally ships: identifiers and source text.
Family information, translation standards, group metadata, per-entry context,
emotion, width limits, references and workflow status are all removed. CLIFF
cannot go below its own required minimum (every entry keeps a type and a
status), and that floor is reported rather than hidden.

**context** adds the full brief. For CLIFF this is the file itself; for the
others it is their native metadata channel.

The difference between the two arms is the honest measurement of what context
is worth: same model, same content, same instructions, one variable.

## 4. Token accounting (D1, D2)

Every prompt is built from labelled components and every component is measured
separately:

    system.role, task.rules, format.notes, spec.digest,
    policy.terminology, context.hint, glossary, document

Because the components are additive, any subset can be priced arithmetically.
The "with and without the CLIFF specification" comparison therefore costs
nothing: subtract `spec.digest` and `format.notes` from the measured total.
The tokenizer is named in every table (tiktoken `o200k_base` by default, with
a documented heuristic fallback that is labelled as such and never mixed into
the same table).

Reported per format: document tokens, tokens per entry, glossary tokens,
format-instruction tokens, prompt total, prompt total without format
instructions, and the percentage difference against CLIFF.

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
file is validated with a checker of comparable strictness: the official CLIFF
validator for CLIFF, XML well-formedness plus structural requirements for XLIFF
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

## 9.1 Reading a model answer back: strict or tolerant

CLIFF 1.1 defines a tolerant parsing mode for exactly one consumer: an
automated translation pipeline that must not lose a translation because a model
punctuated a line differently (specification Appendix C). CLARION is that
consumer, so `read_mode: tolerant` is the shipped default, and `strict` is one
configuration key away.

The two readings answer different questions, and neither replaces the other:

| Reading | The question it answers | What a failure means |
| --- | --- | --- |
| `strict` | would the project's own toolchain accept these bytes? | the answer is not valid CLIFF as written |
| `tolerant` | how much of this answer is usable? | Appendix C.5 was hit — content the parser must not invent |

The mode is not a footnote. It is recorded on every row — `read_mode` plus
`repairs`, the number of documented repairs the tolerant read made — in the
translation records, the robustness outcomes and the fidelity records, and the
D3/D4/D7 tables carry both as columns (Appendix C.1 requires the mode in effect
to be observable by the caller; C.6 requires every repair to be reported).

Three consequences worth stating plainly:

1. **A repair is not free and not hidden.** The repairs are exactly the six of
   Appendix C.2 — a bare scalar in a list-typed field, a repeated field, a quoted
   tag, a quoted entry id, a quoted key, an identifier containing a reserved
   character, a version line spelled differently. The `repairs` column prices the
   answer's untidiness; a format whose answers need many repairs is doing less well
   than one whose answers need none, even when both finally parse.
2. **A trailing `,` / `;` is not a repair.** It is standard CLIFF 1.1 syntax
   (5.6), discarded before the line is classified, and reporting it as a repair
   would inflate the count for a habit the specification deliberately tolerates.
   A test asserts this.
3. **The tolerant read still refuses what Appendix C.5 forbids**: a missing
   `source`, `status` or effective `type`, a `status` that contradicts the
   presence of `target`, an unbalanced ICU brace, a tag outside its closed
   vocabulary, an unknown non-`x-` key, a line that is none of the six line
   kinds, a document over a resource limit, or an unimplemented version. The
   mode preserves information; it never guesses it. The quoted-key relaxation
   (C.2.7) is the cleanest illustration: it removes the quotes and then checks the
   word against the legal keys of its scope, so `"translater":` is refused exactly
   as `translater:` is. A relaxation may change the shape of a line; it never
   changes the vocabulary
   (`tests/fixtures/tolerant/quoted-unknown-key.zh-CN.cliff`).

### What the tolerant read cannot save, and why that matters for prompting

A reader who assumes "tolerant" means "forgiving" will misread the D7 table. The
recorded run shows both halves of the behaviour in one cell: `cliff/context`
took **7 repairs** — quoted tags, a bare list value, a normalized id — and still
failed 2 of 12 edits. The failures are not shapes a repair could fix. They are
keys the model invented:

| Edit asked for | What the model wrote | Why it cannot be repaired |
| --- | --- | --- |
| set the context of an entry | `translator-context:` | an unknown non-`x-` key (C.5) |
| set the context of a group | `translator-context:` | same, in group scope |
| set a status | `status:` inside a **group** | `status` is not group metadata; only `context`, `type`, `emotion`, `max-width` are |
| add a reference (twice) | `ref:` / `source-ref:` | unknown entry keys; the field is `reference` |

Appendix C.5 forbids a tolerant parser from repairing an unknown key, and the
reason is sound: `translator-context` is *semantically* obviously `context`, but
"repair what I can infer you meant" is exactly the guessing the appendix exists
to prevent. The consequence for this project is direct and it is a prompt problem,
not a parser problem:

> **Because a tolerant parser will not repair a wrong key name, a wrong scope or a
> wrong value shape, the prompt must state those facts exactly.** A prompt that
> teaches CLIFF only by example can leave the model free to invent a plausible
> field name, and no amount of tolerant parsing will rescue that answer.

That claim is now measured, and the measurement is worth recording because the
number is large enough to change a default. D7's edit prompt carried **no CLIFF
content at all**, so an instruction like "set the context of this entry" left the
model to name the field itself. Running the same 48 edits with the field table and
task verbs prepended (`python .tools/d7_pilot.py`), both conditions sent at
temperature 0.0 — see the temperature note in the measurement protocol above for
why the edit dimension could not yet honour the configured value:

| edit prompt | invented-key failures | edit not valid |
| --- | ---: | ---: |
| historical (no CLIFF content) | **18.8 %** (95 % CI 10.2–31.9) | 18.8 % |
| with the field names and scopes stated | **0 %** (95 % CI 0–7.4) | 0 % |

Fisher exact p = 0.0129, and the historical figure reproduces the 18.8 % of the
full recorded run. The invented names were `translator-context` (in entry *and*
group scope), `status` inside a group section, `ref` and `source-ref`. See
[clarion-prompt-design.md](clarion-prompt-design.md) for the prompt that fixes it
and for the token cost it replaces.

The measured cost of the current prompt makes the trade explicit: CLIFF's
`format instructions` component is ~46 400 tokens per arm (16 cells), of which
**16 316 per cell is the full specification text**. The full text is what a
prompt-design experiment should try to earn or drop; the lexical facts — exact
key names, their legal scopes, the closed vocabularies and the shape of each
value — are what it must keep.

Two behaviours are decided here rather than left open, and both are the
implementation's, not a preference stated after the fact:

- **A collision produced by normalization is disambiguated, not rejected.**
  Appendix C.4 lets an implementation either rename a colliding identifier
  (`-2`, `-3`, …) or reject the document, and requires it to offer both and
  document the default. Tolerant parsing normalizes first and then disambiguates
  the later entry, reporting an `id-collision` repair that names both final ids
  (fixture `tests/fixtures/tolerant/collision.zh-CN.cliff`). This is the choice
  that keeps the data: the entries arrived with different spellings and different
  text, so dropping one would lose a translation.
- **A *textually identical* duplicate entry id is still rejected**, in both
  readings, because §10.2 makes a duplicate canonical ID a validity error and a
  tolerant parser must surface it rather than silently let one entry win
  (fixture `tests/fixtures/invalid/duplicate-entry-id.zh-CN.cliff`). The
  distinction is exact: disambiguation applies to ids that only *became* equal
  through normalization, not to ids the author wrote twice.

One more reading decision, because it changes what an answer may look like:

- **An answer may hold two documents.** The terminology workflow lets a
  translator return the translated file plus a glossary (13.2.2), so the harness
  splits an answer on the version line (either 1.0 or 1.1) and validates each
  document on its own: concatenating two valid documents is not one valid
  document. `tools/cliff_validator.py --multi-document` exposes the same reading
  standalone.

### What the two readings measured

Re-scoring the stored CLIFF answers of a run under both readings, with no model
call, is the comparison this section exists to make possible. On the recorded
`deepseek-flash` run (96 CLIFF answers, three repeats per cell):

| Arm | strict valid | tolerant valid | repairs | salvaged only by tolerance |
| --- | ---: | ---: | ---: | --- |
| bare | 89.6% | 93.8% | 3 | 2 answers |
| context | 83.3% | 89.6% | 6 | 3 answers |

The repairs were one quoted tag (C.2.3), four identifiers containing a reserved
character (C.2.5) and — in the context arm — two entry ids that normalization
made colliding (C.4). Every one of them is a shape repair: no answer was salvaged
by inventing content, which is what Appendix C.5 forbids. The gap is the honest
size of the claim "a translation pipeline should not lose a translation because a
model punctuated a line differently".

When a report quotes "valid answer %", it is quoting one of the two readings,
and the table says which.

## 10. Statistics

- The design is paired: identical segments, identical model, one variable.
  Differences are therefore tested with a **paired bootstrap** and an
  **approximate randomisation (paired permutation)** test over items.
- Pass rates use **Wilson intervals**; paired pass/fail comparisons use
  **McNemar's exact test**.- With ten formats there are dozens of pairwise comparisons, so p-values are
  corrected (Holm or Benjamini-Hochberg) before any claim is made.
- **Sampling temperature: 0.0 in the first recorded run; 1.3 by configuration
  afterwards, but reached only by the translation dimension.** DeepSeek documents
  1.3 as the recommended temperature for translation, and the UE5 plugin that
  consumes CLIFF in production uses it, so the benchmark intends to measure the
  model as it is actually deployed. The edit dimension did not: `run_robustness`
  built its own request with a hard-coded `temperature=0.0` and ignored
  `provider.temperature`, so **every D7 number published so far is a 0.0 number**,
  including the rows labelled as the deployment settings. That is fixed (the
  temperature is now a parameter, forwarded from the configuration, guarded by
  `tests/clarion/test_edit_request.py`) and D7 has since been measured at 1.3 for
  CLIFF: **97.7 % valid / 95.9 % intent** over 171 edits in three passes, against
  100 % / 98.6 % at 0.0. The two regimes are **not comparable**, and a report must
  say which one produced its numbers:
  - at 0.0 the three repeats of a cell were observed to be **byte-identical**
    (for example the three `wmt24pp` context answers failed on the same line with
    the same message), so "3 repeats" measured internal consistency, not
    sampling variance, and the effective sample size was smaller than the run
    count suggests;
  - at 1.3 the repeats are genuine independent samples, which is what the
    paired tests in this section assume. It gives up bit-for-bit reproducibility
    of a run in exchange for measuring a distribution, which is the honest
    object for a stochastic decoder.
- Temperature 0 is not determinism either: at least three repeats per cell,
  reported as mean with a confidence interval. At 1.3 report the **spread across
  repeats** as well as the mean, because at that temperature the spread is part
  of the result.
- A metric difference is only called meaningful when it exceeds the accepted
  threshold for that metric and language pair, not because it is positive.
  There is no published "magic N" of segments; MT-Thresholds is the right
  instrument, and its anchor is sobering: an improvement of about 1 BLEU buys
  only roughly 65 percent agreement with human preference. Report the interval
  and the converted accuracy, never a self-invented threshold.
- CLARION-Core is small on purpose - 392 entries across 16 documents in 0.3.0
  - which is the small end of the studied regime. Treat a single-run difference
  as a hypothesis, and widen the corpus through the recipes before publishing
  a claim.

### Where the evidence lives

Every number in these documents is reproducible from **this repository** or from a
run directory, and the distinction matters when reading a citation:

- **In the repository**, under `tools/`: `cliff_validator.py` (the validation modes
  the fixtures are checked with), `corpus_version.py` (the corpus version line and
  its semantic fingerprint), `token_benchmark.py` (D1/D2), `package_benchmark.py`,
  `qe_score.py`, `compare_readings.py` (the two-readings table of C6.11),
  `prompt_cost.py` (the prompt-cost table of `clarion-prompt-design.md`, with
  `prompt_block_delta.py` for the per-block price of a prompt edit) and
  `coverage_audit.py` (which modules the suite reaches). `make check` runs the
  gates, and `tests/` pins the behaviour of everything that scores. A tool that
  produces a published number belongs here rather than in the working copy: the
  working copy is for questions that are still open.
- **A run directory**, under `results/` (gitignored, regenerated by a run): its
  `records.jsonl`, its `answers/` and its `report.md` are the raw evidence behind
  any recorded table. A recorded run is named wherever its numbers are quoted.
- **A working-copy scripts directory**, `../.tools/`, beside the three checkouts and
  **not part of any of them**: the one-off pilots and forensics written while a
  question was open (`probe_repairs.py`, `prompt_pilot.py`, `d7_pilot.py`,
  `show_breakage.py` and the run-specific analysis scripts). They are cited in the
  design documents as the instrument that produced a finding, not as something a
  reader is expected to run: where a finding matters, the repository carries a
  fixture, a test or a recorded run that pins it, and the citation says so. When a
  script's output becomes a published number, the script moves into `tools/` and a
  test pins the number (`compare_readings.py`, `prompt_cost.py`).

## 11. Contamination control

Public benchmarks released before a model's training cut-off may already be in
its training data. Every corpus item therefore records an `origin`:

- `original` - text written for CLARION, unavailable to any crawler before
  publication;
- `public` - text imported from an external corpus.

Reports compare the two groups. Contamination inflates absolute scores; it is
much less harmful to the *ranking of formats*, which is what CLARION claims.

## 12. Corpus

[CLARION-Core](../datasets/clarion-core/) covers six strata - UI strings, news
and social text, classical and modern literature, legal and academic text, game
dialogue and screenplay, and a minimal-pair probe set. Version 0.3.0 holds 16
standard documents (392 entries) and two `variant: glossary` term files; the
authored text is original CC0, which makes it redistributable and
contamination-free, and external corpora are added through
[recipes](../datasets/recipes/recipes.json) with their licences and vendoring
tier attached. See
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
| `original` | written by hand together with the text, as in the authored part of CLARION-Core | the reference standard |

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
| Closed vocabularies | `type` and `emotion` must be CLIFF tags. Invalid tags are rejected and counted, never coerced into something valid. |
| Reference-consistent constraints | A proposed `max-width` that the human reference itself violates is rejected. A brief may not demand what the gold translation does not do. |
| Different annotator | The annotator should not be the model under test; using one model for both phrases the brief the way that model likes to read it. The model id is recorded, the CLI warns when they match, and every report prints it. |

Three rules keep this from contaminating the measurement:

1. **The annotator never sees or writes a target.** It reads source text and
   upstream metadata only, and it may only write context, type, emotion and
   max-width; tags are validated against the closed CLIFF vocabularies before
   they are accepted.
2. **Context is generated once, into the CLIFF document.** Every other format is
   converted from that same document, so the quality of the context can never
   favour one format over another - it moves all formats together.
3. **Results are broken down by `context_origin`.** A context-arm gain measured
   on annotated context is a weaker claim than one measured on native context,
   and the report must not hide the difference.

Practical consequence: prefer `native` sources (Godot, Firefox, Unciv, MASSIVE)
for the context arm, and use flat corpora (WMT24++, FLORES+) for volume,
translation difficulty and the plain arm.

### Two comparisons, and the difference between them

"CLIFF carrying a full brief" against "a JSON file carrying nothing" is a
legitimate and important comparison - it is the real choice a project makes -
but it is a **workflow** claim, not a **format** claim, and CLARION never
reports it alone:

| Comparison | What it shows | Where it appears |
| --- | --- | --- |
| CLIFF context arm vs other formats' **context** arm | a format property: the same brief costs fewer tokens and survives editing better in CLIFF | D2, D4, D6, D7 - the apples-to-apples result |
| CLIFF context arm vs other formats' **plain** arm | a workflow property: what a project gains by moving from a bare resource file to a context-carrying working file | reported separately and always labelled as a workflow comparison |

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
2. **In-file attribution.** Every generated file starts with CLIFF comment lines
   naming the upstream project, its licence, its SPDX identifier and the exact
   revision. CLIFF comments are inert developer notes, so this can never leak
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
| validate | the official CLIFF validator over every corpus document | yes |
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
  The shipped configuration annotates and measures with the same model
  (`deepseek-flash`), because the run is budgeted for one endpoint; every
  report therefore prints the pairing, and the `context source` column says
  which rows carry annotated briefs. A context-arm gain measured on annotated
  context is the weaker claim.

## 13. Reproducibility

Every run writes a directory containing the resolved configuration, a JSONL
record per task (including the prompt component costs, the raw metrics and the
provider usage), a JSON summary with the cliff-python version, and the Markdown
report. A number in a report can always be traced back to the exact request
that produced it.

## 14. Threats to validity

1. **Model familiarity.** Models know XLIFF and PO and do not know CLIFF. The
   specification digest reduces the gap but does not erase it; a result should
   be read as "CLIFF plus a one-screen digest" versus "a format the model
   already knows".
2. **Converter quality.** All non-CLIFF fixtures are produced by cliff-python. A bug
   there is a bug in the benchmark; the round-trip fidelity check is the guard.
3. **Reference bias.** The reference translations were written by the same
   kind of system that is being evaluated. Human sign-off is tracked per item
   (`human_verified`) and is required before publishing quality claims.
4. **One language pair.** Most of CLARION-Core is English to Simplified
   Chinese. Format effects should be re-measured for at least one non-CJK pair
   before generalising.
5. **Latency portability.** Wall-clock numbers do not transfer between
   endpoints, regions or days.
