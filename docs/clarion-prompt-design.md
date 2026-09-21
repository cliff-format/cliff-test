# Prompt design: what the CLIFF specification text was buying

This records a measured prompt-cost experiment, not a proposal. The question was
whether the 16 316-token reference specification that CLIFF's prompt carried in
every recorded run earned its place, and the answer turned out to be narrower than
either side of the argument expected.

## What was measured

`python -m clarion tokens` on the recorded run puts CLIFF's `format instructions`
at about 46 400 tokens per arm (16 cells), of which **16 316 per cell is the full
text of `cliff-1.1.0.md`**, injected with the sentence *"Before writing the
answer, consult the relevant sections of this full specification"*. In the plain
arm CLIFF's instructions cost more than twice the document they describe.

The replacement (`clarion/prompts/cliff_prompt_v2.py`, selected with
`prompt_style: examples`) states only what a tolerant reader cannot repair, and
teaches the rest with two conforming documents. Every number below is measured,
not estimated: `python tools/prompt_cost.py` assembles both styles through the same
`build_translation_prompt` the run uses and prints these rows, and
`tests/test_prompt_cost_tool.py` checks that the tool reproduces the published
totals and that each column adds up to its own total.

| | current (`digest`) | example-driven (`examples`) |
| --- | ---: | ---: |
| specification text, block as sent | 16 691 | — |
| specification digest, core + supplement | 2 785 | — |
| stated facts: keys, scopes, vocabularies | — | 402 |
| task rules (generic + CLIFF + output shape) | 280 | 482 |
| format notes | 117 | — |
| edit-safety reminder | 118 | — |
| examples | — | 425 |
| system role | 63 | 63 |
| terminology policy | 236 | 236 |
| glossary workflow | 231 | 231 |
| the document itself | 571 | 571 |
| **one cell, `ui-console` plain arm** | **21 092** | **2 410** |

The rows are the measured blocks of one cell; each column adds up to its total. The
specification text was 16 316 tokens when the recorded run priced it and is 16 656
now — the specification itself has grown since (Appendix C.2.7 among the additions),
which is a second reason a prompt that carries it is expensive to keep current.

The quoting rule is the last of the five CLIFF task rules and costs 66 of those 482
tokens: two of the 1.3 edit run's four invalid answers were a text value written
without quotes, which is the one shape error no reading repairs (Appendix C.5). The
specification text it replaced cost 16 691.

Across the four pilot files the saving is **74 728 tokens**, which is
**−84.6 %** of the prompts in the plain arm and −78.5 % in the context arm
(`python tools/prompt_cost.py --pilot`). The saving is the same 18 682 tokens per
cell on every file and in both arms — the redesign swaps fixed-size instruction
blocks for fixed-size instruction blocks — so only the percentage moves with the
document: −75.9 % (`wmt24pp`, the longest file) to −88.7 % (`probe-ambiguity`) in
the plain arm. `tests/test_prompt_cost_tool.py` asserts that constancy, because a
change that made the saving document-dependent would be a different claim.

## The third style: the specification, compressed to its rules

Both styles above are a choice about how much of the specification to *drop*. The
question they answer badly is the obvious one: the specification does not have to
be 16 656 tokens, because **only 2 467 of its tokens are sentences that state a
rule**. Everything else is motivation, worked examples, comparisons with other
formats, migration notes and design discussion — material a model reproducing a
file cannot use.

`prompt_style: spec` (`clarion/prompts/cliff_rules.py`) sends the rules and nothing
else. It is assembled **from the specification repository at prompt-build time**,
which is the part that matters: there is no hand-written restatement to go stale.
It carries

- the normative ABNF, comments stripped;
- the ABNF's trailing semantic-constraint block, where the rules a grammar cannot
  express already live (required fields, the `status`/`target` dependency, escape
  rules, brace balance, list-typed fields, key uniqueness, identifier case);
- the field tables of sections 7, 8 and 9, extracted from the specification's own
  markdown, so the key names, required flags and inheritance cannot drift;
- the closed vocabularies, read from the specification's reference tables;
- the specification's own quick example (section 3), not one of ours;
- the `variant: glossary` rules of section 13.2.

| what one CLIFF cell carries | tokens |
| --- | ---: |
| the full specification text (the `digest` style) | 16 656 |
| the old hand-written digest plus that text | 21 092 |
| **`spec`: the specification compressed to its rules** | **2 568** |
| `examples`: our hand-written facts plus two conforming files | 1 029 |

The compressed block decomposes as the ABNF (613), the ABNF's semantic-constraint
block (794), the field tables of sections 7-9 (258), the specification's own example
(173), the escape rule (136) and the glossary section (307), with the closed
vocabularies and the lines that frame them at 287 — `tests/clarion/test_spec_digest.py`
reproduces each of them.

Three guards hold it in `tests/clarion/test_spec_digest.py`: the key tables are
compared against the key sets the parser actually accepts, every section of the
specification that states a rule must appear in `SECTION_COVERAGE` with a reason
(so a compression pass cannot drop a normative section silently), and the token
ceiling is asserted — a change that doubles the digest fails there rather than in a
paid run.

**First measurement, one repeat.** CLIFF, bare arm, the sixteen files, 1.3, one
repeat per file (16 answers, run `clarion-deepseek-flash-20260921T164514`):

| style | valid | 95 % Wilson | prompt tokens per call |
| --- | ---: | --- | ---: |
| `spec` | **11/16 = 68.8 %** | 44–86 % | 4 297 |
| `examples` | 7/16 = 43.8 % | 23–67 % | 3 326 |

Six files flip from a parse failure to valid (`game-quest`, `game-shard`,
`godot-l10n`, `legal-privacy`, `news-wire`, `probe-ambiguity`), two flip the other
way, and the difference is **not yet significant** (Fisher exact p = 0.25 against
the three-repeat `examples` cell; n = 16 on one side). It is recorded because the
direction is the one the failure analysis predicted: what the hand-written prompt
was missing is exactly what the specification states and we had compressed away.

**Second measurement: the answer boundary, stated, changes nothing.** The five
remaining failures in that run were read line by line and three of them were the
model writing its own notes into the answer (a `{"note": ...}` object, `##### Result
impossible.`, an entry marker followed by a comment on the corpus), one was an
answer that stopped mid-string, and two were invented duplicate entries. That looked
like one missing fact — nothing said the answer *is* the file — so the shared rules
gained a sentence stating its extent ("opening with that file's first line and
closing with its last", +14 tokens, guarded by
`test_the_answer_boundary_is_stated_in_the_shared_rules`), the CLIFF block gained the
grammar's own version of it ("one `cliff-file`, from its version line to its last
field"), and the same cell was re-run (`clarion-deepseek-flash-20260921T171241`).

**11/16 = 68.8 % again.** Two files were fixed, two broke, and the behaviour the
sentence was for survived in new spellings: `[CONTINUATION VIA NOPER])</chapter-1-004>`
inside a `target` value, `</final-direction></final-direction>` on a line of its own,
an entry marker whose id is the field name `source`, and the same duplicated entry
(`abstract-2`) the previous run had produced.

That is a result, and it is a negative one: at 1.3 the failure rate does not respond
to prompt content. Two levers have now been pulled in this same cell — the rewrite
(−15 points) and the boundary statement (0 points) — while the compressed
specification moved it +25 points in one pass, which is why the specification stays
and the boundary sentence is recorded as insufficient rather than harmful.

**Third measurement: the decoder regime is the lever.** Same cell, same prompt, same
temperature, one argument different — `--reasoning low`
(`clarion-deepseek-flash-20260921T171557`):

| cell (CLIFF, bare, 16 files, one repeat) | valid | chrF++ all | chrF++ on survivors | output tokens per call |
| --- | ---: | ---: | ---: | ---: |
| `examples`, thinking off | 7/16 = 43.8 % | 25.1 | 47.8 | 3 161 |
| `spec`, thinking off | 11/16 = 68.8 % | 42.2 | 50.5 | 2 443 |
| `spec`, thinking off + boundary sentence | 11/16 = 68.8 % | — | — | 2 221 |
| **`spec`, `reasoning: low`** | **14/16 = 87.5 %** | **46.9** | **53.6** | 9 154 |

The p-value between the two `spec` cells is 0.39 — sixteen answers cannot settle it —
but the *failure list* changes kind, which is what this sample can support: the notes
the model wrote into its own answer, the invented wrapper tags, the entry marker
carrying a comment on the corpus and the duplicated invented entries are all gone,
leaving two answers whose quoting fails on the longest classical-Chinese lines.
Quality moves for the first time as well (+4.7 all, +3.1 on survivors), and the cost
is 4.1× the output tokens and 2.7× the wall clock, because thinking tokens are billed
as output.

**What this settles about the earlier attribution.** The stored runs could not
separate temperature from prompt content: every 0.0 run also carried the full
specification text, so the −35 points between them were being charged to a variable
that was never varied alone. What the same-cell comparisons now show is that the
*decoder regime* is what the single-pass number responds to, and `--temperature` and
`--reasoning` exist so the two can be told apart from here on.

## The escaping and glossary ablations: two rules the compression dropped

Compressing the specification is a lossy operation, and two losses were found the
hard way — by reading the two remaining failures line by line, and by noticing that
a measured delivery had stopped happening.

**One: the escape rule was only implied.** The `spec` style stated the escape set
only inside the grammar, as `double-escape = "\" ( DQUOTE / "\" / "n" / "r" / "t" )`,
and nothing in prose said *every* ASCII double quote inside a value is written `\"`.
Two answers failed on exactly that, and the character-level read is unambiguous:

- `hongloumeng-joly`, an 801-character `source` value of classical Chinese: the
  model escaped two of the three inner ASCII quotes and missed the third, so the
  value closed early. The trap is that the same value also contains CJK curly quotes
  (`“ ”`), which are ordinary characters.
- `sanguo-brewitt-taylor`, a 933-character `target`: the model wrote both inner
  English dialogue quotes raw.

A paragraph stating the escape set, plus the CJK note, costs 136 tokens. In the next
run the `sanguo` answer was valid and the `hongloumeng` answer parsed (its remaining
failure is a duplicated entry), and no answer has failed on a missing escape since.
`test_the_escape_rule_is_stated_as_prose_and_not_only_as_a_production` holds it.

**Two: the glossary lost its trigger and its shape, and the trigger alone is worse
than neither.** `glossary emitted` went from 41/96 in the recorded run to **0/16**
once the `spec` style replaced the hand-written workflow blocks. Reading what the
style actually sent: it stated what a glossary *is* and when one is warranted
(section 13.2.2's criterion) and never said that this task expects one. So the
ablation ran in the same cell, one repeat, `reasoning: low` throughout:

| cell — CLIFF, bare, 16 files, one repeat | valid | answers with a 2nd document | separator banners written | chrF++ all | instruction % |
| --- | ---: | ---: | ---: | ---: | ---: |
| no trigger (the state that measured 0/16) | 14/16 | 0/16 | 0/16 | 46.9 | 70.9 |
| **A: trigger only** | **5/16** | 10/16 | **9/16** | 15.5 | **22.0** |
| B: trigger + shape + boundary | 14/16 | 13/16 | 0/16 | 49.0 | 70.6 |
| **B2: the same, stated affirmatively** | **16/16** | 10/16 | 0/16 | 49.0 | 70.0 |

- **The trigger was the missing piece** for emission: the criterion sentence was
  already there and produced nothing, because nothing said the glossary was wanted
  *here*. One task-level sentence — the deliverable statement the other styles have
  always carried — took it from 0/16 to 10/16.
- **But the trigger alone is the worst cell in this document.** Nine of the sixteen
  answers introduced their own separator between the two documents —

  ```
  ===== OPTIONAL DELIVERABLE: CLIFF GLOSSARY (variant: glossary) =====
  ----- OPTIONAL DELIVERABLE: GLOSSARY (CLIFF, variant: glossary) -----
  ===== OPTIONAL SECOND FILE: GLOSSARY (separate deliverable) =====
  ```

  — and the parser reads each as an invalid field name, so the whole answer fails:
  5/16 valid, instruction % 22, chrF++ 15.5. The model had been told there were two
  deliverables and had not been told how a second document is recognised. The
  removed workflow block had said it in passing (*"add a CLIFF document after the
  translated file:"*), and dropping it removed the boundary with it.
- **So the answer to "is the sentence too weak or is the trigger missing" is both,
  in that order of danger.** The trigger was absent; the statement of how the second
  document attaches was absent too, and its absence is the one that costs ten
  answers. Both are now in the specification block — the shape from section 13.2.1
  (the `-terms` clan suffix, the `[terms]` section, one entry per term with `source`,
  `target`, `type`, `status`, `context`) and the boundary as section 13.2.2 states
  it (a second document is recognised by its own version line, so the glossary
  begins with its own `CLIFF 1.1` line placed immediately after the last field of
  the translated file). Stated affirmatively: the first attempt phrased it as *"no
  heading, no separator, no line of explanation"*, which names the banner it was
  meant to prevent; the affirmative version is the one that scored 16/16.

**What this round establishes about the prompt as a whole.** With `reasoning: low`
and the specification block carrying the escape rule, the glossary trigger, its
shape and the two-document boundary, this cell is at **16/16 valid** — the first
time any CLIFF cell has been clean. The remaining failures are not format failures:
they are the corpus's own content rules (`instruction %` 70 — `require` 61, `forbid`
21, `max-width` 13, `name-policy` 10, `cjk-latin-space` 9, `regex` 7, `term` 6,
`keep-verbatim` 2, `length-ratio` 1 across fourteen files), which no parser can see
and which the model does not check.

**Confirmed at three repeats, and this is the number to quote.** The same cell with
`--repeats 3` (48 answers, run `clarion-deepseek-flash-20260921T173854`):

| cell — CLIFF, bare, sixteen files | valid | 95 % Wilson | 2nd document | chrF++ all | instruction % | output tokens/call |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `examples`, thinking off (3 repeats) | 23/48 = 47.9 % | 34–62 % | 23/48 | 30.8 | 48.4 | 2 963 |
| the recorded deployment run (3 repeats) | 28/48 = 58.3 % | 44–71 % | 18/48 | 36.5 | 56.4 | 2 648 |
| **`spec` + `reasoning: low` (3 repeats)** | **44/48 = 91.7 %** | **80–97 %** | 26/48 | **46.7** | 65.4 | 13 310 |

Fisher exact against the shipped settings before this work: **p < 0.0001**. The
isolated comparison — same prompt, same cell, only the decoder regime — is
`spec` with thinking off 11/16 against `spec` with `reasoning: low` 16/16,
**p = 0.043**.

The four failures are one shape plus one, and neither is a misunderstanding of the
format: three are an ASCII double quote written without its backslash (two in
`hongloumeng-joly`, whose classical-Chinese values mix CJK curly quotes with ASCII
ones; one in `ui-console`, `context: "…连接词 "across" 译为…"`), and one is a
reviewer note appended after the last entry (`lit-drama`: *"Notes for the reviewer:
every entry's new text is in `target:`…"*). Both were the failure modes the escape
paragraph and the answer-boundary sentence were for. The glossary trigger holds at
scale (26/48, against 41/96 in the recorded run) and **no answer wrote a separator
line**.

What is left is no longer a format problem: `instruction %` 65.4 means about a third
of the corpus's own content rules are still violated — `require`, `forbid`,
`max-width`, `name-policy`, `cjk-latin-space`, `regex`, `term`, `keep-verbatim`,
`length-ratio` — in answers that parse, validate and carry every identifier.

## The prompt has a floor: two levers that worked and one class that does not move

Three prompt edits were made against the failures of the clean cell, and the
difference between them is the useful part of this record.

**Naming the convention worked.** The three escaping failures went to zero when the
paragraph stopped listing the rule and started *naming* it — a value is **a C-style
string literal**, five escapes, and the file you were given already spells them that
way, so the backslashes come through as written. The second half is what mattered:
the corpus line the model was copying already contained `\"`, and the model had been
"tidying" the backslashes out of it. Naming the convention supplies the prior; the
copy sentence stops it from being overridden.

**Stating the rule the ABNF comment carried did not.** The grammar's comment on
`entry-line` says *"single-line marker; no closing tag exists"* — and
`grammar_only()` strips every comment, so the prompt had never said it. A paragraph
now states it affirmatively ("each stands alone on its own line, and what it opens
runs until the next such line or the end of the document"). It is worth keeping and
it is guarded by a test, but it did not remove the behaviour:

| prompt variant | answers | with a stray closing tag | tags in total |
| --- | ---: | ---: | ---: |
| recorded run (`examples` + the skeleton blocks, thinking off) | 48 | 3 | 3 |
| `examples` after the rewrite (no skeleton, thinking off) | 48 | 5 | 10 |
| `spec`, thinking off (one repeat) | 16 | 4 | **58** |
| `spec` + `reasoning: low` | 48 | 3 | 3 |
| `spec` + `reasoning: low` + the marker paragraph | 48 | **2** | 3 |

The model closes what it opens — `</terms>`, `</result>`, `</preset>`, and in one
answer a whole chain of closers (`</hp></loot></default></cache>…`) as if every entry
needed one. It has done so in **every prompt variant this project has measured**,
including the recorded run, and thinking off makes it an order of magnitude worse
(58 tags in 16 answers). This is a model habit, not a missing sentence, and the
prompt side has reached its floor on it.

**What that leaves.** The class is 2–5 answers per 48, and it costs the whole answer
even though a closing tag carries no information: the tolerant reader normalises
`</terms>` into the entry id `terms` (Appendix C.2.5 lists `/` among its reserved
characters, and C.3 strips it), so the document fails on `entry 'terms' is missing
required field 'source'` — an entry the answer does not contain. **A reader that must
not invent data is the tool for this**, which is the C.2.8 proposal in the changelog:
either clarification (a marker whose identifier does not begin with a name character
is not an entry marker, so the line is rejected honestly) or a documented wrapper
relaxation (the tag is dropped and reported). Both are specification changes, and
neither has been made.

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

The change is priced: `python tools/prompt_block_delta.py <ref>` prints the token
delta of every block against a revision. Against `778bfdc` (the state before this
rewrite) the CLIFF task rules fell by 91 tokens, the shared task rules by 15, the
deliverable block by 6, and the facts block rose by 8 (the orientation paragraph);
with the system role (+13), the output shape (+5), the glossary workflow (+17) and
the edit-safety reminder (+2), the net for the whole prompt is **−67 tokens per
call**. Every other format's prompt moved by the shared blocks only, which is the
same block set for all ten, so the format comparison stays like-for-like.

**That paragraph read "facts +115 … net +24" until the tool was fixed.** It compared
each block's *template source* against the live *rendered* string, and `CLIFF_FACTS`
is an f-string whose `{_row(...)}` calls are long in the source and short in the
value — so the comparison invented a 107-token difference in a block that had not
grown. `tools/prompt_block_delta.py` now executes the previous revision and reads
the attribute, and `tests/test_prompt_cost_tool.py` holds the two ends together.

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

Two pilots at the deployment settings (temperature 1.3, thinking off), 52 cells
over four files, scoring every stored answer offline:

| style | n | valid | 95 % Wilson | repairs/run | prompt tokens |
| --- | ---: | ---: | --- | ---: | ---: |
| `digest` | 26 | 16 | 43–78 % | 0.31 | 23 880 |
| `examples` | 26 | 17 | 46–81 % | 0.23 | 5 345 |

Per file, the longest file dominated every failure: `wmt24pp` (42 entries, 41 KB)
scored 7/17 and 9/17 valid, while `probe-ambiguity` and `ui-workbench` scored 3/3
in both styles. No difference is distinguishable: 16/26 against 17/26 over all
files gives Fisher exact p = 1.0000, and the worst single file, `wmt24pp`,
p = 0.7319.

**Conclusion: the specification text was not buying format validity.** The
token saving is real and large; the validity difference is not measurable at this
sample size in either direction.

## The failure mode is not what either hypothesis predicted

Reading the breakages line by line (`.tools/show_breakage.py`) shows what actually
went wrong, and it is the same in both styles:

- a 487-character `context` value with one inner quote left unescaped
  (`...the "pensioner", New South Wales...`), which moved the string's end and
  broke the parse at the next line;
- a string left unterminated in the middle of the file;
- an entry marker written as `<target: "..."` ;
- a group section containing a `source` key;
- in one case the model echoed a brief back instead of translating it
  (`coverage 0.12` with a *valid* file).

Every one of these is **output degradation on a long document** — lost escaping
and damaged markers — not an invented key name. That is why the expensive
specification text could not have helped: it defends against the failure the
prompt-prevention hypothesis was about, and the observed failure is a different
one. It also means a prompt that teaches only by example was not shown to be
worse; both styles fail the same way, roughly as often.

The corollary matters for how this benchmark should describe itself: on this
corpus, **a large part of what the D3/D4 validity columns measure is single-shot
whole-file regeneration endurance**, not the format. The production workflow does
not ask a model for a 41 KB document — the UE5 plugin sends a compact JSON list
and receives `{id, translation}` pairs, then serializes CLIFF itself — so the
whole-file arm is a harder task than the one it stands in for.

## The failure the prompt *can* prevent, and where it lives

The translation task never asks the model to name a field: every key it writes is
already on the page. So a translation pilot cannot test the reason this fact set
exists. The recorded run's invented keys came from **D7**, whose instruction is
"set the context of this entry" — the model has to produce the key itself, and
D7's prompt carried **no CLIFF content at all**: just a role sentence, the
instruction and the file.

Re-running the same edit sequence with the field table and the task verbs
prepended to the edit prompt (`python .tools/d7_pilot.py`, 48 edits per condition,
**sent at temperature 0.0** — see "The temperature that never reached the wire"
below, because the edit dimension could not yet honour the configured value):

| edit prompt | invented-key failures | edit not valid | repairs per edit |
| --- | ---: | ---: | ---: |
| historical (no CLIFF content) | **9 / 48 = 18.8 %** (95 % CI 10.2–31.9) | 18.8 % | 0.17 |
| with the field table | **0 / 48 = 0 %** (95 % CI 0–7.4) | 0 % | 0.42 |

Fisher exact **p = 0.0026** (this figure was published as 0.0129 while the test that
produced it was defective - see the correction in the changelog and
`clarion/metrics/stats.py::fisher_exact`; the corrected p is smaller, so the
conclusion is unchanged and stronger); the `examples` condition was 100 % valid and 100 %
intent-applied in all six cells. The historical condition's 18.8 % reproduces the
18.8 % measured on the full recorded run, so the pilot is exercising the real
mechanism rather than a contrived one. The invented names were
`translator-context` (in both entry and group scope), `status` inside a group,
`ref` and `source-ref`.

Two things follow that are worth more than the token saving:

1. **The objective's premise is confirmed with evidence.** Told the exact key
   names and scopes, the model uses them; not told, it invents plausible ones. An
   example-driven prompt is sufficient for this, so the full specification text
   was not what prevented the error — naming the fields is.
2. **Repairs went *up* while failures went to zero** (0.17 → 0.42 per edit). That
   is not a regression: with the keys right, the file no longer fails before the
   shape deviations can be reached, so the tolerant reader finally gets to absorb
   them and they are priced in the `repairs` column instead of the failure column.
   A lower repair count under a prompt that breaks earlier was never a cleaner
   model, only a truncated measurement.

## A metric error worth recording

The first pilot summary reported **35 "lexical failures"** for one `digest` cell
against 1 for `examples`, which looked like a decisive result for the lean prompt.
It was an artifact: the same semantic error (`status: translated` on an entry with
no `target`) was raised once per affected entry, and the metric counted entries
instead of defects. Deduplicated by message, the cell has **one** failure. The
pilot now counts *distinct* failures and separates semantic from syntax failures
(`.tools/prompt_pilot.py`), because the two call for different fixes: a wrong key
is a prompt problem, a lost escape is output degradation.

## The temperature that never reached the wire

**Every D7 number ever published by this harness was measured at temperature 0.0,
including the ones labelled as the deployment settings.** The cause was one
literal: `run_robustness` built its own `CompletionRequest` with a hard-coded
`temperature=0.0`, and `build_provider` never passes a temperature to the provider
at all — `ProviderConfig.temperature` reached the wire only through
`translate.py`, which reads it for the translation dimension. The same literal was
present in the harness's first commit and never changed.

Two consequences worth separating:

- **`d7_pilot.py --temperature 1.3` was a no-op.** The flag rebuilt a
  `ProviderConfig` whose `temperature` field the provider does not read, so the
  edit dimension kept sending 0.0. The D7 pilot table above and the D7 re-run table
  below are 0.0 measurements.
- **The controlled comparisons survive.** Both D7 columns use the same model, the
  same `ui` stratum and the same 12 edits, and `EDIT_SYSTEM` was not edited, so for
  every format except CLIFF the two runs sent byte-identical requests. CLIFF's
  movement (validity 83.3 % → 100.0 %, intent 77.8 % → 98.6 % in the context arm)
  is attributable to the prompt change, because that is the only input that
  differed. What that comparison cannot support is a claim about behaviour at
  1.3: at the time it was written that regime had never been sampled, and it is
  measured separately below.

The defect is fixed by making the temperature a parameter of `run_robustness` and
forwarding `provider.temperature` from `run_robustness_matrix`, with
`tests/clarion/test_edit_request.py` as the guard: it fails with
`{0.0} == {1.3}` if the forward is dropped, so the two cannot drift apart again.
The 1.3 baseline it made possible is below.

## The CLIFF edit baseline at 1.3, and what the failures are

CLIFF only - the format under test. Three passes over the same `ui` stratum and
the same 12 edits, `python .tools/d7_cliff_13.py --passes 3`, 171 applicable
edits, every answer kept (`results/d7-cliff-13/`):

| temperature | still valid | intent applied | per-pass intent |
| --- | ---: | ---: | --- |
| 0.0 (every earlier number) | 100.0 % | 100.0 % / 98.6 % | repeats byte-identical |
| **1.3 (deployment)** | **97.7 %** | **95.9 %** | 96.5 / 93.0 / 98.2 |

The honest headline: **at the temperature the pipeline ships, CLIFF edits are
97.7 % valid and 95.9 % intent-applied**, with about 1 point of pass-to-pass
spread on validity and 2.7 on intent. The earlier 100 % was real but it was a 0.0
number, and the difference between the two rows is the decoder.

Seven of 171 edits failed, and the stored answers attribute each one
(`.tools/d7_cliff_forensics.py`):

**Four answers were not CLIFF at all** (the tolerant reader cannot save a value):

- `context: Reviewed in the 2026 audit.` - a text value with no quotes. Appendix
  C.5 forbids repairing a value, and C.2.1's list relaxation does not cover an
  unquoted string either, so the refusal is correct behaviour.
- `context: "Line under the time zone option on the settings page.".;` - a
  sentence-final period written *outside* the closing quote.
- `reference: src/ui/panel.cpp:42` - an unquoted string as a list value. C.2.1
  repairs a bare *tag*, a *quoted* scalar, or a comma-separated series; this is
  none of the three, and the value has no determinate end, so it is refused.
- a **32-byte stub**, `<support>...invalid...</support>`, in place of the file. This
  is not a format deviation but a degenerate answer, and it is the most severe
  shape available: nothing in it is usable. Rate 1/171.

**Three answers were valid but did not apply the instruction:**

- `set-emotion` on `billing` (`ui-console`): the entry is **byte-identical before
  and after** - the model did nothing. The same edit, on the same entry, was also
  the single gap in the 0.0 run, so this is a reproducible no-op rather than
  sampling noise.
- `set-target` on `billing` (bare arm): the instruction gives the value
  `计费(修订)`; the model wrote `Billing (revised)`. It invented a value instead of
  copying the one it was given.
- `rename-entry` on `billing`: the model renamed the **group** `billing` to
  `billing-v2` and left the entry id alone. The reference resolver is not
  ambiguous - it looks at entries only - and the instruction does say "the entry",
  so the harness's own answer is well defined. What the file supplies is a
  referential hazard: `ui-console` contains a group `[billing]` *and* an entry
  `<billing>` (in `[nav]`) from the start, and task 7's `move-entry` then places
  that entry *inside* the group of its own name, so by task 8 a single name denotes
  both a group and a member entry. The collision is a property of the corpus file
  and the generated sequence, not of the model, which is why it is recorded here
  rather than treated as a plain instruction-following failure.

**The one prompt gap this found, and the rule it added.** The design states "an
unquoted string" is unrepairable and therefore must be in the prompt, but the prompt
text never said it: quoting was taught only by the examples (`context: "..."`,
`dependency: ["..."]`). Two of the four invalid answers were exactly that gap.

`CLIFF_TASK_RULES` rule 5 now states it, and only it: *each text value is one
quoted string, with its final punctuation inside the quotes and the closing quote
last on the line; inside a list, each item is a quoted string.* It says nothing
about tags or brackets, because those are repairs the reader already performs
(C.2.3, C.2.1) and `tests/clarion/test_prompt_v2.py` deliberately forbids
re-adding. A later edit dropped the half-sentence that named the failure ("an
unquoted text value is the one shape error nothing downstream can repair") for the
reason this document keeps coming back to: the prompt's job is to say what to
write, and a sentence that describes the wrong answer is a sentence a model can
follow. The boundary is unchanged — it is stated in the fact table above and
asserted by the test — only the prompt stopped reciting it. The test guards both
directions: the unrepairable fact is present, the repairable phrasings are absent,
and so are the negative phrasings of either.

Repairs introduced by the model were again confined to the two operations that
require creating a field that is not on the page: 7 in total, `add-reference` 5
and `set-emotion` 2. Note the count: the per-step sum is 51, because a deviation
introduced once is re-counted by every later step of the chain.

## Open decisions for a full re-run

1. `prompt_style: examples` is what the shipped configuration
   (`configs/deepseek-flash.json`) selects, and one deployment-settings run has
   used it (below). The code's `DEFAULT_PROMPT_STYLE` is still `digest`, so a
   caller that builds a prompt without a configuration gets the older style; that
   default is what a full re-run should revisit, not the configuration.
2. Temperature 1.3 changes the meaning of the repeats: at 0.0 the three answers of
   a cell were byte-identical, so they measured consistency rather than sampling
   variance. At 1.3 they are independent samples, which is what the paired tests
   assume. Numbers recorded at 0.0 and at 1.3 are not comparable. **This applies to
   the translation dimension only** — the edit dimension had no 1.3 measurement at
   all until the defect above was fixed.
3. The next measurement with real leverage is not prompt length but **batching the
   document** (fewer entries per call), since that is what the observed failure
   mode responds to. That is a change to the task, so it belongs in its own arm
   and must not be mixed into the format comparison.
4. The prompt rewrite of this round (affirmative phrasing, and no constraint beyond
   the specification and the deliverable) is **unmeasured**: the recorded run sent
   the previous wording. It is +31 tokens per call and it changes the shared blocks
   for all ten formats, so it needs its own run before any of its numbers are quoted
   as current.

## The D7 re-run with the example prompt

`prompt_style: examples` was adopted after the pilots along with
`temperature: 1.3`, and dimension 7 was re-run through the real matrix
(`run_robustness_matrix`, not a stand-in) over the configured `ui` stratum,
2 passes × 12 edits, 240 model calls. Of the two settings **only the prompt
change reached this run**: the edit path sent every request at temperature 0.0
regardless of the configuration, for the reason recorded above. The comparison in
the table is therefore valid — same model, same files, same edits, same
temperature, only the CLIFF edit prompt differs — but it is a 0.0 comparison, not
a deployment-settings one.

| format | arm | still valid % | intent applied % | invented-key failures | repairs |
| --- | --- | ---: | ---: | ---: | ---: |
| **cliff** | bare | **100.0** | 100.0 | **0** | 0 |
| **cliff** | context | **100.0** (was 83.3) | 98.6 | **0** (was 2) | 44 |
| xliff-2.1 | bare | 59.5 (was 57.1) | 59.5 | 0 | 0 |
| xliff-2.1 | context | 62.5 (was 55.6) | 48.6 | 0 | 0 |
| the other eight formats | both arms | 100.0 | 70.8–100.0 | 0 | 0 |

CLIFF's context arm moved from 83.3 % to **100.0 % still valid with no invented
key anywhere in the run**. The tolerant reader absorbed every repair and none
became a failure. The count needs care, because a repair count is the count for
the *whole document* at that step and the answer text carries forward: summing the
per-step counts gives **44** for the six context cells, but a deviation introduced
once is re-counted by every later step. The repairs the model actually
*introduced* are **6**, and they sit on exactly the two operations that require it
to create a field that is not on the page — `add-reference` 4 and `set-emotion`
2 (`.tools/d7_audit.py` prints both numbers, and the counts are monotone within
every cell, so the difference is re-counting rather than fluctuation). The bare
arm introduced 0. That is the division of labour the design intends: the prompt
gets the key names right, and the tolerant reader absorbs the shapes.

**Correction to an earlier version of this paragraph**, which attributed all 44 to
operations named per operation (`set-target` 18, `rename-entry` 6, and so on). That
sum is real but it is not an attribution: it is the running total over steps, and
it charges early operations for deviations introduced later. The per-operation
claim belongs to the 6 introduced repairs only.

**The XLIFF row is a model difference, not a temperature effect.** An earlier
version of this section said the 100 % figure came from a temperature-0.0 lucky
sample that 1.3 broke. That was wrong twice over: the edit path never ran at 1.3
at all (see below), and the 100 % did not come from this model. It came from the
frozen `benchmark/clarion-2026-09-02` run, whose configuration reads
`model: deepseek-v4-flash` with the same `ui` stratum and the same 12 edits. The
same-model baseline in the recorded `deepseek-flash` run is **57.1 % bare /
55.6 % context**, so the model change, not the decoder temperature and not the
prompt, is what separates 100 % from 59.5 %. Every XLIFF failure is an XML parse
error (`not well-formed (invalid token)`, clustered at a few fixed columns of a
reformatted document): XLIFF asks the model to rewrite a whole XML document per
edit, and `deepseek-flash` is markedly worse at that than `deepseek-v4-flash`.
CLIFF's own comparison is unaffected, because both of its columns come from the
same model.

Also visible once the failures stop dominating: **valid-but-ignored edits**, where
the file stayed valid but the instruction did not take (the mock's failure mode in
reverse). For CLIFF that is **1 of 72** context edits — `set-emotion` on `billing`
in `ui-console` — and 0 of 42 in the bare arm. Other formats are outside the
question this benchmark now answers, and are listed only so the table is not
silently truncated: json-plain 21/72, json-cliff 9/72, csv 6/72, against the
Android / iOS / Fluent bare arms at 0. It is the reason both numbers are always
reported together.

## The shipped prompt's first translation measurement, and what it confirms

The pilot in this document compared the two prompt styles but the *translation*
path ignored the setting until the defect above was fixed, so no translation run had
ever actually sent the example-driven prompt. The deployment-settings run is the
first one that did (`python -m clarion pipeline --skip fetch`, 1.3, all ten formats,
run `clarion-deepseek-flash-20260921T142211`):

| CLIFF, single-pass translation | bare | context |
| --- | ---: | ---: |
| valid (tolerant) | **58.3 %** | **70.8 %** |
| identifiers kept | 75.0 % | 72.9 % |
| coverage | 75.0 % | 72.9 % |
| chrF++ on the runs that survive | 53.3 | — |

Two things follow, and the first is a confirmation rather than a surprise: the pilot
measured **61.5 % (digest) and 65.4 % (examples)** valid on the same files at the
same temperature, so this run sits inside the band the pilot predicted, and the
difference between the styles is still not measurable at that sample size. The
specification text was not what made CLIFF survive; the decoder's treatment of a
long whole-file rewrite is.

The failure is not shape, which is why the tolerant reader cannot help: the dominant
error is `status 'translated' requires a target field` — entries and targets dropped
while the status stays — followed by the quoting and escaping degradation of a long
generation (`expected a quoted string`, `unterminated string`). Failures cluster by
file, all three repeats together, on the files whose values are longest
(`hongloumeng-joly` emits 6–20 k output tokens for fourteen entries), and **no run hit
the output ceiling**. That is the failure mode rule 5 addresses and the failure mode
no prompt can fully remove: the unit of work is the whole document.

**What this costs the format comparison.** Only CLIFF's prompt changed in this
redesign, so in that run CLIFF is measured on the example-driven prompt while the
other nine still carry their established instructions. CLIFF is the least surviving
of the ten there and the best on the answers that survive (chrF++ 53.3), which is a
statement about this protocol, not a like-for-like format ranking.

### Why CLIFF's row is the weakest, and what it is not

The obvious explanations do not survive the controls, which is worth recording
because each one is the first thing a reader reaches for.

- **Not the values.** `json-cliff` carries exactly the same strings, the same
  escaping needs and the same required `status`/`target` fields — it is the same
  data model in JSON — and it scores **91.7 %** against CLIFF's **58.3 %** in the
  bare arm.
- **Not the size.** CLIFF's rendered document is the *second smallest* of the ten
  (24 322 tokens over the sixteen files, against android's 41 228), and `json-cliff`'s
  rendering of the same file is 56 % *longer* in characters. A longer file is not the
  problem; the two largest outputs in the run are `wmt24pp` and `hongloumeng-joly`,
  and both fail in both formats' CLIFF-like arms only.
- **Not the prompt content.** The 1.3 pilot's `digest` condition carried the full
  16 316-token specification text and scored **61.5 %** — the same band as this run.
  Telling the model more about CLIFF did not make it survive.
- **Not the temperature alone.** Every format in this run is at 1.3, and CLIFF is 25
  points below the next-weakest bare arm (csv, 83.3 %).

What is left is the property the format chose deliberately: **CLIFF has no
delimiters.** Structure is positional — an entry runs from its `<id>` to the next
`<id>` or `[group]` — so there is nothing that contains a slip.

- A **dropped `target:` line is invisible**: the document still parses, the entry is
  simply one line shorter, and only the required-field rule rejects it, as
  `status 'translated' requires a target field`. That is 8 of CLIFF's 20 bare
  failures.
- A **lost closing quote is a cascade**: the next line begins with a quote, which is
  the documented adjacent-string continuation, so it is absorbed into the broken
  string and the parser reports a failure far from its cause. That is most of the
  other 12.

So the format is robust to *structural* damage and fragile to *semantic* damage —
exactly the trade its design makes, and the reason "deleting a line cannot unbalance
the document" is a true statement that is not the same as "a deleted line is
harmless". A format with braces or closing tags contains the same slip locally, and
the model's prior for those syntaxes is larger; both effects point the same way.
