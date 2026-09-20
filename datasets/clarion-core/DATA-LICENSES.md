# CLARION-Core data licences

The CLARION harness (all Python code in `clarion/`) is MIT. **Corpus text is
licensed separately, per item.** This file is the authoritative summary; the
per-item truth is the `provenance` block of each gold manifest.

## Tier 0 - vendored, original, CC0-1.0

The authored part of CLARION-Core is **original text written for this
benchmark** and dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/). 274 of the 392
entries are in this tier; the rest are imported and carry their own licence in
their provenance block.

Why original text rather than an existing benchmark:

1. **Redistribution is unambiguous.** FLORES-200 and NTREX are CC-BY-SA 4.0;
   segmenting and re-publishing them makes the derived files ShareAlike, which
   conflicts with an MIT repository unless they are segregated. WMT test sets,
   the UN Parallel Corpus and OpenSubtitles cannot be redistributed at all.
2. **Training-data contamination.** Every public benchmark released before a
   model's cut-off may sit in its training data. Original text gives a control
   group: if a model scores much better on public items than on original ones,
   the public number is contaminated.

The trade-off is honest and recorded in every provenance block:
`human_verified: false` until a qualified reviewer signs the item off. Run
`python -m clarion corpus stats` to see the current verification state.

## Tier 1 - permissive, vendorable after fetching

Added by `datasets/recipes/*.json`. Safe to commit with attribution:

| Source | Licence | Use |
| --- | --- | --- |
| Godot editor l10n | MIT | UI strings with translator comments |
| VS Code loc | MIT | UI strings |
| Mozilla firefox-l10n | MPL-2.0 | Fluent UI strings with comment levels |
| Unciv | MPL-2.0 | game units, techs, tutorials |
| Amazon MASSIVE | CC-BY-4.0 | 51-locale intent utterances |
| Creative Commons 4.0 legal code | public domain (CC dedicates its licence texts) | legal register, official zh-Hans translation |
| World Bank OKR | CC-BY 3.0/4.0 IGO | formal en-zh institutional prose |
| EUR-Lex / DGT-TM / JRC-Acquis | EU Decision 2011/833/EU reuse, JRC also CC-BY-4.0 | EU legal (no Chinese) |
| Global Voices (filtered) | CC-BY 3.0 | news, human volunteer translations |
| Tatoeba | CC-BY 2.0 FR | short sentences |
| Public-domain literature | PD | 三国演义 / Brewitt-Taylor 1925, Shakespeare / 朱生豪, 论语 / Legge, 聊斋 / Giles, 红楼梦 / Joly, WEB or ASV / 和合本 1919 |

## Tier 2 - ShareAlike, segregated

FLORES-200, NTREX-128, KFTT, Cataclysm: DDA. If fetched they are written to
`datasets/cc-by-sa/` with their own LICENSE file, because our segmentation is
an adaptation and inherits ShareAlike.

## Tier 3 - never vendored

Fetch-only, or excluded entirely:

- GPL/AGPL translation catalogues (GNOME, KDE, WordPress, Wesnoth, 0 A.D.,
  OpenTTD, Signal, Element): redistributable only under the GPL.
- OpenSubtitles and every fansub corpus: no clean licence chain.
- WMT news test sets, News-Commentary, UN Parallel Corpus, TED/IWSLT (NC-ND),
  Amazon reviews, Yelp, tweet text: redistribution not permitted; use IDs plus
  checksums.
- Microsoft, Apple and Google terminology databases: proprietary.
- Copyrighted literature and its translations: Harry Potter, 金庸, 三体,
  《小王子》, Waley's *Monkey*, 赵元任's Alice, Bynner's *Jade Mountain*
  (public domain in the United States only).

## How an imported corpus is made publishable

`clarion corpus fetch <recipe>` does four things beyond downloading:

1. **Converts** the upstream file into CLIFF through cliff-python (PO, Fluent and the
   HuggingFace loaders), keeping any translator comments, source references and
   msgctxt disambiguation the project wrote.
2. **Enriches** the result deterministically where the upstream is flat: the
   document id becomes the group, the domain label and segment count become the
   group context, neighbouring segments become the entry context, and a
   placeholder-integrity note is added where message-format syntax is detected.
   Nothing is invented, so the output is byte-reproducible. Add `--annotate` to
   have a model write a fuller brief; those items are marked
   `context_origin: annotated` and need human sign-off.
3. **Routes by licence tier**, so ShareAlike and MPL text never lands in the
   MIT-licensed part of the tree:

   | Licence | Destination | Extra file |
   | --- | --- | --- |
   | MIT, Apache-2.0, BSD, ISC, CC0, CC-BY | `datasets/clarion-core/<stratum>/` | ATTRIBUTION.md |
   | MPL-2.0 | `datasets/mpl-2.0/<stratum>/` | LICENSE + ATTRIBUTION.md |
   | CC-BY-SA | `datasets/cc-by-sa/<stratum>/` | LICENSE + ATTRIBUTION.md |
   | no redistribution right | `.clarion-cache/fetch/` (gitignored) | none |

4. **Attributes in-file**: the generated CLIFF starts with comment lines naming
   the upstream project, its licence, its SPDX identifier and the revision, and
   the gold manifest stores a SHA-256 of every source and reference string.

Verify before pushing:

    python -m clarion corpus license-check

It fails when a committed file has no provenance, no licence, no attribution
file, no SPDX header, or when ShareAlike or MPL text sits outside its
segregated directory.

## Copyright terms relied on

United States: published in or before 1930 is public domain. China: life plus
50 years. EU and UK: life plus 70. Japan: life plus 70 since 2018 with no
revival. An item is only vendored when it is public domain in the United
States **and** in the source country **and** under a life-plus-70 rule.

Full research notes with citations and open verification items:
[../../docs/research/corpus-sources.md](../../docs/research/corpus-sources.md).
