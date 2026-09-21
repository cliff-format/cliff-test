# Prompt design: what the CLIFF specification text was buying

This records a prompt-cost experiment and the design rules it produced, not a
proposal. The question was whether the reference specification that CLIFF's prompt
carried in every recorded run earned its place, and the answer turned out to be
narrower than either side of the argument expected.

**Provenance, and what this document does not publish.** The exploratory rounds
behind these rules were single cells: one-run ablations, pilot batches, per-cell
comparisons. Their run directories have been pruned, so their per-cell numbers are
no longer published here — a figure whose evidence has been deleted is a figure a
reader cannot check, and a superseded cell quoted next to a current one is worse
than either alone. What remains is stated in one of three ways:

- the **decision** an experiment produced and the **rule** it became, with no
  per-cell number;
- a figure from the **final run** (`clarion-deepseek-flash-20260921T211031+0000-de29a5`,
  revision `b81d3e6`, prompt fingerprint `6ef59ba44d454294`, shipped in
  `benchmark/clarion-2026-09-21`), which is the only run whose answers this
  document quotes as current;
- a figure from **`python tools/prompt_cost.py`**, which prices the prompt styles
  and prints the cost table below, so the reader can re-derive it.

Where a figure comes from the final run it is the **tolerant reading** of Appendix C,
which is the reading the shipped configuration declares (`read_mode: tolerant`), and
the strict column of the same answers is quoted wherever the two differ — the
difference is small and is the subject of
[clarion-methodology.md](clarion-methodology.md) §9.1.

Where a number appears without one of those three behind it, it is a defect.

## What was measured

`python -m clarion tokens` prices CLIFF's `format instructions` component at
**46 800 tokens per arm** (16 documents) under the shipped configuration, against a
document payload of 24 322 (plain) and 47 499 (context): the instructions cost
about twice the plain document they describe. Under the `digest` style, 16 838 of
that per-cell figure is the full text of `cliff-1.1.0.md`, injected with the
sentence *"Before writing the answer, consult the relevant sections of this full
specification"*. That block is what the `spec` style replaces with 2 925 tokens of
rules extracted from the specification repository, and `spec` is what the shipped
configuration selects (`configs/deepseek-flash.json`).

The replacements are selected with `prompt_style`. `examples`
(`clarion/prompts/cliff_prompt_v2.py`) states only what a tolerant reader cannot
repair and teaches the rest with two conforming documents; `spec`
(`clarion/prompts/cliff_rules.py`) sends the specification's own rules, extracted
from the specification repository at prompt-build time. Every number below is
measured, not estimated: `python tools/prompt_cost.py` assembles all three styles
through the same `build_translation_prompt` the run uses and prints these rows, and
`tests/test_prompt_cost_tool.py` checks that the tool reproduces the published
totals and that each column adds up to its own total.

| | current (`digest`) | example-driven (`examples`) | compressed (`spec`) |
| --- | ---: | ---: | ---: |
| specification text, block as sent | 16 838 | — | — |
| specification digest, core + supplement | 2 932 | — | — |
| the specification compressed to its rules | — | — | 2 925 |
| stated facts: keys, scopes, vocabularies | — | 402 | — |
| task rules (generic + CLIFF + output shape) | 287 | 489 | 287 |
| format notes | 117 | — | — |
| edit-safety reminder | 118 | — | — |
| answer-boundary reminder | — | — | 60 |
| examples | — | 425 | — |
| system role | 63 | 63 | 63 |
| terminology policy | 236 | 236 | 236 |
| glossary workflow | 231 | 231 | — |
| the document itself | 571 | 571 | 571 |
| **one cell, `ui-console` plain arm** | **21 393** | **2 417** | **4 142** |

The rows are the measured blocks of one cell; each column adds up to its total. The
specification text has grown since this style was first priced, which is a second
reason a prompt that carries it is expensive to keep current: 16 838 tokens today,
against 2 925 for the rules extracted from it. The `spec` column's glossary workflow
is empty because that style states the glossary rules inside the specification block,
and its answer-boundary reminder is the CLIFF answer-extent sentence placed immediately
before the file.

The quoting rule — the last of the example-driven CLIFF task rules, *each text value
as one quoted string, with its final punctuation inside the quotes and the closing
quote last on the line* — is **68 of the 202 tokens** that block costs. Both are
`o200k_base` counts of `clarion.prompts.cliff_prompt_v2.CLIFF_TASK_RULES` and of its
fifth rule; `python tools/prompt_cost.py` prices the block itself as `task.rules` in
the table above. The rule is in the prompt because an unquoted value is the one shape
error no reading repairs (Appendix C.5), and it is the only rule in that block that
states a *shape*: quoting, brackets and spacing are otherwise taught by the two
conforming examples.

Against the `digest` prompt the saving is **18 976 tokens per cell**, which is
**−88.7 %** in the plain arm (`python tools/prompt_cost.py --pilot`); over the four
pilot files it is **75 904 tokens** and −84.7 %. The saving is the same on every file
and in both arms — the redesign swaps fixed-size instruction blocks for fixed-size
instruction blocks — so only the percentage moves with the document: −76.1 %
(`wmt24pp`, the longest file) to −88.7 % (`probe-ambiguity`) in the plain arm.
`tests/test_prompt_cost_tool.py` asserts that constancy, because a change that made
the saving document-dependent would be a different claim.

## The third style: the specification, compressed to its rules

Both styles above are a choice about how much of the specification to *drop*. The
question they answer badly is the obvious one: the specification does not have to
be 16 838 tokens, because **only 2 492 of its tokens are sentences that state a
rule**. Everything else is motivation, worked examples, comparisons with other
formats, migration notes and design discussion — material a model reproducing a
file cannot use.

`prompt_style: spec` (`clarion/prompts/cliff_rules.py`) sends the rules and nothing
else, and it is the style the shipped configuration selects. Most of it is read
**out of the specification repository at prompt-build time**, which is the part that
matters: there is no hand-kept restatement of those parts to go stale. It carries

- the normative ABNF, comments stripped;
- the ABNF's trailing semantic-constraint block, where the rules a grammar cannot
  express already live (required fields, the `status`/`target` dependency, escape
  rules, brace balance, list-typed fields, key uniqueness, identifier case);
- the field tables of sections 7, 8 and 9, extracted from the specification's own
  markdown, so the key names, required flags and inheritance cannot drift;
- the closed vocabularies, read from the specification's reference tables;
- the specification's own quick example (section 3), not one of ours.

The paragraphs that are written in the module rather than extracted are named in
`cliff_rules.WRITTEN_HERE`, each with the section whose rule it carries, so a reader
knows which parts to review by hand instead of assuming an extraction that does not
cover them; a test asserts each named part is really in the block. They are the
marker rule, the intro, the group-inheritance sentence, the framing line of the
vocabularies, the escape paragraph and the `variant: glossary` section.

| what one CLIFF cell carries | tokens |
| --- | ---: |
| the full specification text, as the reference block `digest` sends | 16 838 |
| the old hand-written digest plus that text | 21 393 |
| **`spec`: the specification compressed to its rules** | **2 925** |
| `examples`: the three blocks that replace it | 1 316 |

The `examples` figure is the stated facts (402), the task rules (489) and the
examples (425). The task rules are not CLIFF-only — every format's prompt carries
them — so the CLIFF-specific part of that column is smaller than the total, and the
comparison that matters is between the two CLIFF specifications: 16 838 tokens of
specification text against 2 925 tokens of extracted rules.

The block decomposes as `python tools/prompt_cost.py --decomposition` prints it —
each part measured on its own, which is why the parts sum to 2 922 against a block of
2 925: a token boundary at a join is shared, and a table that added up by
construction would be wrong about what the block costs.

| part of the compressed block | tokens |
| --- | ---: |
| title line | 17 |
| marker rule, first injection | 99 |
| intro | 65 |
| grammar | 625 |
| semantic constraints | 941 |
| field tables | 258 |
| closed vocabularies | 163 |
| quick example | 190 |
| escape paragraph | 158 |
| glossary section | 307 |
| marker rule, second injection | 99 |
| **sum of the parts** | **2 922** |
| **the block as sent** | **2 925** |

`tests/test_prompt_cost_tool.py` reads both figures out of this document — the
per-part table and the block total — and recomputes them with
`cliff_rules.block_decomposition`, so a part that drifts fails the suite instead of the
table. The ceiling below is the other half of the pair, and it is deliberately loose:
it guards against a doubling, and the exact figures are the ones this document
publishes.

`tests/clarion/test_spec_digest.py` holds the block's other properties: the field
tables are compared against the key sets the parser actually accepts, the closed
vocabularies against the implementation's, every section of the specification that
states a rule must appear in `SECTION_COVERAGE` with a reason (so a compression pass
cannot drop a normative section silently), every paragraph the module writes itself
must be named in `WRITTEN_HERE` and be present in the block, the extraction is proven
to read the specification rather than a copy of it, the marker rule is asserted to be
injected in its primacy and recency positions, and the token ceiling is asserted — a
change that doubles the digest fails there rather than in a paid run. The ceiling is
deliberately loose; the figures that are *published* are pinned exactly by the
decomposition test above, which is the arrangement that let the published parts drift
from 2 834 to 2 925 unnoticed until they were pinned.

**The three levers this style was found by.** They were measured in one cell — CLIFF,
bare arm, the sixteen documents, temperature 1.3, one repeat — because that was the
cheapest design in which a single variable moves. The cell's answers have been pruned,
so the per-cell rates are not republished here; what each lever decided is:

1. **The compressed specification replaced the hand-written prompt.** In the same cell
   the `spec` style left more documents valid than the example-driven style had, six
   files flipping from a parse failure to valid against two the other way, and — the
   part that mattered more than the rate — the *failure list changed kind*. What the
   hand-written prompt had been missing was exactly what the specification states and
   the compression had dropped: the rules, not the rationale. The decision was to keep
   the compression and to read the failures line by line for the rules that were lost
   (both of which are recorded below).
2. **Stating the extent of the answer changes nothing on its own.** The failures at
   that point looked like one missing fact — nothing said the answer *is* the file — so
   the shared rules gained a sentence stating its extent ("opening with that file's
   first line and closing with its last"), the CLIFF block gained the grammar's own
   version of it ("one `cliff-file`, from its version line to its last field", which
   `test_the_answer_boundary_is_stated_in_the_shared_rules` holds), and the cell came
   back at the same rate with two files fixed, two broken, and the behaviour surviving
   in new spellings: `[CONTINUATION VIA NOPER])</chapter-1-004>` inside a `target`
   value, `</final-direction></final-direction>` on a line of its own, an entry marker
   whose id is the field name `source`, and the same invented duplicate entry. That is
   a negative result, and it is kept because it is the reason the sentence stays: it
   costs 14 tokens and states a true property of the deliverable, and it was never
   claimed to be a fix. It also produced the vocabulary-hypothesis that the
   closing-tag section below resolves.
3. **The decoder regime is a lever, and the first one that moved quality.** The same
   cell with `--reasoning low` — one argument different — left more documents valid
   *and* improved chrF++ over all answers and over the survivors, at roughly four times
   the output tokens and 2.7 times the wall clock, because thinking tokens are billed
   as output. The rate difference at n = 16 was not significant, but the failure list
   changed kind again: the notes the model had written into its own answer, the
   invented wrapper tags, the entry marker carrying a comment on the corpus and the
   duplicated invented entries were all gone, leaving quoting failures on the longest
   classical-Chinese lines. This is the lever that made the shipped protocol what it
   is.

**What that round settled about an earlier attribution.** The stored runs could not
separate temperature from prompt content: every 0.0 run also carried the full
specification text, so the difference between them was being charged to a variable
that was never varied alone. The same-cell comparisons above are the first ones that
vary one thing, and they are why `--temperature` and `--reasoning` exist as per-run
arguments rather than as configuration-only settings.

## Two rules the compression dropped, and what the final run shows

Compressing the specification is a lossy operation, and two losses were found the
hard way — by reading the remaining failures line by line, and by noticing that a
measured delivery had stopped happening. Both became paragraphs in the shipped
block, and both are visible in the final run.

**One: the escape rule was only implied.** The `spec` style stated the escape set
only inside the grammar, as `double-escape = "\" ( DQUOTE / "\" / "n" / "r" / "t" )`,
and nothing in prose said *every* ASCII double quote inside a value is written `\"`.
The failures that exposed it are worth describing rather than counting: a long
classical-Chinese `source` value in `hongloumeng-joly` where the model escaped two of
three inner ASCII quotes and missed the third, so the value closed early — the trap
being that the same value also contains CJK curly quotes (`“ ”`), which are ordinary
characters and take no backslash; and a long `target` in `sanguo-brewitt-taylor` that
wrote both inner English dialogue quotes raw.

The paragraph that states the rule — the five escapes, the sentence that the file you
were given already spells them that way, and the CJK-ordinary-character note — costs
**158 tokens**, and
`test_the_escape_rule_is_stated_as_prose_and_not_only_as_a_production` holds it. It
removed the class, not every instance: in the final run three of CLIFF's eight
failures are still on this shape, all three in `sanguo-brewitt-taylor` — `expected a
quoted string` on the same line of two bare-arm answers, at 854 and 948 characters,
and `unterminated string` in the context arm, where a 41-character line opens a string
that never closes. A rule a model must apply inside a long value it is copying
survives most of the time, which is a different claim from "the failures stopped".

**Two: the glossary lost its trigger and its shape, and the trigger alone is worse
than neither.** Once the `spec` style replaced the hand-written workflow blocks,
`glossary emitted` fell to zero: the style said what a glossary *is* and when section
13.2.2 says one is warranted, and never said that this task expects one. The ablation
that followed separated the two failures, and they are not of equal weight:

- **The trigger was the missing piece for emission.** One task-level sentence — the
  deliverable statement the other styles had always carried — is what took emission
  from nothing to roughly two thirds of answers.
- **The trigger alone was the worst configuration measured.** Answers told there were
  two deliverables, and not told how a second document is recognised, invented their
  own separator line between them (`===== OPTIONAL DELIVERABLE: CLIFF GLOSSARY
  (variant: glossary) =====` and two other forms). Every such line is read as a
  malformed field and fails the whole answer, so the arm that delivered the most
  glossaries also had the lowest validity and the lowest chrF++. The block it had
  replaced said the boundary in passing — *"add a CLIFF document after the translated
  file:"* — and dropping it removed the boundary with the delivery.
- **So both were missing, and the boundary was the expensive one.** The shipped block
  states the shape from section 13.2.1 (the `-terms` clan suffix, the `[terms]`
  section, one entry per term carrying `source`, `target`, `type`, `status`,
  `context`) and the boundary as 13.2.2 states it: a second document is recognised by
  its own version line. The first attempt phrased it as *"no heading, no separator, no
  line of explanation"*, which names the banner it was meant to prevent; the
  affirmative phrasing is what ships.

**The final run confirms both halves at scale.** Across the 96 CLIFF answers, **28 of
the 48 bare-arm answers and 37 of the 48 context-arm answers carry a second
document**, and **none of the 96 contains a separator rule line of its own** (checked
as any line consisting only of `=`, `-`, `#`, `*` or `_`, three or more characters).
Emission that high with banners at zero is the combination the ablation said was only
reachable with the trigger *and* the boundary stated, and it is the strongest
evidence in this document for a rule that was written from a sixteen-answer cell.

## The closing-tag question, and the correction this document owes

An earlier version of this section concluded that the model's habit of closing what it
opens "is a model habit at 2–5 % of answers, and prompt position and repetition do not
touch it", on the strength of six prompt variants that all still showed the behaviour.
That conclusion is wrong in one specific way, and the correction is the most useful
thing in this document.

The rule the variants were stating — a section line and an entry line are markers, and
nothing in a CLIFF file is closed — was being stated in a prompt that also told the
model about closing tags. The ABNF's trailing comment block, which the `spec` style
injects, carried three cues and all three were ours:

- the phrase *"single-line marker; no closing tag exists"*;
- an attribution of the status tags to *"(XLIFF 2.x state model)"*;
- the literal `</terms>` in the C.5 note, which put the very string in the prompt that
  the model then emitted.

Removing them removed the behaviour's vocabulary. The same cell that had produced
stray closers under every earlier variant produced none in the de-cued cell — and
then a later cell with the same de-cued block, and a reworded answer-boundary
sentence, produced **8 of 48**. So neither available explanation is the whole truth:

- the **explicit markup vocabulary** (`closing tag`, `XLIFF`, a spelled-out `</terms>`)
  was ours, and removing it removed the class that dominated the earlier cells;
- a **residual rate of a few per cent survives every prompt variant measured**,
  including the de-cued one — which is the part the earlier conclusion got right, and
  the only part of it that is still standing.

What ships is the de-cued block, the marker rule stated positively in three positions
(first in the format block, last in it, and in the user message immediately before the
file), and a `CLIFF_ANSWER_REMINDER` rewritten so that it states what a marker *is*
rather than naming the shape it must not take. The repetition is a deliberate
exception to this project's "say each thing once" rule, recorded in
`clarion/prompts/templates.py`, held by
`test_the_single_line_marker_rule_is_injected_repeatedly_and_in_prime_position`, and
the reminder's wording is held by
`test_the_answer_boundary_is_stated_in_the_shared_rules`.

**The final run's rate is the number to quote: 4 of 96 CLIFF answers — 2 of 48 in each
arm — end with a stray closing line** (`</term>`, `</terms>`, `</glossary>`, and in one
answer a model note glued to the next version line), **and every one of them fails**,
because Appendix C.5 forbids reading markup as an entry. That is the residual. It is
what this format pays for being the one in the comparison whose markers look like XML
tags and have no closing form, and no prompt shape tried against it removed it: three
injections in primacy and recency positions did not, and the one edit that did reach
the class from the other side — a sentence pointing at a tag value written with
something extra — brought eight of forty-eight back.

What is left is therefore the reader, not the prompt: either the C.2.5 clarification
already made (reject the line honestly, which is what happens now) or a documented
wrapper relaxation that drops a stray tag and reports it, which is the only route to a
clean 48/48 and is a specification change that has not been made.

## What the prompt may constrain: the specification and the deliverable

A prompt block may say two things: what the format's own specification requires of
the file, and what we need back. Anything else constrains the model's *working
method*, and that is a constraint we have no reason to impose. If a model produces
the answer by reproducing the file it was given and editing the values in place,
that is a good method, and the prompt's job is to say what the answer is — not how
to get there.

The rule was written down because the shipped blocks violated it, and the clearest
violation was the first sentence every one of the ten formats received:

```
You always return a complete file, never a diff and never a commentary.
```

Three things were wrong with it at once. It fenced a method (`never a diff`) when
the deliverable had already been stated by the sentence before it; it named two
failure shapes, and a named failure shape is a thing a model can produce; and it
addressed three of the ten formats' shared blocks, so every format paid for it.

`tests/clarion/test_tools.py::test_no_prompt_block_fences_the_working_method` now
holds the rule, and it names the phrases an edit would add back rather than
guessing at mood:

| removed | why it is not allowed |
| --- | --- |
| `never a diff` / `never a commentary` | a prohibition where the deliverable statement belongs |
| `Hard rules:` | our framing of the request as a rule list, in all ten formats |
| `Leave the source field untouched` | a prohibition where a property will do |
| `in its original order and count` | no specification section requires entry order; that was our bookkeeping |
| `Keep the glossary concise` / `stop after the last needed term` | a house cap on the optional glossary; 13.2.2 states the criterion instead |

The same rule is why `CLIFF_TASK_RULES` reads as properties of the delivered file
(*"The translation of each entry, in that entry's `target` field"*) rather than as
imperatives (*"Write the translation into the entry's `target` field"*), and why
the glossary block now cites 13.2.2's own criterion for when a glossary is
warranted instead of a rule of ours about repetition. The CLIFF rules still state
the quoting rule and the `status`/`target` dependency, because the specification
and the validator require those of the file; they no longer state anything the
specification does not.

The change is priced per block: `python tools/prompt_block_delta.py <ref>` prints the
token delta of every block against a revision, and its table is the instrument a
reader should use rather than a sentence here — the tool has since been extended to
cover the composed specification block and the paragraphs inside it, so the net figure
this paragraph used to quote (−67 tokens per call against `778bfdc`) was measured by a
narrower version of the same tool and is no longer reproducible as written. What does
not depend on the instrument: the CLIFF task rules fell by about a third, the shared
blocks moved by single digits, and the format comparison stays like-for-like because
every format receives the same shared block set. Every other format's prompt moved by
the shared blocks only.

**The paragraph above once read "facts +115 … net +24", and that was the tool's
fault.** It compared each block's *template source* against the live *rendered*
string, and `CLIFF_FACTS` is an f-string whose `{_row(...)}` calls are long in the
source and short in the value — so the comparison invented a 107-token difference in
a block that had not grown. `tools/prompt_block_delta.py` now executes the previous
revision and reads the attribute, a name the revision does not define is treated as
absent rather than as unchanged, and the parts of a composed block are shown but not
added to the net so that a paragraph and the block containing it are counted once.

## The fact set is bounded by an empirical probe, not by taste

`.tools/probe_repairs.py` runs one minimal document per deviation through both
readings and reports what happens. Under the tolerant reading the harness uses:

| Repaired — so not worth prompt tokens | Unrepairable — must be stated |
| --- | --- |
| quoted tag (C.2.3) | unknown key, in any scope |
| bare scalar in a list-typed field (C.2.1) | `status` in group scope |
| quoted entry id (C.2.4) | value outside a closed vocabulary |
| quoted key (C.2.7) | `status: translated` with no `target` |
| repeated field (C.2.2) | unbalanced ICU brace |
| version-line spelling (C.2.6) | unquoted string |
| identifier with a reserved character (C.2.5) | |

C.2.7 was added after this table was first drawn, and it belongs in the left
column for a checkable reason rather than a stylistic one: the repair removes the
quotes and then checks the enclosed word against the legal keys of its scope, so
`"translater":` is refused exactly as `translater:` is. A relaxation that cannot
legalize a word is shape, so the prompt does not spend a token on it — and the
prompt's "an unquoted string is unrepairable" entry is unaffected, because that is
about a *value* carrying no determinate end, not about a key.

A repair is recorded and priced as `repairs` per row, which is where shape
untidiness belongs: it is a cost, not a failure. Spending instruction tokens on it
would pay twice for something the reader already handles. So the prompt states
**key names and their scope, and the closed vocabularies**, and nothing else; the
examples carry spacing, quoting, brackets and layout.

`tests/clarion/test_prompt_v2.py` checks every stated fact against
`cliff_format` (key sets, vocabularies, required fields), asserts that the
examples validate strictly with zero repairs, and asserts the *absence* of the
repairable rules — an edit that helpfully adds "tags are never quoted" back would
spend tokens on a deviation that no longer fails.

## What the pilot found

Two pilots ran at the deployment settings (temperature 1.3, thinking off), over four
files including the longest in the corpus, scoring every stored answer offline. The
answer they produced is a decision, and it has held up:

**The specification text was not buying format validity.** The token saving was real
and large — measured at the time as a per-cell reduction of about 89 % — while the
validity difference between the two styles was not distinguishable in either
direction at that sample size. The longest file dominated every failure in both
styles and the shortest files were clean in both. That is what made the compressed
`spec` style worth building rather than simply dropping the specification: the
question was never "text or no text", it was "which text", and the pilot said the
rationale was not the part that mattered.

## The failure mode is not what either hypothesis predicted

Reading the breakages line by line (`.tools/show_breakage.py`, a working-copy
instrument) showed what actually went wrong, and it was the same in both styles:

- a long `context` value with one inner quote left unescaped, which moved the
  string's end and broke the parse at the next line;
- a string left unterminated in the middle of the file;
- an entry marker written as `<target: "..."`;
- a group section containing a `source` key;
- in one case the model echoed a brief back instead of translating it — a *valid*
  file with no translation in it.

Every one of these is **output degradation on a long document** — lost escaping and
damaged markers — not an invented key name. That is why the expensive specification
text could not have helped: it defends against the failure the prompt-prevention
hypothesis was about, and the observed failure is a different one. It also means a
prompt that teaches only by example was not shown to be worse; both styles failed the
same way, roughly as often.

The corollary matters for how this benchmark describes itself: on this corpus, **a
large part of what the D3/D4 validity columns measure is single-shot whole-file
regeneration endurance**, not the format. The production workflow does not ask a model
for a 41 KB document — the UE5 plugin sends a compact JSON list and receives
`{id, translation}` pairs, then serializes CLIFF itself — so the whole-file arm is a
harder task than the one it stands in for. The final run's failure composition, read
line by line below, is consistent with that reading.

## The failure the prompt *can* prevent, and where it lives

The translation task never asks the model to name a field: every key it writes is
already on the page. So a translation pilot cannot test the reason this fact set
exists. The invented keys it exists for came from **D7**, whose instruction is "set
the context of this entry" — the model has to produce the key itself, and D7's prompt
carried **no CLIFF content at all**: just a role sentence, the instruction and the
file.

Re-running the same edit sequence with the field table and the task verbs prepended to
the edit prompt produced the largest effect of the whole prompt round, and cost one
paragraph. The per-condition counts are not republished here (the pilot's run
directory is pruned); the finding they produced is reproduced by name, because it is
what the fact set exists for:

- **with no CLIFF content, the model invents plausible field names**: a
  `translator-context` key in entry scope, the same key in group scope, a `status`
  inside a group section, and `ref` / `source-ref` where the field is `reference`;
- **with the key names and their scopes stated, none of them appears**, in any edit, of
  any kind.

Two things follow, and they are worth more than the token saving:

1. **Told the exact key names and scopes, the model uses them; not told, it invents
   plausible ones.** The full specification text was not what prevented the error —
   naming the fields is — which is why `KEYS_BY_SCOPE` is in the example-driven fact
   set, and why the `spec` style *extracts* the same key table from the specification
   instead of restating it by hand.
2. **Repairs went *up* while failures went to zero.** That is not a regression: with
   the keys right, the file no longer fails before the shape deviations can be reached,
   so the tolerant reader finally gets to absorb them and they are priced in the
   `repairs` column instead of the failure column. A lower repair count under a prompt
   that breaks earlier was never a cleaner model, only a truncated measurement. The
   final run shows the same pattern in the other direction: the bare arm needs **0.04
   repairs per answer**, the context arm **0.27**, and the context arm is also the one
   whose edits are harder.

## A metric error worth recording

The first pilot summary reported dozens of "lexical failures" for one `digest` cell
against one for the other style, which looked like a decisive result for the lean
prompt. It was an artifact: the same semantic error (`status: translated` on an entry
with no `target`) was raised once per affected entry, and the metric counted entries
instead of defects. Deduplicated by message, the cell had **one** failure.

The pilot now counts *distinct* failures and separates semantic from syntax failures
(`.tools/prompt_pilot.py`), because the two call for different fixes: a wrong key is a
prompt problem, a lost escape is output degradation. The lesson generalises past that
script, and it is why the instruction metric scores declared rules rather than lines.

## The temperature that never reached the wire

**Every D7 number this harness published before the fix was measured at temperature
0.0, including the ones labelled as the deployment settings.** The cause was one
literal: `run_robustness` built its own `CompletionRequest` with a hard-coded
`temperature=0.0`, and `build_provider` never passes a temperature to the provider at
all — `ProviderConfig.temperature` reached the wire only through `translate.py`, which
reads it for the translation dimension. The same literal was present in the harness's
first commit and never changed.

Two consequences worth separating:

- **A `--temperature 1.3` flag on an edit pilot was a no-op.** It rebuilt a
  `ProviderConfig` whose `temperature` field the provider does not read, so the edit
  dimension kept sending 0.0. Every D7 figure published from those pilots is a 0.0
  figure, and none of them is quoted in this document any more.
- **The controlled comparisons survive, as comparisons.** Both sides of a D7
  comparison used the same model, the same `ui` stratum and the same twelve edits, and
  the edit system prompt was not edited, so for every format except CLIFF the two runs
  sent byte-identical requests — which is why a prompt change can still be attributed
  through them. What they cannot support is a claim about behaviour at 1.3: at the
  time they were written that regime had never been sampled on the edit path at all.

The defect is fixed by making the temperature a parameter of `run_robustness` and
forwarding `provider.temperature` from `run_robustness_matrix`, with
`tests/clarion/test_edit_request.py` as the guard: it fails with `{0.0} == {1.3}` if
the forward is dropped, so the two cannot drift apart again. The final run is the
first D7 measurement at the shipped temperature on the shipped prompt.

## Edit robustness in the final run, and the two rules that work produced

The final run is the first D7 measurement at the shipped temperature on the shipped
prompt: ten formats × two arms × the three documents of the `ui` stratum × twelve
sequential edits = **60 chains**, each edit applied to the previous answer and every
step validated with a checker of comparable strictness.

| format | arm | applicable edits | still valid % | intent applied % | repairs/edit |
| --- | --- | ---: | ---: | ---: | ---: |
| **cliff** | bare | 21 | **100.0** | 95.2 | 0.00 |
| **cliff** | context | 36 | **86.1** | 86.1 | 0.17 |
| xliff-2.1 | bare | 21 | 71.4 | 71.4 | 0.00 |
| xliff-2.1 | context | 36 | 77.8 | 69.4 | 0.00 |
| csv | context | 36 | 94.4 | 88.9 | 0.00 |
| fluent | context | 34 | 97.0 | 69.9 | 0.00 |
| every other format/arm | | | 100.0 | 80.6–100.0 | 0.00 |

Mean validity over the 60 chains is **96.3 %**. Averaged per format over its six
chains, CLIFF is **93.1 %** and **xliff-2.1 is the only format below it** (74.6 %);
fluent (98.5 %) and csv (97.2 %) sit above CLIFF, and the other six are at 100.0 %.

Three things in that table are prompt-design facts rather than format facts:

- **The bare arm is clean: 100.0 % valid over 21 applicable edits.** The arm where no
  edit has to create a field that is not on the page is the arm where the fact set has
  least to do — and it is also where the model has least to invent.
- **The context arm carries the cost: 86.1 % over 36 edits, at 0.17 repairs per
  edit.** The harder arm is the one whose answers need the tolerant reader, which is
  the same pattern the translation dimension shows (0.04 repairs per answer bare,
  0.27 context). Repairs appearing where the work is harder is the reader absorbing
  shape deviations rather than the model becoming sloppier.
- **Validity and intent are reported together for a reason.** `fluent` context is
  97.0 % valid and 69.9 % intent-applied, `xliff-2.1` context 77.8 % and 69.4 %: a
  format can keep a file well-formed while ignoring what it was asked to change, which
  is the failure the pair of columns exists to expose.

**The rule this dimension added: text values are quoted.** The fact table states "an
unquoted string" as unrepairable and therefore as something the prompt must say, and
the prompt did not say it: quoting was taught only by the examples (`context: "..."`,
`dependency: ["..."]`). The edit answers that failed on a value with no determinate
end were the evidence, and `CLIFF_TASK_RULES` rule 5 is the rule it bought — *each
text value is one quoted string, with its final punctuation inside the quotes and the
closing quote last on the line; inside a list, each item is a quoted string.* It says
nothing about tags or brackets, because those are repairs the reader already performs
(C.2.3, C.2.1) and `tests/clarion/test_prompt_v2.py` deliberately forbids re-adding
them. An earlier version of the rule ended with a half-sentence naming the failure ("an
unquoted text value is the one shape error nothing downstream can repair"); it was
dropped for the reason this document keeps returning to — the prompt's job is to say
what to write, and a sentence that describes the wrong answer is a sentence a model can
follow. The test guards both directions: the unrepairable fact is present, the
repairable phrasings are absent, and so are the negative phrasings of either.

**A referential hazard the dimension found in the corpus, not in the model.** One edit
instruction asks for an entry to be renamed, and one answer renamed the *group* of the
same name instead. The resolver is not ambiguous — it looks at entries only, and the
instruction says "the entry" — so the harness's reading is well defined. What the
fixture supplies is the hazard: `ui-console` contains a group `[billing]` *and* an
entry `<billing>` (in `[nav]`), and an earlier `move-entry` in the same sequence places
that entry inside the group of its own name, so by the rename task one name denotes
both a group and a member entry. It is recorded here rather than counted as an
instruction-following failure, and it is the kind of thing a corpus author should not
do twice.

## What the full run settled, and what is still open

The questions this document was written with have answers now, and one of them was a
defect rather than a decision:

1. **The configuration and the code default agree.** The shipped configuration selects
   `prompt_style: spec`, and `DEFAULT_PROMPT_STYLE` was moved off `digest` with it: a
   caller that builds a prompt without a configuration used to get the legacy style,
   which carries the markup vocabulary every other style was cleaned of. `spec` is now
   what both select.
2. **The repeats are independent samples.** At 0.0 the three answers of a cell were
   byte-identical, so "3 repeats" measured consistency rather than sampling variance.
   At 1.3 they are independent samples, which is what the paired tests assume — and
   with `reasoning: low` selected, the vendor's thinking mode governs sampling, so
   the recorded temperature is nominal rather than effective. Numbers recorded at 0.0
   and at 1.3 are not comparable, and the final run is a 1.3 run.
3. **The next lever is the unit of work, not the prompt.** The observed failure mode
   responds to long whole-file regeneration, so the measurement with real leverage is
   **batching the document** — fewer entries per call. That is a change to the task,
   so it belongs in its own arm and must not be mixed into the format comparison.
4. **The affirmative rewrite is measured now.** The prompt that constrains only the
   specification and the deliverable, and states things affirmatively, is what the
   final run sent; its numbers are below. The rewrite itself costs single-digit tokens
   against the wording it replaced.

## The edit dimension: what the earlier comparison decided

Before the fix recorded above, dimension 7 was re-run through the real matrix
(`run_robustness_matrix`, not a stand-in) over the configured `ui` stratum, to compare
the CLIFF edit prompt before and after the field table was added. Both sides of that
comparison sit at temperature 0.0, so its per-cell rates are not republished here; two
findings from it do not depend on the rate and are still standing:

- **A repair count is a count for the whole document at that step.** Summing the
  per-step counts of a chain charges early operations for deviations introduced later,
  because the answer text carries forward and one deviation is re-counted by every
  later step. The working-copy audit that printed both the running total and the count
  the model actually introduced was the instrument for this, and it is pruned with its
  run: what survives is the rule, which is why `tools/compare_readings.py` reports the
  repair total per arm and the repair *kinds*, and why no per-operation repair figure
  is published here. This is the correction that an earlier version of this document
  got wrong, in exactly that way.
- **A cross-model difference was read as a temperature effect, and was neither.** The
  best XLIFF row in this project's history came from an earlier run on a different
  model (`deepseek-v4-flash`), not from a lucky 0.0 sample; every XLIFF failure in the
  `deepseek-flash` runs is an XML parse error clustered at the same few columns, and
  XLIFF asks the model to rewrite a whole XML document per edit. The final run's D7
  table above carries the same story with one model throughout, which is why it is the
  table to quote.

## The shipped prompt's translation measurement

The final run is the first one in which every CLIFF cell sent the shipped prompt
(`prompt_style: spec`) at the shipped decoder regime (`reasoning: low`), with all ten
formats measured in the same pass. CLIFF, single-pass translation, sixteen documents,
three repeats:

| CLIFF, single-pass translation | bare | context |
| --- | ---: | ---: |
| valid (tolerant reading) | **91.7 %** (44/48) | **91.7 %** (44/48) |
| chrF++ over all answers | 46.5 | 49.3 |
| chrF++ over the answers that survive | 50.7 | 53.8 |
| instruction-following | 78.7 % | 81.2 % |
| identifiers kept / coverage | 91.7 % / 91.7 % | 91.7 % / 91.7 % |
| repairs per answer | 0.04 | 0.27 |
| answers carrying a glossary | 28 / 48 | 37 / 48 |
| truncated answers | 0 | 0 |

**The same 44 of 48 answers read strictly are 87.5 % bare and 85.4 % context**, which
is the reading a project without the tolerant mode would see; the column and its
repair kinds are in [clarion-methodology.md](clarion-methodology.md) §9.1, which is
where the two readings are defined.

Three things the table says, in the order they matter for prompt design:

- **The decoder regime is what moved the number, and it moved quality with it.** The
  rate went from a band around half to above ninety per cent across the prompt rounds,
  and the lever that produced most of it was `reasoning: low` — the only lever that
  also moved chrF++. Prompt content moved validity at most and quality not at all.
- **The glossary workflow works at scale**: 28 of 48 bare-arm answers and 37 of 48
  context-arm answers carry a second document, and none of the 96 wrote a separator
  banner of its own. That is the confirmation of the two rules recorded above.
- **The residual failures are not shape failures a prompt can address.** Read line by
  line, four of the eight are a stray closing line after the glossary, one is a
  `status` written into a group section, and three are quoting or termination
  failures on thousand-character classical-Chinese values. The first four are the
  class the closing-tag section resolves; the rest are what a whole-document rewrite
  of a long file costs, and the corpus's own content rules account for the distance
  between `instruction %` 78.7 and 100.

### Why CLIFF's row is the weakest of the ten, and what it is not

CLIFF is the only format in the final run whose valid rate is below 100 in either arm,
and the obvious explanations do not survive the controls, which is worth recording
because each one is the first thing a reader reaches for.

- **Not the values.** `json-cliff` carries exactly the same strings, the same escaping
  needs and the same required `status`/`target` fields — it is the same data model in
  JSON — and it scores **100.0 %** in both arms against CLIFF's **91.7 %**. The
  difference between the two is entirely the serialization.
- **Not the size.** CLIFF's rendered document is among the *smallest* of the ten
  (24 322 tokens over the sixteen documents, against android's 41 228), and
  `json-cliff`'s rendering of the same content is longer in characters. A longer file
  is not the problem.
- **Not the prompt content.** The pilot's `digest` condition carried the full
  specification text and landed in the same band as the styles that do not; telling
  the model more about CLIFF did not make it survive.
- **Not the temperature alone.** Every format in the run is measured at the same
  recorded temperature and the same reasoning tier; CLIFF's failure rate is not shared
  by the other nine.

What is left is the property the format chose deliberately: **CLIFF has no
delimiters.** Structure is positional — an entry runs from its `<id>` to the next
`<id>` or `[group]` — so there is nothing that contains a slip.

- A **lost closing quote is a cascade**: the next line begins with a quote, which is
  the documented adjacent-string continuation, so it is absorbed into the broken
  string and the parser reports a failure far from its cause. Two of the eight failures
  are exactly this, on the longest classical-Chinese values.
- A **stray closing line is read as a malformed field**, not ignored: four of the eight
  failures are a `</terms>`-shaped line after the glossary, and Appendix C.5 requires
  the reader to reject it rather than drop it, because dropping it would be inventing
  a document the model did not write.

So the format is robust to *structural* damage and fragile to *semantic* damage —
exactly the trade its design makes, and the reason "deleting a line cannot unbalance
the document" is a true statement that is not the same as "a deleted line is
harmless". A format with braces or closing tags contains the same slip locally, and
the model's prior for those syntaxes is larger; both effects point the same way. That
is the honest reading of CLIFF's row, and it is a statement about this protocol on
this corpus, not a ranking of formats in general.
