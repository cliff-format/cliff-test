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
teaches the rest with two conforming documents:

| | current (`digest`) | example-driven (`examples`) |
| --- | ---: | ---: |
| specification text | 16 316 | — |
| specification digest | 513 | — |
| stated facts (keys, scopes, vocabularies) | — | 390 |
| edit-safety reminder | 116 | — |
| examples | — | 425 |
| **one cell, `ui-console` plain arm** | **20 739** | **2 510** |

Across the four pilot files the saving is **72 916 tokens (−77.7 %)**; measured
per file it ranges from −64.5 % (the longest file) to −85.4 %.

## The fact set is bounded by an empirical probe, not by taste

`.tools/probe_repairs.py` runs one minimal document per deviation through both
readings and reports what happens. Under the tolerant reading the harness uses:

| Repaired — so not worth prompt tokens | Unrepairable — must be stated |
| --- | --- |
| quoted tag (C.2.3) | unknown key, in any scope |
| bare scalar in a list-typed field (C.2.1) | `status` in group scope |
| quoted entry id (C.2.4) | value outside a closed vocabulary |
| repeated field (C.2.2) | `status: translated` with no `target` |
| version-line spelling (C.2.6) | unbalanced ICU brace |
| identifier with a reserved character (C.2.5) | unquoted string |

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
in both styles. No per-file difference was distinguishable (Fisher exact p = 1.000
throughout).

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
temperature 1.3):

| edit prompt | invented-key failures | edit not valid | repairs per edit |
| --- | ---: | ---: | ---: |
| historical (no CLIFF content) | **9 / 48 = 18.8 %** (95 % CI 10.2–31.9) | 18.8 % | 0.17 |
| with the field table | **0 / 48 = 0 %** (95 % CI 0–7.4) | 0 % | 0.42 |

Fisher exact **p = 0.0129**; the `examples` condition was 100 % valid and 100 %
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

## Open decisions for a full re-run

1. `prompt_style: examples` is implemented and switchable but **not yet the
   default**, and no full run has used it. The pilot justifies the saving, not a
   quality claim.
2. Temperature 1.3 changes the meaning of the repeats: at 0.0 the three answers of
   a cell were byte-identical, so they measured consistency rather than sampling
   variance. At 1.3 they are independent samples, which is what the paired tests
   assume. Numbers recorded at 0.0 and at 1.3 are not comparable.
3. The next measurement with real leverage is not prompt length but **batching the
   document** (fewer entries per call), since that is what the observed failure
   mode responds to. That is a change to the task, so it belongs in its own arm
   and must not be mixed into the format comparison.

## The D7 re-run at the shipped settings

Both defaults were changed after the pilots — `temperature: 1.3` and
`prompt_style: examples` — and dimension 7 was re-run through the real matrix
(`run_robustness_matrix`, not a stand-in) over the configured `ui` stratum,
2 passes × 12 edits, 240 model calls.

| format | arm | still valid % | intent applied % | invented-key failures | repairs |
| --- | --- | ---: | ---: | ---: | ---: |
| **cliff** | bare | **100.0** | 100.0 | **0** | 0 |
| **cliff** | context | **100.0** (was 83.3) | 98.6 | **0** (was 2) | 44 |
| xliff-2.1 | bare | 59.5 (was 100.0) | 59.5 | 0 | 0 |
| xliff-2.1 | context | 62.5 (was 55.6) | 48.6 | 0 | 0 |
| the other eight formats | both arms | 100.0 | 70.8–100.0 | 0 | 0 |

CLIFF's context arm moved from 83.3 % to **100.0 % still valid with no invented
key anywhere in the run**. All 44 repairs were absorbed by the tolerant reader
and none became a failure, on exactly the operations that require the model to
*create* a field: `set-target` 18, `add-reference` 6, `rename-entry` 6,
`set-context` 6, `move-entry` 4, `set-emotion` 2, `set-status` 2. That is the
division of labour the design intends — the prompt gets the key names right, and
the tolerant reader absorbs the shapes.

**The XLIFF change is not attributable to the prompt.** The prompt change touches
CLIFF only, and every XLIFF failure is an XML parse error
(`not well-formed (invalid token)`, clustered at a few fixed columns of a
reformatted document). XLIFF asks the model to rewrite a whole XML document per
edit, so at temperature 1.3 the sampling variance breaks it; at 0.0 the single
deterministic answer happened to be well-formed, which is why the earlier
100 % was recorded. The honest reading is that **the earlier XLIFF row was one
lucky sample of a fragile process**, and that D7's cross-format comparison is far
more temperature-sensitive than the recorded 0.0 numbers made it look. A
re-run-to-re-run spread should be reported before any XLIFF claim is made.

Also visible once the failures stop dominating: **valid-but-ignored edits**, where
the file stayed valid but the instruction did not take (the mock's failure mode in
reverse). These are concentrated in the context arm and differ sharply by format —
json-plain 21/72, json-cliff 9/72, csv 6/72 against CLIFF 1/72 and the Android /
iOS / Fluent bare arms at 0. It is the reason both numbers are always reported
together.
