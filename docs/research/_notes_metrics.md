# Automatic MT Quality Scoring — Current Best Practice (2024–2026)

Research notes for the machine-translation benchmark project (en↔zh-CN, plus ja and es).

> **Method note / limitation.** This session had **no direct HTTP access** — `curl` / `Invoke-WebRequest` to huggingface.co, raw.githubusercontent.com, hf-mirror.com and even baidu.com all failed (timeouts / TLS errors). Everything below was gathered through a **web search tool** (~350 queries across this agent and five parallel research subagents).
> Two tricks made verification possible despite near-empty snippets: (1) a Hugging Face **raw-README URL is indexed with its first YAML frontmatter line as the result title**, so a title reading `license: apache-2.0` is a direct read of the model card; (2) **chunk-indexed PDFs** (URLs carrying `#part#chunk`) return the literal first ~100 characters of that chunk as the title, which allowed verbatim quotes from WMT proceedings.
> **Nothing here is guessed.** Facts read from a source are marked **CONFIRMED**; everything else is marked **unverified**. Licenses in particular are never inferred by analogy.

---

## 0. Executive summary — what a credible 2026 benchmark does

1. **Do not lead with BLEU.** The WMT metrics organizers titled their 2022 findings paper literally *"Stop Using BLEU – Neural Metrics Are Better and More Robust"* ([aclanthology.org/2022.wmt-1.2](https://aclanthology.org/2022.wmt-1.2/)).
2. **Primary metric = a neural, reference-based metric.** For a permissive, ungated, CPU-runnable stack that means **COMET-22** (`Unbabel/wmt22-comet-da`, **apache-2.0 CONFIRMED**) plus optionally **MetricX-24-hybrid-large** (**apache-2.0 CONFIRMED**).
3. **Always publish sacreBLEU signatures** and use `tok:zh` for Chinese, `ja-mecab` for Japanese. Default `13a` on Chinese is simply wrong.
4. **Name the exact checkpoint and library version of every metric.** "COMET = 0.85" is unreproducible; COMET-20, COMET-22, CometKiwi and XCOMET are different scales ([Pitfalls and Outlooks in Using COMET](https://aclanthology.org/2024.wmt-1.121/)).
5. **Report significance** (paired bootstrap), not bare deltas, and use [MT-Thresholds](https://github.com/kocmitom/MT-Thresholds) to say what a delta means.
6. **Add degenerate-input control rows** (empty string, copy-source, wrong-language) — metrics fail on these in documented ways ([MSLC25](https://aclanthology.org/2025.wmt-1.69/)).
7. **Mind the license split.** Unbabel's family is *not* uniform: COMET-22 is Apache-2.0 and ungated, but **CometKiwi is CC-BY-NC-SA-4.0 and gated**, and XCOMET is gated with an unverified license.
8. **WMT25's own headline is "References Still Help"** ([2025.wmt-1.24](https://aclanthology.org/2025.wmt-1.24/)) — reference-free QE is not yet a substitute for reference-based scoring.

---

# A) Neural metrics

## A.1 COMET family (Unbabel)

**Framework:** [github.com/Unbabel/COMET](https://github.com/Unbabel/COMET) · PyPI [unbabel-comet](https://pypi.org/project/unbabel-comet/) · docs [unbabel.github.io/COMET](https://unbabel.github.io/COMET/html/models.html).
**Code license:** Apache-2.0, declared in [pyproject.toml](https://github.com/Unbabel/COMET/blob/master/pyproject.toml) (literal LICENSE text not retrievable this session → high confidence, not character-verified).
**The code license is NOT the weight license.** Unbabel maintains a separate [LICENSE.models.md](https://github.com/Unbabel/COMET/blob/master/LICENSE.models.md) and a model table in [MODELS.md](https://github.com/Unbabel/COMET/blob/master/MODELS.md) ("Available Evaluation Models"). **Both files were confirmed to exist but their bodies could not be retrieved** through search snippets — this is the single biggest remaining gap in this report, and it is exactly the file that resolves the XCOMET/CometKiwi-XL license question. Fetch it directly when network is available.

### Per-model verification

**`Unbabel/wmt20-comet-da`** — <https://huggingface.co/Unbabel/wmt20-comet-da>
- Reference-based DA regressor over (source, hypothesis, reference).
- Backbone **XLM-R Large, ~565M** (COMET loads `xlm-roberta-large`; see [Unbabel/COMET issue #59](https://github.com/Unbabel/COMET/issues/59)).
- **Gated: No.** License: **unverified** — a [LICENSE file exists](https://huggingface.co/Unbabel/wmt20-comet-da/blob/main/LICENSE) but neither its text nor a frontmatter license string surfaced.
- Superseded by COMET-22; its score scale differs and is **not** comparable to COMET-22.

**`Unbabel/wmt20-comet-qe-da`** — <https://huggingface.co/Unbabel/wmt20-comet-qe-da> — QE (reference-free), XLM-R Large ~565M (unverified), **gated: No**, license **unverified**. Obsolete.

**`Unbabel/wmt22-comet-da` (COMET-22)** — <https://huggingface.co/Unbabel/wmt22-comet-da>
- **Reference-based.** Paper: *COMET-22: Unbabel-IST 2022 Submission for the Metrics Shared Task*, [aclanthology.org/2022.wmt-1.52](https://aclanthology.org/2022.wmt-1.52/).
- Backbone **XLM-R Large, ~565M**; ~2.3 GB checkpoint ([model.ckpt](https://huggingface.co/Unbabel/wmt22-comet-da/blob/c211a6e9e3ef36f7fce60e6e24663da8b4179aac/model.ckpt)).
- **Gated: No** — no gate banner appears on the page in any indexed title, unlike CometKiwi/XCOMET.
- **License: CONFIRMED `apache-2.0`.** The raw README at commit `1358d906` is indexed with the literal title `license: apache-2.0`: <https://huggingface.co/Unbabel/wmt22-comet-da/blob/1358d906012962aca32f48913d55e967d250adf1/README.md?code=true>
- **CPU: yes.** ~4–6 GB RAM fp32; order of ~5–20 segments/s on 8–16 modern cores at batch 8 (**estimate**, not measured here). A few hundred segments = seconds to a couple of minutes.
- ⭐ **The best permissive + ungated + CPU-runnable neural metric available. This is the default primary metric.**

**`Unbabel/wmt22-cometkiwi-da` (CometKiwi)** — <https://huggingface.co/Unbabel/wmt22-cometkiwi-da>
- **QE / reference-free** — scores (source, hypothesis) with no reference. Paper: [aclanthology.org/2022.wmt-1.60](https://aclanthology.org/2022.wmt-1.60/).
- Backbone **InfoXLM Large, ~565M**.
- **Gated: YES** — the page title reads *"Acknowledge license to accept the repository"*. Real-world friction is documented: <https://huggingface.co/Unbabel/wmt22-cometkiwi-da/discussions/1> ("Cannot access with my read-only token").
- **License: CONFIRMED `cc-by-nc-sa-4.0` (NON-COMMERCIAL).** Read from an un-gated mirror that copies the original frontmatter verbatim: <https://huggingface.co/ben-xl8/wmt22-cometkiwi-da/raw/6c5396ae93eb6fc0bbf73a1964e6e69272090b3d/README.md> (indexed title = `license: cc-by-nc-sa-4.0`). A second mirror carries the ~20 KB CC-BY-NC-SA-4.0 LICENSE body plus `extra_gated_heading: Acknowledge license to accept the repository`: <https://huggingface.co/Supervache/wmt22-cometkiwi-da-safeformat/raw/main/README.md>.
- **CPU: yes**, same cost class as COMET-22.
- ⚠️ **Excluded from any commercial stack.**

**`Unbabel/wmt23-cometkiwi-da-xl`** — <https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xl>
- QE / reference-free. Paper: [aclanthology.org/2023.wmt-1.62](https://aclanthology.org/2023.wmt-1.62/).
- Backbone **XLM-RoBERTa XL, ~3.5B** — corroborated by the community conversion <https://huggingface.co/vince62s/wmt23-cometkiwi-da-roberta-xl>, which ships `modeling_xlm_roberta_xl.py`.
- **Gated: YES** (*"Acknowledge license to accept the repository"*).
- **License: unverified.** Indirect evidence points to `cc-by-nc-sa-4.0` (identical gating heading to the confirmed-NC CometKiwi-22), but **this is not confirmation** — verify on the card before any commercial use.
- **CPU: impractical** (~14 GB fp32, ≥16–20 GB RAM, well under 1 seg/s).

**`Unbabel/wmt23-cometkiwi-da-xxl`** — <https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xxl>
- QE / reference-free, **XLM-R XXL ~10.7B**. **Gated: YES.** License **unverified** (same indirect NC evidence).
- **CPU: no** (~43 GB fp32). Variants: gated `Unbabel/wmt23-cometkiwi-da-xxl-marian`, and `eole-nlp/wmt23-cometkiwi-da-xxl-eole`.

**`Unbabel/XCOMET-XL`** — <https://huggingface.co/Unbabel/XCOMET-XL>
- **Reference-based, and uniquely emits error spans with severities** (it can also run source-only). Paper: *xCOMET: Transparent Machine Translation Evaluation through Fine-grained Error Detection*, TACL 2024 — [aclanthology.org/2024.tacl-1.54](https://aclanthology.org/2024.tacl-1.54/), arXiv [2310.10482](https://arxiv.org/abs/2310.10482).
- Backbone **XLM-R XL, 3.5B** — independently tabulated as "XCOMET-XL | XLMR-XL | 3.5 billion" in [arXiv:2410.18697](https://ar5iv.labs.arxiv.org/html/2410.18697).
- **Gated: YES** — page title reads *"You need to agree to share your contact information to access this model"*.
- **License: unverified.** No mirror exposed the license string; the PR-branch README frontmatter begins `pipeline_tag: translation`, so the license line never surfaced. **Do not claim Apache-2.0 or CC-BY-NC for XCOMET without reading the card.**
- **CPU: impractical.** FP16 conversion: <https://huggingface.co/eole-nlp/xcomet-xl-eole-fp16>.
- Note: **XCOMET-Ensemble ranked #1 in the official WMT23 metrics ranking** (see §A.4).

**`Unbabel/XCOMET-XXL`** — <https://huggingface.co/Unbabel/XCOMET-XXL> — reference-based + error spans, **XLM-R XXL ~10.7B**, **gated: YES** (contact info), license **unverified**, **CPU: no**.

**`Unbabel/eamt22-cometinho-da` (COMETINHO)** — <https://huggingface.co/Unbabel/eamt22-cometinho-da>
- Reference-based, distilled. Paper: *Searching for COMETINHO: The Little Metric That Could*, [aclanthology.org/2022.eamt-1.9](https://aclanthology.org/2022.eamt-1.9/).
- Backbone MiniLM-class (COMET ships a `MiniLMEncoder`); exact parameter count **unverified**.
- **Gated: No.** License **unverified**. **CPU: yes, very fast** — this is its whole purpose.

**`Unbabel/wmt22-unite-da`** — <https://huggingface.co/Unbabel/wmt22-unite-da> — exists, **gated: YES** (contact info), license **unverified**. Note `Unbabel/wmt22-unite-mup` does **not** appear to exist; the related model is <https://huggingface.co/Unbabel/unite-mup>.

### Running COMET fully offline on CPU

```bash
pip install unbabel-comet                      # Apache-2.0 code
huggingface-cli download Unbabel/wmt22-comet-da --local-dir ./models/wmt22-comet-da
# pre-warm the base encoder too, COMET pulls it separately:
huggingface-cli download xlm-roberta-large --local-dir ./models/xlm-roberta-large

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
comet-score -s src.txt -t mt.txt -r ref.txt \
    --model ./models/wmt22-comet-da --gpus 0 --batch_size 8
# QE mode (omit -r, use a QE checkpoint):
comet-score -s src.txt -t mt.txt --model ./models/wmt22-cometkiwi-da --gpus 0
```

**Offline gotcha (CONFIRMED):** COMET downloads the *base encoder* (`xlm-roberta-large`) separately from the checkpoint — see <https://huggingface.co/Unbabel/wmt22-comet-da/discussions/3> ("I see Unbabel comet is downloading models--xlm-roberta-large folder every time") and <https://stackoverflow.com/questions/79137798/how-to-load-the-tokenizer-locally-from-unbabel-comet>. Pre-warm the cache before going air-gapped.

---

## A.2 MetricX (Google)

**Repo:** [github.com/google-research/metricx](https://github.com/google-research/metricx) ([README](https://github.com/google-research/metricx/blob/main/README.md)) · PyPI [metricx](https://pypi.org/project/metricx/). Code license Apache-2.0 (repo LICENSE text **unverified**; every model card carries `license: apache-2.0`).

⚠️ **Score direction: MetricX outputs 0–25 where LOWER is better** — the opposite of COMET. Documented in the repo README and in [Google Cloud Translation evaluation docs](https://docs.cloud.google.com/translate/docs/advanced/translation-model-evaluation). Normalize or clearly label before mixing with COMET, or your table will silently invert.

**MetricX-23** — *MetricX-23: The Google Submission to the WMT 2023 Metrics Shared Task*, [aclanthology.org/2023.wmt-1.63](https://aclanthology.org/2023.wmt-1.63/) ([PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.63.pdf)).
- Reference-based: `google/metricx-23-large-v2p0`, `google/metricx-23-xl-v2p0`, `google/metricx-23-xxl-v2p0`.
- QE / reference-free: `google/metricx-23-qe-large-v2p0`, `google/metricx-23-qe-xl-v2p0`, `google/metricx-23-qe-xxl-v2p0`.
- Backbone mT5 ([arXiv:2010.11934](https://arxiv.org/abs/2010.11934)): large ~1.2B, XL ~3.7B, XXL ~13B — standard mT5 sizes; **an explicit per-model enumeration was not captured, treat exact counts as unverified**.
- **License CONFIRMED `apache-2.0`** for `metricx-23-xl-v2p0` via the indexed README title: <https://huggingface.co/api/resolve-cache/models/google/metricx-23-xl-v2p0/891fc5a7c306e46ec4c122bb7c19f2e7c6a7c9ba/README.md?download=true>. Other -23 cards individually **unverified** (same family).
- **Gated: no evidence of gating on any `google/metricx-*` repo.**

**MetricX-24** — *MetricX-24: The Google Submission to the WMT 2024 Metrics Shared Task*, [aclanthology.org/2024.wmt-1.35](https://aclanthology.org/2024.wmt-1.35/), arXiv [2410.03983](https://arxiv.org/abs/2410.03983), [statmt PDF](http://www2.statmt.org/wmt24/pdf/2024.wmt-1.35.pdf).
- IDs: `google/metricx-24-hybrid-large-v2p6`, `google/metricx-24-hybrid-xl-v2p6`, `google/metricx-24-hybrid-xxl-v2p6`, plus `-bfloat16` variants.
- **"Hybrid" = one model that scores with OR without a reference**, replacing MetricX-23's separate `-qe-` checkpoints. That makes MetricX-24 the most convenient single-checkpoint way to report both a reference-based and a QE number under a permissive license.
- **License CONFIRMED `apache-2.0`** for the **large** card (<https://huggingface.co/google/metricx-24-hybrid-large-v2p6/raw/b6ec8db9a17db7c9e892f4d7e8b3a33c445c5104/README.md>, indexed title `license: apache-2.0`) **and for the XXL** card (<https://huggingface.co/api/resolve-cache/models/google/metricx-24-hybrid-xxl-v2p6/a278c794beddd98273587ae7292a65818fa4eccc/README.md?download=true>, same title). XL card individually **unverified**.
- **CPU:** `large` (~1.2B mT5; ~4.8 GB fp32, ~2.4 GB bf16) is **borderline feasible but slow**; XL (~15 GB fp32) and XXL (~52 GB fp32) are **not** CPU-practical.

**MetricX-25** — the paper exists: *MetricX-25 and GemSpanEval: Google Translate Submissions to the WMT25 Evaluation Shared Task*, [aclanthology.org/2025.wmt-1.70](https://aclanthology.org/2025.wmt-1.70/), arXiv [2510.24707](https://arxiv.org/abs/2510.24707).
- **CONFIRMED verbatim from the paper:** *"In this paper, we present our submissions to the unified WMT25 Translation Evaluation Shared Task"*; and *"We chose the hybrid model as our primary submission, despite being slightly outperformed by the reference-based variant"* ([export PDF chunk](https://export.arxiv.org/pdf/2510.24707#4#2)); and that training used **two-stage fine-tuning, DA first then MQM** ([ar5iv](https://ar5iv.labs.arxiv.org/html/2510.24707#2)).
- That last quote is quietly important: **even Google's own hybrid was beaten by its reference-based variant** — more evidence that references still help.
- **Public weights: NOT FOUND.** Repeated targeted searches (including the raw-README frontmatter technique) surfaced **no `google/metricx-25*` repository**. **HF ids, sizes and license: unverified / apparently unreleased.** Do **not** assume Apache-2.0 by analogy. Do not plan a 2026 stack around MetricX-25 weights until a release is confirmed.

---

## A.3 BLEURT, BERTScore, YiSi, UniTE, xCOMET-lite, newcomers

**BLEURT** — [github.com/google-research/bleurt](https://github.com/google-research/bleurt), paper [arXiv:2004.04696](https://arxiv.org/abs/2004.04696).
- Recommended checkpoint **BLEURT-20** ([checkpoints.md](https://github.com/google-research/bleurt/blob/master/checkpoints.md)), RemBERT-based multilingual; parameter count **unverified** (RemBERT ~580M).
- License Apache-2.0 (google-research convention + Apache header on the HF `evaluate` wrapper); repo LICENSE text **unverified**.
- Official implementation is **TensorFlow-only**. PyTorch ports: <https://huggingface.co/lucadiliello/BLEURT-20>, PyPI [bleurt-pytorch](https://pypi.org/project/bleurt-pytorch/).
- Reference-based. CPU feasible but slow. **Superseded** by COMET/MetricX; keep only for continuity with older literature.

**BERTScore** — [github.com/Tiiiger/bert_score](https://github.com/Tiiiger/bert_score), paper [arXiv:1904.09675](https://arxiv.org/abs/1904.09675).
- License **MIT** (reported; literal LICENSE text **unverified**).
- Reference-based and **untrained**: contextual embeddings + greedy token matching → P/R/F1, optional IDF weighting and `rescale_with_baseline`.
- Defaults per language: `roberta-large` (en), `bert-base-chinese` (zh), `bert-base-multilingual-cased` otherwise ([README](https://github.com/Tiiiger/bert_score/blob/master/README.md)).
- **CPU: yes.** Standing: consistently **below** trained metrics in WMT meta-evaluation. Fine as a cheap permissive secondary signal; not a primary claim.

**YiSi** — YiSi-1 (reference-based) [aclanthology.org/W19-5358](https://aclanthology.org/W19-5358/); YiSi-2 (reference-free) [aclanthology.org/2020.wmt-1.100](https://aclanthology.org/2020.wmt-1.100/). Cross-lingual semantic similarity over mBERT. Distribution/license **unverified**; **dormant** since ~WMT2020. Not recommended for new work.

**UniTE / UniTE-MUP** — [aclanthology.org/2022.acl-long.558](https://aclanthology.org/2022.acl-long.558/), arXiv [2204.13346](https://arxiv.org/abs/2204.13346). Unifies **src-only (QE), ref-only, src+ref** in one model — the design MetricX-24-hybrid later generalized. `Unbabel/wmt22-unite-da` is **gated**, license **unverified**. Superseded.

**xCOMET-lite** — *xCOMET-lite: Bridging the Gap Between Efficiency and Quality in Learned MT Evaluation Metrics*, EMNLP 2024 — [aclanthology.org/2024.emnlp-main.1223](https://aclanthology.org/2024.emnlp-main.1223/), arXiv [2406.14553](https://arxiv.org/abs/2406.14553).
- Method: **distillation + INT8 quantization + pruning** of the 3.5B XCOMET-XL teacher.
- Student size commonly cited as ~278M — **unverified** from a primary snippet.
- **No official `Unbabel/xcomet-lite` release found**; community re-uploads exist (<https://huggingface.co/myyycroft/XCOMET-lite>, <https://huggingface.co/PingFiona/XCOMET-lite>). License **unverified**; since the teacher is a gated Unbabel model, a NC-derivative outcome is plausible — **verify before commercial use**.
- CPU: designed to be feasible. The most interesting "small + error-span" option *if* licensing can be cleared.

**2025–2026 newcomers worth tracking**
- **GemSpanEval** (Google, WMT25) — a **Gemma-based generative error-span evaluator**, i.e. the AutoMQM/GEMBA-MQM paradigm moved onto **open-weight** Gemma. [aclanthology.org/2025.wmt-1.70](https://aclanthology.org/2025.wmt-1.70/) / arXiv [2510.24707](https://arxiv.org/abs/2510.24707). Backbone size, recipe and whether checkpoints were released: **unverified**. **This is the most promising direction for offline, permissive, span-level MT evaluation.**
- **CompactQE: Interpretable Translation Quality Estimation via Small Open-Weight LLMs** — arXiv [2605.15763](https://arxiv.org/abs/2605.15763). Exactly on-topic for "small, open, offline" QE; contents **unverified**.
- **SSA-COMET / SSA-COMET-QE** (McGill-NLP) — African-language COMET family; [paper page](https://huggingface.co/papers/2506.04557), model e.g. <https://huggingface.co/McGill-NLP/ssa-comet-mtl-final>. Licenses **unverified**.
- **SLIDE** — reference-free sliding-document-window metric: [aclanthology.org/2024.naacl-short.18](https://aclanthology.org/2024.naacl-short.18/), arXiv [2309.08832](https://arxiv.org/abs/2309.08832).
- **Align-then-Slide** (2025) — ultra-long document MT evaluation, arXiv [2509.03809](https://arxiv.org/abs/2509.03809).
- **TREQA** — *Do LLMs Understand Your Translations? Evaluating Paragraph-level MT with Question Answering*, arXiv [2504.07583](https://arxiv.org/abs/2504.07583).
- **Sentinel metrics** — *Guardians of the Machine Translation Meta-Evaluation: Sentinel Metrics Fall In!*, [aclanthology.org/2024.acl-long.856](https://aclanthology.org/2024.acl-long.856/), arXiv [2408.13831](https://arxiv.org/abs/2408.13831). Released models e.g. <https://huggingface.co/sapienzanlp/sentinel-cand-mqm> (license unverified). **Read this before trusting any QE correlation number.**
- **MSLC23 / MSLC24 / MSLC25** — metric behaviour on the *wide landscape* of quality including empty strings: [2024.wmt-1.34](https://aclanthology.org/2024.wmt-1.34/), **MSLC25: Metric Performance on Low-Quality Machine Translation, Empty Strings, and Language Variants** [2025.wmt-1.69](https://aclanthology.org/2025.wmt-1.69/) ([PDF](https://aclanthology.org/2025.wmt-1.69.pdf)); data/figures [github.com/nrc-cnrc/MSLC](https://github.com/nrc-cnrc/MSLC), [interactive charts](https://nrc-cnrc.github.io/MSLC/2025/interactive/charts.html).
- **ThinMQM** — *Are Large Reasoning Models Good Translation Evaluators?* (NeurIPS 2025), <https://github.com/NLP2CT/ThinMQM>, [poster](https://neurips.cc/virtual/2025/loc/san-diego/poster/117120).

---

## A.4 WMT Metrics / Evaluation Shared Task findings, 2022 → 2026

| Year | Paper (exact title) | URL | Takeaway |
|---|---|---|---|
| WMT22 | *Results of WMT22 Metrics Shared Task: **Stop Using BLEU** – Neural Metrics Are Better and More Robust* | [2022.wmt-1.2](https://aclanthology.org/2022.wmt-1.2/) · [statmt PDF](https://statmt.org/wmt22/pdf/2022.wmt-1.2.pdf) · [Google Research](https://research.google/pubs/results-of-wmt22-metrics-shared-task-stop-using-bleu-neural-metrics-are-better-and-more-robust/) | **The quotable BLEU deprecation.** The title *is* the organizers' normative statement. Verbatim body recommendation paragraph: **unverified**. |
| WMT23 | *Results of WMT23 Metrics Shared Task: **Metrics Might Be Guilty but References Are Not Innocent*** | [2023.wmt-1.51](https://aclanthology.org/2023.wmt-1.51/) · [DFKI PDF](https://dfki.de/fileadmin/user_upload/import/14644_2023.wmt-1.51.pdf) | Reference quality is a first-order confound. **CONFIRMED ranking: XCOMET-Ensemble = rank 1, MetricX-23 next** (two independent reproductions of the official table: [2024.acl-long.856.pdf](https://aclanthology.org/2024.acl-long.856.pdf), [Sapienza thesis](https://iris.uniroma1.it/bitstream/11573/1762185/1/Tesi_dottorato_Proietti.pdf)). Exact correlation values and the full order below rank 2: **unverified**. |
| WMT24 | ***Are LLMs Breaking MT Metrics?** Results of the WMT24 Metrics Shared Task* | [2024.wmt-1.2](https://aclanthology.org/2024.wmt-1.2/) · [Google Research](https://research.google/pubs/are-llms-breaking-mt-metrics-results-of-the-wmt24-metrics-shared-task/) · [DFKI](https://www.dfki.de/en/web/research/projects-and-publications/publication/15299) | Central worry: do metrics stay reliable on **LLM-produced translations**. **Overall winner: unverified.** But a striking CONFIRMED fragment from the reference-free block: `sentinel-src-mqm` (a deliberately degenerate source-only baseline) at 0.513/0.418/0.630/0.491 sits **in the same band** as the real QE metric `XLSimMqm` at 0.515/0.531/0.520/0.49… ([proceedings PDF chunk](https://aclanthology.org/anthology-files/anthology-files/pdf/wmt/2024.wmt-1.pdf#422#145)). Column semantics unverified. |
| WMT25 | *Findings of the WMT25 Shared Task on Automated Translation Evaluation Systems: **Linguistic Diversity is Challenging and References Still Help*** (Lavie, Hanneman et al. — **not** Freitag) | [2025.wmt-1.24](https://aclanthology.org/2025.wmt-1.24/) · [statmt PDF](http://www2.statmt.org/wmt25/pdf/2025.wmt-1.23.pdf) · [task repo](https://github.com/wmt-conference/wmt25-mteval) | **WMT25 unified the Metrics and QE shared tasks.** CONFIRMED conclusion opening: *"This paper documented the results of the WMT25 shared task on automated machine translation evaluation systems, which unified th…"*. Subtasks: **1 = Segment-Level Quality Score Prediction** ([page](https://www2.statmt.org/wmt25/mteval-subtask1.html)), **2 = Fine-grained error span detection** ([page](http://www2.statmt.org/wmt25/mteval-subtask2.html)), plus a task 3 and a challenge-set subtask. **Per-subtask winners: unverified.** |
| WMT26 | *Shared Task: Automated Translation Quality Evaluation Systems* | [task page](https://www2.statmt.org/wmt26/mteval-task.html) · [subtask 1](https://www2.statmt.org/wmt26/mteval-subtask1.html) · [subtask 2](https://www2.statmt.org/wmt26/mteval-subtask2.html) | Subtasks **reordered**: 1 = Segment-Level Error Detection and Span Annotation; 2 = Segment-Level Quality Score Prediction. **Span annotation is now the headline task** — a signal about where the field is heading. |

**Other WMT25 evaluation-track papers:** [SSA-MTE African challenge set (1.65)](https://aclanthology.org/2025.wmt-1.65/) · [Nvidia-Nemo (1.66)](https://aclanthology.org/2025.wmt-1.66/) · [GEMBA-MQM V2 (1.67)](https://aclanthology.org/2025.wmt-1.67/) · [CUNI & Phrase (1.68)](https://aclanthology.org/2025.wmt-1.68/) · [MSLC25 (1.69)](https://aclanthology.org/2025.wmt-1.69/) · [MetricX-25 + GemSpanEval (1.70)](https://aclanthology.org/2025.wmt-1.70/) · [UvA-MT: LLM uncertainty as QE proxy (1.72)](https://aclanthology.org/2025.wmt-1.72/) · [Task 3 submission (1.73)](https://aclanthology.org/2025.wmt-1.73/).

**Organizer-adjacent guidance**
- *To Ship or Not to Ship: An Extensive Evaluation of Automatic Metrics for Machine Translation* (Kocmi et al., WMT 2021) — [2021.wmt-1.57](https://aclanthology.org/2021.wmt-1.57/), arXiv [2107.10821](https://arxiv.org/abs/2107.10821). CONFIRMED recommendation fragment from Kocmi's own tutorial deck: *"2. Run a paired significance test to reduce metric misjudgement"* ([UFAL MTM22 slides](https://ufal.mff.cuni.cz/mtm22/files/09-mt-evaluation-tom-kocmi.pdf)). The paper's full numbered recommendation list and any **segment-count** guidance: **unverified**.
- *Navigating the Metrics Maze: Reconciling Score Magnitudes and Accuracies* (Kocmi et al., ACL 2024) — [2024.acl-long.110](https://aclanthology.org/2024.acl-long.110/), arXiv [2401.06760](https://arxiv.org/abs/2401.06760). Tooling: [MT-Thresholds](https://github.com/kocmitom/MT-Thresholds) / PyPI [mt-thresholds](https://pypi.org/project/mt-thresholds/) — *"Tool to check how metric deltas for machine translation reflect on system-level human accuracies"*. **Use this instead of inventing a "meaningful delta".** Specific threshold values: **unverified** — read them from the tool.

**On BLEU:** WMT's own title says "Stop Using BLEU". **Whether any WMT findings paper explicitly endorses BLEU as a legitimate *secondary* metric is unverified** — no source stating that was found, and none forbidding it either. The defensible position: report BLEU as a *reproducibility artifact* with its signature, never as the quality claim.

---

# B) LLM-as-judge

## B.1 GEMBA (Kocmi & Federmann)

*Large Language Models Are State-of-the-Art Evaluators of Translation Quality*, EAMT 2023 — [aclanthology.org/2023.eamt-1.19](https://aclanthology.org/2023.eamt-1.19/), arXiv [2302.14520](https://arxiv.org/abs/2302.14520), [ar5iv](https://ar5iv.labs.arxiv.org/html/2302.14520). Prompt templates are in the appendix of the [EAMT proceedings PDF](https://preview.aclanthology.org/ingest-acl-2023-videos/2023.eamt-1.pdf).

- **Prompt design:** four zero-shot variants — **GEMBA-DA** (continuous 0–100 DA-style), **GEMBA-SQM** (scalar quality metric scale), **GEMBA-stars** (1–5 stars), **GEMBA-classes** (named quality classes) — evaluated in **two modes: reference-based and reference-free**. The exact scale wording per variant is **unverified**; read §3 + appendix before quoting. An independent tabulation of the prompt shape ("Score the following translation from (src_lang) to (tgt_lang)…") appears in [arXiv:2410.10995](https://arxiv.org/pdf/2410.10995v1).
- **Required model class:** GPT-3.5-class and larger. The widely cited sentence *"works only with GPT 3.5 and larger models"* could **not** be retrieved verbatim in this session → **wording unverified**, substance consistent across every secondary summary. **This is not an offline-CPU metric.**
- **Reliability:** strong at **system level**; **segment level is markedly weaker** (coarse, heavily tied scores). CONFIRMED partial quote from the arXiv PDF: *"While preliminary results indicate that the GEMBA metric performs very well when compared to other automated metrics evaluated a…"*. Exact segment-level correlations **unverified**. Corroborating downstream evidence: [arXiv:2410.18697](https://ar5iv.labs.arxiv.org/html/2410.18697) — *"The best metric (GEMBA-MQM) correlates moderately with human MQM but it cannot distinguish human translation from LLM out[put]"*.

## B.2 GEMBA-MQM

*GEMBA-MQM: Detecting Translation Quality Error Spans with GPT-4*, WMT 2023 — [aclanthology.org/2023.wmt-1.64](https://aclanthology.org/2023.wmt-1.64/), [statmt PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.64.pdf), arXiv [2310.13988](https://arxiv.org/abs/2310.13988).

- **Prompt design:** a **few-shot (three-shot), language-agnostic** prompt — the same three demonstrations are reused across all language pairs — asking the model to output **MQM-style error spans annotated with severity**, which are then converted into a numeric score. The demonstrations are in **Table 1** of the paper ([Semantic Scholar figure page](https://www.semanticscholar.org/paper/338da2650fbee5b35d1e37b16c2603b466eea962)).
- **Required model class: GPT-4** (stated in the title).
- **Scoring formula: UNVERIFIED.** No primary snippet stating the numeric severity penalties could be retrieved. The commonly quoted −25 / −5 / −1 (critical/major/minor, with a floor) follows the Google MQM convention, but **I will not assert those integers** — read §2–§3 of the [PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.64.pdf). Whether "critical" is folded into "major" is likewise **unverified**.
- **WMT23 rank:** a primary submission, repeatedly described in follow-on literature as **top / joint-top at system level** alongside XCOMET-Ensemble and MetricX-23. **Exact rank and accuracy: unverified** — pull from [2023.wmt-1.51](https://aclanthology.org/2023.wmt-1.51/).
- **The authors' own caveat — CONFIRMED.** The paper contains a section literally titled **"5 Caution with \"Black Box\" LLMs"** (retrieved as an indexed section heading of the [PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.64.pdf)). It warns that a closed, versioned, non-reproducible API model whose training data may already contain WMT test sets is a poor instrument for **ranking MT systems**. The verbatim sentence is **unverified**, but the existence and title of the caveat section are verified. **A benchmark that ranks systems with GPT-4 GEMBA-MQM is doing so against the authors' explicit advice.**
- **CORRECTION to a common assumption:** the repo is **not** `microsoft/GEMBA`. It is **<https://github.com/MicrosoftTranslator/GEMBA>** (author mirror with the license file: <https://github.com/kocmitom/GEMBA/blob/main/LICENSE.md>).
- **License of code AND prompts: CC BY-SA 4.0 — NOT MIT.** CONFIRMED by the official repo commit whose message reads *"Code and data licensed under CC BY-SA 4.0"*: <https://github.com/MicrosoftTranslator/GEMBA/commit/18671baee617b70d852dd7f2984172b23b49f8db>. Character-level LICENSE text **unverified**.
  **Practical consequence:** CC BY-SA is **commercially usable but copyleft/ShareAlike**. If you vendor GEMBA prompts into your harness, ShareAlike obligations plausibly attach to your derived prompt files. Flag this explicitly.
- **2025 successor: GEMBA-MQM V2: Ten Judgments Are Better Than One** — [2025.wmt-1.67](https://aclanthology.org/2025.wmt-1.67/), [statmt PDF](http://www2.statmt.org/wmt25/pdf/2025.wmt-1.67.pdf). Aggregates **ten sampled judgments** instead of one (self-consistency), attacking exactly the segment-level variance problem. CONFIRMED note in the paper: *"At the time this paper was finalized, the shared task organizers had not yet released the final WMT25 metrics task results"* — so it contains no final rankings. Aggregation function / model / temperature: **unverified**.
- **Cost-reduction variant: BatchGEMBA / BatchGEMBA-MQM** — *Token-Efficient Machine Translation Evaluation with Batched Prompting and Prompt Compression*, arXiv [2503.02756](https://arxiv.org/abs/2503.02756). Quality-vs-batch-size tradeoff numbers **unverified**.

## B.3 AutoMQM

*The Devil is in the Errors: Leveraging Large Language Models for Fine-grained Machine Translation Evaluation* (Fernandes et al., WMT 2023) — [aclanthology.org/2023.wmt-1.100](https://aclanthology.org/2023.wmt-1.100/), [statmt PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.100.pdf), arXiv [2308.07286](https://arxiv.org/abs/2308.07286), [Google Research](https://research.google/pubs/the-devil-is-in-the-errors-leveraging-large-language-models-for-fine-grained-machine-translation-evaluation/).

- **CONFIRMED verbatim** from the WMT23 proceedings: *"Motivated by these findings, **we propose AUTOMQM**, a prompting technique for translation quality assessment that instructs LLM[s]…"*.
- Method: **in-context learning** on **PaLM / PaLM-2** to produce **MQM-style error annotations (span + category + severity)**, deriving the score from the annotations rather than asking for a scalar.
- Findings: **error-span prompting beats score-only prompting**; the gain is **concentrated in the largest models** (consistent with GEMBA's "only large models work"); output is **interpretable** and comparable against human MQM spans. A results row for `Unicorn` (largest PaLM-2) shows 84.3% / 56.1% / 48.3% / 49.8% across EN-DE / ZH-EN columns ([ar5iv](https://ar5iv.labs.arxiv.org/html/2308.07286)) — **column semantics unverified, do not reuse without reading the header**.

## B.4 MQM-APE

*MQM-APE: Toward High-Quality Error Annotation Predictors with Automatic Post-Editing in LLM Translation Evaluators* — COLING 2025, [aclanthology.org/2025.coling-main.374](https://aclanthology.org/2025.coling-main.374/) ([PDF](https://aclanthology.org/2025.coling-main.374.pdf)), arXiv [2409.14335](https://arxiv.org/abs/2409.14335). Code: **<https://github.com/trotacodigos/Rubric-MQM>** (repo license **unverified**).

- **Three-module pipeline:** an MQM-style **error-analysis evaluator** (GEMBA-MQM-like) → an **automatic post-editor** that tries to repair each predicted error → a **quality verifier** that checks whether the repair actually improved quality. Errors whose repair does not help are judged **non-impactful and filtered out**. Using APE as a *filter on predicted error annotations* is the contribution.
- Evaluated on the **WMT22 metrics test set**; a row `MQM-APE | 43.5 | 41.7 | 41.7 | 38.9 | 41.5 (+7.4)` appears in [ar5iv](https://ar5iv.labs.arxiv.org/html/2409.14335), i.e. **+7.4 average gain** over its baseline — **column semantics and baseline identity unverified**.
- Selling point: **works across open-weight LLMs**, not just proprietary ones. **The exact model list (Llama / Qwen / Mistral / Gemma / Tower checkpoints and sizes) is UNVERIFIED** — read §4 / Appendix.
- Precursor idea: *Guiding Large Language Models to Post-Edit Machine Translation with Error Annotations*, arXiv [2404.07851](https://arxiv.org/abs/2404.07851).

## B.5 Open-weights LLM judges usable offline

**Headline: the Unbabel Tower family is NOT commercially usable.**

| Judge | HF id / URL | License | Verification |
|---|---|---|---|
| TowerBase-7B-v0.1 | <https://huggingface.co/Unbabel/TowerBase-7B-v0.1> | **cc-by-nc-4.0** | ✅ CONFIRMED — frontmatter title at [resolve-cache README](https://huggingface.co/api/resolve-cache/models/Unbabel/TowerBase-7B-v0.1/7512cb2c27e3b7f0b92c9271c2a845a1365048c8/README.md?download=true) |
| TowerInstruct-7B-v0.1 | <https://huggingface.co/Unbabel/TowerInstruct-7B-v0.1> | **cc-by-nc-4.0** | ✅ CONFIRMED — [resolve-cache README](https://huggingface.co/api/resolve-cache/models/Unbabel/TowerInstruct-7B-v0.1/dd3bcdf0474bf1baf24bb594b5177f867230d2c1/README.md?download=true) |
| TowerInstruct-13B-v0.1 | <https://huggingface.co/Unbabel/TowerInstruct-13B-v0.1> | **cc-by-nc-4.0** | ✅ CONFIRMED via redistribution frontmatter ([LoneStriker exl2](https://huggingface.co/api/resolve-cache/models/LoneStriker/TowerInstruct-13B-v0.1-4.0bpw-h6-exl2/0c15cc6bfd1c26c774d4614863dbf621c1988b25/README.md?download=true)) |
| TowerInstruct-7B-v0.2 / Mistral-7B-v0.2 | <https://huggingface.co/Unbabel/TowerInstruct-7B-v0.2> | **unverified** (family is NC) | ❌ |
| Tower+ 2B / 9B / 72B | <https://huggingface.co/Unbabel/Tower-Plus-9B> | reported **CC BY-NC-SA 4.0** | ⚠️ secondary only — a mirror states *"a 'fork' of Unbabel/Tower-Plus-9B licensed under CC BY NC SA 4.0"* (<https://huggingface.co/pinzhenchen/Unbabel_Tower-Plus-9B>). Bases CONFIRMED: `google/gemma-2-2B` and `google/gemma-2-9b` |
| xTower13B | <https://huggingface.co/sardinelab/xTower13B> | **cc-by-nc-4.0** | ✅ CONFIRMED — [raw README](https://huggingface.co/sardinelab/xTower13B/raw/78536b89be8ed335d17788656711cab31cee2e4e/README.md) title `license: cc-by-nc-4.0` |
| Prometheus 2 (7B / 8x7B) | <https://huggingface.co/prometheus-eval/prometheus-7b-v2.0> | **unverified** (widely said Apache-2.0) | ❌ — do **not** print Apache-2.0 until checked |
| **M-Prometheus 3B / 7B / 14B** | <https://huggingface.co/Unbabel/M-Prometheus-7B> ([collection](https://huggingface.co/collections/Unbabel/m-prometheus)) | **unverified** | ❌ — Qwen2.5-derived (upstream Apache-2.0) but Unbabel's own terms unknown |
| CompassJudger-2-7B-Instruct | <https://huggingface.co/opencompass/CompassJudger-2-7B-Instruct> | **apache-2.0** | ✅ CONFIRMED via indexed README title |
| ThinMQM | <https://github.com/NLP2CT/ThinMQM> | **unverified** | ❌ |

Papers: Tower [arXiv 2402.17733](https://huggingface.co/papers/2402.17733) / [COLM 2024](https://openreview.net/pdf?id=EHPns3hVkj) · Tower+ [arXiv 2506.17080](https://huggingface.co/papers/2506.17080) · xTower [arXiv 2406.19482](https://arxiv.org/abs/2406.19482) · Prometheus 2 [arXiv 2405.01535](https://arxiv.org/abs/2405.01535) · **M-Prometheus: A Suite of Open Multilingual LLM Judges** [arXiv 2504.04953](https://arxiv.org/abs/2504.04953).

**CPU feasibility:** GGUF conversions exist for the 2B–13B tier, so llama.cpp CPU inference is practical: [prometheus-7b-v2.0-GGUF (official)](https://huggingface.co/prometheus-eval/prometheus-7b-v2.0-GGUF), [TowerInstruct-7B-v0.2-GGUF](https://huggingface.co/cstr/TowerInstruct-7B-v0.2-GGUF), [xTower13B-gguf](https://huggingface.co/RichardErkhov/sardinelab_-_xTower13B-gguf). **The NC license follows the weights into the GGUF.** Expect seconds per segment; feasible overnight for a few hundred segments, not a CI metric. **No source benchmarks judge-quality degradation under quantization** — an open question.

**Not an MT judge:** CroissantLLM ([arXiv 2402.00786](https://arxiv.org/abs/2402.00786), ~1.3B) is a bilingual FR-EN base model, far below the size threshold where LLM judging works at all. License **unverified** (commonly reported MIT).

**Caution to cite:** *What do Large Language Models Need for Machine Translation Evaluation?* (EMNLP 2024, [arXiv 2410.03278](https://ar5iv.org/html/2410.03278)) — CONFIRMED verbatim: *"Our experiments with prompting LLMs for translation evaluation reveal that these models are often inconsistent in generating num[eric scores]…"*. That instability is the core reason GEMBA-MQM V2 moved to ten-sample aggregation.

---

# C) Surface metrics

## C.1 sacreBLEU

- Repo <https://github.com/mjpost/sacrebleu> · PyPI <https://pypi.org/project/sacrebleu/> · [CHANGELOG](https://github.com/mjpost/sacrebleu/blob/master/CHANGELOG.md)
- **Versions in the 2024–2026 window:** 2.4.0 / 2.4.2 / [2.4.3](https://pypi.org/project/sacrebleu/2.4.3/), 2.5.1, and **2.6.0** as newest indexed release ([deps.dev](https://deps.dev/pypi/sacrebleu/2.6.0), [socket.dev](https://socket.dev/pypi/package/sacrebleu/versions/2.6.0/tar-gz), [Snyk](https://security.snyk.io/package/pip/sacrebleu/2.6.0)). Release date of 2.6.0: **unverified**.
- **License: Apache-2.0** ([LICENSE.md](https://github.com/mjpost/sacrebleu/blob/master/LICENSE.md)). The literal file text was not fetchable here but is quoted verbatim by third parties and reflected in the Apache-2.0 headers of derived wrappers ([HF datasets sacrebleu.py](https://raw.githubusercontent.com/huggingface/datasets/2.0.0/metrics/sacrebleu/sacrebleu.py)). **Permissive — safe commercially.**

## C.2 Signatures, and why they matter

Example: `BLEU|nrefs:1|case:mixed|eff:no|tok:13a|smooth:exp|version:2.4.2`
(older releases used `+` separators, e.g. `BLEU+nrefs:1+case:mixed+eff:no+tok:none+smooth:exp+version:2.2.0`).

| Field | Meaning |
|---|---|
| `nrefs` | number of references used |
| `case` | `mixed` (default) or `lc` (lowercased) |
| `eff` | effective reference length / effective order correction |
| `tok` | tokenizer (`13a`, `intl`, `zh`, `ja-mecab`, `flores200`, …) |
| `smooth` | n-gram smoothing (`exp` default, `add-k`, `floor`, `none`) |
| `version` | the sacreBLEU version that produced the number |

chrF / chrF++ signature: `nrefs:1|case:mixed|eff:yes|nc:6|nw:2|space:no|version:2.3.1` — `nc` = character order, `nw` = word order, `space` = whether spaces count as tokens.

**Why signatures matter:** BLEU moves by several points purely from tokenization, casing, reference count and smoothing. Two papers both reporting "BLEU 30.2" may not be comparable at all. The signature makes every one of those decisions explicit and machine-checkable. This is the entire argument of **Matt Post, *A Call for Clarity in Reporting BLEU Scores*, WMT 2018** — [aclanthology.org/W18-6319](https://aclanthology.org/W18-6319/), arXiv [1804.08771](https://arxiv.org/abs/1804.08771). **Paste the signature verbatim into the report.**

## C.3 Tokenizers — and the correct one for Chinese

Available for BLEU: `13a` (default, mimics Moses `mteval-v13a`), `intl`, **`zh`**, **`ja-mecab`**, `ko-mecab`, `char`, `none`, `flores101`, `flores200`, plus **spBLEU-1K** added in 2.6.0. See the [README](https://github.com/mjpost/sacrebleu) and [DeepWiki: language-specific tokenizers](https://deepwiki.com/mjpost/sacrebleu/6.1-language-specific-tokenizers).

- **Chinese → `--tokenize zh`.** It **splits runs of CJK characters into individual characters** (and splits CJK punctuation / compatibility forms) instead of doing word segmentation — the point being to remove any dependence on which Chinese segmenter you used. Character-range handling is visible in the tokenizer source (CJK ranges incl. `\ufe30`–`\ufe4f`).
- **Japanese → `--tokenize ja-mecab`** (MeCab). Korean → `ko-mecab`. Spanish → default `13a` (or `intl`).
- **There is no auto-detection.** Scoring en→zh with the default `13a` measures whitespace, not translation quality. This is the single most common Chinese-benchmark error.

```bash
sacrebleu ref.zh -i hyp.zh -m bleu chrf --chrf-word-order 2 --tokenize zh
sacrebleu ref.ja -i hyp.ja -m bleu chrf --chrf-word-order 2 --tokenize ja-mecab
sacrebleu ref.es -i hyp.es -m bleu chrf --chrf-word-order 2 --tokenize 13a
```
Python: `sacrebleu.corpus_bleu(hyps, [refs], tokenize='zh')` / `BLEU(tokenize='zh')`.

## C.4 chrF and chrF++

- chrF: Popović, WMT 2015 — [aclanthology.org/W15-3049](https://aclanthology.org/W15-3049/) ([PDF](https://www.cs.cmu.edu/~ark/EMNLP-2015/proceedings/WMT/pdf/WMT49.pdf)). chrF++: Popović, WMT 2017 — [aclanthology.org/W17-4770](https://aclanthology.org/W17-4770/) (**arXiv id unverified**). Parameter study: [aclanthology.org/W16-2341](https://aclanthology.org/W16-2341/).
- chrF = β-weighted F-score over **character n-grams**; **chrF++** adds **word n-grams** on top.
- sacreBLEU defaults: **character order 6** (`nc:6`), **word order 0 for chrF / 2 for chrF++** (`nw:0` / `nw:2`), **β = 2** (recall-weighted).
- **Why it beats BLEU for our language set:** character n-grams are insensitive to morphology and to segmentation/whitespace conventions. For **Chinese and Japanese** chrF needs **no segmentation at all** (`space:no` by default). For **Spanish** it is more robust to inflection than BLEU. This makes chrF++ the best *cheap* metric across en↔zh-CN, en↔ja and en↔es simultaneously.

## C.5 spBLEU

- BLEU computed after tokenizing with the **FLORES SentencePiece model**; introduced with FLORES-101/200 in NLLB — [arXiv:2207.04672](https://arxiv.org/abs/2207.04672), [FLORES-200 README](https://github.com/facebookresearch/flores/blob/main/flores200/README.md). Added to sacreBLEU in [PR #168 / commit 65a8a9e](https://github.com/mjpost/sacrebleu/commit/65a8a9eeccd8c0c7875e875e12edf10db33ab0ba).
- Use `--tokenize flores200` (or `flores101`). sacreBLEU 2.6.0 adds a successor **spBLEU-1K**.
- **Caveats:** the SPM model is **downloaded on first use** — pre-fetch it for air-gapped runs. spBLEU is **not comparable** to `13a` or `zh` BLEU (different subword vocabulary). Only worth reporting if you need FLORES-style cross-language comparability.

## C.6 TER

- Snover et al., AMTA 2006 — [aclanthology.org/2006.amta-papers.25](https://aclanthology.org/2006.amta-papers.25/).
- Minimum edit operations (insert / delete / substitute **+ phrase shifts**) normalized by reference length; **lower is better**. Unlike BLEU it explicitly models reordering.
- sacreBLEU: `sacrebleu -m ter` (Python `corpus_ter` / `sentence_ter`), with options including `--ter-normalize`, case/punctuation handling and Asian-character handling. **Exact TER signature field names: unverified.**
- For en↔zh TER inherits BLEU's segmentation problems and adds little over chrF. **Optional at best.**

## C.7 BLEU on Chinese

Word-level BLEU on Chinese is **segmentation-dependent** — different segmenters give different scores for identical output. Classic reference: Denoual & Lepage, *BLEU in Characters: Towards Automatic MT Evaluation in Languages without Word Delimiters* (IJCNLP 2005) — [PDF](https://mt-archive.net/IJCNLP-2005-Denoual.pdf). Mitigations: sacreBLEU `tok:zh` (character splitting) or, better, chrF.

**Counterpoint worth citing** (BLEU is not worthless): *Sentence-level Aggregation of Lexical Metrics Correlates Stronger with Human Judgements than Corpus-level Aggregation* (AAAI 2025), [arXiv:2407.12832](http://arxiv.org/pdf/2407.12832) — if you do report BLEU/chrF, **aggregate at the segment level**, not corpus level.

---

# D) Practical guidance

## D.1 Master table

| Metric | Type (ref / QE) | Model size | License | HF id / package | CPU-runnable | Notes |
|---|---|---|---|---|---|---|
| **chrF++** | ref (surface) | n/a | **Apache-2.0** (sacrebleu) | `sacrebleu` | ✅ instant | Best cheap metric for zh/ja/es; no segmentation needed; report signature |
| **BLEU** | ref (surface) | n/a | **Apache-2.0** (sacrebleu) | `sacrebleu` | ✅ instant | Secondary only. **Must** use `tok:zh` / `ja-mecab`. WMT22 title: "Stop Using BLEU" |
| **TER** | ref (surface) | n/a | **Apache-2.0** (sacrebleu) | `sacrebleu -m ter` | ✅ instant | Optional; edit-distance view; segmentation-sensitive on zh |
| **spBLEU** | ref (surface) | SPM model | **Apache-2.0** (sacrebleu) | `--tokenize flores200` | ✅ (one-time SPM download) | Only for FLORES-style comparability |
| **BERTScore** | ref | roberta-large 355M / mBERT 178M | **MIT** (text unverified) | `bert-score` | ✅ | Untrained baseline; below trained metrics |
| **COMET-22** | **ref** | XLM-R Large **~565M** | **apache-2.0** ✅CONFIRMED | `Unbabel/wmt22-comet-da` | ✅ ~4–6 GB RAM | ⭐ **Primary recommendation.** Ungated + permissive |
| **COMET-20** | ref | XLM-R Large ~565M | **unverified** | `Unbabel/wmt20-comet-da` | ✅ | Ungated; superseded; different scale |
| **COMET-20-QE** | **QE** | ~565M | **unverified** | `Unbabel/wmt20-comet-qe-da` | ✅ | Ungated; obsolete |
| **COMETINHO** | ref | MiniLM-class (small) | **unverified** | `Unbabel/eamt22-cometinho-da` | ✅ very fast | Ungated; distilled; CPU fallback |
| **CometKiwi-22** | **QE** | InfoXLM Large **~565M** | **cc-by-nc-sa-4.0** ✅CONFIRMED | `Unbabel/wmt22-cometkiwi-da` | ✅ | **GATED**; **non-commercial** |
| **CometKiwi-23-XL** | **QE** | XLM-R XL **~3.5B** | **unverified** (indirect NC) | `Unbabel/wmt23-cometkiwi-da-xl` | ❌ | **GATED** |
| **CometKiwi-23-XXL** | **QE** | XLM-R XXL **~10.7B** | **unverified** (indirect NC) | `Unbabel/wmt23-cometkiwi-da-xxl` | ❌ | **GATED** |
| **XCOMET-XL** | ref (+error spans) | XLM-R XL **3.5B** | **unverified** | `Unbabel/XCOMET-XL` | ❌ | **GATED** (contact info); #1 at WMT23 as Ensemble |
| **XCOMET-XXL** | ref (+error spans) | XLM-R XXL **~10.7B** | **unverified** | `Unbabel/XCOMET-XXL` | ❌ | **GATED** (contact info) |
| **xCOMET-lite** | ref (+spans) | ~278M (**unverified**) | **unverified** | community `myyycroft/XCOMET-lite` | ✅ | No official release found; likely NC-derived |
| **UniTE (wmt22-unite-da)** | ref + QE modes | ~XLM-R Large (unverified) | **unverified** | `Unbabel/wmt22-unite-da` | ✅ | **GATED**; superseded |
| **MetricX-23** | ref | mT5 ~1.2B / ~3.7B / ~13B | **apache-2.0** (✅ XL confirmed) | `google/metricx-23-{large,xl,xxl}-v2p0` | large ⚠️ / XL,XXL ❌ | Ungated; **0–25, lower = better** |
| **MetricX-23-QE** | **QE** | same sizes | apache-2.0 family (per-card unverified) | `google/metricx-23-qe-*-v2p0` | large ⚠️ | Ungated |
| **MetricX-24-hybrid** | **ref + QE in one model** | mT5 large / XL / XXL | **apache-2.0** ✅CONFIRMED (large, xxl) | `google/metricx-24-hybrid-{large,xl,xxl}-v2p6` | large ⚠️ (bf16 helps) | ⭐ Best permissive ref+QE combo |
| **MetricX-25** | ref + QE (unified hybrid) | unknown | **unverified** | **no public weights found** | — | Paper only ([2025.wmt-1.70](https://aclanthology.org/2025.wmt-1.70/)) |
| **BLEURT-20** | ref | RemBERT-based (~580M, unverified) | Apache-2.0 (text unverified) | `lucadiliello/BLEURT-20` (PyTorch port) | ✅ slow | TF-only officially; superseded |
| **YiSi-1 / YiSi-2** | ref / **QE** | mBERT-based | **unverified** | NRC distribution | ✅ | Dormant since ~2020 |
| **GEMBA / GEMBA-MQM** | ref **or** QE (LLM) | GPT-3.5+ / **GPT-4** | code+prompts **CC BY-SA 4.0** ✅CONFIRMED | [MicrosoftTranslator/GEMBA](https://github.com/MicrosoftTranslator/GEMBA) | ❌ API only | System-level strong, segment-level coarse; §5 "black box" caveat |
| **GEMBA-MQM V2** | ref/QE (LLM) | GPT-class | **unverified** | [2025.wmt-1.67](https://aclanthology.org/2025.wmt-1.67/) | ❌ | Ten-sample aggregation |
| **AutoMQM** | ref (LLM, spans) | PaLM-2 Unicorn | **unverified** | [2023.wmt-1.100](https://aclanthology.org/2023.wmt-1.100/) | ❌ | Error-span ICL beats score-only |
| **MQM-APE** | ref/QE (LLM, spans) | open-weight LLMs | **unverified** | [Rubric-MQM](https://github.com/trotacodigos/Rubric-MQM) | ⚠️ | APE-filters non-impactful errors |
| **GemSpanEval** | ref (LLM, spans) | Gemma-based (size unverified) | **unverified** | [2025.wmt-1.70](https://aclanthology.org/2025.wmt-1.70/) | ⚠️ | ⭐ Open-weight generative span evaluator |
| **M-Prometheus 3B/7B/14B** | LLM judge | 3B / 7B / 14B (Qwen2.5) | **unverified** | `Unbabel/M-Prometheus-7B` | ⚠️ | Open multilingual judge (2025) |
| **Prometheus 2 7B / 8x7B** | LLM judge | 7B / 8x7B | **unverified** | `prometheus-eval/prometheus-7b-v2.0` | ⚠️ GGUF exists | English-centric general judge |
| **CompassJudger-2-7B** | LLM judge | 7B | **apache-2.0** ✅CONFIRMED | `opencompass/CompassJudger-2-7B-Instruct` | ⚠️ 4-bit | General-purpose judge |
| **TowerInstruct 7B/13B** | LLM (gen + judge) | 7B / 13B | **cc-by-nc-4.0** ✅CONFIRMED | `Unbabel/TowerInstruct-13B-v0.1` | ⚠️ GGUF | **Non-commercial** |
| **Tower+ 2B/9B/72B** | LLM | 2B / 9B / 72B | **cc-by-nc-sa-4.0** (secondary evidence) | `Unbabel/Tower-Plus-9B` | ⚠️ | **Non-commercial + ShareAlike** |
| **xTower13B** | LLM error explainer | 13B | **cc-by-nc-4.0** ✅CONFIRMED | `sardinelab/xTower13B` | ⚠️ GGUF | **Non-commercial** |

Legend: ✅ practical on CPU · ⚠️ possible but slow / needs quantization · ❌ not practical on CPU.

## D.2 Recommended offline-CPU, permissive-license stack

For a few hundred segments, en↔zh-CN plus ja and es, **runnable air-gapped on CPU, permissive licenses only**:

**Tier 1 — must report (all Apache-2.0 / MIT, all ungated, all CPU):**
1. **COMET-22** — `Unbabel/wmt22-comet-da` (**apache-2.0 CONFIRMED**, ungated). Report the **mean segment score plus a bootstrap CI**. Headline quality number.
2. **chrF++** — sacreBLEU (**Apache-2.0**), with the **full signature**.
3. **BLEU** — sacreBLEU, `--tokenize zh` for Chinese, `ja-mecab` for Japanese, `13a` for Spanish, **with signature**, explicitly labelled legacy/secondary.
4. **Paired bootstrap significance** on every pairwise comparison (sacreBLEU exposes paired bootstrap / approximate-randomization tests against a baseline; **verify the exact flag spellings with `sacrebleu --help` — the literal `--paired-bs` / `--paired-ar` spellings and default resample counts are unverified here**). Cite **Koehn 2004** ([W04-3250](https://aclanthology.org/W04-3250/)), whose analysis is parameterised over test sets of **100 / 300 / 600 / 3000 sentences** — a few hundred segments is exactly the regime he studies, and it is small.
   **Interpret the delta, do not assert it.** Use **MT-Thresholds** ([repo](https://github.com/kocmitom/MT-Thresholds), [PyPI](https://pypi.org/project/mt-thresholds/)) from *Navigating the Metrics Maze* ([2024.acl-long.110](https://aclanthology.org/2024.acl-long.110/)). **CONFIRMED verbatim anchor:** *"an improvement of 1.06 BLEU has the same estimated accuracy (65%) as the 0.24 CometKiwi"* ([ar5iv](https://ar5iv.labs.arxiv.org/html/2401.06760#2)) — i.e. a ~1 BLEU or ~0.24 CometKiwi gap buys only ~65% agreement with human system-level preference. That paper also explicitly studies **test-set size as a factor in delta reliability**. **There is no credible "magic N" of segments** — I found no 2024–2026 paper giving one. Report the CI, convert the delta, and say what accuracy it implies.
5. **Control rows:** empty string, copy-source, and wrong-language-variant outputs, following [MSLC25](https://aclanthology.org/2025.wmt-1.69/). Any metric that ranks these above a real system is disqualified for your use case.

**Tier 2 — strongly recommended, still Apache-2.0 and offline:**
6. **MetricX-24-hybrid-large** — `google/metricx-24-hybrid-large-v2p6` (**apache-2.0 CONFIRMED**, ungated). Gives an **independently trained second reference-based number AND a reference-free number from one checkpoint**. Remember **0–25, lower is better** — state the direction explicitly.
7. **BERTScore** (MIT) as a cheap sanity check; low weight.
8. **COMETINHO** if you need a fast smoke-test metric in CI.

**Explicitly NOT in the default stack:** CometKiwi (CC-BY-NC-SA-4.0 + gated), XCOMET-XL/XXL (gated, license unverified, not CPU-feasible), TowerInstruct / xTower / Tower+ (CC-BY-NC), any GPT-4 judge (not offline, not reproducible).

**Metadata to publish with every number — this is what makes a small benchmark credible:**
- metric name + **exact checkpoint id + revision hash** + **library version** (e.g. `unbabel-comet 2.2.x`, `sacrebleu 2.4.3`);
- the **sacreBLEU signature verbatim** for every surface metric, and a **sacreCOMET signature** ([sacreCOMET](https://github.com/PinzhenChen/sacreCOMET)) for every COMET-family score;
- **segment count**, language pair and direction, domain, how references were produced (human? post-edited? single or multiple?);
- **significance test + CI**, and the score **direction** for each metric;
- an explicit statement that scores are **not comparable across language pairs** or across COMET/MetricX versions;
- the control-row results (empty / copy-source / shuffled / wrong-variant).

*Why this matters:* Marie, Fujita & Rubino, ***Scientific Credibility of Machine Translation Research: A Meta-Evaluation of 769 Papers*** (ACL 2021) — [2021.acl-long.566](https://aclanthology.org/2021.acl-long.566/) — is the standard citation for how routinely MT papers omit exactly these items. And WMT25's General MT findings are titled ***"Time to Stop Evaluating on Easy Test Sets"*** ([2025.wmt-1.1](https://aclanthology.org/2025.wmt-1.1/)) — state whether your test set is easy.

## D.3 What to add with GPU or API access

- **GPU:** `google/metricx-24-hybrid-xl-v2p6` (Apache-2.0) and/or **XCOMET-XL** for **error spans with severities** — the biggest qualitative upgrade, because it tells you *what* is wrong rather than just how much. (XCOMET is gated with an unverified license → research use; clear it before any commercial claim.)
- **GPU + QE:** `Unbabel/wmt23-cometkiwi-da-xl` — but gated and NC-indicative.
- **API:** **GEMBA-MQM** with a **pinned GPT-4 snapshot**, reported as a secondary, dated, non-reproducible signal with model version and date in the table — and honour the authors' §5 caveat by not using it as the system-ranking criterion. Consider **GEMBA-MQM V2** (ten-judgment aggregation).
- **Either:** a **small human MQM spot-check** (even 50 segments × 2 annotators). Every WMT findings paper is a meta-evaluation *against human MQM*; with no human anchor a benchmark is asserting, not measuring. In 2026 this is the main thing separating a credible benchmark from a metric dump.

## D.4 Known issues — COMET on Chinese, and reference-free QE

### COMET pitfalls
Primary reference: ***Pitfalls and Outlooks in Using COMET*** (Zouhar et al., WMT 2024) — [aclanthology.org/2024.wmt-1.121](https://aclanthology.org/2024.wmt-1.121/), arXiv [2408.15366](https://arxiv.org/abs/2408.15366).
- **Version/checkpoint confusion.** "COMET" is not one metric. COMET-20, COMET-22, CometKiwi and XCOMET have different scales and behaviours; a paper that just says "COMET" is unreproducible. **CONFIRMED verbatim:** *"In addition, out of the almost 1000 papers running COMET in their evaluation, most only cite the first COMET paper (Rei et al…"* ([arXiv HTML](https://arxiv.org/html/2408.15366v3#bib.bib51#4)). The authors' remedy is a signature tool analogous to sacreBLEU's: **sacreCOMET** — <https://github.com/PinzhenChen/sacreCOMET>, PyPI `sacrecomet`. **Emit a sacreCOMET signature alongside your sacreBLEU signature.** Version instability is real: see the COMET issue *"[CRITICAL BUG] Inconsistent scores of XCOMET between v2.2.4 and v2.2.5"* — <https://github.com/Unbabel/COMET/issues/244>.
- **Empty and degenerate translations can score surprisingly well.** **CONFIRMED verbatim:** *"We then count the number of empty lines that score better than a translation from Online-A in Table 4. We observe roughly 0.25% …"* ([arXiv v2](http://web3.arxiv.org/pdf/2408.15366v2#5#2)). The degeneracy ladder is worse than it sounds — **CONFIRMED verbatim:** *"We observe that sentence-shuffled hypotheses attain comparable scores to empty ones, but word-shuffled hypotheses have the lowes…"* ([ar5iv](https://ar5iv.labs.arxiv.org/html/2408.15366#2#2)). In other words **a well-formed but completely mismatched sentence scores about as well as an empty string**, and only word-salad scores lower. The paper also states the desideratum outright: *"Robustness: Metrics should have the correct behaviour even in corner cases, be it empty output or incorrect language"*. Corroborated by the **MSLC** line at WMT ([MSLC24](https://aclanthology.org/2024.wmt-1.34/), [MSLC25](https://aclanthology.org/2025.wmt-1.69/)). Per-language-pair breakdown of Table 4 (i.e. whether En→Zh is an outlier): **unverified**.
- **Sensitivity to sentence segmentation.** The paper contains a section with exactly that heading ([WMT24 proceedings chunk](https://aclanthology.org/anthology-files/anthology-files/pdf/wmt/2024.wmt-1.pdf#422#365)); magnitude **unverified**. Directly relevant to Chinese, where splitting on 。！？ versus commas changes segment boundaries. **Sentence-split identically for every system and document the splitter.**
- **Scores are not comparable across language pairs.** COMET 0.86 on en–es and 0.86 on en–zh do not mean the same thing. Operational proof: **RankedCOMET** (WMT25 QE, top-5 finish) exists precisely to **rank-normalize COMET per language pair** — [2025.wmt-1.74](https://aclanthology.org/2025.wmt-1.74/), described in the findings as *"based on the pre-trained Unbabel/wmt22-comet-da model, deployed in a…"* ([chunk](https://aclanthology.org/2025.wmt-1.pdf#435#154)). See also the COMET [FAQ](https://unbabel.github.io/COMET/html/faqs.html) on score interpretation.
- **Chinese specifically — read this one carefully, it is subtler than "COMET is bad at Chinese".** **CONFIRMED verbatim caption:** *"Figure 2: Setup of an experiment with bottom 75% of En→Zh scores which creates a bias in COMET_22^DA…"* ([WMT24 proceedings chunk](https://aclanthology.org/anthology-files/anthology-files/pdf/wmt/2024.wmt-1.pdf#422#364)), and the body sentence: *"As expected, for both En→De and En→Zh, training on the top or bottom-scoring data would lead to increased or decreased COMET sc…"* ([arXiv v1](http://arxiv.org/pdf/2408.15366v1#5#3)).
  What this actually establishes is **circularity/self-reinforcement**: if you use COMET to filter or select data and then evaluate with the same COMET, the measured gain is partly an artefact — demonstrated on **both En→De and En→Zh**. The exact magnitude, and whether Zh is *worse* than De, are **unverified**.
  **Rule that follows: never use the same metric to filter, rerank or select, and to evaluate.** Corroborating quantified work: *Adding Chocolate to Mint: Mitigating Metric Interference in Machine Translation* ([TACL](https://transacl.org/index.php/tacl/article/view/8051), [ar5iv](https://ar5iv.labs.arxiv.org/html/2503.08327)) and *Mitigating Metric Bias in Minimum Bayes Risk Decoding* ([2024.wmt-1.109](https://aclanthology.org/2024.wmt-1.109.pdf), arXiv [2411.03524](https://arxiv.org/abs/2411.03524)).
  Practical consequence for us: **on en→zh, small COMET deltas are not trustworthy.** Insist on significance testing and always pair COMET with chrF and a second neural metric (MetricX).
- Additional Chinese-side hygiene: XLM-R's SentencePiece treatment of full-width punctuation, and zh-CN vs zh-TW variants, are **not** controlled by the metric. Normalize punctuation and script/variant before scoring — and say that you did. (MSLC25's title explicitly covers **"Language Variants"**.)
- **Honest caveat — do not repeat a popular claim that has no source.** I found **no WMT statement, and no paper, asserting that metrics correlate worse on Chinese than on other pairs.** That claim is **unverified and should be treated as unsupported until shown otherwise.** The closest sourced WMT25 statement is its title: *"Linguistic Diversity is Challenging"*. WMT23 MQM did cover **zh→en** ([findings chunk](https://aclanthology.org/anthology-files/anthology-files/pdf/wmt/2023.wmt-1.pdf#302#168); corroborated by [arXiv 2411.15387](https://ar5iv.labs.arxiv.org/html/2411.15387#2)). Likewise, **no source was found** claiming XLM-R's SentencePiece handling of Chinese degrades COMET — that is my hygiene suggestion, not a documented finding.
- **What the Chinese-specific literature *does* document** is failure on **multiword expressions, idioms/proverbs, named entities, culturally-loaded content and classical Chinese** — not tokenizer artefacts:
  - *Benchmarking the Performance of Machine Translation Evaluation Metrics with Chinese Multiword Expressions* (LREC-COLING 2024) — [2024.lrec-main.198](https://aclanthology.org/2024.lrec-main.198/) — the closest thing to a "metrics are unreliable on Chinese" study; its conclusions are **unverified** here.
  - *A Deep Analysis of the Impact of Multiword Expressions and Named Entities on Chinese-English Machine Translations* — [2024.findings-emnlp.357](https://aclanthology.org/2024.findings-emnlp.357/)
  - *MQM-Chat: Multidimensional Quality Metrics for Chat Translation* (zh/ja chat MQM) — arXiv [2408.16390](https://arxiv.org/abs/2408.16390)
  - *MITRA-zh-eval* (Buddhist Chinese) — [2025.nlp4dh-1.12](https://aclanthology.org/2025.nlp4dh-1.12/) · *HardMTBench* zh-en — arXiv [2605.28315](https://arxiv.org/abs/2605.28315) · *Benchmarking MT on Chinese Social Media Texts* — arXiv [2601.22931](https://arxiv.org/abs/2601.22931)
  - *RUBRIC-MQM: Span-Level LLM-as-judge in Machine Translation* — [2025.acl-industry.12](https://aclanthology.org/2025.acl-industry.12/)
  **→ For a zh benchmark, add targeted challenge slices for MWEs/idioms, named entities, numbers and culturally-loaded terms.**

### Reference-free QE issues
1. **WMT25's headline is literally "References Still Help"** ([2025.wmt-1.24](https://aclanthology.org/2025.wmt-1.24/)). QE has not caught up. Even Google's own hybrid MetricX-25 was *"slightly outperformed by the reference-based variant"* ([2510.24707](https://export.arxiv.org/pdf/2510.24707#4#2)). **Run QE in addition to, not instead of, reference-based scoring.**
2. **Sentinel metrics expose meta-evaluation fragility.** *Guardians of the Machine Translation Meta-Evaluation: Sentinel Metrics Fall In!* — [2024.acl-long.856](https://aclanthology.org/2024.acl-long.856/), arXiv [2408.13831](https://arxiv.org/abs/2408.13831): *"we incorporate three sentinel metrics into the current meta-evaluation framework and re-comp[ute]…"*. **Hard corroboration inside WMT24 itself:** the degenerate source-only `sentinel-src-mqm` lands in the same score band as the genuine QE metric `XLSimMqm` in the reference-free results block ([chunk](https://aclanthology.org/anthology-files/anthology-files/pdf/wmt/2024.wmt-1.pdf#422#145)). Part of QE's apparent correlation comes from **source-side/domain artefacts**, not from judging the translation.
3. **Length bias.** *Penalizing Length: Uncovering Systematic Bias in Quality Estimation Metrics* — arXiv [2510.22028](https://arxiv.org/abs/2510.22028) ([ar5iv](https://ar5iv.labs.arxiv.org/html/2510.22028)). Since zh↔en changes length dramatically, this bias is directly relevant here.
4. **Fluent-but-wrong output, and insensitivity to critical errors.** QE relies on cross-lingual representations alone and is comparatively weak on omission / addition / hallucination and on critical errors. The canonical demonstration is **Amrhein & Sennrich, *Identifying Weaknesses in Machine Translation Metrics Through Minimum Bayes Risk Decoding: A Case Study for COMET*** (AACL 2022) — [2022.aacl-main.83](https://aclanthology.org/2022.aacl-main.83/), [ar5iv](https://ar5iv.labs.arxiv.org/html/2202.05148), [code](https://github.com/ZurichNLP/mbr-sensitivity); its results table is organized by **"Numbers | Named Entities"**, i.e. exactly the critical-error classes that matter commercially. Also: **ACES** challenge sets ([WMT22](https://aclanthology.org/2022.wmt-1.44/), [WMT23](https://ar5iv.labs.arxiv.org/html/2311.01153), journal version [2025.cl-1.4](https://aclanthology.org/2025.cl-1.4/), [code](https://github.com/EdinburghNLP/ACES)) — *"Surface-level metrics are often too reliant on overlap with the reference"*. Hallucination-specific: [2023.eacl-main.75](https://aclanthology.org/2023.eacl-main.75/), [arXiv 2303.16104](https://arxiv.org/abs/2303.16104), [2023.acl-long.770](https://aclanthology.org/2023.acl-long.770/). Adequacy-vs-fluency tradeoff (2025): [2025.wmt-1.16](https://aclanthology.org/2025.wmt-1.16/).
   **→ Add deterministic checks** — number, entity, negation and unit preservation. Free, deterministic, and they catch precisely what QE misses.
   *Nuance worth keeping honest:* ACES also reports that **reference-based metrics degrade more steeply than reference-free ones** on some challenge phenomena, so "QE is simply worse" is too crude.
5. **Do not use QE as a training/reranking reward casually.** The foundational result is **Deutsch, Dror & Roth, *On the Limitations of Reference-Free Evaluations of Generated Text*** (EMNLP 2022) — [2022.emnlp-main.753](https://aclanthology.org/2022.emnlp-main.753/), arXiv [2210.12563](https://ar5iv.labs.arxiv.org/html/2210.12563): reference-free metrics are biased and should not be used to evaluate outputs optimized against them. See also *Quality-Aware Decoding for NMT* (arXiv [2205.00978](https://arxiv.org/abs/2205.00978)) — systems *"learn to exploit \"pathologies\" in these metrics rather than improving translation quality"*; *Improving MT with Human Feedback: QE as a Reward Model* ([2024.naacl-long.451](https://aclanthology.org/2024.naacl-long.451/)); and *Reward Models are Metrics in a Trench Coat* (arXiv [2510.03231](https://arxiv.org/abs/2510.03231)), the cleanest 2025 statement that MT metrics and reward models are the same object and inherit each other's hacking failure modes.
6. **Licensing is itself a QE problem.** The best-known QE metric, CometKiwi, is **CC-BY-NC-SA-4.0 and gated**. For a permissive stack use **MetricX-24-hybrid in QE mode (Apache-2.0)** instead.

---

# E) Source index

**COMET** — [repo](https://github.com/Unbabel/COMET) · [MODELS.md](https://github.com/Unbabel/COMET/blob/master/MODELS.md) · [LICENSE.models.md](https://github.com/Unbabel/COMET/blob/master/LICENSE.models.md) · [PyPI](https://pypi.org/project/unbabel-comet/) · [docs](https://unbabel.github.io/COMET/html/models.html) · [wmt22-comet-da](https://huggingface.co/Unbabel/wmt22-comet-da) (license CONFIRMED: [raw README](https://huggingface.co/Unbabel/wmt22-comet-da/blob/1358d906012962aca32f48913d55e967d250adf1/README.md?code=true)) · [wmt20-comet-da](https://huggingface.co/Unbabel/wmt20-comet-da) · [wmt22-cometkiwi-da](https://huggingface.co/Unbabel/wmt22-cometkiwi-da) (license CONFIRMED via [mirror](https://huggingface.co/ben-xl8/wmt22-cometkiwi-da/raw/6c5396ae93eb6fc0bbf73a1964e6e69272090b3d/README.md), [second mirror](https://huggingface.co/Supervache/wmt22-cometkiwi-da-safeformat/raw/main/README.md)) · [wmt23-cometkiwi-da-xl](https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xl) · [wmt23-cometkiwi-da-xxl](https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xxl) · [XCOMET-XL](https://huggingface.co/Unbabel/XCOMET-XL) · [XCOMET-XXL](https://huggingface.co/Unbabel/XCOMET-XXL) · [eamt22-cometinho-da](https://huggingface.co/Unbabel/eamt22-cometinho-da) · [wmt22-unite-da](https://huggingface.co/Unbabel/wmt22-unite-da)
Papers: [COMET-22](https://aclanthology.org/2022.wmt-1.52/) · [CometKiwi](https://aclanthology.org/2022.wmt-1.60/) · [CometKiwi-XL/XXL](https://aclanthology.org/2023.wmt-1.62/) · [xCOMET TACL](https://aclanthology.org/2024.tacl-1.54/) / [arXiv 2310.10482](https://arxiv.org/abs/2310.10482) · [COMETINHO](https://aclanthology.org/2022.eamt-1.9/) · [xCOMET-lite](https://aclanthology.org/2024.emnlp-main.1223/) / [arXiv 2406.14553](https://arxiv.org/abs/2406.14553)

**MetricX** — [repo](https://github.com/google-research/metricx) · [metricx-24-hybrid-large](https://huggingface.co/google/metricx-24-hybrid-large-v2p6) · [metricx-24-hybrid-xl](https://huggingface.co/google/metricx-24-hybrid-xl-v2p6) · [metricx-24-hybrid-xxl](https://huggingface.co/google/metricx-24-hybrid-xxl-v2p6) · [metricx-23-xl](https://huggingface.co/google/metricx-23-xl-v2p0) · [metricx-23-qe-large](https://huggingface.co/google/metricx-23-qe-large-v2p0)
Papers: [MetricX-23](https://aclanthology.org/2023.wmt-1.63/) · [MetricX-24](https://aclanthology.org/2024.wmt-1.35/) / [arXiv 2410.03983](https://arxiv.org/abs/2410.03983) · [MetricX-25 + GemSpanEval](https://aclanthology.org/2025.wmt-1.70/) / [arXiv 2510.24707](https://arxiv.org/abs/2510.24707)

**WMT findings** — [WMT22 "Stop Using BLEU"](https://aclanthology.org/2022.wmt-1.2/) · [WMT23](https://aclanthology.org/2023.wmt-1.51/) · [WMT24](https://aclanthology.org/2024.wmt-1.2/) · [WMT25](https://aclanthology.org/2025.wmt-1.24/) · [WMT26 task](https://www2.statmt.org/wmt26/mteval-task.html) · [wmt25-mteval repo](https://github.com/wmt-conference/wmt25-mteval) · [To Ship or Not to Ship](https://arxiv.org/abs/2107.10821) · [Navigating the Metrics Maze](https://aclanthology.org/2024.acl-long.110/) / [MT-Thresholds](https://github.com/kocmitom/MT-Thresholds) · [Pitfalls and Outlooks in Using COMET](https://aclanthology.org/2024.wmt-1.121/) · [MSLC24](https://aclanthology.org/2024.wmt-1.34/) · [MSLC25](https://aclanthology.org/2025.wmt-1.69/) · [Sentinel metrics](https://aclanthology.org/2024.acl-long.856/)

**LLM judges** — [GEMBA EAMT23](https://aclanthology.org/2023.eamt-1.19/) / [arXiv 2302.14520](https://arxiv.org/abs/2302.14520) · [GEMBA-MQM](https://aclanthology.org/2023.wmt-1.64/) / [PDF](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.64.pdf) / [arXiv 2310.13988](https://arxiv.org/abs/2310.13988) · [GEMBA repo](https://github.com/MicrosoftTranslator/GEMBA) / [license commit](https://github.com/MicrosoftTranslator/GEMBA/commit/18671baee617b70d852dd7f2984172b23b49f8db) / [LICENSE.md](https://github.com/kocmitom/GEMBA/blob/main/LICENSE.md) · [GEMBA-MQM V2](https://aclanthology.org/2025.wmt-1.67/) · [BatchGEMBA](https://arxiv.org/abs/2503.02756) · [AutoMQM](https://aclanthology.org/2023.wmt-1.100/) / [arXiv 2308.07286](https://arxiv.org/abs/2308.07286) · [MQM-APE](https://aclanthology.org/2025.coling-main.374/) / [arXiv 2409.14335](https://arxiv.org/abs/2409.14335) / [Rubric-MQM](https://github.com/trotacodigos/Rubric-MQM) · [M-Prometheus](https://arxiv.org/abs/2504.04953) · [Prometheus 2](https://arxiv.org/abs/2405.01535) · [Tower](https://huggingface.co/papers/2402.17733) · [Tower+](https://huggingface.co/papers/2506.17080) · [xTower](https://arxiv.org/abs/2406.19482) · [ThinMQM](https://github.com/NLP2CT/ThinMQM) · [What do LLMs need for MT evaluation?](https://ar5iv.org/html/2410.03278) · [CompactQE](https://arxiv.org/abs/2605.15763)

**Surface metrics** — [sacreBLEU](https://github.com/mjpost/sacrebleu) / [PyPI](https://pypi.org/project/sacrebleu/) / [LICENSE.md](https://github.com/mjpost/sacrebleu/blob/master/LICENSE.md) · [Post 2018](https://aclanthology.org/W18-6319/) / [arXiv 1804.08771](https://arxiv.org/abs/1804.08771) · [chrF](https://aclanthology.org/W15-3049/) · [chrF++](https://aclanthology.org/W17-4770/) · [chrF deconstructed](https://aclanthology.org/W16-2341/) · [NLLB / FLORES-200](https://arxiv.org/abs/2207.04672) / [FLORES-200 README](https://github.com/facebookresearch/flores/blob/main/flores200/README.md) · [TER](https://aclanthology.org/2006.amta-papers.25/) · [Koehn 2004 bootstrap](https://aclanthology.org/W04-3250/) · [BLEU in Characters](https://mt-archive.net/IJCNLP-2005-Denoual.pdf) · [Segment-level lexical aggregation](http://arxiv.org/pdf/2407.12832)

**Other metrics** — [BLEURT](https://github.com/google-research/bleurt) / [arXiv 2004.04696](https://arxiv.org/abs/2004.04696) / [BLEURT-20 PyTorch](https://huggingface.co/lucadiliello/BLEURT-20) · [BERTScore](https://github.com/Tiiiger/bert_score) / [arXiv 1904.09675](https://arxiv.org/abs/1904.09675) · [YiSi-1](https://aclanthology.org/W19-5358/) · [YiSi-2](https://aclanthology.org/2020.wmt-1.100/) · [UniTE](https://aclanthology.org/2022.acl-long.558/) · [SLIDE](https://aclanthology.org/2024.naacl-short.18/) · [TREQA](https://arxiv.org/abs/2504.07583) · [QE length bias](https://arxiv.org/abs/2510.22028)

---

# F) Explicitly UNVERIFIED — do not cite as fact

- **Exact license strings** for: `Unbabel/wmt20-comet-da`, `wmt20-comet-qe-da`, `wmt23-cometkiwi-da-xl`, `wmt23-cometkiwi-da-xxl`, `XCOMET-XL`, `XCOMET-XXL`, `eamt22-cometinho-da`, `wmt22-unite-da`, xCOMET-lite re-uploads, Prometheus 2, M-Prometheus, ThinMQM, MetricX, CroissantLLM, Rubric-MQM.
- **The body of `LICENSE.models.md` and the `MODELS.md` table rows** — files confirmed to exist, contents not retrievable without direct HTTP. **This is the highest-value item to fetch first.**
- Literal LICENSE text for sacrebleu (Apache-2.0), bert_score (MIT), bleurt (Apache-2.0), metricx (Apache-2.0), unbabel-comet (Apache-2.0) — all consistently reported by secondary sources and model cards, none read verbatim here.
- **MetricX-25**: weight release, HF ids, sizes, license. No `google/metricx-25*` repo found.
- Exact mT5 parameter enumeration (1.2B / 3.7B / 13B); BLEURT-20 parameter count; xCOMET-lite student size (~278M); COMETINHO parameter count.
- **GEMBA-MQM's severity penalty weights**; GEMBA's per-variant scale wording; GEMBA's exact segment-level correlations; GEMBA-MQM's exact WMT23 rank; the MQM-APE open-model list; AutoMQM table column semantics.
- **Exact WMT correlation numbers and full rank orders for all years**; the WMT24 overall winner; WMT25 per-subtask winners; the verbatim organizer recommendation paragraphs; whether any WMT paper endorses BLEU as a legitimate secondary metric.
- Any **Chinese-specific metric-quality claim by WMT** (no such statement found); WMT24's exact MQM language-pair set.
- sacreBLEU TER signature field names; chrF++ arXiv id; sacreBLEU 2.6.0 release date; **the exact sacreBLEU paired-test flag spellings (`--paired-bs` / `--paired-ar`) and their defaults**.
- **Which QE checkpoints arXiv 2510.22028 shows to be length-biased** (no retrieved source names CometKiwi, MetricX-QE or any other checkpoint), and the direction/magnitude of the effect.
- **"en-zh is where metrics correlate worst"** — no supporting source found; treat as unsupported.
- Zouhar et al. Table 4 per-language-pair empty-translation percentages; the magnitude of the En→Zh bottom-75% filtering bias; the verbatim cross-LP/cross-version incomparability sentences.
- Kocmi et al. 2021 numeric recommendations; Koehn 2004 CI widths per test-set size; the conclusions of [2024.lrec-main.198](https://aclanthology.org/2024.lrec-main.198/) on Chinese MWEs.
- Any single canonical **EAMT/AMTA "MT evaluation guidelines" checklist** — AMTA has a [QE evaluation framework announcement](https://slator.com/amta-translation-quality-estimation-evaluation-framework/) and the [Multi-Range Theory presentation](https://aclanthology.org/2024.amta-presentations.6/), but no retrievable guideline PDF. Do not cite one.
- **All CPU RAM and throughput figures are estimates**, not measurements on this machine.

**Fastest way to close these gaps when network is available:** fetch [LICENSE.models.md](https://github.com/Unbabel/COMET/blob/master/LICENSE.models.md), [MODELS.md](https://github.com/Unbabel/COMET/blob/master/MODELS.md), the four WMT findings PDFs ([2022](https://statmt.org/wmt22/pdf/2022.wmt-1.2.pdf), [2023](https://dfki.de/fileadmin/user_upload/import/14644_2023.wmt-1.51.pdf), [2024](https://aclanthology.org/2024.wmt-1.2/), [2025](http://www2.statmt.org/wmt25/pdf/2025.wmt-1.23.pdf)), [2023.wmt-1.64.pdf](http://www2.statmt.org/wmt23/pdf/2023.wmt-1.64.pdf) §2–3 and §5, and the gated HF cards after accepting their terms.
