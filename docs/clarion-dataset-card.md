# CLARION-Core dataset card

## Summary

| Field | Value |
| --- | --- |
| Name | CLARION-Core |
| Version | 0.3.0 |
| Size | 16 standard documents plus 2 `variant: glossary` term files (18 `.cliff` files), 392 entries, 6 strata |
| Languages | en-US to zh-CN, plus zh-CN to en-US for the classical literature |
| Format | CLIFF 1.1, validated by cliff-python. The documents are deliberately not cliff-python's canonical output: the authors order fields the way a translator reads them, keep long header values as adjacent-string continuation lines, and keep the licence attribution block at the top of imported files. Every file is strictly valid and needs zero tolerant repairs. |
| Licence | per item: CC0-1.0 for authored text, public domain for the classical literature, MIT and Apache-2.0 for the imported corpora |
| Human verified | partially: the 118 imported items carry `human_verified: true`; the authored items are marked `human_verified: false` until a reviewer signs them off |
| Contamination control | 274 entries are original text written for this benchmark and were never published before |

## Composition

| Stratum | Document | Entries | Origin | What it probes |
| --- | --- | ---: | --- | --- |
| ui | godot-l10n | 40 | Godot editor l10n, MIT | real product strings with upstream translator comments |
| ui | ui-console | 24 | original | labels, tooltips, empty states, ICU plurals, width budgets |
| ui | ui-workbench | 32 | original | type/context/width minimal pairs, jargon traps, a term across six entries |
| news | wmt24pp | 42 | WMT24++, Apache-2.0 | professional post-edited news references |
| news | news-wire | 21 | original | headline register, long paragraphs, quotation punctuation |
| news | news-social | 28 | original | irony pairs, hashtags and emoji, thread replies that complete an ellipsis |
| lit | sanguo-brewitt-taylor | 22 | public domain | 三國志演義 with Brewitt-Taylor's 1925 translation, verified paragraph alignment |
| lit | hongloumeng-joly | 14 | public domain | 紅樓夢 with Joly's 1892 translation |
| lit | lit-classical | 11 | original | original classical Chinese rendered into archaic English |
| lit | lit-modern | 10 | original | modern literary prose, voice and rhythm |
| lit | lit-drama | 23 | original | one continuous stage scene, emotion and type pairs, a motif quoted back |
| legal | legal-terms | 21 | original | defined terms, modal verbs, enumerated clauses, an abstract |
| legal | legal-privacy | 26 | original | the same clause under grant and under restriction, cross-references |
| game | game-shard | 24 | original | the Ash naming policy, width-limited skills, ICU payloads |
| game | game-quest | 30 | original | a second naming policy in both directions, NPC emotion pairs |
| probe | probe-ambiguity | 24 | original | the minimal-pair diagnostic set across four deciding channels |

## Phenomenon coverage

139 entries carry an A/B/C/D classification; the remainder are imported corpora
and earlier authored files, which serve as additional ordinary text:

| Class | Entries | Share | Quota |
| --- | ---: | ---: | --- |
| A decisive | 49 | 35.3% | 30-40% |
| B high risk | 31 | 22.3% | 20-25% |
| C cross-entry | 23 | 16.5% | 15-20% |
| D normal text | 36 | 25.9% | 25-30% |

**32 minimal pairs** share a source string and differ only in one CLIFF field:
10 decided by emotion, 9 by context, 6 by max-width, 5 by type, 2 by other
means. Every pair was checked by applying one member's rules to the other
member's reference; all of them fail, so ignoring the deciding field
necessarily costs at least one rule.

543 machine-checkable rules are attached, and **every reference translation
passes every rule attached to it**. `clarion corpus validate` enforces that,
and also rejects a pair identifier that leaks the distinction, a context line
that contains the answer, and a rule that can never fail.

## Provenance and licence

Authored text is CC0-1.0. The classical novels are public domain on both sides
(Project Gutenberg 23950/77416 and 24264/9603). Imported corpora keep their own
licences and carry an SPDX header, an attribution file and per-item checksums:
see [DATA-LICENSES.md](../datasets/clarion-core/DATA-LICENSES.md) and the
[recipes](../datasets/recipes/recipes.json).

## Verification status

`human_verified` is `true` for the 118 imported items (Godot, WMT24++, and the
two classical novels, whose paragraph alignment was checked) and `false` for the
274 authored items. References were written to the house style and every attached
rule passes against its own reference, but no qualified human reviewer has signed
the authored ones off. Quality claims published from this corpus must say so.

    python -m clarion corpus stats
    python -m clarion corpus validate

## Known limitations

1. One language pair dominates. Format effects should be re-measured for at
   least one non-CJK target before being generalised.
2. 392 entries is still small for statistical claims about small differences.
   Widen it through the recipes before publishing a headline number.
3. The authored part was written with LLM assistance under a written
   specification, which is why human sign-off is tracked as a first-class
   field.
4. The paragraph alignment of the two classical novels is model-proposed and
   verified (index-only, monotonic, length-ratio checked, then semantically
   re-checked). Brewitt-Taylor and Joly translate freely, so unverifiable pairs
   were dropped rather than repaired.

## Citation

    CLARION-Core 0.3.0, part of the CLIFF format project.
    Authored corpus text: CC0-1.0. Imported corpora: see DATA-LICENSES.md.
    Harness code: MIT.
