# Benchmark Survey for the CLIF Localization-Format Benchmark

> **Status:** research notes, compiled by the benchmark-research agent.
> **Scope:** which established MT / localization datasets we can sample a few hundred segments from,
> for a benchmark that feeds *localization files* (CLIF vs XLIFF 2.x / PO / Fluent / JSON / YAML / CSV /
> Android strings.xml / iOS .strings) to an LLM and measures token cost, translation quality, latency,
> instruction-following, and round-trip parse/validate success.
> **Primary language pair:** en<->zh-CN. Secondary: ja-JP, es-ES.

## 0. Method and confidence caveat (read this first)

All findings below were gathered with a web-search tool. **Direct HTTP fetching of dataset cards was not
available in this sandbox** (outbound TLS is blocked), so license strings could only be confirmed when a
search snippet quoted them verbatim. Every claim is therefore tagged:

- **[confirmed]** - a search snippet quoted the fact verbatim from a primary source (dataset card, LICENSE
  file, paper PDF, shared-task page).
- **[reported]** - consistent with the paper/abstract/secondary sources, but the primary string was not seen.
- **[unverified]** - could not be confirmed; **treat as unknown and check before shipping anything**.

Two companion files in this directory hold the deep dives and are cited from here:
`_notes_metrics.md` (metrics/licences/LLM judges, 474 lines) and `corpus-sources.md` (copyright-clean corpus
sourcing per stratum). A later pass reached `http://www2.statmt.org` over plain HTTP and read the WMT task
pages and findings PDFs directly - those results are in §15 and are the most reliable claims in this document.

**Do not ship a redistributed segment on the basis of a [reported] or [unverified] license.** The rule we
should adopt: *only* segments whose license we confirmed by opening the primary LICENSE/dataset card go into
the repo; everything else ships as a download script + manifest of IDs.

### 0.1 Licensing decision rule for an MIT repo

Three tiers matter for us:

1. **Permissive (Apache-2.0 / MIT / CC0 / CC-BY-4.0)** -> we may copy segments into the public repo, keeping
   attribution and the original license notice in `data/<source>/LICENSE`. Our *code* stays MIT; the *data*
   directory carries its own license. This is normal and legally clean.
2. **CC-BY-SA-4.0 (FLORES family, and most Wikipedia-derived data)** -> redistribution **is allowed**, but the
   derived data files stay CC-BY-SA-4.0 (ShareAlike is viral over the data, not over our MIT code, as long as
   the data is a separate "collection" and not merged into the code). We must ship attribution + a copy of
   CC-BY-SA-4.0 next to those files. We may **not** relabel them MIT.
3. **Research-only / non-commercial / "no redistribution" (Meta Dataset Research License, many shared-task
   test sets, OpenSubtitles, most webnovel corpora)** -> **download script + ID manifest only**. Never vendored.

A practical consequence: our repo should have `clif-test/data/` split into `vendored/` (tiers 1-2, with
per-source LICENSE files) and `fetched/` (tier 3, gitignored, populated by `scripts/fetch_corpora.py` from a
manifest of stable IDs + SHA-256 checksums). Ship the manifest, not the text.

---

## 1. BOUQuET (Meta / FAIR, 2025)

**What it is.** BOUQuET ("dataset, Benchmark and Open initiative for Universal Quality Evaluation in
Translation") is a hand-crafted, *multi-way and multicentric* translation benchmark from FAIR at Meta with UCL
and UPV/EHU. Unlike FLORES it is not English-sourced: source material is written natively in several pivot
languages and then translated multi-way, so it avoids "translationese from English" artefacts. Sentences are
authored to cover controlled linguistic phenomena (tense/aspect/mood, register, POS distribution) and several
domains, and are grouped into paragraph-like sentence groups rather than being isolated lines. It is also an
*open initiative*: a HuggingFace Space collects community translations into new languages. A companion subset,
**Met-BOUQuET**, is intended for meta-evaluation of automatic MT metrics.
Paper: [arXiv:2502.04314](https://arxiv.org/abs/2502.04314) / [EMNLP 2025 main](https://aclanthology.org/2025.emnlp-main.1400/) ([ar5iv HTML](https://ar5iv.labs.arxiv.org/html/2502.04314)).

- **Good for:** a clean, non-English-centric quality anchor with *controlled linguistic difficulty* and
  paragraph grouping; the closest thing to "well-designed general prose" that is not FLORES.
- **Languages / zh-CN:** multi-way; Chinese is among the hand-crafted source languages, and every language is
  paired with English in both directions **[reported]**. ja and es also covered **[reported]**.
- **Size:** "In total, BOUQuET currently contains 1,750 sentences" **[confirmed via arXiv PDF snippet]**
  ([source](http://arxiv.org/pdf/2502.04314)), organised into sentence groups.
- **References:** human-authored and human-translated by professional linguists/translators, multi-way
  aligned **[reported]**.
- **Quality labels:** the main set carries **no** per-segment MQM/DA. Met-BOUQuET carries human judgements for
  metric meta-evaluation **[reported]**.
- **LICENSE:** :warning: The LICENSE file in the BOUQuET HuggingFace repo is a **"Meta Dataset Research License
  Agreement"** - the snippet reads *"This Meta Dataset Research License Agreement ('Agreement') contains the
  terms and conditions that govern your access and use of..."*
  ([source](https://huggingface.co/spaces/facebook/bouquet/blob/main/LICENSE)) - i.e. **research-only, not a
  CC license**. The "CC BY-SA 4.0" that appears on the arXiv HTML page refers to *the paper*, not the data.
  The dataset card also states an intent of *"Protecting the integrity of BOUQuET for evaluation"*
  ([card](https://huggingface.co/datasets/facebook/bouquet)), i.e. they discourage redistribution/training use.
  **Redistributable into an MIT repo: NO.** Ship a download script + ID manifest.
- **Access:** HuggingFace `facebook/bouquet`; also mirrored on
  [Mozilla Data Collective](https://mozilladatacollective.com/datasets/cmr4tclcu01anmm075pvvntbz).
- **Flat vs context:** **context-carrying** - domain labels, linguistic-phenomenon metadata, and
  sentence-group (paragraph) structure. Good fit for CLIF's "context travels with the string" thesis.
- **Verdict for us:** excellent *content*, bad *license* for vendoring. Use as an optional fetched corpus, or
  use it only for a small "hard prose" slice via download script.

---

## 2. FLORES-101 / FLORES-200 / FLORES+ (OLDI)

**What it is.** FLORES is the de-facto multilingual MT evaluation set: 3,001 English sentences sampled from
Wikimedia sources (Wikinews, Wikijunior, Wikivoyage), professionally translated into 101 (FLORES-101) and then
204 (FLORES-200, released with NLLB) language variants, split into **dev (997) / devtest (1,012) / test (992,
held out)** **[reported]**. **FLORES+** is the community-maintained continuation under the
[Open Language Data Initiative (OLDI)](https://github.com/openlanguagedata/flores): it fixes errors in the
original, adds languages, and is the version WMT's OLDI shared task builds on
([WMT25 OLDI findings](https://aclanthology.org/anthology-files/anthology-files/anthology-files/pdf/wmt.real/2025.wmt-1.57.pdf)).

- **Good for:** a universally recognised, cheap, multi-parallel baseline slice; every reviewer knows it, and
  because it is multi-parallel we get en->zh, en->ja, en->es on *identical* sources - which is exactly the
  control we want when comparing file formats across languages.
- **Languages / zh-CN:** yes - `zho_Hans` (Simplified) and `zho_Hant` (Traditional), plus `jpn_Jpan`,
  `spa_Latn`.
- **Size:** 3,001 sentences per language (997 dev / 1,012 devtest / 992 hidden test) **[reported]**;
  drawn from ~840 source articles, so sentences cluster by article.
- **References:** professional translators, with a documented QA/verification pass (translations accepted only
  above a quality threshold) **[reported]**.
- **Quality labels:** **none**. FLORES is a reference set, not a quality-annotated set. No MQM/DA.
- **LICENSE:** **CC-BY-SA-4.0** for FLORES-200 and FLORES+ **[reported; strongly consistent across mirrors -
  e.g. a derived card shows `license: cc-by-sa-4.0`](https://huggingface.co/api/resolve-cache/datasets/HiTZ/flores_plus_gender/8c587bed9230cf32cc87f4c1b8dd0f195daf47e0/README.md)**.
  -> **Redistributable: YES, with attribution and ShareAlike.** We may vendor a few hundred segments into the
  public repo *provided* those files stay CC-BY-SA-4.0 and are clearly marked (separate `LICENSE` in the data
  folder). We may **not** relicense them MIT.
- **Access:**
  - HuggingFace: `openlanguagedata/flores_plus` (current), `facebook/flores`, `Muennighoff/flores200`.
  - GitHub: [facebookresearch/flores](https://github.com/facebookresearch/flores/blob/main/flores200/README.md),
    [openlanguagedata/flores](https://github.com/openlanguagedata/flores).
  - sacreBLEU built-in: `sacrebleu -t flores101 / flores200 -l eng-zho ...` ([sacrebleu](https://github.com/mjpost/sacrebleu)).
- **Flat vs context:** mostly **flat sentences**, *but* FLORES ships `metadata_dev.tsv` / `metadata_devtest.tsv`
  with **URL, domain, topic, has_image, has_hyperlink** per sentence **[reported]**. That gives us (a) domain
  labels for stratification and (b) article grouping, so we can reconstruct short pseudo-documents - useful for
  a "context matters" ablation.
- **Risk:** **contamination**. FLORES has been public since 2021 and is in almost every multilingual training
  mix. Fine as a *format-comparison* control (all formats see the same memorised text, so the comparison is
  still internally valid), bad as an absolute quality claim.

---

## 3. GlotEval (2025)

**What it is.** GlotEval is a *toolkit*, not a dataset: a unified, massively multilingual evaluation test suite
for LLMs from the MaLA-LM group (Helsinki/Turku), covering machine translation plus text classification,
summarisation, open-ended generation, comprehension and intrinsic evaluation, with language-specific prompt
templates and non-English-centric prompting. It wraps many existing benchmarks (FLORES+, NTREX, Tatoeba,
AmericasNLP, IN22, etc.) behind one runner.
Paper: [arXiv:2504.04155](https://arxiv.org/abs/2504.04155) / [EMNLP 2025 demo](https://aclanthology.org/2025.emnlp-demos.43/).
Code: [MaLA-LM/GlotEval](https://github.com/MaLA-LM/GlotEval); project page: [mala-lm.github.io/GlotEval.html](https://mala-lm.github.io/GlotEval.html);
plus [GlotEval-HumanEval](https://github.com/MaLA-LM/GlotEval-HumanEval) for human comparison UI.

- **Good for:** stealing the *harness* design - multilingual prompt templates, per-language reporting, and a
  ready list of MT benchmarks with loaders. Also a citable precedent for "language-specific prompting matters",
  which is adjacent to our "format matters" claim.
- **Languages / zh-CN:** hundreds of languages via wrapped benchmarks; zh covered.
- **Size / references / quality labels:** N/A - inherits from the wrapped datasets.
- **LICENSE:** repository license **[unverified]** - check `LICENSE` in the GitHub repo before vendoring any
  code or prompt template.
- **Access:** GitHub (pip/conda install per README).
- **Flat vs context:** inherits; predominantly flat-sentence benchmarks.
- **Verdict:** use as *tooling/prior art*, not as a data source.

---

## 4. Instruction-following MT benchmarks (IFMTBench, WMT25 Multilingual Instruction, TICO-19)

This is the closest existing family to what we are actually measuring, because "did the model obey the
constraints carried by the file" *is* instruction following.

### 4.1 IFMTBench (Tencent)
"A Comprehensive Benchmark for Multilingual Translation Instruction Following"
([arXiv:2605.28218](https://arxiv.org/abs/2605.28218), [ar5iv](https://ar5iv.labs.arxiv.org/html/2605.28218)),
released alongside Tencent's Hunyuan-MT (Hy-MT2) models. Evaluates whether an MT system obeys explicit
instructions (terminology, style/register, formatting, do-not-translate, length) on top of translating.
- **Access:** HuggingFace `tencent/IFMTBench`
  ([card](https://huggingface.co/datasets/tencent/IFMTBench), [README](https://huggingface.co/datasets/tencent/IFMTBench/blob/main/README.md)).
- **Languages / zh-CN:** multilingual, Chinese-centric team; zh<->en covered **[reported]**.
- **Size / constraint taxonomy / references / labels:** **[unverified]** - the card was not readable through
  search snippets. Read the card and the paper's data section directly.
- **LICENSE:** **[unverified]**. Tencent dataset repos are often Apache-2.0 or a custom Tencent license -
  **do not assume**.
- **Flat vs context:** instruction + source pairs, i.e. *constraint-carrying* by construction. Highly relevant:
  their constraint taxonomy is a ready-made checklist for our instruction-following metric.
- **Verdict:** **read this one first** - even if we cannot use the data, we should reuse its constraint
  taxonomy and its scoring rubric for our own "instruction-following" axis.

### 4.2 WMT25 Multilingual Instruction Shared Task
Shared task page: [www2.statmt.org/wmt25/multilingual-instruction.html](http://www2.statmt.org/wmt25/multilingual-instruction.html);
findings: ["Findings of the WMT25 Multilingual Instruction Shared Task: Persistent Hurdles in Reasoning,
Generation, and Evaluation"](https://aclanthology.org/2025.wmt-1.23/)
([PDF](https://dfki.de/fileadmin/user_upload/import/16512_2025.wmt-1.23.pdf)).
Combines MT with instruction-following/reasoning subtasks across many languages. **License [unverified]**;
WMT task data is normally "free for research purposes" with per-source restrictions -> assume **fetch-only**.
Related: `LumiOpen/ifeval_mt` (a multilingual translation of IFEval)
([card](https://huggingface.co/datasets/LumiOpen/ifeval_mt/blob/main/README.md)) - useful as an
*instruction-following* probe, license **[unverified]**.

### 4.3 TICO-19
COVID-19 translation initiative: ~3k sentences x 35+ languages (incl. zh), *with terminology glossaries*.
Site: [tico-19.github.io](https://tico-19.github.io/); mirrors e.g. `SEACrowd/tico_19`
([card](https://huggingface.co/datasets/SEACrowd/tico_19/blob/main/README.md)). TICO-19 was also the basis of
the **WMT21 "MT using terminologies"** task ([findings](https://aclanthology.cn/2021.wmt-1.69/)).
License commonly stated as CC0/very permissive **[unverified - confirm on the site's terms page]**.
Value for us: it is one of the few *terminology-annotated, zh-covering, plausibly permissive* sets, i.e. a
natural source for a "glossary constraint" slice.

### 4.4 "IF-MT"
A benchmark literally named **IF-MT** could not be confirmed as a distinct public artefact **[unverified]**.
Treat IFMTBench + WMT25 MI + IFEval-MT as the concrete instances of this family.

---

## 5. TQ-AutoTest

**What it is.** A DFKI *test-suite* methodology (not a large corpus): hand-built test items targeting specific
linguistic phenomena (tense/aspect/mood, negation, coordination, MWEs, ambiguity...), scored semi-automatically
with regex-style accept/reject patterns, so you get a phenomenon-level profile of an MT system instead of one
scalar. Papers: [LREC 2018 "TQ-AutoTest - A Semi-Automatic Test Suite for (Machine) Translation Quality"](http://www.lrec-conf.org/proceedings/lrec2018/summaries/121.html)
([PDF](https://preview.aclanthology.org/ingest-acl-2023-videos/L18-1142.pdf)),
plus DFKI follow-ups incl. ["TQ-AutoTest: Novel analytical quality measure confirms that DeepL is better than
Google Translate"](https://www-live.dfki.de/en/web/research/projects-and-publications/publication/10174).

- **Good for:** the *idea* we should copy - a phenomenon test suite with machine-checkable accept/reject
  patterns. This is exactly how we should score "did the placeholder survive", "was the plural rule kept",
  "was the do-not-translate token preserved". WMT's "test suite" subtask institutionalised this approach.
- **Languages / zh-CN:** primarily **en<->de** (and other European pairs). **No zh coverage** **[reported]**.
- **Size:** ~5k test items for German **[reported]**, phenomenon-annotated.
- **References:** hand-written by linguists; accept/reject token patterns rather than single references.
- **Quality labels:** phenomenon-level pass/fail, not MQM/DA.
- **LICENSE / access:** **[unverified]** - no public HF/GitHub release found; appears to be DFKI-internal or
  request-based.
- **Verdict:** **methodological prior art only**, not a data source for us.

---

## 6. DiBiMT

**What it is.** DiBiMT ("Disambiguation Biases in Machine Translation") is an entirely manually curated
benchmark from Sapienza NLP measuring **word-sense disambiguation errors** in MT: for each ambiguous English
word in context it defines sets of *correct* and *incorrect* target lemmas (grounded in BabelNet/WordNet
senses), so you can compute an accuracy that is immune to reference-based metric noise.
Papers: [ACL 2022](https://aclanthology.org/2022.acl-long.298.pdf) and the extended
[Computational Linguistics 2025 journal version](https://aclanthology.org/2025.cl-2.1/)
([MIT Press](https://mitp.silverchair.com/coli/article/doi/10.1162/coli_a_00541/124626/DiBiMT-A-Gold-Evaluation-Benchmark-for-Studying)).
Artifact record: [Zenodo 6625312](https://zenodo.org/records/6625312).

- **Good for:** a *hard, adversarial semantic* slice. Because scoring is lemma-set based, it works even when
  the model's output is embedded in a localization file - and it directly tests whether **context carried by
  the file** (a `comment`/`description` field!) fixes a sense error. That is a killer experiment for CLIF:
  same ambiguous string, with vs without the context field, measured on a gold WSD benchmark.
- **Languages / zh-CN:** **English -> {Chinese, German, Italian, Russian, Spanish}** **[reported]** -
  so en->zh yes, ja no, es yes. One direction only (English source).
- **Size:** thousands of manually curated instances per target language **[reported]**.
- **References:** manually curated by expert annotators; gold sense annotations. Not free-running references -
  it is a "good lemma / bad lemma" set.
- **Quality labels:** no MQM/DA; instead gold **sense correctness** labels.
- **LICENSE:** **[unverified]** - check the Zenodo record and the
  [DiBiMT site](https://nlp.uniroma1.it/dibimt/). Sapienza NLP resources are frequently CC-BY-NC-SA, which
  would **block** vendoring into a permissive repo. Also note part of the data may be withheld for the
  leaderboard **[unverified]**.
- **Flat vs context:** flat sentences **plus** rich sense metadata (synset ids, good/bad lemma sets).
- **Verdict:** high scientific value for one targeted experiment; assume **fetch-only** until the license is
  confirmed.

---

## 7. MMTE (and the naming ambiguity)

Two different things are called "MMTE"/"multi-dimensional MT evaluation":

1. **MMTE: Corpus and Metrics for Evaluating Machine Translation Quality of Metaphorical Language**
   (EMNLP 2024 main, [aclanthology 2024.emnlp-main.634](https://aclanthology.org/2024.emnlp-main.634/),
   [arXiv:2406.13698](https://arxiv.org/abs/2406.13698)). A corpus of metaphor-bearing source sentences with
   human ratings along metaphor-specific dimensions (equivalence type, emotional/associative preservation)
   plus proposed metrics. Data appears deposited at the University of Sheffield ORDA repository
   ([record](https://orda.shef.ac.uk/articles/dataset/MMTE_Corpus_and_Metrics_for_Evaluating_Machine_Translation_Quality_of_Metaphorical_Language/30239443)).
   ORDA deposits are usually CC-BY-4.0, which would make it vendorable - **[unverified, must check the record]**.
   Languages / size / zh coverage **[unverified]**.
2. **Multi-Dimensional Machine Translation Evaluation** ([arXiv:2403.12666](https://arxiv.org/abs/2403.12666)) -
   a *Korean* resource and models predicting separate accuracy/fluency dimensions. Not zh; not our target.

- **Good for:** if (1) covers zh-en, it is the best available "figurative/literary hardness" probe with
  *human multi-dimensional labels*. Otherwise treat as inspiration for our own rubric axes.
- **Verdict:** verify (1)'s languages and ORDA license before counting on it.

---

## 8. WMT Quality Estimation shared tasks (MLQE-PE, WMT20-24 QE)

**What it is.** The QE tasks provide (source, MT output) pairs *with human quality labels but without
references* - sentence-level DA/MQM scores, word-level OK/BAD tags, and post-edits. For us they are not a
translation *source* so much as a **gold quality anchor**: a public set where we know the human score, which we
can use to calibrate/sanity-check whatever automatic metric we adopt.

- **MLQE-PE** ([LREC 2022](https://aclanthology.org/2022.lrec-1.530.pdf), [arXiv:2010.04480](https://arxiv.org/abs/2010.04480),
  [ar5iv](https://ar5iv.labs.arxiv.org/html/2010.04480)): 11 language pairs **including en-zh**, ~10k segments
  per pair from Wikipedia (plus Reddit for some pairs), each with 3-annotator **DA z-scores**, **post-edits**,
  **word-level OK/BAD tags**, and the NMT model's own log-probabilities.
  Access: GitHub `facebookresearch/mlqe`; HuggingFace `wmt/wmt20_mlqe_task1`, `wmt/wmt20_mlqe_task2`
  ([card](https://huggingface.co/datasets/wmt/wmt20_mlqe_task2/raw/main/README.md)).
  **LICENSE [unverified]** - the underlying text is Wikipedia (CC-BY-SA), the annotations' license needs
  checking on the repo.
- **WMT21-WMT24 QE tasks**: hosted under the [WMT-QE-Task GitHub org](https://github.com/WMT-QE-Task)
  (e.g. [wmt-qe-2023-data mirror](https://github.com/alvations/wmt-qe-2023-data)); task pages:
  [WMT24 QE](http://www2.statmt.org/wmt24/qe-task.html), [WMT22 task 1](https://wmt-qe-task.github.io/wmt-qe-2022//subtasks/task1/);
  findings: [WMT23 QE](https://aclanthology.org/2023.wmt-1.52/), [WMT24 QE "Are LLMs Closing the Gap in QE?"](https://aclanthology.org/2024.wmt-1.3/).
- **Which years have MQM usable for zh-en:** WMT22 and WMT23 QE used **MQM-derived sentence scores for
  en-de, zh-en, en-ru** (WMT22) and en-de / zh-en / he-en (WMT23) **[reported - confirm in the findings PDFs]**;
  WMT24 moved to **ESA** (Error Span Annotation) style human evaluation **[reported]**.
- **References human-produced?** MLQE-PE post-edits are human post-edits of MT (professional post-editors)
  **[reported]**; the MT outputs themselves are machine.
- **Flat vs context:** flat segments; some sets carry document ids **[unverified]**.
- **Verdict:** **use as a metric-calibration anchor**, not as translation input. Fetch-only until licenses are
  confirmed. If you want a single well-maintained entry point to all WMT human scores, use
  **`mt-metrics-eval`** (below) rather than assembling QE tarballs by hand.

---

## 9. WMT General MT + MQM annotations + WMT Terminology task

### 9.1 WMT General MT test sets and their MQM annotations
Each year's WMT general task publishes source + human reference test sets with **document boundaries and
domain labels**; since WMT20 the *human evaluation* has increasingly been professional **MQM** (Google's
"Experts, Errors, and Context", [arXiv:2104.14478](https://arxiv.org/abs/2104.14478)), later Unbabel MQM and
then ESA.
- **Data:**
  - [github.com/google/wmt-mqm-human-evaluation](https://github.com/google/wmt-mqm-human-evaluation) - the
    original Google MQM ratings (newstest2020+, en-de / zh-en, multiple systems, error spans with category and
    severity). **LICENSE [unverified] - check the repo's LICENSE file.**
  - HuggingFace mirrors: `RicardoRei/wmt-mqm-human-evaluation`
    ([card](https://huggingface.co/datasets/RicardoRei/wmt-mqm-human-evaluation)),
    `RicardoRei/wmt-mqm-error-spans`, `RicardoRei/wmt-da-human-evaluation` (DA scores across many WMT years).
    Licenses **[unverified]**.
  - [google-research/mt-metrics-eval](https://github.com/google-research/mt-metrics-eval) (and
    [kocmitom/mt-metrics-eval](https://github.com/kocmitom/mt-metrics-eval)) - the canonical toolkit + database
    of WMT human scores (MQM/DA/ESA) and system outputs, used to run the Metrics shared task. **Code license
    Apache-2.0 [reported]; the downloaded data keeps WMT's own terms [unverified].**
- **zh-CN coverage:** yes - **zh-en** has MQM in multiple years; **en-zh** appears in the general task test sets
  **[reported]**.
- **Verdict:** the *best gold quality anchor in existence* for zh-en, but treat as **fetch-only**.

### 9.2 WMT24++ - the single most useful redistributable set we found
["WMT24++: Expanding the Language Coverage of WMT24 to 55 Languages & Dialects"](https://aclanthology.org/2025.findings-acl.634/)
([arXiv:2502.12404](https://arxiv.org/abs/2502.12404)) extends the WMT24 English source test set with
**human post-edited references for 55 languages/dialects**, produced by professional translators post-editing a
strong MT baseline.
- **HuggingFace `google/wmt24pp`, dataset card states `license: apache-2.0`**
  **[confirmed via snippet]** ([README](https://huggingface.co/datasets/google/wmt24pp/blob/main/README.md)).
  There is also `google/wmt24pp-images` for the screenshot/context variant.
- **Domains:** WMT24's general test set was built from **news, social, speech and literary** sources
  **[reported]** - i.e. it single-handedly covers three of our five domains (news/social, speech-like dialogue,
  literary), with **document ids** and **domain labels** per segment **[reported]**.
- **Size:** ~1k source segments per language direction (English source, 55 targets) **[reported]**.
- **zh-CN:** yes (`zh_CN` locale code among the 55) **[reported]**; ja and es also present **[reported]**.
- **References:** **human post-edited by professional translators** (that is the paper's whole point), and
  the paper argues these are higher quality than the original WMT24 references.
- **Quality labels:** no per-segment MQM in `wmt24pp` itself, but the *same* WMT24 sources have MQM/ESA in
  `mt-metrics-eval`, so the two can be joined.
- **Redistributable: YES** (Apache-2.0) - we may vendor a few hundred segments into the MIT repo with an
  Apache-2.0 NOTICE. **This should be our backbone corpus.**
- **Caveat:** English-source only (en->X). For zh->en we still need another source - and note that
  **WMT24/WMT25 general test sets are also en->X only [confirmed]**, so zh->en must come from WMT23 or from our
  own permissive/PD sources (see §15.2).

### 9.3 WMT Terminology shared task
- **WMT21 "MT using terminologies"** ([findings](https://aclanthology.cn/2021.wmt-1.69/),
  [GMU page](https://nlp.cs.gmu.edu/publication/alam-etal-21-findings/)) - COVID/TICO-19 based, terminology
  constraints supplied as glossaries; language pairs include **en-zh** **[reported]**.
- **WMT23 Terminology task** ([task site](https://wmt-terminology-task.github.io/),
  [findings PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.54.pdf)) - **de-en, zh-en, en-cs** **[reported]**,
  with per-sentence terminology constraint annotations. A convenient mirror exists at HuggingFace
  `zouharvi/wmt-terminology-2023`
  ([card](https://huggingface.co/datasets/zouharvi/wmt-terminology-2023/blob/main/README.md)); **license
  [unverified]**.
  Notable participant systems include NCSOFT's [VARCO-MT](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.84.pdf) -
  a *game-localization* company doing terminology-constrained MT, relevant to our game-dialogue domain.
- **Why it matters to us:** terminology constraints are precisely the kind of metadata a localization format
  can carry. A WMT-terminology-derived slice lets us claim "CLIF carries the glossary inline; here is the
  measured term-hit-rate delta versus JSON+system-prompt glossary", against an *established* benchmark
  definition of term accuracy.

---

## 10. Document-level / context-carrying candidates (including ones we did not name)

Our format's selling point is that context travels with the string, so a benchmark that is *only* flat
sentences cannot show CLIF's advantage. These carry structure:

| Candidate | What context it carries | zh-en? | Notes |
|---|---|---|---|
| **WMT24++ (`google/wmt24pp`)** | document ids, domain labels (news / social / speech / literary) | en->zh yes | **Apache-2.0 [confirmed]** - our backbone |
| **WMT general test sets (WMT21-25)** | full documents, doc ids, domain labels; WMT25 adds a per-domain `prompt_instruction` and even images/video | WMT23 = zh-en **and** en-zh; **WMT24/25 = en-zh only** (organisers deliberately avoid X-to-English) | fetch via sacreBLEU (`-t wmt24 -l en-zh`) / `mt-metrics-eval`; licence is **"freely used for research purposes" [confirmed]** - fetch-only |
| **GuoFeng Webnovel** (WMT23/24 Discourse-Level Literary Translation) | chapter-level web fiction, character names, recurring terminology | **zh->en** | [GitHub](https://github.com/longyuewangdcu/GuoFeng-Webnovel); [WMT23 findings](https://aclanthology.org/2023.wmt-1.3/), [WMT24 findings](https://aclanthology.org/2024.wmt-1.58/), [task page](http://www2.statmt.org/wmt24/literary-translation-task.html). Research-use agreement - see section 11 |
| **Par3** | paragraph-aligned world literature, multiple human translations per paragraph | many source langs -> en | [GitHub katherinethai/par3](https://github.com/katherinethai/par3/), [EMNLP 2022](https://aclanthology.org/2022.emnlp-main.672.pdf) |
| **MuDA / "When Does Translation Require Context?"** | automatically tagged *context-dependent* phenomena (pronoun/formality/lexical cohesion) over doc-level corpora | includes zh **[reported]** | [ACL 2023](https://aclanthology.org/2023.acl-long.36/) - a ready-made way to *select* segments that genuinely need context. **Use MuDA tags to build our "context matters" stratum.** |
| **CTXPRO / "Identifying Context-Dependent Translations for Evaluation Set Production"** | rule-extracted context-dependent segments | multiple | [WMT23 paper](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.42.pdf) |
| **IWSLT / TED talks, ACL 60-60** | talk-level context, technical terminology | zh yes | ACL 60-60 mirror: `ymoslem/acl-6060`; [IWSLT 2023 multilingual track](https://iwslt.org/2023/multilingual) |
| **ParaMed (NEJM zh-en)** | paragraph-level medical | zh-en | `bigbio/paramed` ([card](https://huggingface.co/datasets/bigbio/paramed/blob/main/README.md)) |
| **TransLaw** (HK case law) | full judgments, legal terminology, professional translation workflow | zh-en | [arXiv:2507.00875](https://arxiv.org/abs/2507.00875) - legal domain candidate |
| **HardMTBench** | knowledge-intensive zh-en domains, deliberately hard | zh-en | [arXiv:2605.28315](https://arxiv.org/abs/2605.28315), [GitHub jasonNLP/HardMTBench](https://github.com/jasonNLP/HardMTBench) |
| **Prompsit D1/D2/D3 (Mozilla Data Collective)** | "Inline Asset Integrity", "Locale-data Integrity", "Structured-resource Integrity" | **[unverified]** | [D1](https://mozilladatacollective.com/datasets/cmr0mng9z01bsmk07cuqltz81), [D2](https://mozilladatacollective.com/datasets/cmr0mnoo201bwmk07nh4yc04u), [D3](https://mozilladatacollective.com/datasets/cmr0mny2b01asns073985z0va) - by their titles these are **exactly our problem space** (does the model preserve inline tags, placeholders and structured resources?). **Investigate first for the app/UI-string domain.** |
| **Wukong localization study** | game text, culture-specific items | zh->en | [GitHub zcocozz/wukong-localization](https://github.com/zcocozz/wukong-localization), [LM4DH@RANLP 2025](https://aclanthology.org/2025.lm4dh-1.16/) |

### 10.1 Prior art on "format costs tokens" (non-MT, but citable)
- [TOON - Token-Oriented Object Notation](https://github.com/consteuni/toon): a serialization format explicitly
  designed to cut LLM prompt tokens versus JSON, with published benchmarks.
- [file-format-token-accuracy-benchmark](https://github.com/thoeltig/file-format-token-accuracy-benchmark):
  token efficiency *and* accuracy across CSV/JSON/TOON/XML/YAML for LLM consumption.
These are the closest existing precedents for the "token cost per format" axis, and they are engineering
benchmarks rather than peer-reviewed work - precisely the gap CLIF's benchmark can fill by adding
*translation quality* and *round-trip validity* to the token-cost story.

### 10.2 Sourcing the app/SaaS/UI-string domain (no established MT benchmark exists)

There is **no established academic MT benchmark for UI/software strings**. Searches for one surfaced only
tooling and vendor blogs, not a citable test set. Practical, license-clean options we found:

- **`mozilla-l10n/firefox-l10n`** ([GitHub](https://github.com/mozilla-l10n/firefox-l10n)) and
  **`mozilla-l10n/firefox-l10n-source`** ([GitHub](https://github.com/mozilla-l10n/firefox-l10n-source)) -
  real Firefox UI strings in **Fluent (.ftl)** with **localizer comments** (exactly the "context field" we care
  about), for ~100 locales including `zh-CN`, `ja`, `es-ES`. Individual .ftl files carry the header
  *"This Source Code Form is subject to the terms of the Mozilla Public [License]"*
  **[confirmed via file snippet]** ([example](https://github.com/mozilla-l10n/firefox-l10n/blob/main/el/toolkit/toolkit/about/aboutRights.ftl)),
  i.e. **MPL-2.0**. MPL-2.0 is file-level copyleft: we may include those files in a public repo if we keep the
  MPL header and mark modifications; MPL files coexist fine with MIT-licensed code.
  Mozilla also published guidance on reusing its translations:
  [blog.mozilla.org/l10n/2017/05/30/reuse-mozilla-translations/](https://blog.mozilla.org/l10n/2017/05/30/reuse-mozilla-translations/) **[content unverified]**.
  **This is the strongest candidate for domain (1), and it is Fluent-native, which our benchmark needs anyway.**
- **OPUS software-localization corpora** - `GNOME`, `KDE4`, `Ubuntu` collections, aligned en<->zh-CN
  (e.g. [KDE4 en&zh-CN](https://opus.nlpl.eu/KDE4/en&zh-CN/v2/KDE4)); HF loaders `Helsinki-NLP/opus_gnome` etc.
  These are PO/gettext-derived and therefore carry `msgctxt` and translator comments upstream, though the OPUS
  alignment usually strips them. **License: inherits the original projects' (GPL/LGPL) terms; OPUS states
  corpora are provided under the original licenses [unverified] - check per collection.**
- **Microsoft Terminology Collection** (`microsoft/ms_terms` on HF,
  [loader](https://huggingface.co/datasets/microsoft/ms_terms)) - UI terminology in ~100 languages incl. zh-CN.
  Microsoft's terminology license historically permits reference use but **restricts redistribution**
  **[unverified - read the MS Language Portal terms]**. Useful as a *glossary* for terminology constraints, not
  as translation input.
- **Prompsit D1/D2/D3** on Mozilla Data Collective (see table above) - if these are what their titles say
  (inline-asset / locale-data / structured-resource integrity), they may already be the benchmark we are trying
  to build. **Highest-priority item to verify manually.**

---

## 11. Terminology-constrained and literary translation benchmarks

### 11.1 Terminology-constrained
| Benchmark | Pairs | Constraint format | License | Access |
|---|---|---|---|---|
| **WMT21 "MT using terminologies"** | incl. **en-zh** **[reported]** | glossary/term lists per sentence, COVID (TICO-19) domain | **[unverified]** - shared-task terms | [findings](https://aclanthology.cn/2021.wmt-1.69/), [GMU page](https://nlp.cs.gmu.edu/publication/alam-etal-21-findings/) |
| **WMT23 Terminology task** | **de-en, zh-en, en-cs** **[reported]** | per-segment term pairs, blind test | **[unverified]** | [task site](https://wmt-terminology-task.github.io/), [findings](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.54.pdf), HF mirror `zouharvi/wmt-terminology-2023` |
| **TICO-19** | 35+ incl. zh | separate glossary files | commonly described as very permissive **[unverified]** | [tico-19.github.io](https://tico-19.github.io/) |
| **Microsoft Terminology Collection** | ~100 incl. zh-CN | TBX/glossary | proprietary, **no redistribution** **[reported]** | `microsoft/ms_terms` |
| **IFMTBench** | multilingual, zh-centric | natural-language instructions incl. terminology | **[unverified]** | `tencent/IFMTBench` |

Related method papers worth citing when we define our term-accuracy metric:
["Terminology-Aware Translation with Constrained Decoding and LLM Prompting"](https://aclanthology.org/2023.wmt-1.80/),
["Translate-and-Revise: Boosting LLMs for Constrained Translation"](https://arxiv.org/abs/2407.13164),
["Domain Terminology Integration into MT: Leveraging LLMs"](https://arxiv.org/abs/2310.14451).
The standard metrics there are **term hit rate / constraint completion rate** alongside BLEU/COMET - adopt that
vocabulary so our numbers are comparable.

### 11.2 Literary
| Benchmark | Pair | Unit | License | Notes |
|---|---|---|---|---|
| **GuoFeng Webnovel** (WMT23/24 Discourse-Level Literary Translation) | **zh->en** | chapters (document-level), web fiction | **research-use agreement, NOT open** **[reported - verify the repo's LICENSE/terms]** | [GitHub](https://github.com/longyuewangdcu/GuoFeng-Webnovel), [WMT23 findings](https://aclanthology.org/2023.wmt-1.3/), [WMT24 findings](https://aclanthology.org/2024.wmt-1.58/) |
| **WMT24 Discourse-Level Literary Translation task** | zh-en (+en-de in some editions) | documents | shared-task terms **[unverified]** | [task page](http://www2.statmt.org/wmt24/literary-translation-task.html), [findings PDF](https://export.arxiv.org/pdf/2412.11732v1) |
| **Par3** | many->en | aligned **paragraphs**, multiple human translations of the same PD source | **[unverified]** - built from PD source texts + *copyrighted* modern translations, so redistribution is likely constrained | [GitHub](https://github.com/katherinethai/par3/), [EMNLP 2022](https://aclanthology.org/2022.emnlp-main.672.pdf) |
| **WMT24++ literary slice** | en->zh (+54) | segments with doc ids | **Apache-2.0 [confirmed]** | `google/wmt24pp` - the only literary-ish slice we can legally vendor |
| **Wukong localization study** | zh->en | game/culture text | **[unverified]** | [GitHub](https://github.com/zcocozz/wukong-localization), [LM4DH 2025](https://aclanthology.org/2025.lm4dh-1.16/) |

For *vendorable* literature, the companion document `clif-test/docs/research/corpus-sources.md` already did the
copyright work: use public-domain source + public-domain translation pairs (Brewitt-Taylor's *Three Kingdoms*,
Legge, Giles, Joly, Shakespeare <-> 朱生豪, 和合本 1919 <-> WEB/ASV). That is a better answer for our repo than any
research-licensed literary benchmark.

---

## 12. Automatic MT quality scoring: best practice 2024-2026

### 12.1 What the field currently does
The WMT Metrics/Evaluation shared task is the authority. Recent findings to cite:
- [Findings of the WMT24 Metrics Shared Task](https://aclanthology.org/volumes/2024.wmt-1/)
- [Findings of the WMT25 Shared Task on Automated Translation Evaluation Systems: *Linguistic Diversity is
  Challenging and References Still Help*](https://aclanthology.org/2025.wmt-1.24/) - the title is the headline
  result: **reference-based metrics still beat reference-free QE**, so we should keep human references in the loop.
- [MetricX-25 and GemSpanEval: Google Translate Submissions to the WMT25 Evaluation Shared Task](https://aclanthology.org/2025.wmt-1.70/)
- [Kocmi et al., *To Ship or Not to Ship* (WMT 2021)](https://aclanthology.org/2021.wmt-1.57/) and
  [*Navigating the Metrics Maze: Reconciling Score Magnitudes and Accuracies* (ACL 2024)](https://aclanthology.cn/2024.acl-long.110/),
  with the companion tool [**MT-Thresholds**](https://github.com/kocmitom/MT-Thresholds) - it converts a metric
  delta into an estimated probability of agreeing with human judgement. **Use this to justify our sample size
  and our "is this difference real" claims.**
- [*Pitfalls and Outlooks in Using COMET* (arXiv:2408.15366)](https://arxiv.org/html/2408.15366v3) - required
  reading before we report COMET numbers (version pinning, score non-comparability across model versions,
  sensitivity to empty/degenerate outputs - which we *will* produce when a format round-trip fails).

### 12.2 Metric table

| Metric | Type | Approx size | License | HF id / repo | CPU-runnable | Notes |
|---|---|---|---|---|---|---|
| **chrF++ / chrF** | surface, ref | n/a | Apache-2.0 (sacreBLEU) **[reported]** | [mjpost/sacrebleu](https://github.com/mjpost/sacrebleu) | yes, instant | Character-based -> **works for zh without tokenisation debates**. Report with the sacreBLEU signature. |
| **BLEU / spBLEU** | surface, ref | n/a | Apache-2.0 **[reported]** | sacreBLEU | yes | For zh use `tokenize=zh`; for multilingual comparability use `spBLEU` with the FLORES-200 SPM. Report as a *baseline only* - WMT organisers have moved away from BLEU for system ranking. |
| **TER** | surface, ref | n/a | Apache-2.0 | sacreBLEU | yes | Useful as an edit-distance proxy for post-editing effort. |
| **COMET-22 (`Unbabel/wmt22-comet-da`)** | neural, **ref-based** | XLM-R Large ~565M | **`license: apache-2.0`** and **ungated** **[confirmed from the raw card](https://huggingface.co/Unbabel/wmt22-comet-da/blob/1358d906012962aca32f48913d55e967d250adf1/README.md?code=true)**. NB the *code* licence and the *weight* licence are separate files ([`LICENSE.models.md`](https://github.com/Unbabel/COMET/blob/master/LICENSE.models.md)); Unbabel licences differ per model, so never generalise from this row | [Unbabel/wmt22-comet-da](https://huggingface.co/Unbabel/wmt22-comet-da) | yes, ~4-6 GB RAM fp32 | ⭐ **Permissive + ungated + CPU-runnable: the default primary metric.** [Paper](https://aclanthology.org/2022.wmt-1.52/) |
| **CometKiwi (`Unbabel/wmt22-cometkiwi-da`)** | neural, **reference-free QE** | ~580M | **CC-BY-NC-SA-4.0** **[confirmed on a mirror card](https://huggingface.co/ben-xl8/wmt22-cometkiwi-da/blob/6c5396ae93eb6fc0bbf73a1964e6e69272090b3d/README.md?code=true)**; the official Unbabel repo is **gated** | [Unbabel/wmt22-cometkiwi-da](https://huggingface.co/Unbabel/wmt22-cometkiwi-da) | yes | **NC = do not use if the benchmark must be usable commercially.** |
| **CometKiwi-XL / XXL (`wmt23-cometkiwi-da-xl/xxl`)** | QE | 3.5B / 10.7B **[reported]** | gated - *"Acknowledge license to accept the repository"* **[confirmed]** ([xl](https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xl)) | Unbabel | XL borderline on CPU; XXL no | NC-style terms **[unverified]** |
| **XCOMET-XL / XXL** | neural, ref-based **+ error spans** | 3.5B / 10.7B **[reported]** | **gated** - *"You need to agree to share your contact information to access this model"* **[confirmed]** ([XCOMET-XL](https://huggingface.co/Unbabel/XCOMET-XL)) | Unbabel | XXL needs GPU | Produces MQM-like error spans - attractive, but licence + size make it a GPU-only extra. |
| **MetricX-24 (`google/metricx-24-hybrid-large-v2p6`)** | neural, **hybrid ref-based *and* QE in one model** | large / XL / XXL (mT5-based) | **`license: apache-2.0`** **[confirmed from the raw card](https://huggingface.co/google/metricx-24-hybrid-large-v2p6/raw/b6ec8db9a17db7c9e892f4d7e8b3a33c445c5104/README.md)** | [google-research/metricx](https://github.com/google-research/metricx) | `large` borderline on CPU (bf16 helps); XL/XXL need GPU | ⚠️ **Scores are 0-25 and LOWER IS BETTER - the opposite of COMET.** "Hybrid" = one checkpoint gives both a reference-based and a reference-free number. XXL card also confirmed apache-2.0; XL card [unverified]. [Paper](https://aclanthology.org/2024.wmt-1.35/). **MetricX-25 is paper-only - no `google/metricx-25*` weights found [confirmed absent]**, so do not plan around it. |
| **BLEURT** | neural, ref | BERT/RemBERT-based | Apache-2.0 (code) **[reported]** | google-research/bleurt | yes | Largely superseded by COMET/MetricX. |
| **BERTScore** | neural, ref | encoder-dependent | MIT **[reported]** | Tiiiger/bert_score | yes | Weak correlation vs COMET/MetricX; keep only as a cheap sanity metric. |
| **GEMBA / GEMBA-MQM** | **LLM-as-judge** | GPT-3.5+ / GPT-4 | **code AND prompts are CC-BY-SA-4.0, not MIT** **[confirmed via the repo commit "Code and data licensed under CC BY-SA 4.0"](https://github.com/MicrosoftTranslator/GEMBA/commit/18671baee617b70d852dd7f2984172b23b49f8db)** - commercially usable but **ShareAlike attaches to vendored prompt files** | [MicrosoftTranslator/GEMBA](https://github.com/MicrosoftTranslator/GEMBA) (**not** `microsoft/GEMBA`) | no (API only) | Strong at **system level**, coarse at segment level. The paper has a section literally titled **"Caution with 'Black Box' LLMs"** [confirmed] warning against using it to rank systems. Our study is *about* LLM behaviour, so an LLM judge shares failure modes - secondary signal only. [GEMBA](https://aclanthology.org/2023.eamt-1.19/), [GEMBA-MQM](https://aclanthology.org/2023.wmt-1.64/), [V2](https://aclanthology.org/2025.wmt-1.67/) |

### 12.3 Recommended stack for CLIF (offline, CPU, permissive)
1. **COMET-22** (`Unbabel/wmt22-comet-da`, apache-2.0, ungated) - headline quality number; report **mean segment score + bootstrap CI**.
2. **chrF++** (sacreBLEU, with the signature pasted verbatim) - surface baseline; for zh use `--tokenize zh`, for ja `ja-mecab`, for es `13a`. **There is no auto-detection - scoring en->zh with the default `13a` measures whitespace, not translation.**
3. **MetricX-24-hybrid-large** (apache-2.0, ungated) - an independently-trained second reference-based number *and* a QE number from one checkpoint. **State the direction: 0-25, lower is better.**
4. **Format-integrity metrics we define ourselves** (parse rate, placeholder preservation, key preservation,
   count match, terminology hit rate) - these are the *real* contribution and they are deterministic.
5. Optional GPU/API extras: **XCOMET** error spans and **GEMBA-MQM**, clearly labelled as non-permissive/extra.

**zh-specific caveats.** :warning: A claim in an earlier draft of this document - that neural metrics are
miscalibrated on zh relative to en-de - is **unsupported**: a dedicated search found **no WMT statement and no
paper** asserting it. Do not repeat it. What *is* sourced:
- **Word-level BLEU on Chinese is segmentation-dependent**; `--tokenize zh` splits CJK runs into characters to
  remove the dependence, and **chrF needs no segmentation at all** - which is why chrF++ is the best cheap
  metric across zh/ja/es simultaneously.
- **COMET scores are not comparable across language pairs** (0.86 on en-es != 0.86 on en-zh). `RankedCOMET`
  ([WMT25](https://aclanthology.org/2025.wmt-1.74/)) exists precisely to rank-normalise COMET per pair.
- **Metric interference / circularity**: *Pitfalls and Outlooks in Using COMET*
  ([WMT24](https://aclanthology.org/2024.wmt-1.121/)) shows on **both en-de and en-zh** that filtering or
  selecting data with a metric and then evaluating with that same metric inflates the gain. **Rule: never use
  the same metric to select/rerank and to evaluate.** On en->zh, **small COMET deltas are not trustworthy** -
  always pair COMET with chrF and a second neural metric, and always significance-test.
- What the zh literature *does* document is failure on **multiword expressions, idioms, named entities and
  culturally-loaded content** ([LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.198/),
  [Findings EMNLP 2024](https://aclanthology.org/2024.findings-emnlp.357/)) - so our zh strata should include
  targeted MWE/idiom/named-entity/number slices.
- Normalise full-width punctuation and zh-CN vs zh-TW **before** scoring, and say that you did.
- *any* reference-based metric collapses when the model returns a partially-broken file, so **always report
  parse success separately and exclude/flag failed round-trips rather than silently scoring garbage**.

### 12.4 Non-negotiable reporting hygiene (from the 2024-2026 literature)

**a) Degenerate outputs score better than you think - and we will produce them.**
*Pitfalls and Outlooks in Using COMET* ([WMT24](https://aclanthology.org/2024.wmt-1.121/),
[arXiv:2408.15366](https://arxiv.org/abs/2408.15366)) confirms verbatim that **empty translations sometimes
outscore a real system**, and that **sentence-shuffled hypotheses score comparably to empty ones** - only
word-salad scores lower. Since a failed format round-trip produces exactly these artefacts (truncated files,
dropped entries, mismatched keys), a naive COMET average would *reward* some broken outputs.
**Mitigation, and it is cheap:** add **control rows** - empty string, copy-source, shuffled, wrong-variant -
following [MSLC25](https://aclanthology.org/2025.wmt-1.69/) / [MSLC24](https://aclanthology.org/2024.wmt-1.34/)
([data](https://github.com/nrc-cnrc/MSLC)). **Any metric that ranks a control above a real system is
disqualified for our use case.** Report parse/round-trip success as a first-class result, not a footnote.

**b) Emit signatures for neural metrics too.** sacreBLEU signatures are standard practice
([Post 2018](https://aclanthology.org/W18-6319/)); the COMET equivalent is **sacreCOMET**
([repo](https://github.com/PinzhenChen/sacreCOMET), PyPI `sacrecomet`), proposed in *Pitfalls* precisely
because "COMET = 0.85" is unreproducible - COMET-20/22/Kiwi/XCOMET are different scales, and scores have
changed between library versions ([COMET issue #244](https://github.com/Unbabel/COMET/issues/244)).
Publish: metric name + **checkpoint id + revision hash** + **library version** + signature + score direction.

**c) The credibility checklist.** Marie, Fujita & Rubino, *Scientific Credibility of Machine Translation
Research: A Meta-Evaluation of 769 Papers* ([ACL 2021](https://aclanthology.org/2021.acl-long.566/)) is the
standard citation for how routinely MT papers omit exactly these items. Also state whether our test set is
*easy* - WMT25's General MT findings are titled *"Time to Stop Evaluating on Easy Test Sets"*
([2025.wmt-1.1](https://aclanthology.org/2025.wmt-1.1/)).

**d) Reference-free QE is not a shortcut.**
- WMT25's evaluation findings are titled *"...References Still Help"*
  ([2025.wmt-1.24](https://aclanthology.org/2025.wmt-1.24/)); even Google's own hybrid MetricX-25 was
  *"slightly outperformed by the reference-based variant"* [confirmed].
- **Sentinel metrics** ([ACL 2024](https://aclanthology.org/2024.acl-long.856/)) show part of QE's apparent
  correlation comes from source-side/domain artefacts: inside WMT24's own results a deliberately degenerate
  source-only baseline (`sentinel-src-mqm`) lands in the same band as a genuine QE metric.
- QE has a documented **length bias** ([arXiv:2510.22028](https://arxiv.org/abs/2510.22028)) - relevant because
  zh<->en changes length dramatically.
- QE is weak on **omission/addition/hallucination, numbers and named entities**
  ([Amrhein & Sennrich AACL 2022](https://aclanthology.org/2022.aacl-main.83/),
  [ACES](https://aclanthology.org/2025.cl-1.4/)). **=> Add deterministic checks for number, entity, placeholder
  and negation preservation.** These are free, exact, and catch what QE misses - and they are the same checks
  our format-integrity metric already needs.

**e) BLEU's status.** The WMT22 metrics findings are literally titled *"**Stop Using BLEU** - Neural Metrics
Are Better and More Robust"* ([2022.wmt-1.2](https://aclanthology.org/2022.wmt-1.2/)). Report BLEU only as a
reproducibility artefact with its signature, never as the quality claim. WMT23's findings add the complementary
warning: *"Metrics Might Be Guilty but References Are Not Innocent"*
([2023.wmt-1.51](https://aclanthology.org/2023.wmt-1.51/)); WMT24's ask *"Are LLMs Breaking MT Metrics?"*
([2024.wmt-1.2](https://aclanthology.org/2024.wmt-1.2/)) - directly relevant since our outputs are LLM outputs.
For **WMT26** the headline subtask has become **error-span annotation**
([task page](https://www2.statmt.org/wmt26/mteval-task.html)), which is where the field is heading.

**f) Open-weight judges, if we ever want span-level evaluation offline.** The Unbabel **Tower / TowerInstruct /
xTower / Tower+** family is **CC-BY-NC** [confirmed on several cards] and therefore unusable in a commercially
open benchmark. Permissive alternatives worth watching: **CompassJudger-2-7B-Instruct** (apache-2.0
[confirmed]), and **GemSpanEval** ([WMT25](https://aclanthology.org/2025.wmt-1.70/)), a Gemma-based generative
error-span evaluator - the most promising direction for offline, permissive, span-level MT evaluation, though
its weights/licence are **[unverified]**. **MQM-APE** ([COLING 2025](https://aclanthology.org/2025.coling-main.374/))
is a useful design: predict MQM errors, try to post-edit each one, and **discard errors whose repair does not
improve quality** - an elegant filter for false-positive error spans.

**g) Full detail** lives in `clif-test/docs/research/_notes_metrics.md` (474 lines), including a per-model
gated/licence/CPU table, offline `comet-score` invocation notes (COMET downloads `xlm-roberta-large`
separately - pre-warm the cache before going air-gapped), and an explicit list of what remains unverified.

---

## 13. Sampling and statistics for a few-hundred-segment benchmark

### 13.1 Stratification
Stratify explicitly and record the stratum on every item:
- **domain** (our five: UI strings / news+social / literature / legal+academic / game+script),
- **segment length** (short UI label, medium sentence, long paragraph) - short strings are where formats differ
  most in *relative* token overhead, long ones where quality differs most,
- **context dependence** - use the [MuDA](https://aclanthology.org/2023.acl-long.36/) tag families
  (pronoun/formality/lexical cohesion) or [CTXPRO](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.42.pdf) rules to
  guarantee a stratum where context genuinely changes the correct translation,
- **structural features** - placeholders (`%s`, `{count}`, `{$var}`), plurals/ICU selectors, inline markup,
  do-not-translate tokens, escapes/quotes. This is *our* axis and no existing benchmark stratifies on it.
- **terminology density** - segments carrying glossary terms vs not.

Target something like **50-80 segments per (domain x length) cell** so each cell can be analysed on its own,
giving 300-500 total per direction. Keep documents intact where a stratum is document-level.

### 13.2 How big must the sample be?
- The classic reference is [Koehn, *Statistical Significance Tests for Machine Translation Evaluation*
  (EMNLP 2004)](https://aclanthology.org/W04-3250/) - paired **bootstrap resampling** over the test set.
- For "is this delta meaningful", use [Kocmi et al., *Navigating the Metrics Maze* (ACL 2024)](https://aclanthology.cn/2024.acl-long.110/)
  and the [**MT-Thresholds** tool](https://github.com/kocmitom/MT-Thresholds), which maps a metric delta +
  test-set size to an estimated human-agreement probability. **Report our deltas through that lens instead of
  inventing a threshold.**
- [Card et al., *With Little Power Comes Great Responsibility* (EMNLP 2020)](https://arxiv.org/abs/2010.06595)
  is the general warning that typical NLP experiments are underpowered; it is the right citation for why we do
  a power/MDE calculation at all.
- **Concrete anchor from MT-Thresholds [confirmed verbatim]:** *"an improvement of 1.06 BLEU has the same
  estimated accuracy (65%) as the 0.24 CometKiwi"* ([Navigating the Metrics Maze](https://ar5iv.labs.arxiv.org/html/2401.06760#2)).
  Read that carefully: a **~1 BLEU gap buys only ~65% agreement with human system-level preference.** That is
  the honest scale of what a small benchmark can claim, and it is why we must convert every delta through the
  tool rather than asserting it.
- **There is no credible "magic N" of segments.** A dedicated search found **no 2024-2026 paper giving one**.
  Koehn 2004 parameterises his analysis over test sets of **100 / 300 / 600 / 3000 sentences** - a few hundred
  segments is exactly the regime he studies, and it is the *small* end of it. So: report the CI, convert the
  delta with MT-Thresholds, and state the implied accuracy - do not claim a threshold we invented.
- Rough orientation **[our own estimate, explicitly not from a citation - validate with a pilot]**: with n=300
  paired segments and a per-segment COMET SD around 0.10-0.15, the paired-difference standard error is
  ~0.006-0.009, so a true mean difference of ~0.02 is detectable at 80% power while 0.005 is not; **chrF++
  deltas below ~1 point should not be claimed at n=300.**

### 13.3 Test design - ours is a **paired, repeated-measures** design
Every format sees **identical source segments** and the **same model**, so:
- Use **paired** tests on per-segment differences (paired bootstrap / paired approximate randomisation), never
  unpaired two-sample tests. sacreBLEU exposes paired bootstrap and paired approximate-randomisation tests
  against a baseline system ([sacreBLEU](https://github.com/mjpost/sacrebleu),
  [issue #70](https://github.com/mjpost/sacrebleu/issues/70) for background). :warning: **The exact flag
  spellings and default resample counts are [unverified] - check `sacrebleu --help` before writing them into
  our scripts or the paper.** Cite [Koehn 2004](https://aclanthology.org/W04-3250/) for the method.
- **Aggregate surface metrics at the segment level, not the corpus level** - segment-level aggregation
  correlates better with human judgement ([AAAI 2025](http://arxiv.org/pdf/2407.12832)), and it is also what
  makes the paired test possible.
- With 9 formats you are making up to 36 pairwise comparisons -> **correct for multiplicity (Holm or
  Benjamini-Hochberg)**, or designate CLIF-vs-each-baseline as the pre-registered family and correct within it.
  General guidance: [Dror et al., *The Hitchhiker's Guide to Testing Statistical Significance in NLP* (ACL 2018)](https://aclanthology.org/P18-1128/).
- Prefer a **mixed-effects model** (quality ~ format + (1|segment) + (1|domain)) if you want one clean
  inferential statement across strata; report per-stratum paired deltas as the descriptive layer.
- **LLM nondeterminism:** temperature 0 is *not* determinism (batching/kernel nondeterminism, provider-side
  changes). Run **>=3 seeds/repeats per (format x direction)**, report mean +- CI **across seeds**, and treat
  the run as a random effect. Also pin and record the model version string - a provider silently updating the
  model invalidates cross-run comparisons.
- **Order/position effects:** randomise the order of entries inside each file and keep the *same* randomisation
  across formats, so a format is not accidentally favoured by segment ordering.

### 13.4 Contamination
- FLORES and WMT test sets are heavily contaminated. There is direct evidence for FLORES:
  [*When Flores Bloomz Wrong: Cross-Direction Contamination in Machine Translation Evaluation*](https://www-live.dfki.de/en/web/research/projects-and-publications/publication/17528).
- General detection method: [Oren et al., *Proving Test Set Contamination in Black-Box Language Models* (ICLR 2024)](https://arxiv.org/abs/2310.17623).
- Mitigations for us: (a) prefer **recent** test sets (WMT24++/WMT25) over FLORES for absolute claims;
  (b) **author some segments ourselves and dedicate them CC0** (also the licence-cleanest option - see
  `corpus-sources.md` §5.1.9); (c) apply light, meaning-preserving perturbations (rename entities,
  renumber placeholders) and report both perturbed and unperturbed results; (d) note that contamination
  is *largely neutral for our main claim*, because every format is fed the same possibly-memorised text -
  contamination biases the absolute quality numbers, not the format ranking.

---

## 14. Recommendation summary

### 14.1 Master table

| Dataset | Domain fit | License | Redistributable into MIT repo? | Access | Use it? |
|---|---|---|---|---|---|
| **WMT24++** (`google/wmt24pp`) | news, social, speech, literary (en->X) | **Apache-2.0 [confirmed]** | **YES** | HF `google/wmt24pp` | **Yes - backbone.** Recent (low contamination), professional post-edited refs, doc ids + domain labels, zh/ja/es covered |
| **FLORES+ / FLORES-200** | general Wikimedia prose | **CC-BY-SA-4.0 [reported]** | **Yes, but SA-viral** - segregate in `data/cc-by-sa/` | HF `openlanguagedata/flores_plus`; sacreBLEU `-t flores200` | Yes, as a small comparability slice; **not** for absolute quality claims (contaminated) |
| **BOUQuET** | controlled multi-domain prose, paragraph groups | **Meta Dataset Research License [confirmed on the HF LICENSE file]** | **No** | HF `facebook/bouquet` | Optional fetch-only slice; excellent design but research-only |
| **WMT MQM / DA human scores** | quality anchor for zh-en | **[unverified]**, shared-task terms | **No** | `google/wmt-mqm-human-evaluation`, `RicardoRei/wmt-*-human-evaluation`, `mt-metrics-eval` | Yes, **fetch-only**, as a metric-calibration anchor |
| **WMT QE / MLQE-PE** | QE labels incl. en-zh | **[unverified]** | **No** | `wmt/wmt20_mlqe_task1`, WMT-QE-Task GitHub | Only if we need DA/post-edit labels; otherwise skip |
| **WMT Terminology (2021 / 2023)** | terminology-constrained, zh-en | **[unverified]** | **No** | `zouharvi/wmt-terminology-2023`, task site | Yes, fetch-only, for the glossary-constraint experiment |
| **DiBiMT** | WSD ambiguity, en->zh | **[unverified]** (Sapienza resources are often NC) | **No until verified** | Zenodo 6625312 / project site | Yes for one high-value "does context fix the sense?" experiment |
| **IFMTBench** | instruction-following MT | **[unverified]** | **No until verified** | HF `tencent/IFMTBench` | Read it for the **constraint taxonomy** even if we cannot use the data |
| **GuoFeng Webnovel** | literary zh->en, chapter-level | research-use agreement **[reported]** | **No** | GitHub longyuewangdcu/GuoFeng-Webnovel | Fetch-only; prefer PD literature instead |
| **Par3** | paragraph literary | **[unverified]** | **No until verified** | GitHub katherinethai/par3 | Reference for paragraph-level design |
| **TICO-19** | COVID domain + glossaries, zh | very permissive **[unverified]** | **Probably - verify** | tico-19.github.io | Good glossary-constraint source if the licence checks out |
| **GlotEval** | toolkit | **[unverified]** | n/a | GitHub MaLA-LM/GlotEval | Tooling/prior art only |
| **TQ-AutoTest** | phenomenon test suite, en-de | **[unverified]**, no public release found | **No** | - | Methodological prior art only |
| **MMTE (metaphor)** | figurative language | **[unverified]** (Sheffield ORDA, often CC-BY) | **Verify** | ORDA record | Optional hard-literary probe |
| **Mozilla `firefox-l10n`** | **UI strings, Fluent, with comments** | **MPL-2.0 [confirmed from file headers]** | **Yes, segregated** | GitHub mozilla-l10n/firefox-l10n | **Yes - primary UI-string source** |
| **Godot editor l10n** | UI strings, gettext PO with `#.` comments | **MIT [per `corpus-sources.md`]** | **Yes** | GitHub godotengine/godot-editor-l10n | **Yes - primary PO source** |
| **Amazon MASSIVE** | app-style utterances, 51 locales | **CC-BY-4.0 [per `corpus-sources.md`]** | **Yes** | HF `AmazonScience/massive` | Yes - filler for short app strings |
| **CC 4.0 legal code translations** | legal/EULA register, official zh-Hans/ja/es | CC0-style dedication **[per `corpus-sources.md`]** | **Yes** | creativecommons.org legalcode | **Yes - primary legal source** |
| **World Bank OKR** | formal policy/academic prose en<->zh | CC-BY(-IGO) **[per `corpus-sources.md`]** | **Yes** | openknowledge.worldbank.org | Yes - academic/legal filler |
| **Unciv** | game skills/units/tutorials | MPL-2.0 **[per `corpus-sources.md`]** | **Yes, segregated** | GitHub yairm210/Unciv | **Yes - primary game source** |
| **OpenSubtitles / TED-IWSLT** | dialogue/subtitles | murky / CC-BY-NC-ND | **No** | - | **Do not ship** |

*(Entries marked "per `corpus-sources.md`" come from the companion sourcing study in this same directory; its
own verification checklist still applies.)*

### 14.2 Top picks per required domain

**(1) App / SaaS / web UI strings** - *no academic benchmark exists; build it from real l10n repos.*
1. **Godot editor l10n** (MIT, gettext `.po` with `#.` translator comments, `msgctxt`) - vendorable.
2. **Mozilla `firefox-l10n`** (MPL-2.0, Fluent `.ftl` with `#`/`##`/`###` comments, zh-CN/ja/es-ES) - vendorable, segregated.
3. **Amazon MASSIVE** (CC-BY-4.0) for short utterance-style strings; **VS Code loc** (MIT) as filler.
4. Investigate **Prompsit D1/D3 "Inline Asset / Structured-resource Integrity"** on Mozilla Data Collective -
   possibly an existing benchmark for exactly our placeholder/tag-integrity metric.

**(2) Articles / news / tweets / comments**
1. **WMT24++** news + social slices (Apache-2.0, professional post-edited, recent) - **primary**.
2. **FLORES+** (CC-BY-SA-4.0) - small comparability slice.
3. **Global Voices** (CC-BY, per-article check) and **Tatoeba** (CC-BY) for short comment/tweet-length text.
4. **NTREX-128** if we want WMT19 news references without WMT licensing (verify its LICENSE).

**(3) Classical & modern literature**
1. **Public-domain pairs** (Brewitt-Taylor *Three Kingdoms*, Legge, Giles, Joly, Shakespeare <-> 朱生豪) -
   vendorable, per `corpus-sources.md`.
2. **WMT24++ literary slice** (Apache-2.0) for contemporary literary register.
3. **GuoFeng Webnovel** / **WMT24 Discourse-Level Literary** - fetch-only, for a document-level ablation.
4. **Par3 / MMTE** - optional, licence-dependent.

**(4) Legal / EULA / license / academic**
1. **Creative Commons 4.0 legal code** official translations (en / zh-Hans / ja / es) - dense legalese, cleanest licence.
2. **World Bank Open Knowledge Repository** (CC-BY IGO) for en<->zh formal policy/academic prose.
3. **ACL 60-60** (`ymoslem/acl-6060`) for academic/scientific register incl. zh - verify licence.
4. **TransLaw** (HK case law, zh-en) and **ParaMed** as fetch-only hard-domain probes. **Avoid the GNU licence
   texts** (verbatim-copying-only) and the UN corpus (non-commercial ambiguity).

**(5) Game dialogue / skills / movie scripts**
1. **Unciv** (MPL-2.0) - unit/tech/skill names, tutorials, quotes, with `#` context comments.
2. **Shakespeare <-> 朱生豪** - genuine PD *dialogue* with speaker structure; doubles as literature.
3. **Cataclysm: DDA** (CC-BY-SA-3.0) if ShareAlike is acceptable - the densest game-dialogue corpus.
4. **Commission ~50 CC0 original RPG/gacha-style segments** to cover contemporary game register - also the best
   contamination defence. **Never OpenSubtitles.**

### 14.3 Concrete next actions
1. Verify, with network access, the licences flagged **[unverified]** above (IFMTBench, DiBiMT, TICO-19,
   WMT terminology mirrors, MMTE/ORDA, GlotEval, Par3, GuoFeng) and archive each LICENSE page.
2. Pull **WMT24++** for en->zh_CN / ja_JP / es_ES, keep `domain` + `document_id`, and build the news/social/
   literary strata from it.
3. Build the UI stratum from Godot + Mozilla Fluent, preserving comments/`msgctxt` - these become CLIF's
   context fields and the baseline formats' "lost context".
4. Stand up the metric stack: **COMET-22** (`Unbabel/wmt22-comet-da`, apache-2.0, ungated) + **sacreBLEU
   chrF++** (with signature, `--tokenize zh`/`ja-mecab`) + **MetricX-24-hybrid-large** (apache-2.0; remember
   0-25, lower is better) + our deterministic format-integrity checks + **MSLC-style control rows** (empty,
   copy-source, shuffled) to prove the metrics are not rewarding broken round-trips.
5. Pre-register the analysis: paired bootstrap on per-segment differences, Holm correction across formats,
   >=3 seeds, mean +- CI, and MT-Thresholds to interpret deltas.

---

## 15. Verified addenda (primary sources read directly)

A follow-up pass reached `http://www2.statmt.org` over plain HTTP and read the WMT task pages and findings
PDFs directly. The following are **[confirmed] verbatim from primary sources** and supersede any weaker claim
above.

### 15.1 WMT General MT licence - the exact wording
[WMT23](http://www2.statmt.org/wmt23/translation-task.html), [WMT24](http://www2.statmt.org/wmt24/translation-task.html)
and [WMT25](http://www2.statmt.org/wmt25/translation-task.html) all say, verbatim:

> "The data released for the WMT General MT task **can be freely used for research purposes**, we ask that you
> cite the WMT shared task overview paper, and respect any additional citation requirements on the individual
> data sets. **For other uses of the data, you should consult with original owners of the data sets.**"

That is **not** an open licence and is **not MIT-compatible** (MIT grants unrestricted commercial use and
sublicensing downstream). **WMT general test sets: fetch-only, never vendored.**

### 15.2 WMT General MT - facts that change our sampling plan
- **Language directions:** WMT23 has **zh-en and en-zh**; **WMT24 and WMT25 have en-zh (and ja-zh) but NOT
  zh-en** - the organisers explicitly "avoid evaluation on X-to-English". So **for zh->en we must use WMT23 or
  a non-WMT source.**
- **WMT24 size:** "All language pairs had **649 segments over 170 documents**" ([findings](http://www2.statmt.org/wmt24/pdf/2024.wmt-1.1.pdf)); testsets are **paragraph-level**, one paragraph per line.
- **WMT25 size/shape:** each test set is "approximately **9,000 words distributed across 60 to 100 segments**",
  **document-level by default**, **JSONL replaces XML**, and every item carries `doc_id`, `dataset_id` and a
  per-domain **`prompt_instruction`** (an explicit translation brief). Speech items carry video and social
  items carry Mastodon screenshots. ([findings](http://www2.statmt.org/wmt25/pdf/2025.wmt-1.22.pdf))
- **WMT25 has no standalone Literary task** - literary is now a *domain inside General MT* ("a domain focussing
  on a long-context"), sourced from an Archive-of-Our-Own story (English) and Aozora Bunko public-domain
  stories (Japanese), 2 documents per source language, ~42.5 segments each.
- **References:** "the source texts were **originally written in the source language** and subsequently
  translated into the target languages by **human translators**", with the brief requiring translation "**from
  scratch, without post-editing from machine translation or usage of CAT**".
- **Human labels:** WMT24/25 use **ESA (Error Span Annotation)** plus **MQM** on a subset; for **English->Chinese**
  the annotators are described as professional translators/linguists. All sources, system outputs and human
  judgments are released.

### 15.3 GuoFeng Webnovel - the licence, verbatim (this settles it)
From the [WMT24 literary task page](http://www2.statmt.org/wmt24/literary-translation-task.html):

> "GuoFeng Webnovel Corpus are copyrighted by Tencent AI Lab and China Literature Limited. After completing the
> registration process with your institute information, WMT participants or researchers are granted permission
> to use the dataset **solely for non-commercial research purposes** ... **Modifying or redistributing the
> dataset is strictly prohibited.** If you plan to make any changes to the dataset ... please contact us first
> to obtain **written consent**."

**=> Absolutely not vendorable**: redistribution is expressly prohibited, use is non-commercial-only
(incompatible with MIT), and access is behind a registration form. Fetch-instructions + `(book_id, chapter_id,
line_no)` manifest only.
Structure (useful even if we only cite it): V1 is **zh->en**, train 179 books / 22,567 chapters / 1.94M
sentences; **Test_final = 12 books / 239 chapters / 16,742 sentences**, average document ~28.1K words. Two
references on the test set (one newly commissioned, one aligned from the published bilingual text). It has a
bespoke **literary MQM typology** including *Terminology-mistranslation* and *Terminology-inconsistent*
categories - directly reusable as our rubric for character-name/glossary consistency.

### 15.4 WMT Terminology - corrected picture
- **WMT23** ([findings](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.54.pdf)): **de-en, en-cs, zh-en**.
  **zh-en = 2,640 segments, avg 1.1 terms/segment, and it is a repackaging of the BWB web-novel corpus** -
  i.e. the terminology being tested is largely **character names** (example given: 凌寒 -> "Ling Han"). The task
  ships three conditions: **Base / Proper / Random** (random non-terminological phrases as a control) - an
  excellent design to copy for our "glossary in the file vs glossary in the prompt vs no glossary" arms.
  Licence: **[unverified]**, and BWB's web-novel copyright flows through -> fetch-only.
- **WMT25** ([task page](http://www2.statmt.org/wmt25/terminology.html), [findings](http://www2.statmt.org/wmt25/pdf/2025.wmt-1.30.pdf)):
  **Track 1 = en->de/ru/es, domain = information technology, JSONL with `proper_terms`/`random_terms` - the
  published examples are literally software-UI sentences.** That is the closest thing WMT has to a UI-string
  terminology benchmark, and it covers **es**, one of our secondary languages.
  **Track 2 = en<->zh-Hant (Traditional!), finance, document-level**, 10 HKMA annual reports / 111 documents,
  with **corpus-level** (not segment-level) glossaries. Licence **[unverified]**; HKMA owns the reports.
  :warning: Track 2 is **Traditional Chinese**, not zh-CN - do not silently mix scripts.

### 15.5 WMT Chat Translation - verified NC
[WMT24 Chat task page](http://www2.statmt.org/wmt24/chat-task.html), verbatim: "all the data released for the
WMT24 Chat Translation task is under the license of **CC-BY-NC-4.0** and can be freely used for **research
purposes only** ... no commercial uses are permitted". Bilingual customer-support conversations **with speaker
roles and full conversation context** - the closest public analogue to in-game dialogue, but **NC blocks us**.

### 15.6 Additional context-carrying candidates worth knowing
- **BWB** (Jiang et al.) - zh->en web novels/books with **dense discourse annotation: entities, coreference
  chains, terminology, tense, ambiguity**; the basis of the **BlonDe** document-level metric and the upstream
  source of WMT23-Terminology zh-en. Repo [EleanorJiang/BlonDe](https://github.com/EleanorJiang/BlonDe),
  papers [arXiv:2210.14667](https://arxiv.org/abs/2210.14667), [BlonDe arXiv:2103.11878](https://arxiv.org/abs/2103.11878).
  Licence **[unverified]**, web-novel copyright -> fetch-only. **This is the single richest "context + glossary +
  characters" zh-en resource in existence** and the best model for what CLIF should be able to express.
- **LitEval-Corpus** ([NAACL 2025](https://aclanthology.org/2025.naacl-long.548/),
  [code](https://github.com/zhangr2021/LitMT_eval)) - literary corpus with **professional, student and LLM
  translations annotated with MQM**. Primarily de-en; zh coverage **[unverified]**.
- **DITING** ([arXiv:2510.09116](https://arxiv.org/abs/2510.09116)) - 2025 zh->en **web-novel translation
  benchmark** scoring idiom, cultural, terminology and **character-name consistency**. Licence **[unverified]**.
- **Disco-Bench** ([arXiv:2307.08074](https://arxiv.org/abs/2307.08074)) - discourse-aware Chinese benchmark
  from the GuoFeng group; expect GuoFeng-like restrictions.
- **DOLFIN** ([Findings NAACL 2025](https://aclanthology.org/2025.findings-naacl.307/)) - document-level
  **finance** MT test set; HF `LinguaCustodia/dolfin` is **gated**; European pairs only.
- **ACL 60-60** ([IWSLT 2023](https://aclanthology.org/2023.iwslt-1.2/), HF `ymoslem/acl-6060`) - ACL talks into
  10 languages **including zh, ja, es**, talk-level documents **plus a scientific-terminology component**. Rare
  doc-level + terminology + en->zh combination. Licence **[unverified]**.
- **UN Parallel Corpus v1.0** ([un.org](https://www.un.org/dgacm/en/content/uncorpus),
  [LREC 2016](https://aclanthology.org/L16-1561/)) - **six-way parallel incl. en<->zh, document-level (UN
  symbols preserved), professional UN translators**. The strongest doc-level legal/institutional en-zh option;
  licence **[unverified]** and the companion `corpus-sources.md` rates it fetch-only for a commercial-friendly
  repo.
- **WMT Biomedical has no Chinese test set** **[confirmed]** ([WMT24 page](http://www2.statmt.org/wmt24/biomedical-translation-task.html));
  test sets are en<->fr/de/it/pt/ru/es only, delivered as **titles + abstracts as long text with no sentence
  segmentation**.
- **Mozilla Pontoon L10n** via `SEACrowd/mozilla_pontoon` - the SEACrowd repackaging's card front-matter reads
  **`license: bsd-3-clause`** (indirect evidence only, **re-verify**); upstream Mozilla l10n is MPL-2.0.
- **TED / IWSLT and OpenSubtitles**: both carry serious rights problems (TED terms are widely reported as
  NC/ND; OpenSubtitles is fan-subtitled copyrighted film). **Do not vendor.** Note OPUS does expose an explicit
  `en&zh_CN` OpenSubtitles pair, and `Helsinki-NLP/OpenSubtitles2024` on HF is **gated**.

### 15.7 Net effect on our plan
Nothing above changes the headline: **`google/wmt24pp` (Apache-2.0) is the only established MT benchmark we can
actually vendor**, and everything else is either fetch-only or must be replaced by the permissive/PD sources
catalogued in `corpus-sources.md`. Two refinements:
1. For **zh->en** we cannot use WMT24/25 (en->zh only). Use **WMT23** (fetch-only) or build zh->en from PD
   literature and permissive OSS strings.
2. Copy the **WMT23 Terminology Base/Proper/Random design** and the **GuoFeng literary MQM typology** as our
   evaluation rubrics - they are free to reuse as *methods* even where the data is not.

