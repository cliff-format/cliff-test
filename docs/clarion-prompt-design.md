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
