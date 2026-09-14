# CLIFF Benchmark — License-Clean Corpus Sourcing Notes

**Status:** research draft · **Author:** research subagent · **Date:** 2026-09-01
**Target repo:** `cliff-format` (MIT), public on GitHub
**Deliverable scope:** ~a few hundred short segments per stratum, each = SOURCE text + an existing HUMAN reference translation. Primary pair EN<->zh-Hans; secondary ja, es, fr.

---

## 0. Method, and an important verification caveat

This research was done inside a sandboxed agent session in which **outbound HTTPS from the shell was blocked** (TLS interception without credentials: `curl (35) schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`). The `web_search` tool returned **URLs and page titles only, with no page snippets**. Consequently:

* Every URL below was returned by a live search (so the page exists and its title matches the claim), **but the license text on the page was not re-read byte-for-byte in this session.**
* Each claim carries a confidence marker:
  * **[V]** — verified by a returned page title/URL that states the fact, or by a stable, well-known legal fact (statute text, copyright term arithmetic).
  * **[C]** — high-confidence domain knowledge, consistent with the returned sources, but the exact license file was not re-read here.
  * **[?]** — genuinely uncertain; **must** be checked by a human before shipping.
* **Before publishing anything, run the checklist in §8.** Do not treat this document as legal advice; it is engineering due diligence.

---

## 1. Copyright ground rules relied on

| Jurisdiction | Rule | Practical cutoff on 2026-09-01 |
|---|---|---|
| **United States** (published works) | 95 years from publication for works published 1929-1977 with notice/renewal; everything published **before 1931** is public domain. 1930 works entered the PD on 2026-01-01. | Published **≤ 1930** → PD **[V]** ([Public Domain Day 2026 — "Party like it's 1930"](https://fordham.libguides.com/blogs/news-from-the-stacks/public-domain-day-2026-party-like-its-1930); [Yale Copyright Conversations, Jan 2026](https://campuspress.yale.edu/copyrightconversations/2026/01/)) |
| **United States** (1931-1977 US works) | 95 yrs **only if** renewed; ~85% were not renewed → many are PD, but renewal must be searched (Stanford Copyright Renewal DB, CCE scans). | Case-by-case **[V]** |
| **United States** (foreign works, URAA/§104A) | Foreign works restored on 1996-01-01 **only if** still protected in the source country on that date. A work already PD in its source country on 1996-01-01 was **not** restored. | Key test for Chinese translations **[V]** |
| **China (PRC)** | 著作权法 art. 23: natural-person economic rights = **life + 50 years**, expiring 31 Dec of the 50th year. Corporate/anonymous works = 50 years from first publication. The 2020 amendment did **not** extend to 70. | Author died **≤ 1975** → PD in China **[V]** ([法院普法说明](http://dqdebt.hljcourt.gov.cn/public/detail.php?id=34561), [辽阳市宏伟区法院《知识产权法》概览](https://lyhw.lncourt.gov.cn/article/detail/2024/11/id/8213255.shtml)) |
| **EU / UK** | Life + 70 (Term Directive 2006/116/EC). | Author died **≤ 1955** → PD **[V]** |
| **Japan** | Life + 70 since 2018-12-30 (TPP11), **no revival**: authors who died **1967 or earlier** stayed PD under the old life+50 rule. | Died **≤ 1967** → PD in JP regardless of the extension; died **≥ 1968** → protected until death+70 **[C]** |
| **Berne** | Minimum life+50; national treatment; **rule of the shorter term is optional** and the EU applies comparison-of-terms only to non-EEA works. | Do not rely on it **[C]** |
| **France (special)** | Wartime extensions (arts. L123-8/9) plus **+30 years for "Mort pour la France"** authors. This is why *Le Petit Prince* is still protected in France. | Trap — see §5.1.9 **[C]** |

**Publication rule adopted for this repo:** ship a literary segment only if it is PD **(a)** in the US, **(b)** in the source country, and **(c)** under a life+70 term. Anything that clears only (a) goes into the fetch-script tier (§7), never into `data/`.

---

## 2. What "MIT repo" actually constrains

"The repository is MIT" means **our code and our own authored content** are MIT. It does **not** require every bundled data file to be MIT. The real constraints are:

1. **Redistribution must be permitted** at all (this kills Yelp, Amazon MARC, X/Twitter text, OpenSubtitles, most news).
2. **The obligations must be ones we can discharge** — attribution, notice preservation, keeping license headers.
3. **We must not mislead**: a root `LICENSE` saying MIT while `data/` is CC-BY-SA is a licensing bug. Fix by segregation + a `DATA-LICENSES.md` / per-directory `LICENSE` + SPDX headers.
4. **Copyleft strength matters:**

| License of the strings | Ship in-tree? | Why |
|---|---|---|
| MIT / BSD / ISC / Apache-2.0 / CC0 / Unlicense | ✅ Yes | Notice preservation only. |
| **MPL-2.0** | ✅ Yes, segregated | **File-level** copyleft. An MIT repo containing MPL-2.0 files is normal and legal, provided those files keep their MPL headers and are listed as MPL. This is *not* the GPL problem. |
| **CC-BY 3.0/4.0 (incl. IGO)** | ✅ Yes, with ATTRIBUTION file | Attribution + indicate changes (we segment/align = "changes"). |
| **CC-BY-SA 3.0/4.0** | ⚠️ Yes but viral | Our segmented/aligned corpus is plausibly an **adaptation** → the derived corpus files must be CC-BY-SA. Acceptable if isolated in `data/cc-by-sa/` and clearly flagged; it does constrain downstream commercial users. |
| **GPL-2.0 / GPL-3.0 / AGPL / LGPL** | ❌ Not in-tree | Redistribution *is* permitted, but only under the GPL. Vendoring GPL `.po` files as benchmark fixtures inside an MIT project invites the "single work vs. mere aggregation" argument, forces GPL notices/source-offer obligations onto every downstream user, and is exactly the conflict the task warns about. Use the fetch-script tier (§7). |
| **CC-BY-NC / CC-BY-ND / NC-ND** | ❌ Never | NC is incompatible with an open benchmark; ND forbids the derivative that segmentation creates. |
| Custom "research use only" | ❌ Not in-tree | Fetch-script tier. |

**Thin-copyright nuance (real, but not a licence):** individual micro-strings — "Save", "OK", "Are you sure you want to delete this file?" — very likely fall below the originality threshold and are not independently copyrightable. But a curated **selection of several hundred strings from one project** is a compilation drawn from a copyrighted whole, and in the EU may additionally touch *sui generis* database right. So: never use "the strings are too short to be copyrighted" as the justification for vendoring a GPL project's `.po` file. Use it only as a secondary comfort factor for sources that are already licensed OK.

---

## 3. Stratum 1 — App / SaaS / Web UI strings

### 3.1 Candidate matrix

| Project | Translation-string license | Where the files live | Dev comments / context? | In-tree in MIT repo? |
|---|---|---|---|---|
| **Godot editor l10n** | **MIT** (engine + editor l10n repo) **[C]** | [github.com/godotengine/godot-editor-l10n](https://github.com/godotengine/godot-editor-l10n) — `editor/*.po`, `classes/*.po`; Weblate: [hosted.weblate.org/projects/godot-engine/godot](https://hosted.weblate.org/projects/godot-engine/godot/) | **Excellent** — gettext `#.` extracted comments, `#:` source refs, `msgctxt` disambiguation, `#,` flags | ✅ **Best pick** |
| **VS Code language packs** | **MIT** **[C]** ([LICENSE.md](https://github.com/Microsoft/vscode-loc/blob/94a7bfabcf0239d89aa9879fb7964670b483b953/LICENSE.md)) | [github.com/microsoft/vscode-loc](https://github.com/microsoft/vscode-loc/blob/main/i18n/vscode-language-pack-zh-hans/README.md?plain=1) — `i18n/vscode-language-pack-{zh-hans,zh-hant,ja,es,fr}/translations/*.i18n.json` | Weak — key-path only (`vs/workbench/...`), no translator notes; context must be recovered from the MIT `microsoft/vscode` source | ✅ Yes |
| **Mozilla Firefox (Fluent)** | **MPL-2.0** **[V]** — file headers say so ([el/toolkit/.../aboutRights.ftl](https://github.com/mozilla-l10n/firefox-l10n/blob/main/el/toolkit/toolkit/about/aboutRights.ftl)) | [github.com/mozilla-l10n/firefox-l10n](https://github.com/mozilla-l10n/firefox-l10n) (single-locale dirs `zh-CN/`, `ja/`, `es-ES/`, `fr/`); Pontoon front-end | **Excellent** — Fluent `#` / `##` / `###` comment levels are mandated by [Fluent reviewer guidelines](https://gecko-docs.mozilla.org-l1.s3.us-west-2.amazonaws.com/l10n/fluent/review.html); see [Fluent comment semantics](https://deepwiki.com/projectfluent/fluent/5.4-comments-and-organization) | ✅ Yes, segregated as MPL |
| **LibreOffice** | **MPL-2.0** (modern code/strings; some legacy LGPL-3.0+) **[C]** ([core README](https://cgit.freedesktop.org/libreoffice/core/tree/README.md)) | Weblate `libo_ui-master` / `libo_help-master`; `translations` submodule `source/<lang>/**/*.po` | Good — `.po` with `#.` and KeyID context | ⚠️ Yes, but audit for LGPL-only files first **[?]** |
| **Amazon MASSIVE** | **CC-BY-4.0** **[C]** | `github.com/alexa/massive` / HF `AmazonScience/massive` — 51 locales incl. `zh-CN`, `ja-JP`, `es-ES`, `fr-FR` | Slot/intent annotations rather than dev comments | ✅ Yes — best *professional* human localization of app-style utterances |
| **OpenStreetMap iD editor** | **ISC** **[C]** ([iD README](https://raw.githubusercontent.com/openstreetmap/iD/v1.8.3/README.md)) | `dist/locales/*.json`, Transifex `id-editor` | Some `_comment` fields | ✅ Yes |
| **Scratch GUI / scratch-l10n** | **BSD-3-Clause** **[C]** (see [scratch-l10n packages](https://npm.io/package/scratch-l10n-me)) | `scratch-l10n` npm / `scratchfoundation/scratch-l10n` | ICU messages with `description` fields → **good context** | ✅ Yes |
| **Zulip** | **Apache-2.0** **[C]** ([docs/translating.md](https://raw.githubusercontent.com/zulip/zulip/8d4b32a13a5c0a014f960a63122300b622576b18/docs/translating.md), [Transifex sync commit](https://github.com/zulip/zulip/commit/83d02af9aa90a0feea0258cec66f77f5c203d063)) | `locale/<lang>/LC_MESSAGES/django.po`, `locale/<lang>/translations.json` | `.po` comments present | ✅ Yes |
| **Home Assistant frontend** | **Apache-2.0** **[C]** ([frontend repo](https://github.com/jasonhargrove/frontend)) | `src/translations/*.json` (upstream `home-assistant/frontend`) | Minimal | ✅ Yes |
| **Element Web / matrix-react-sdk** | **⚠️ AGPL-3.0 since late 2024** (was Apache-2.0 when matrix-react-sdk was separate) **[?]** — [Weblate project](https://weblate.element.dev/projects/element-web/matrix-react-sdk/) | `src/i18n/strings/*.json` | Some | ❌ Treat as copyleft until verified |
| **GNOME** | **GPL-2.0 / GPL-3.0**, same as each module; explicitly litigated inside GNOME ([evince #2130 "translations appear to be GPL-2-only"](https://gitlab.gnome.org/GNOME/evince/-/work_items/2130), [gnome-i18n: "Licenses of .po files, and translations"](https://lists.gnome.org/archives/gnome-i18n/2008-September/msg00341.html), [bug 438348 "License problems in po files"](https://bugzilla.gnome.org/show_bug.cgi?id=438348)) **[V]** | l10n.gnome.org (Damned Lies), per-module `po/` | **Best-in-class** `#. TRANSLATORS:` comments | ❌ fetch-script tier |
| **KDE** | GPL-mixed, same conclusion ([kde list: "About the license of L10n products"](https://mail.kde.org/pipermail/kde/2009-October/021528.html)) **[V]** | `l10n-kf6/<lang>/messages/**/*.po` (invent.kde.org), scripty | Good | ❌ fetch-script tier |
| **WordPress / GlotPress** | GPLv2+ ([Polyglots](https://make.wordpress.org/polyglots/2020/03/03/hi-69/)) **[C]** | translate.wordpress.org | Weak | ❌ fetch-script tier |
| **Signal Android** | AGPL-3.0 **[C]** ([translation sync commit](https://github.com/signalapp/Signal-Android/commit/5626fb74ae0a11f5be98c6ca96028b43e3e2535c), [strings.xml example](https://gitlab.ibr.cs.tu-bs.de/zrtp/Signal-Android/-/blob/fa0c783c6473a3efe9c77e0164722dab55873352/res/values-bo/strings.xml)) | `app/src/main/res/values-<lang>/strings.xml` | XML comments only | ❌ |
| **Ubuntu / Launchpad Translations** | Launchpad requires translators to license contributions **BSD-3-Clause** for the Launchpad-hosted translation set **[?]** — see [Launchpad Q#65679 "Copyright issue accepting translation upstream"](https://launchpad.net/launchpad/+question/65679) | Launchpad export tarballs | Inherited from upstream POT | ⚠️ Attractive **if** the BSD policy is confirmed; do **not** ship until confirmed, because the underlying upstream template may still be GPL |
| **Microsoft Terminology / Apple / Google glossaries** | Proprietary, no redistribution | — | — | ❌ **Never** |

### 3.2 Where the "developer comments/context" actually is

Our stratum specifically needs context, so pick formats accordingly:

* **gettext `.po`** (Godot, GNOME, KDE, LibreOffice, Zulip): `#.` = programmer-supplied extracted comment (typically `/* TRANSLATORS: ... */` in source), `#:` = file:line references, `msgctxt` = disambiguation context, `#,` = flags (`fuzzy`, `c-format`), plus `Plural-Forms`. See [gettext PO structure reference](https://docs.memoq.com/12-0/en/Workspace/po-gettext-files.html) and [gettext_parser](https://pub.dev/documentation/gettext_parser/latest/). **[V]**
* **Fluent `.ftl`** (Mozilla): three comment levels — `#` attached to a message, `##` group, `###` resource-wide — plus `.attribute` and selectors that encode plural/gender context. **[V]**
* **ICU MessageFormat JSON** (Scratch, many React apps): `description` field per message → clean, structured context.

**Recommended stratum-1 build:** Godot `.po` (MIT, rich `#.` comments) as the primary, Mozilla Fluent (MPL-2.0, rich `#`/`##` comments) as the "context-heavy" second, VS Code loc (MIT) and MASSIVE (CC-BY-4.0) as fillers. That covers en↔zh-CN/ja/es/fr with zero copyleft conflict.

---

## 4. Stratum 2 — Articles / news / tweets / comments

| Source | Langs | Human translation? | License | In-tree? | URL |
|---|---|---|---|---|---|
| **FLORES-200** | 200+ incl. zho_Hans, jpn, spa, fra | ✅ professional translators, from Wikimedia (Wikinews/Wikijunior/Wikivoyage) source | **CC-BY-SA 4.0** **[C]** | ⚠️ yes, under SA | [huggingface.co/datasets/facebook/flores](https://huggingface.co/datasets/facebook/flores/blob/751d24d88b0d7d90ec0b533a52965050f694eae0/README.md) |
| **NTREX-128** | 128 langs, human refs of the WMT19 EN news test set | ✅ | CC-BY-SA 4.0 **[?] verify repo LICENSE** | ⚠️ yes, under SA | [github.com/MicrosoftTranslator/NTREX](https://github.com/MicrosoftTranslator/NTREX) |
| **Global Voices** (OPUS `GlobalVoices`) | en, zh, es, fr, ja, ~40 more | ✅ volunteer *human* translators (Lingua project) | **CC-BY 3.0** site default **[C]**; a minority of posts are CC-BY-NC-ND → **per-article check required [?]** | ✅ yes, with attribution + per-article filter | [OPUS GlobalVoices via GlotLID sources](https://github.com/cisnlp/GlotLID/blob/main/sources.md); [HF mirror en-fr](https://huggingface.co/datasets/Nicolas-BZRD/Parallel_Global_Voices_English_French/blob/main/README.md) |
| **Wikinews** | en/zh/es/fr/ja editions | ⚠️ *some* articles are translations, alignment is manual | **CC-BY 2.5** **[C]** ([Wikinews-l reuse thread](https://lists.wikimedia.org/hyperkitty/list/wikinews-l@lists.wikimedia.org/message/ZNCJWQU76TOYCGWJNJFHWMXOTVSBI6DR/)) | ✅ yes | wikinews.org dumps |
| **Wikipedia / WikiMatrix / CCMatrix** | many | ❌ **mined**, not human reference translations | CC-BY-SA 3.0/4.0 ([WMF Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)) | ⚠️ license OK, but **fails the "human reference" requirement** | wikimatrix / OPUS |
| **Tatoeba** | 400+, dense en/zh/ja/es/fr | ✅ human, volunteer, sentence-level | **CC-BY 2.0 FR** (some CC0) **[C]**; attribution to Tatoeba + contributors required | ✅ yes | [Using the Tatoeba Corpus for Your Own Projects](https://en.wiki.tatoeba.org/history/show-version/3336) |
| **News-Commentary (WMT)** | en/zh/es/fr/de/… | ✅ professional | **Underlying Project Syndicate articles are copyrighted**; statmt redistributes for research; no clean grant **[?]** | ❌ fetch-script | statmt.org/wmt* |
| **WMT news test sets** | many | ✅ professional | Released for the shared task / research; upstream news content licensed to organizers only **[C]** ([CRACKER D3.9 on WMT16 test sets](http://cracker-project.eu/wp-content/uploads/CRACKER-D3.9-final.pdf)) | ❌ fetch-script — this is exactly why **sacrebleu downloads test sets at runtime** ([sacrebleu](https://pypi.org/project/sacrebleu/2.4.3/)) | statmt.org |
| **UN Parallel Corpus v1.0** | ar,en,es,fr,ru,**zh** — all human UN translations | ✅ excellent quality | UN retains copyright; UN terms allow non-commercial reproduction, commercial needs permission **[?]** | ❌ fetch-script (MIT repo implies commercial reuse) | [LREC 2016 paper](https://preview.aclanthology.org/update-css-js/L16-1561.pdf) |
| **Amazon Multilingual Reviews (MARC)** | 6 langs | ⚠️ not translations | **Retired; license forbids redistribution** **[C]** | ❌ | — |
| **Yelp Open Dataset** | en | ❌ | No redistribution, no commercial use **[C]** | ❌ | — |
| **TED / IWSLT** | many incl. zh, ja | ✅ volunteer human subtitles | **CC-BY-NC-ND** **[C]** | ❌ NC **and** ND | ted.com |
| **Tweets / X posts** | — | — | X ToS forbids redistributing post text; standard practice is **ID-only ("dehydrated") datasets** | ❌ | — |
| **Stack Exchange dumps** | en (+zh SE sites) | ❌ not parallel | CC-BY-SA 4.0 | ⚠️ no translations | archive.org |

**Stratum-2 recommendation:** FLORES-200 (news-ish Wikimedia prose, SA-segregated) + Global Voices (real news/blog register, CC-BY, filtered) + Tatoeba (short colloquial "comment/tweet-length" segments, CC-BY). That fully covers en↔zh/ja/es/fr with attribution-only or SA obligations, and needs zero murky sources. Use **NTREX-128** if you want true news-domain WMT-style references without WMT's licensing.

---

## 5. Stratum 3 — Classical & modern literature (PD source **and** PD translation)

### 5.1 Per-work verdicts

**5.1.1 西游记 / Journey to the West** — source PD (16th c.).
* **Timothy Richard, *A Mission to Heaven* (Shanghai, 1913)** — published ≤1930 → **PD in US**; Richard d. 1919 → life+70 expired 1989 → **PD globally**. ✅ **[V/C]** ⚠️ *Caveat:* it is an abridged, Christianizing paraphrase, poor as a "reference translation" for MT-style evaluation; label it explicitly as a *loose* rendering. Background: [Durham thesis on 20th-c. English translations of JTTW](https://etheses.durham.ac.uk/id/eprint/12841/1/W_Luo._E-Thesis.pdf).
* **Helen M. Hayes, *The Buddhist Pilgrim's Progress* (1930)** — PD in the US as of 2026-01-01; author's death date unconfirmed → life+70 status **[?]**.
* **Arthur Waley, *Monkey* (1942)** — Waley d. 1966 → protected in UK/EU/JP until **2036**; in the US 1942+95 = **2038** (if renewed, and it was). ❌ **NOT PD.**
* **Anthony C. Yu (1977-83, rev. 2012, U. Chicago)**, **W.J.F. Jenner (FLP, 1982-86)** — ❌ fully in copyright.

**5.1.2 三国演义 / Romance of the Three Kingdoms** — ✅ **BEST classical pick.**
* **C.H. Brewitt-Taylor, *San Kuo, or Romance of the Three Kingdoms* (Kelly & Walsh, 1925)** — published ≤1930 → PD in US; Brewitt-Taylor d. 1938 → life+70 expired **2009** → PD in EU/UK/JP. ✅ **[V]**
* It is **already on Project Gutenberg**: [PG ebook #77416, vol. 1](https://www.gutenberg.org/cache/epub/77416/pg77416.rdf); catalogue entry [Online Books Page](https://onlinebooks.library.upenn.edu/webbin/book//lookupid?key=olbp110195). Gutenberg texts are free of US copyright restrictions; strip the PG trademark header/footer or comply with the [PG License](https://gutenberg.org/cache/epub/72834/pg72834.txt) (unrestricted redistribution only if the "Project Gutenberg" trademark is removed).
* Chinese source: Ming-era text via 维基文库 (transcriptions of PD works remain PD; the WMF CC-BY-SA ToU covers *contributions*, not the PD original) **[C]**.

**5.1.3 罗密欧与朱丽叶 / Romeo and Juliet** — ✅ **BEST bilingual literary pick for en↔zh.**
* Shakespeare: PD everywhere.
* **朱生豪 (Zhu Shenghao), 1912-1944-12-26.** China life+50 → economic rights expired **1994-12-31 → PD in China since 1995-01-01**. Life+70 → PD since **2015-01-01**. **US:** because the translation was already PD in China on the URAA restoration date (1996-01-01), it was **not restored** under §104A → PD in the US too. ✅ **[C]** Author page: [维基文库 Author:朱生豪](https://zh.wikisource.org/wiki/Author:%E6%9C%B1%E7%94%9F%E8%B1%AA).
* ⚠️ **Editions matter.** Modern 人民文学 / 译林 editions of "朱生豪译" incorporate later editorial revision (吴兴华, 方平 et al.), and those revisions carry their own copyright. Use the 1947-48 世界书局 text or the Wikisource transcription, and record the edition in the dataset card. Chinese Shakespeare translations are actively litigated — see [2024 中译本剽窃争议报道](https://news.qq.com/rain/a/20240904A00BSC00).
* ❌ 梁实秋 (d. 1987), 方平 (d. 2008), 卞之琳 (d. 2000) — all still protected.

**5.1.4 出埃及记 / Exodus**
* **KJV**: PD in the **US**. In the **UK** it is under **perpetual Crown copyright / royal letters patent**, administered by Cambridge University Press and the King's Printer; UK reproduction beyond CUP's standard allowance (broadly, ≤500 verses, not a whole book, <25% of a work) needs permission. **[C]** ([background](http://alexandria.sensagent.com/alexandria-workstation-2011/v2.1/search.main.jsp?w=AUTHORIZED+KING+JAMES+VERSION&sl=en&tl1=en&dl=en))
  * **Cleaner English substitutes:** *American Standard Version* (1901, PD) or *World English Bible* (explicitly PD/CC0-dedicated) — **use WEB or ASV instead of KJV** and the UK problem disappears entirely. ✅
* **和合本 / Chinese Union Version (1919)** — published 1919 by a committee → PD in the US (≤1930) and >50 years from publication in China → **PD** **[C]**. ✅
  * ❌ Do **not** use 新标点和合本 (UBS claims copyright in the new punctuation/typography), 和合本2010, 思高本 (1968, Studium Biblicum), 新译本, CNV.
* **Pairing WEB/ASV ↔ 和合本 1919 gives a fully PD, verse-aligned legal/liturgical-register parallel corpus.** ✅ Highly recommended.

**5.1.5 永乐大典** — Ming-era, PD as source, but there is **no substantial published translation**, and the surviving volumes exist mainly as manuscript scans held by NLC/BL. **Not viable.** Substitutes with PD translations:
* 《聊斋志异》 ↔ **Herbert Giles, *Strange Stories from a Chinese Studio* (1880)** — Giles d. 1935 → PD 2006. ✅
* 《红楼梦》 ↔ **H. Bencraft Joly (1892-93)** — PD, on Gutenberg. ✅
* ❌ 《水浒传》↔ Pearl Buck *All Men Are Brothers* (1933) — Buck d. 1973 → 2044. ❌ Sidney Shapiro (1980). ❌ 金瓶梅 ↔ Egerton (1939).

**5.1.6 论语 / 道德经**
* **James Legge, *The Chinese Classics* vol. 1 (1861)** — Legge d. 1897 → PD everywhere. ✅ **[V]** [Wikisource: The Chinese Classics/Volume 1/Confucian Analects](https://en.wikisource.org/wiki/The_Chinese_Classics%2fVolume_1%2fConfucian_Analects).
* **Legge, *Tao Te Ching* (Sacred Books of the East XXXIX, 1891)** ✅; **Paul Carus (1898)** ✅; **辜鸿铭 English Analects (1898)** — d. 1928 → ✅.
* ❌ **Arthur Waley, *The Way and Its Power* (1934)** — d. 1966 → protected to 2036 outside the US. ❌ D.C. Lau (d. 2010), 陈荣捷.

**5.1.7 唐诗 / Tang poetry — a jurisdiction trap**
* **Witter Bynner & 江亢虎, *The Jade Mountain* (Knopf, 1929)** — **PD in the US since 2025-01-01**, but Bynner d. 1968 → **protected under life+70 until 2039**. 江亢虎 d. 1954 clears life+70, Bynner does not. ❌ **Do not ship globally**; US-only is not a workable rule for a GitHub repo. **[C]**
* ✅ **Globally-safe Tang translations instead:**
  * **W.J.B. Fletcher, *Gems of Chinese Verse* (1918)** — d. 1933 → PD 2004. ✅
  * **Herbert Giles, *Chinese Poetry in English Verse* (1898)** — d. 1935 → PD 2006. ✅
  * **Amy Lowell & Florence Ayscough, *Fir-Flower Tablets* (1921)** — Lowell d. 1925, Ayscough d. 1942 → PD 2013. ✅
  * ❌ **Arthur Waley, *170 Chinese Poems* (1918)** — US-PD only; blocked to 2036 elsewhere.

**5.1.8 Alice in Wonderland ↔ 赵元任《阿丽思漫游奇境记》(1922)** — ⚠️ **the reverse trap.**
* Carroll (1865): PD. 
* **赵元任 d. 1982-02-24** → China life+50 → PD only on **2033-01-01**; life+70 → 2053. In the **US** it is PD (published 1922; even under URAA restoration 1922+95 expired in 2017). So: **PD in the US, still copyrighted in China.** ❌ **DO NOT SHIP.** [商务印书馆 edition page](https://www.cp.com.cn/book/7-100-03588-0_17.html) — an in-print commercial edition, which is itself a red flag.

**5.1.9 "Modern novel" cell — what NOT to use, and what to use**

❌ **Absolutely not** (all fully in copyright, in every relevant jurisdiction):
| Work | Why |
|---|---|
| 《哈利·波特》 | Rowling alive; 马爱农/马爱新 translations © 人民文学出版社 |
| 金庸《神雕侠侣》《射雕英雄传》 | 金庸 d. 2018-10-30 → China PD 2069; Anna Holmwood/Gigi Chang translations © MacLehose |
| 刘慈欣《三体》 | author alive; Ken Liu translation © Tor |
| 余华《活着》, 莫言, 村上春树, 东野圭吾 | in copyright |
| 《百年孤独》 | García Márquez d. 2014; 范晔 译 © 新经典 |
| **《小王子》** | **Classic trap.** Saint-Exupéry d. 1944 → PD in most life+70 countries since 2015, **but France applies wartime extensions + 30 years for "Mort pour la France"** → protected in France to ~2032; and the US 1943 publication runs to 2039. Any Chinese translation is separately copyrighted anyway. ❌ |
| 傅东华《飘》(1940), 徐迟《瓦尔登湖》 | 傅东华 d. 1971 → life+70 to 2042; 徐迟 d. 1996 ❌ |
| Cory Doctorow's CC novels | mostly **CC BY-NC-SA** → NC ❌ |

✅ **License-clean substitutes for the "modern prose/novel" stratum** — in priority order:

1. **PD source (≤1930) + PD Chinese translator.** The Chinese translators who are PD in *both* China and life+70 jurisdictions:
   * **林纾 (d. 1924-10-09)** — PD everywhere. 《巴黎茶花女遗事》(Dumas fils d. 1895, PD), 《黑奴吁天录》(Uncle Tom's Cabin, PD). ⚠️ 文言, very free/paraphrastic — legally spotless, translationally loose.
   * **鲁迅 (d. 1936-10-19)** — China PD 1987; life+70 PD 2007. ✅ 《月界旅行》(Verne, *De la Terre à la Lune*, PD) is a great **"modern novel" surrogate**: PD French/English source + PD Chinese target + vernacular register.
   * **伍光建 (d. 1943)** — PD in life+70 since 2014. 《侠隐记》(*The Three Musketeers*, Dumas PD). ✅ Modern-ish vernacular Chinese, closer register to contemporary prose.
   * **朱生豪 (d. 1944)** ✅ (see 5.1.3).
   * ⚠️ 周作人 (d. 1967): China PD 2018 and Japan PD, but life+70 → 2038 ❌ for EU/UK.
2. **Wikisource "Translations" namespace** — CC-BY-SA 4.0 volunteer translations; acceptable in the SA-segregated tier. **[C]**
3. **Author our own.** Commission (or draft and have a human translator produce) ~50-100 original modern-register passages + reference translations, dedicated **CC0**. This is the cleanest option, gives full control over difficulty/phenomena, and removes every provenance question. Precedent: many eval suites now author their held-out items to defeat training-set contamination. **If any source text is LLM-drafted, say so in the dataset card, and make sure the human reference comes from a translator under a contributor agreement or CC0 dedication.**
4. **Standard Ebooks** — PD works with editorial improvements dedicated to the public domain ([About Standard Ebooks](https://standardebooks.org/about), [imprint/CC0 statement](https://standardebooks.org/ebooks/camille-flammarion/omega/j-b-walker/text/imprint)). ✅ Clean English side.

---

## 6. Stratum 4 — Legal / EULA / license / academic

| Source | Langs | Human translation? | License | In-tree? | URL |
|---|---|---|---|---|---|
| **Creative Commons 4.0 legal code — official translations** | en + **zh-Hans**, ja, fr, es, de, … | ✅ official, lawyer-reviewed | CC dedicates its own license text to the **public domain via CC0**; only the CC *trademarks* are restricted **[C]** ([Why Creative Commons uses CC0](https://creativecommons.org/2015/02/25/why-creative-commons-uses-cc0/)) | ✅ **Best legal-register pick** | `creativecommons.org/licenses/by/4.0/legalcode.zh-Hans` (also `.ja`, `.fr`, `.es`) |
| **EUR-Lex / EU legislation** | 24 EU official langs (fr, es, de, it…; **no zh**) | ✅ DGT professional translators | **Commission Decision 2011/833/EU** — reuse free of charge, incl. commercial, with source acknowledgement and no distortion **[V]** ([Art. 4 text](https://www.legislation.gov.uk/eudn/2011/833/article/4/data.htm), [full decision](https://risapp.lawthek.eu/detail/c89c4471-72f9-4b09-a3e2-093807e72cb0/en/SINGLE)) | ✅ with "© European Union, eur-lex.europa.eu" + "only the printed OJ is authentic" disclaimer | eur-lex.europa.eu |
| **DGT-TM (Acquis translation memories)** | 24 EU langs, TMX, sentence-aligned | ✅ | EU reuse decision; some mirrors label it **EUPL-1.1** — reconcile before shipping **[?]** ([HF mirror README](https://huggingface.co/datasets/rinto/dgt-tm/raw/main/README.md)) | ✅ | JRC / EC Language Technology Resources |
| **JRC-Acquis 3.0** | 22 EU langs | ✅ | EU reuse; a **CC-BY-4.0**-licensed redistribution exists **[V]** ([Kielipankki JRC-Acquis CC-BY](https://www.kielipankki.fi/lic/heko-jrc-acquis-cc-by-eng/), [corpus header](https://wt-public.emm4u.eu/Acquis/JRC-Acquis.3.0/corpus/jrcHeader.html)) | ✅ | emm4u.eu |
| **World Bank Open Knowledge Repository** | en + **zh**, es, fr, ar | ✅ official translations of flagship reports | **CC-BY 3.0/4.0 IGO** **[C]** | ✅ — **the best en↔zh formal/policy-register source with a real permissive licence** | openknowledge.worldbank.org |
| **KFTT (Kyoto Free Translation Task)** | ja↔en | ✅ human translations by NICT of Japanese Wikipedia Kyoto articles | **CC-BY-SA 3.0** **[C]** ([HF loader](https://huggingface.co/datasets/may-ohta/kftt/blob/main/kftt.py)) | ⚠️ yes, SA tier | phontron.com/kftt |
| **SciELO parallel corpus** | en↔es, en↔pt (biomedical/scientific) | ✅ author-provided bilingual abstracts | **CC-BY** (SciELO is OA CC-BY) **[C]** ([bigbio/scielo card](https://huggingface.co/datasets/bigbio/scielo/blob/5525afafc20e778471e4fb693e7240549a1fe365/README.md)) | ✅ | scielo.org |
| **arXiv** | en (abstracts) | ❌ essentially no human translations | **Per-paper**: default arXiv non-exclusive licence gives **no redistribution right**; only the CC-BY / CC-BY-SA / CC0 subsets are reusable. Kaggle's arXiv **metadata** snapshot is CC0 for the metadata **[?]** ([Kaggle arXiv metadata](https://www.kaggle.com/datasets/amanpriyanshu/arxiv-cs-only-11-16-2026-metadata-snapshot/)) | ⚠️ only if you filter to CC licences **and** find bilingual abstracts | arxiv.org |
| **GNU GPL / LGPL / AGPL text + "unofficial translations"** | many | ✅ but explicitly **unofficial** | The GPL document itself permits **verbatim copying only** ("changing it is not allowed"); the FSF does not approve translations and hosts only links **[V]** ([Unofficial Translations — GNU Project](https://www.gnu.org/licenses/translations.html), [mirror](http://ftp1.gwdg.de/pub/gnu/www/savannah-checkouts/gnu/www/licenses/translations.html), [中文页](https://gnu.net.cn/licenses/translations.html)) | ❌ **Avoid.** Chopping the licence into benchmark segments is not "a verbatim copy", and each translation has its own author + terms. Use CC legal code instead. | gnu.org |
| **Apache-2.0 text + translations** | many | ✅ community | ASF permits reproduction of the licence text; translations are third-party and unofficial **[?]** ([ASF licence FAQ](https://apache.googlesource.com/www-site/+/refs/heads/preview/cml-staging/output/foundation/license-faq.html)) | ⚠️ medium risk — prefer CC | apache.org/licenses |
| **UN documents / UNv1.0** | ar,en,es,fr,ru,**zh** | ✅ excellent | UN copyright; non-commercial reproduction tolerated, commercial requires permission **[?]** | ❌ fetch-script | [LREC 2016](https://preview.aclanthology.org/update-css-js/L16-1561.pdf) |
| **WHO / OECD / IMF publications** | multi incl. zh | ✅ | Mostly **CC BY-NC-SA 3.0 IGO** or **NC-ND** **[C]** | ❌ NC | — |

**Stratum-4 recommendation:** CC 4.0 legal code (en/zh-Hans/ja/fr/es — official, dense legalese, CC0-clean) as the licence/EULA core; World Bank OKR for en↔zh formal policy prose; EUR-Lex + DGT-TM for fr/es legal; KFTT for ja academic-ish; SciELO for es scientific. **Do not** build the legal stratum on the GPL text.

---

## 7. Stratum 5 — Game dialogue / skills / movie scripts

| Project | License of code / of translations | zh-CN? | Dialogue-shaped text? | In-tree? |
|---|---|---|---|---|
| **Unciv** | **MPL-2.0** **[C]** | ✅ `Simplified_Chinese.properties`, ja, es, fr | ✅ tutorials, civ/leader quotes, unit & tech ("skill") names, UI | ✅ **Best permissive game pick** — [template.properties (with `#` context comments)](https://github.com/yairm210/Unciv/blob/master/android/assets/jsons/translations/template.properties) |
| **Ren'Py** | permissive (MIT-family) **[C]** ([licence page](http://nightly.renpy.org/current-8/doc/license.html)) | ✅ launcher/GUI translations | ⚠️ engine/UI strings, not story text; the bundled demo needs its own licence check **[?]** | ✅ |
| **Scratch** | BSD-3-Clause **[C]** | ✅ | block/opcode text, tutorials | ✅ |
| **Battle for Wesnoth** | **GPL-2.0-or-later** (code + `po/`); art CC-BY-SA **[V]** ([ru.po](https://raw.githubusercontent.com/wesnoth/wesnoth/master/po/wesnoth-multiplayer/ru.po)) | ✅ | ✅✅ **the richest campaign dialogue with `#.` context comments** | ❌ fetch-script |
| **0 A.D.** | GPL-2.0 code, **CC-BY-SA 3.0** assets **[C]** ([overview](https://fr.m.wikipedia.org/wiki/0AD)) | ✅ | unit/tech/civ descriptions | ❌ / ⚠️ SA tier only |
| **OpenTTD** (GPL-2.0-only), **Mindustry** (GPL-3.0), **Luanti/Minetest** (LGPL-2.1 + CC-BY-SA media), **Veloren** (GPL-3.0), **Naev** (GPL-3.0), **Endless Sky**, **OpenRA**, **Freeciv**, **SuperTuxKart**, **Shattered Pixel Dungeon** | copyleft | ✅ | ✅ | ❌ fetch-script |
| **Cataclysm: DDA** | content **CC-BY-SA 3.0** **[C]** | ✅ | ✅✅ huge item/skill/NPC-dialogue corpus | ⚠️ SA tier — the best *dialogue-dense* option if you accept ShareAlike |
| **OpenSubtitles / OPUS `OpenSubtitles`** | **No clean licence.** Subtitles are derivative works of copyrighted films; uploaders almost never hold rights; OPUS redistributes "for research". **[C]** ([discussion of subtitle legality](https://lists.ubuntu.com/archives/ubuntu-in/2007-November/002232.html), [a Finnish institutional copy behind an access licence](https://datakatalogi.helsinki.fi/items/8cc006d2-3319-4369-abe9-3623be2ac6bc/full)) | ✅ | ✅ | ❌ **Do not ship.** Being honest: this is *legally murky at best*. Publishing OpenSubtitles-derived text in an MIT repo exposes us and every downstream user. Not worth it for a few hundred segments. |
| **PD films / screenplays** (e.g. *Night of the Living Dead*, 1968, PD for missing notice; pre-1931 silents) | source PD **[C]** ([how to spot PD films](http://archive.org/post/355898/)) | ❌ | ✅ | ⚠️ **English side is PD, but every Chinese subtitle for them is a copyrighted fansub.** Only usable if we commission our own translation. |

**Stratum-5 recommendation:** **Unciv (MPL-2.0)** for skills/units/tutorial text + **Ren'Py/Scratch** for game-UI, and for true *dialogue*, use **PD drama**: Shakespeare ↔ 朱生豪 (§5.1.3) — legally spotless, genuinely dialogue-structured, and it double-serves stratum 3. If ShareAlike is acceptable, add **Cataclysm: DDA** (CC-BY-SA 3.0) for modern game-dialogue register. Optionally commission ~50 original game-dialogue segments (CC0) to cover contemporary RPG/gacha register that no PD source provides.

---

## 8. When we cannot redistribute: the standard workarounds

These are the established practices; adopt all five.

1. **Fetch script + pinned manifest ("recipe, not the food").** Ship `sources/<corpus>.yaml` containing: upstream URL, **immutable revision** (git SHA / release tag / dataset version), file path within the archive, license SPDX id, and per-segment locators. A `cliff corpus fetch` command reconstructs the corpus locally at first run. **Canonical precedent: sacrebleu downloads WMT test sets on demand rather than vendoring them** ([sacrebleu](https://pypi.org/project/sacrebleu/2.4.3/), [README](https://raw.githubusercontent.com/mjpost/sacrebleu/refs/tags/v1.2.9/README.md)); `lm-evaluation-harness` and `mteb` do the same.
2. **Segment IDs + checksums instead of text.** Store `{corpus, file, key/msgid, sha256(source), sha256(reference), n_chars}`, optionally with an 8-char prefix/suffix of each string for debugging. This lets anyone *verify* they reconstructed the identical corpus without us republishing a single sentence. HF's own dataset infrastructure records `download_checksums` for exactly this integrity purpose ([example](https://huggingface.co/datasets/aps/super_glue/discussions/9/files)).
3. **Dataset card ("datasheet") practice.** Every stratum gets a card: provenance, upstream licence + link, collection date, revision pin, transformations applied (segmentation, normalization), languages, known biases, personal-data statement, and an explicit *"what you may do with this"* section. Mirror it as a HF dataset card + Croissant metadata so the licence travels with the data.
4. **Gated distribution for the grey tier.** Hugging Face supports **gated datasets** requiring users to accept terms / be manually approved before download ([Gated datasets — Hub docs](https://huggingface.co/docs/hub/en/datasets-gated), [source](https://github.com/huggingface/hub-docs/blob/8577fc77/docs/hub/datasets-gated.md)). Use this only for material we *do* have the right to distribute under conditions — gating does **not** legalize distributing something we have no licence for.
5. **License segregation in-tree.**
   ```
   data/
     mit/        (Godot, VS Code loc, our own CC0 items)   -> LICENSE + ATTRIBUTION.md
     mpl-2.0/    (Mozilla Fluent, Unciv)                   -> keep upstream headers
     cc-by/      (Global Voices, Tatoeba, World Bank, CC legalcode, SciELO)
     cc-by-sa/   (FLORES-200, NTREX, KFTT, CDDA)           -> derived files are CC-BY-SA
     public-domain/ (Brewitt-Taylor, Legge, 朱生豪, 和合本1919, WEB)
   fetch/        (recipes for GNOME/KDE/Wesnoth/WMT/UN — no text in git)
   ```
   Root `README` states: *"Code is MIT. Data files are under the licences listed in `DATA-LICENSES.md`; the MIT grant does not extend to them."*
6. **Two more legitimate options:** (a) **ask** — email the rights holder / translator for an explicit CC-BY or CC0 grant for a few hundred segments; small asks are often granted for benchmarks; (b) **author our own** with a contributor licence agreement / CC0 dedication (see §5.1.9).
7. **Cautionary precedent:** the Books3 / "The Pile" takedowns show that "everyone else redistributes it" is not a defence, and that a widely-mirrored corpus can be pulled years later, breaking every benchmark that depended on it. Prefer sources whose licence you could defend in writing.

---

## 9. Pre-publication verification checklist (must be done by a human with network access)

- [ ] Re-read and archive (WARC/PDF) the **LICENSE file at the exact pinned commit** for: godot-editor-l10n, vscode-loc, firefox-l10n, Unciv, scratch-l10n, iD, Zulip, home-assistant/frontend.
- [ ] Confirm **NTREX-128** repo LICENSE (CC-BY-SA 4.0?) **[?]**
- [ ] Confirm **Element Web** current licence (AGPL-3.0 vs Apache-2.0) **[?]**
- [ ] Confirm **Launchpad Translations BSD-3-Clause** contributor policy, and whether it can override upstream GPL templates **[?]**
- [ ] Per-article licence check for every **Global Voices** post used (CC-BY 3.0 vs NC-ND) **[?]**
- [ ] Reconcile **DGT-TM** licence: EU reuse decision vs. the EUPL-1.1 label on mirrors **[?]**
- [ ] Confirm **CC**'s statement that its licence texts are unrestricted/CC0, and comply with the CC trademark policy (don't imply CC endorsement) **[?]**
- [ ] Confirm death dates: 伍光建 (1943?), Helen M. Hayes, 江亢虎 (1954) **[?]**
- [ ] Confirm the **朱生豪 edition** used is the pre-revision text, not a modern edited edition **[?]**
- [ ] Run a US **renewal search** for anything published 1931-1977 that we want to use.
- [ ] Write `DATA-LICENSES.md` + per-directory `LICENSE` + `ATTRIBUTION.md`, and add SPDX headers to generated corpus files.
- [ ] Add a public **takedown/contact** line in the README (good-faith posture, and it works).

---

## 10. Bottom line

* **Fully clean, no-copyleft core:** Godot l10n (MIT) · VS Code loc (MIT) · Mozilla Fluent (MPL-2.0) · Unciv (MPL-2.0) · MASSIVE (CC-BY-4.0) · CC 4.0 legal code (CC0) · World Bank OKR (CC-BY IGO) · EUR-Lex/DGT (EU reuse) · Global Voices (CC-BY 3.0) · Tatoeba (CC-BY 2.0 FR) · PD literature set (Brewitt-Taylor, Legge, Giles, Joly, Fletcher, 朱生豪, 和合本 1919 ↔ WEB/ASV, 鲁迅/林纾/伍光建).
* **Accept ShareAlike only in a segregated directory:** FLORES-200, NTREX-128, KFTT, Cataclysm: DDA, Wikisource translations.
* **Never in-tree:** GNOME/KDE/WordPress/Signal/Element (copyleft UI strings) · Wesnoth/0 A.D./OpenTTD/Mindustry/Veloren/Naev (copyleft game text) · OpenSubtitles · TED/IWSLT (NC-ND) · Yelp/Amazon MARC · tweet text · News-Commentary/WMT news · UN corpus · Microsoft/Apple/Google terminology · Waley, Yu, Jenner, Pearl Buck, 梁实秋, 赵元任-Alice, Bynner (US-only), 小王子, 哈利波特, 金庸, 三体.
* **The gap that no PD/permissive source fills** is *contemporary* narrative prose and *contemporary* game dialogue. Fill it by **authoring ~50-100 original segments per gap and dedicating them CC0** — cheapest, cleanest, and it also protects the benchmark against training-set contamination.
