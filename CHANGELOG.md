# cliff-test Changelog

cliff-test is versioned with CLIFF 1.1.0. See the Git history for the complete record of changes.

## 1.1.0 — 2026

The suite follows CLIFF 1.1, which is a pure relaxation of 1.0: every 1.0
fixture still passes, and the checks below answer the 1.1 questions.

### Recorded

- **The decoder regime is the lever that moves the single-pass number: `reasoning:
  low` takes the same cell from 68.8 % to 87.5 %.** Same prompt (`spec`), same
  sixteen files, same arm (bare), same temperature, one repeat — run
  `clarion-deepseek-flash-20260921T171557+0000-4ef58c`, command
  `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch
  robustness --formats cliff --arms bare --repeats 1 --prompt-style spec
  --reasoning low`.
  - **14/16 = 87.5 % valid** (95 % Wilson 64–97 %) against 11/16 = 68.8 % with
    thinking off, and 7/16 = 43.8 % for the `examples` style. Fisher exact
    p = 0.39 between the two `spec` cells — n = 16 is not enough to call it — but
    the *failure list* changes kind, which is the part n = 16 can support: the
    meta-notes written into the file, the invented wrapper tags (`</langkau>`,
    `</final-direction>`), the entry marker carrying a comment on the corpus and
    the duplicated invented entries are all **gone**. What remains is two answers
    whose `expected a quoted string` fails on the longest classical-Chinese lines.
  - **Quality moves with it**, which no other lever did: chrF++ over all answers
    42.2 → **46.9**, and over the answers that survive 50.5 → **53.6** (`examples`
    off: 25.1 / 47.8). The compressed specification moved survival without moving
    quality; the thinking tier moves both.
  - **Cost**: output tokens 35 551 → **146 471** (2 221 → 9 154 per call, ~4.1x;
    thinking tokens are billed as output and are recorded per record, 1 257–12 596
    here), and wall clock 53 s → 141 s for the cell. A full run at this setting
    costs about four times its output budget, which is the price of the result.
  - **The two levers so far, measured in the same cell**: prompt content moved the
    number by +25 (compressed specification) and 0 (boundary statement) and −15
    (the affirmative rewrite); the decoder regime moved it +18.7 and moved quality
    for the first time. The stored runs could not have shown this: every 0.0 run
    also carried the full specification text, so temperature and prompt content were
    confounded, which is why `--temperature` and `--reasoning` now exist as
    per-run arguments.
- **Partial re-measurement of the affirmative prompt: CLIFF, both arms.**
  `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch
  robustness --formats cliff --repeats 3` in two passes, one arm each: run
  `results/clarion-deepseek-flash-20260921T163044+0000-da6d9d` (bare, 159 669
  prompt + 142 225 output tokens, 90 s) and
  `results/clarion-deepseek-flash-20260921T163515+0000-b943b1` (context, 230 772 +
  211 785, 91 s), plus a one-repeat first pass (`...-20260921T162803+0000-591dd9`).
  96 answers per wording, 0 provider errors. **Deliberately partial**:
  `robustness` is skipped, so the D7 rows are empty by construction, and this is
  the CLIFF cell of the ten-format comparison, not a table.
  - **Result: 47/96 = 49.0 % valid against 62/96 = 64.6 %** for the previous wording
    at the same settings (temperature 1.3, `prompt_style: examples`, the same
    sixteen files, three repeats). Fisher exact **p = 0.041** (Wilson 39.2–58.8 %
    against 54.6–73.4 %). Bare: 23/48 = 47.9 % against 28/48 = 58.3 %
    (p = 0.41). Context: 24/48 = 50.0 % against 34/48 = 70.8 % (**p = 0.060**).
  - **The failure mix names the two sentences that were cut**, which is why this is
    recorded as a finding rather than a shrug:
    - **Escaping and quoting**, which is `CLIFF_TASK_RULES` rule 5. Bare quoting
      failures went 5 → 11 (`unterminated string` 2 → 6, `expected a quoted
      string` 3 → 5), and the context arm adds `unknown escape sequence \` and
      `unknown escape sequence \u` plus three answers with an empty field name
      (`invalid field name ''`). The rewrite kept the positive half of rule 5
      ("each text value as one quoted string") and dropped the escape facts and
      the sentence that said the quoting error is the one nothing downstream can
      repair.
    - **The extent of the answer**, which is the sentence *"The answer begins with
      the first character of that file and ends with its last"* in the shared rules.
      Two context answers put content outside the file — one ends with a Chinese
      summary of what it did (*"本文已完成术语策略文件…"*), and three end with
      invented wrapper tags (`</langkau>`, `</params>`, a bare `<`) — and others
      carried a misplaced key (`unknown group key 'source'`, `unknown entry key
      'Emotion'`).
  - **Per file it is a widespread small loss, not a few files collapsing**:
    `godot-l10n` 3/3 → 1/3 (bare) and 3/3 → 2/3 (context), `lit-classical`
    3/3 → 1/3, `lit-drama` 2/3 → 1/3, `lit-modern` 2/3 → 1/3, `news-social`
    2/3 → 1/3, `ui-workbench` (context) 3/3 → 1/3; against improvements on
    `legal-privacy` (bare) 0/3 → 2/3, `news-wire` 1/3 → 2/3, `ui-console`
    (context) 2/3 → 3/3 and `wmt24pp` (context) 0/3 → 1/3.
  - **What this does not establish**: it is a before/after across two runs, not a
    randomised paired experiment. The provider may not serve the same model
    snapshot, the arms were run in separate passes, and several comparisons were
    made while stepping through the measurement, so one p near 0.05 is weaker than
    it looks. It is enough to justify a controlled re-measurement of the two
    sentences above, not enough to call the rewrite a regression on its own.
  - **The channel requirement's other half survived.** All 96 answers begin with
    `CLIFF 1.1`, so removing the sentence did not invite a preamble; what it cost
    was the tail and the wrapping.
- **The deployment-settings run: 1.3, the example-driven prompt, all ten formats.**
  `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch`,
  run `results/clarion-deepseek-flash-20260921T142211+0000-904a70`: 1 180 records
  (960 translation + 60 robustness chains + 160 fidelity), exit 0, 3 831 306 prompt
  + 3 813 836 output tokens, 34 minutes, **no truncated run**. This is the first
  translation measurement taken with the settings the pipeline actually ships, and
  the first in which the configuration's `prompt_style` reached the wire at all.
  - **C6.12, the modification-correctness number.** CLIFF, single-pass rewrite:
    bare **58.3 % valid, 75.0 % ids kept, 75.0 % coverage, 75.0 % source kept,
    0.38 repairs/answer, 41.7 % failed**; context **70.8 % / 72.9 % / 72.9 % /
    72.2 %, 0.79 repairs, 29.2 % failed**. The other nine formats' rows are in the
    report; CLIFF is the **least surviving** of the ten (android 91.7, fluent 91.7,
    json-cliff 91.7, json-plain 91.7, xliff-2.1 97.9, ios 89.6, po 89.6,
    yaml-cliff 85.4, csv 83.3) and, on the answers that do survive, the **best**
    (chrF++ 53.3, the highest of the ten).
  - **Why it fails, from the stored answers** rather than from the rate: the
    dominant error is `status 'translated' requires a target field` — the model
    drops entries or their `target` lines and leaves the status behind, which is
    also what the 252 (bare) and 333 (context) missing identifiers count. Then the
    1.3 quoting degradation (`expected a quoted string`, `unterminated string`,
    `expected 'key: value' or 'key = value' field`). Failures cluster **by file**,
    all three repeats together, on the files whose values are longest
    (`hongloumeng-joly` emits 6–20 k output tokens for 14 entries). **Not an output
    budget problem**: 0 runs hit the ceiling.
  - **D7 at the same settings**: CLIFF bare **100.0 % still valid / 95.2 % intent
    applied**, context **100.0 % / 94.4 %**; xliff-2.1 bare 47.6 %, the only format
    below 97 %. Editing and translating are different tasks, and the format that is
    most robust to being edited is not the one that survives being rewritten.
  - Round-trip fidelity: CLIFF **100 %** retention, csv/json-cliff/yaml-cliff/
    xliff-2.1 100 %, android/fluent/ios/po 97.6 % (header fields only), json-plain
    67.3 %.
  - **Not comparable to the 0.0/digest run.** Two variables changed at once
    (temperature and prompt style), so the difference between 89.6 % and 70.8 %
    cannot be attributed to either. The 1.3 pilot that varied the prompt style
    alone measured 61.5 % (digest) and 65.4 % (examples) on the same files, which
    places this run in the temperature regime rather than the prompt regime.
  - **One caveat on the cross-format comparison**: only CLIFF's prompt changed in
    the redesign, so in this run CLIFF is measured on the example-driven prompt
    while the other nine still carry their established instructions. A format
    ranking that mixes the two protocols is not a like-for-like claim.
- **The CLIFF edit baseline at the shipped temperature 1.3**, which no earlier
  D7 number could be: `python .tools/d7_cliff_13.py --passes 3`, CLIFF only, the
  `ui` stratum, the same 12 edits, 171 applicable edits, every answer kept
  (`results/d7-cliff-13/`). **97.7 % still valid / 95.9 % intent applied**, per
  pass 96.5 / 93.0 / 98.2 on intent and 1.0 point of standard deviation on
  validity. Against the 0.0 rows (100 % / 98.6 %) the difference is the decoder.
  All seven failures are attributed from the stored answers in
  [docs/clarion-prompt-design.md](docs/clarion-prompt-design.md): four answers were
  not CLIFF (an unquoted text value, a period outside the closing quote, an
  unquoted string as a list value, and one 32-byte `<support>...invalid...</support>`
  stub), three were valid but did not apply the instruction (a reproducible no-op
  on `set-emotion`, an invented target value, and a rename applied to a group
  rather than to an entry of the same name). Repairs the model introduced were
  confined to `add-reference` (5) and `set-emotion` (2).
- **The first benchmark run on the 1.1 corpus and the current model name**:
  `python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch`,
  model `deepseek-flash`, `read_mode: tolerant`, 3 repeats per cell over
  CLARION-Core 0.3.0 (16 documents, 392 entries). Run
  `results/clarion-deepseek-flash-20260920T114819+0000-6a5259`: 1 180 records,
  exit 0, 960 translation runs + 60 robustness chains + 160 fidelity
  conversions, 5 598 954 prompt + 4 172 463 output tokens, 53 minutes, no
  truncated run.
  - CLIFF **chrF++ 51.2 plain / 53.9 context**, instruction-following
    79.5% / 83.0%, round-trip context retention **100%**, still valid after
    edits **100.0% bare / 83.3% context**.
  - `--skip fetch` is deliberate and recorded in
    [docs/acceptance-criteria.md](docs/acceptance-criteria.md): the fetch cache
    was empty, so importing again would have rewritten the committed corpus —
    the 118 `human_verified` items, their checksums and their attribution — and
    spent several hundred extra annotation calls on the same model as the system
    under test, which `clarion/corpus/annotate.py` warns against.
  - **The two readings measured on the same answers**: re-scoring the 96 stored
    CLIFF answers with no model call gives strict valid 89.6% / 83.3% against
    tolerant valid 93.8% / 89.6%, at 0.06 / 0.12 repairs per answer. All six
    repairs were shape repairs; one `wmt24pp` answer claimed
    `status: translated` on an entry with no `target`, which both readings
    refuse (Appendix C.5). This is the number that makes the tolerant mode worth
    having, and it could not be produced before this revision.
  - 61 of 960 runs failed to parse, all in the two formats that cannot carry
    multi-line context cleanly (`csv` context writes a newline into one row and
    shifts every later column; `xliff-2.1` context emits malformed XML). Each
    was inspected in the stored answer text rather than read off the summary.
  - Correction: the D1/D2 prompt columns of [BENCHMARK.md](BENCHMARK.md) are
    restated from the regenerated tables, because `token_matrix` had been
    pricing a CLIFF prompt no arm sends.

### Changed

- **The prompt now states what the specification requires and what we need back,
  and nothing else.** Two rules, applied to every block all ten formats receive:
  state the rule affirmatively (a sentence that names the failure — "an unquoted
  text value cannot be repaired", "never a diff" — describes a shape a model can
  produce), and do not constrain the model's working method. `SYSTEM_ROLE` opened
  with *"You always return a complete file, never a diff and never a commentary"*:
  a prohibition where the deliverable belongs, naming two failure shapes, paid for
  by all ten formats. It now reads *"We need the translated file itself, complete:
  the file we gave you, with its text in the target language and its structure
  intact."* Reproducing the file and editing it in place is a good method, and the
  prompt's job is to say what the answer is, not how to get there.
  - `TASK_RULES` lost its `Hard rules:` framing and the clause *"in its original
    order and count"*: no specification section requires entry order, so that was
    our bookkeeping stated as a rule. It now lists properties of the delivered
    file.
  - `CLIFF_TASK_RULES` is titled **WHAT WE NEED IN CLIFF** and every item is a
    property of the delivered file, not an imperative. The title had to change
    twice: it was first rewritten to **WHAT WE NEED**, which is also the shared
    block's heading, so one message carried two numbered lists under the same
    heading and read as one list restarting at 1. Rule 5 keeps the quoting rule
    (the one shape error no reading repairs, C.5) and drops the half-sentence that
    named the failure; the boundary itself is unchanged and still asserted. Rule 2
    now states only the fields the shared rules do not already cover, since
    "every identifier, key, group path and structural element" is rule 2 of the
    shared block and saying it twice cost tokens for nothing.
  - `GLOSSARY_WORKFLOW` no longer caps the optional glossary (*"keep it concise …
    stop after the last needed term"*). It cites specification 13.2.2 instead,
    which is where the criterion for when a glossary is warranted and what belongs
    in it actually lives. `GLOSSARY_DELIVERABLE` and `OUTPUT_RULES_BILINGUAL` lost
    one prohibition each (*"concise"*, *"leave the source field untouched"*).
  - `CLIFF_EDIT_SAFETY` (the `digest` style's reminder) states the same facts as
    properties rather than as a *"copy exactly as written"* imperative.
  - **Priced, because these blocks reach every call of every format**:
    `tools/prompt_block_delta.py <ref>` prints the delta per block against a
    revision. Against the state before the rewrite: CLIFF task rules **−91**, shared
    task rules **−15**, glossary deliverable **−6**, CLIFF facts **+8** (the
    orientation paragraph), system role **+13**, output shape **+5**, glossary
    workflow **+17**, edit safety **+2** — net **−67 tokens per call**. The prompt
    was *cheaper* after the rewrite, not dearer. The original figures here said
    "facts **+115** … net **+24**": the tool was comparing each block's template
    source against the live rendered string, and `CLIFF_FACTS` is an f-string whose
    `{_row(...)}` calls are long in the source and short in the value, so it
    invented a 107-token difference in a block that had barely moved. The tool now
    executes the previous revision and reads the attribute, and
    `tests/test_prompt_cost_tool.py` holds both ends together.
    The prompt-cost table in `docs/clarion-prompt-design.md` is re-measured through
    the assembly path and reads **21 092 → 2 410** tokens for the `ui-console` plain
    cell (the older 20 739 / 2 630 figures are superseded; the specification text
    alone grew from 16 316 to 16 656 tokens).
  - The rule is held by
    `tests/clarion/test_tools.py::test_no_prompt_block_fences_the_working_method`,
    which names the phrases an edit would add back,
    `test_the_two_rule_lists_in_one_message_have_different_headings` (the
    duplication test compares paragraphs longer than 40 characters and cannot see
    a repeated two-word heading), and `tests/clarion/test_prompt_v2.py`, which
    holds the CLIFF blocks to the repairable/unrepairable boundary in both
    directions.
  - Two assertions in `tests/clarion/test_cli.py` and `tests/clarion/test_tools.py`
    pinned the literal heading **FIELD NAMES AND THEIR SCOPE** and went stale when
    the facts block was retitled. Both now read the marker from
    `cliff_prompt_v2.CLIFF_FACTS`, so a retitle cannot leave an assertion pointing
    at a string that no longer exists.
  - **Not yet measured by a run**: the recorded deployment run sent the previous
    wording. This is recorded as an open decision in
    `docs/clarion-prompt-design.md` rather than quoted as a result.
- **`tools/cliff_validator.py` follows the relaxed `name` production**
  (`A-Z a-z 0-9 _ -`, never `.`) and keeps tags narrow via a separate
  `TAG_NAME_RE`. A near-miss tag is reported as a `vocabulary` error listing the
  allowed values, and a quoted tag is a shape error in strict mode.
- **Strict mode is strict again.** The validator previously accepted a bare
  scalar in a list-typed field (`emotion: neutral`) and a quoted tag. Both are
  errors under specification 6.1; the relaxations exist only in `--tolerant`.
- **Layout mismatches are warnings by default** (`layout` category), because
  1.1 recommends a layout rather than requiring it. `--check-layout` reports
  them as errors for a project that enforces the convention.
- Tolerant reading of the version line accepts `CLIFF 1.0` and `CLIFF 1.1`; an
  unimplemented version is rejected with the supported versions named.
- **CLARION reads model answers in the tolerant mode CLIFF 1.1 defines for a
  translation pipeline** (specification Appendix C), and can be switched to the
  strict, reference-toolchain reading with `read_mode` / `--read-mode`. Every
  translation, robustness and fidelity row records the mode and the number of
  repairs it took, and the D3/D4/D7 tables carry both, so a row can always state
  which question its number answers. Until this change the Appendix C path was
  unreachable from CLARION: `check_validity` and `parse_back` were always called
  in strict mode, so an answer a model punctuated the way models punctuate was
  scored as a format failure.
- **The CLARION-Core corpus declares CLIFF 1.1.** All 18 documents moved from
  `CLIFF 1.0` to `CLIFF 1.1`, and the manifest version moved to `0.3.0` to match
  the version the benchmark documents and the dataset card already carried. The
  documents' content is unchanged, field for field: a version-line move is not a
  rewrite, and the corpus is deliberately *not* in canonical serialized form
  (field order, adjacent-string continuation lines and the licence comment blocks
  are author choices that a serializer would normalise away). `tools/corpus_version.py`
  is the guard: it changes the version line and nothing else, and proves it with
  a semantic fingerprint of every field plus the gold manifests' provenance
  digests.
- 1.0-era labels replaced where they named the current specification: the format
  registry label, the token benchmark's emitters, result keys and report titles,
  the edit-robustness and quality prompts and their reports, and the corpus
  authoring specification.
- **Token-cost prompt columns corrected.** `token_matrix` built its prompt
  without `allow_glossary_output` and `workflow_style`, and never accounted for
  the reference specification that only the CLIFF prompt carries (16 316 tokens
  per cell). CLIFF's D1/D2 prompt totals were therefore roughly half of what the
  translation arms actually send; the other nine formats were correct, and the
  document-token columns were never affected.

### Added

- **`prompt_style: spec` — the specification compressed to its rules, assembled
  from the specification repository.** The format's own text is 16 656 tokens, of
  which only **2 467 are sentences that state a rule**; the rest is motivation,
  examples, comparisons and migration notes. `clarion/prompts/cliff_rules.py`
  builds a **2 252-token** prompt block out of the parts that state rules and
  nothing else: the ABNF with comments stripped (613), the ABNF's semantic-
  constraint block (794, where required fields, the `status`/`target` dependency,
  the escape rules, brace balance, list-typed fields and identifier case already
  live), the field tables of sections 7-9 (258, extracted from the specification's
  own markdown), the closed vocabularies and the rules that frame them (414), and
  the specification's own quick example (173).
  - **Nothing in it is hand-written**, which is the difference between this style
    and `examples`: a hand-maintained restatement is a second source of truth, and
    the second source is the one that goes stale. `tests/clarion/test_spec_digest.py`
    holds the trace: the extracted key tables are compared against the key sets the
    parser accepts (`HEADER_KEYS`/`ENTRY_KEYS`), the inherited set against section 9,
    the vocabularies against the implementation, `SECTION_COVERAGE` must account for
    every section of the specification that states a rule (represented, or excluded
    with a reason), and the token ceiling is asserted so growth fails here rather
    than in a paid run.
  - The style is reachable per run without editing a configuration:
    `--prompt-style {digest,examples,spec}` on `pipeline` and `translate`, because a
    run directory records the configuration it was started with and two styles have
    to be switchable inside one session to be comparable.
  - Assembly fixes that came with it: the `spec` style no longer appends the full
    specification text (the first assembled `spec` prompt came out at 20 016 tokens
    - the digest *plus* the text it replaces), and it drops the hand-written
    `FORMAT_NOTES`, `CLIFF_TASK_RULES`, `GLOSSARY_WORKFLOW` and edit-safety blocks,
    each of which restates rules the specification block already carries.
  - **First measurement** (CLIFF, bare, sixteen files, 1.3, one repeat, run
    `clarion-deepseek-flash-20260921T164514`): **11/16 = 68.8 % valid against
    7/16 = 43.8 %** for the `examples` style in the same cell, six files flipping
    from a parse failure to valid and two the other way. **Not significant yet**
    (Fisher exact p = 0.25, n = 16 on one side) and recorded as a direction to
    confirm at three repeats, not as a result.
  - **Second measurement, with the answer boundary stated** (same cell, same
    settings, run `clarion-deepseek-flash-20260921T171241`, +14 prompt tokens):
    **11/16 = 68.8 % again.** The number did not move, and the failures are the
    finding: two files were fixed and two broke, while the behaviour that was
    supposed to be fixed persisted in new spellings — a bare `[CONTINUATION VIA
    NOPER])</chapter-1-004>` inside a `target` value, `</final-direction></final-direction>`
    on its own line, an entry marker whose id is the field name `source`, and the
    same duplicated entry (`abstract-2`, missing `source` and `status`) that the
    first run had. **Conclusion: the remaining failures are not a missing
    instruction.** Two different prompt-content levers have now been tested in the
    same cell (the rewrite, −15 points; the boundary statement, 0 points) and the
    failure rate did not respond to either, which leaves the decoding regime as the
    variable still standing.
- **`tools/prompt_cost.py` and `tools/prompt_block_delta.py`, with
  `tests/test_prompt_cost_tool.py`.** The prompt-cost table in
  `docs/clarion-prompt-design.md` is quoted in this changelog and in the acceptance
  criteria, and until now the instrument that produced it lived in the working-copy
  `.tools/` directory outside the repository — a number a reader cannot reproduce is
  a number they have to take on trust. `prompt_cost.py` prints the per-component
  table for one cell (`--pilot` for the four pilot files, `--block-delta` for the
  per-block token delta against the last commit, which `prompt_block_delta.py` also
  does on its own). Both styles are assembled through `build_translation_prompt`,
  the call path a run uses; the earlier measurement projected the example-driven
  side arithmetically and drifted the moment the assembly changed. The test pins
  what the document publishes, and checks the invariant that catches this table's
  own failure mode: every column's rows sum to that column's total.
- **A quoted key is now a repaired deviation (specification Appendix C.2.7).**  The specification gained the relaxation, so this suite gained the fixtures that
  decide it: `tests/fixtures/tolerant/quoted-key.zh-CN.cliff` carries the three
  spellings (double quotes, single quotes, `=`) in header, group and entry scope
  and is repaired as three `name-quote` repairs, and
  `tests/fixtures/tolerant/quoted-unknown-key.zh-CN.cliff` **must still be
  refused** — the repair removes the quotes and then checks the word against the
  legal keys of its scope, so the relaxation is what lets the line reach the key
  check, not what lets it pass. `tests/run_all.py` lists the second file in
  `UNREPAIRABLE`, `tests/clarion/test_read_modes.py` pins the repair count by
  category, and the boundary is recorded in `docs/clarion-methodology.md`
  (§9.1) and in the prompt-design fact table: because the relaxation cannot
  legalize a word, the prompt still spends no token on it, and
  `tests/clarion/test_prompt_v2.py` now rejects the phrasings a helpful edit
  would add back ("quote a key", "unquoted key", "keys are bare").
- **`CLIFF_TASK_RULES` rule 5: the quoting rule the prompt was missing.** The
  design table has always listed "an unquoted string" as unrepairable and therefore
  as something the prompt must state, and the prompt taught quoting by example only.
  Two of the four invalid answers in the 1.3 edit run were exactly that. The rule
  states the unrepairable fact and nothing else — a text value is one quoted string
  with its final punctuation inside, and the same holds inside a list — so it says
  nothing about tags or brackets, which a tolerant read repairs (C.2.3, C.2.1).
  `tests/clarion/test_prompt_v2.py` now guards both directions: the fact is present,
  the repairable phrasings are absent. Cost **+120 tokens per call**; the prompt cost
  table in docs/clarion-prompt-design.md moves from 2 510 to **2 630** per cell, and
  the specification text the redesign replaced was 16 316.
- **The modification-correctness table the benchmark quotes**:
  `clarion/report.py` gained `structure_report`, rendered between D4 and latency.
  Per format and arm it prints `valid %`, `ids kept %`, `coverage %`,
  `source kept %`, `repairs/answer` and the counts of extra, missing, drifted and
  untranslated identifiers — the question the quality tables do not answer: did a
  single-pass rewrite hand back the document it was given. Dimension 7 measures
  something else (whether a file survives twelve sequential edits) and is
  deliberately not the source of these numbers. `test_pipeline.py` asserts the
  discrimination that justifies the table: an answer that is a **valid** CLIFF file
  while having dropped three of four entries must read as 100 % valid and 25 %
  coverage, in those columns and no others.
- **`tests/clarion/test_secrets.py`** (8 tests): `clarion/secrets.py` is the only
  module that reads an API key and the only one that claims a tree is clean, and it
  had no test. The suite pins the lookup order, the absent-key return,
  `install_key`, and that `scan_tree` catches each credential shape it advertises
  while skipping the places a key is supposed to live.
- **`tests/clarion/test_roundtrip_fields.py`** (70 cases): every format must read
  back each field it wrote, in both its single-valued and multi-valued form.
  `roundtrip_fidelity` answers this in aggregate and the corpus hides the failure —
  it holds only two entries with a multi-valued list, so a codec that loses the
  second element of every list still scores 98 %. The two json-plain cases where a
  `|` separates both list items and fields are pinned with a **strict** xfail, so
  fixing that codec becomes an XPASS failure rather than passing quietly.
- **CI runs the whole suite.** The workflow ran `python tests/run_all.py` and
  nothing else, so the harness tests, the lint gate, the corpus guard and the
  offline self-check never ran on a push. It now checks out the sibling `cliff` and
  `cliff-python` repositories and runs `run_all.py`, `tools/corpus_version.py`,
  `ruff check clarion tests/clarion`, `pytest` and `python -m clarion selfcheck`.
  `make check` runs the same five steps in the same order.
- **`testpaths` is `tests/`, not `tests/clarion/`.** A bare `pytest` collected 245
  tests and silently never collected `tests/test_validator_tool.py` or
  `tests/test_edit_robustness.py` — eleven tests that existed and did not run. It
  now collects 381 plus the two pinned xfails.
- **`tests/clarion/test_judge.py`** (13 tests): the optional MQM judge is disabled
  by default, so nothing in a default run exercised it. The suite pins the parts
  that fail silently — JSON wrapped in prose must still be read, a missing object is
  an error rather than a score of zero (a zero would look like a bad translation),
  a malformed error entry is skipped instead of crashing the run, the published
  severity weights, the clamp at zero, and that the group score excludes entries the
  judge never answered.
- **C6.12 in `docs/acceptance-criteria.md` names the modification-correctness
  criterion and its source.** It is the `D3/D4 - structural integrity of the
  rewrite` table of the single-pass translation task. The document now states why
  C4 (100 sequential edits) and C6.8 (twelve sequential edits) are *not* that
  number: they measure whether a file survives being edited repeatedly, which
  production never asks for, so the two must not be quoted for each other.
- **`tests/clarion/test_gutenberg.py`** (12 tests): the last module no test
  touched. `download` needs the network and is not exercised; everything downstream
  is pure text work and is, which matters because the licence header is cut at a
  marker pair — an error there shifts every aligned paragraph in the corpus. The
  suite pins the marker cut, the CRLF normalisation, both heading forms (`CHAPTER
  <roman>` and `第N回`), the two paragraph layouts (blank lines, and hard-wrapped
  lines where a new paragraph starts with an ideographic space), and the minimum
  length filter. It also **pins a real inconsistency** rather than asserting it
  away: `_EN_CHAPTER` begins with `^\s*` and `\s` matches newlines, so a heading
  preceded by a blank line makes the chapter's block begin with `\n`,
  `split_chapters` then takes the `chapter N` fallback title, and the heading text
  is lost as a title. The corpus already carries that form in its context strings,
  and the paragraphs (what alignment consumes) are unaffected.
- **`tests/clarion/test_cli.py`, `test_openai_compat.py`, `test_pipeline_module.py`** —
  three modules a quarter of the harness by size that no test imported, found by
  `tools/coverage_audit.py`, which now reports **53 of 53** modules under `clarion/`
  reachable from the suite:
  - `tests/clarion/test_cli.py` — the command surface: every top-level command
    answers `--help`, the command list is compared against a written-down set so
    adding one is deliberate, and `corpus validate`, `corpus stats`, `secret-scan`
    and `selfcheck` run end to end offline, which also exercises the corpus lint and
    the credential scan behind them.
  - `tests/clarion/test_openai_compat.py` — what goes on the wire: the temperature
    the request carries, `extra_body` precedence, the per-vendor reasoning switch,
    the endpoint and header, usage and finish reason, and the retry policy in both
    directions (429 retried, 401 not). `httpx.Client` is scripted, so no socket is
    opened. It found the retry defect fixed above.
  - `tests/clarion/test_pipeline_module.py` — the orchestrator: a run reaches its
    report and summary, a skipped stage does not run, a failing stage reaches the
    exit code instead of only the log, and the report is still written when a stage
    fails.
- **`ruff check .` passes over the whole repository.** The lint gate had only ever
  been run over `clarion` and `tests/clarion`, because the rest of the tree carried
  148 findings — 26 in `tools/` and ~90 in the edit-robustness task table. The code
  findings are fixed (an unused variable, an unused import, `.format` in an
  f-string context, two f-strings with no placeholders, `zip()` without `strict`,
  two ambiguous `l` names, and ~30 long lines wrapped); the two that remain are
  **embedded documents** — the README a benchmark bundle ships and the 100-edit task
  table — and are waived per file in `pyproject.toml` with the reason written down,
  because wrapping them would obscure the bytes under test without changing one.
  CI and `make check` now run `ruff check .` rather than a subset.
- **`make check` and CI now run the same six steps**, in the same order, including
  the credential scan: a key pasted into a test can no longer reach a commit
  unnoticed.
- **`tools/coverage_audit.py`** — the reachability audit, in the repository rather
  than beside it, so the claim "no module is untested" is checkable by whoever reads
  it. It resolves relative imports and walks the graph, because a text search reports
  the eight modules a package re-exports as phantom gaps.
- **`--check-layout`**, **`--style`**, and **`--tolerant`** modes, each with its
  own fixture suite: `tests/fixtures/layout/`, `style/`, `tolerant/`.
- **Optional line terminator** support (`CLIFF 1.1` §5.6) in the strict parser,
  with `tests/fixtures/valid/valid-terminators.zh-CN.cliff` and
  `tests/fixtures/invalid/double-terminator.zh-CN.cliff`.
- **`tests/run_all.py`** now states the mode and the expected exit code of
  every suite, checks both spec example directories, and warns when the
  tolerant refusal set (Appendix C.5) is empty.
- `--tolerant` delegates to `cliff_format`, so the tolerant contract has exactly
  one implementation in the ecosystem.
- **`--read-mode {strict,tolerant}`** on the CLARION commands, plus the
  `read_mode` run-configuration key.
- **`read_mode` and `repairs`** on every translation row, robustness outcome and
  fidelity record; `repairs/run`, `repairs/edit` and a `read mode` column in the
  report tables.
- **`--multi-document`** on the validator: an answer may hold a translated file
  *plus* the glossary the terminology workflow produced, and each document is
  validated on its own (concatenating two valid documents is not one valid
  document). Fixture: `tests/fixtures/tolerant/two-documents.txt`.
- **Three tolerant fixtures** pinning the repair set by category, including one
  whose every line ends with `,` / `;` to assert that a line terminator is
  syntax and not a repair: `terminators-and-quoted-tags.zh-CN.cliff`,
  `quoted-id-and-bare-list.zh-CN.cliff`, `two-documents.txt`.
- **`tools/corpus_version.py`**: the corpus version-line guard and migration,
  with a semantic fingerprint that makes "only the version line changed" a
  checkable claim.
- **Tests**: `tests/clarion/test_read_modes.py` (the two readings, per-category
  repair counts, Appendix C.5 refusals, document splitting, comment lines that
  mention a version), `tests/clarion/test_corpus_1_1.py` (the corpus's declared
  version, strict validity, zero repairs, provenance digests, gold agreement),
  `tests/test_validator_tool.py` (the validation modes, including the
  multi-document contract), and a prompt-parity test in
  `tests/clarion/test_tools.py`.
- **`tests/clarion/test_edit_request.py`**: the temperature contract for the edit
  dimension — the request carries the value it is given (0.0 / 0.7 / 1.3), the
  matrix forwards `provider.temperature`, and the CLIFF field table is present
  under `examples` and absent under `digest`.
- **The temperature a request was actually sent at** is recorded per row
  (`RobustnessResult.temperature`, `TaskResult.temperature`), not only in the run
  directory's `config.json`. A record that carries the configuration alone cannot
  show a divergence between the two, which is exactly how D7 spent its whole
  history sending 0.0 while its `config.json` said 1.3.
- **A CLIFF intent assertion in `clarion/selfcheck.py`**: the deterministic
  reference application must not merely keep the file valid, it must apply the
  edit (100 % on both arms). The validity-only check could not see the silent
  failure shape this dimension exists to detect — a legal file whose instruction
  never landed. Scoped to CLIFF deliberately: json-plain fails it for a codec
  reason (a `|` used both inside a list value and between fields, so a
  multi-valued `reference` or `emotion` loses every element after the first on
  read-back), which is a defect of a format outside the question this benchmark
  now answers.
- **`docs/clarion-prompt-design.md`** records the temperature defect, the XLIFF
  attribution correction and the repair-attribution correction alongside the
  existing metric-error note, so the method's own mistakes are readable rather
  than only their fixed results.
- Appendix C.4 behaviour documented from what the implementation actually does,
  after the recorded run contradicted the first draft of the note: a collision
  that normalization *creates* is disambiguated (`-2`, `-3`, …) and reported as
  an `id-collision` repair, while a duplicate id the author wrote twice is still
  rejected in both readings (10.2). The two cases are distinguished by whether
  the ids became equal through normalization.
- `docs/clarion-methodology.md` §9.1 states what each reading answers, which
  repairs exist, what a terminator is not, and which C.5 refusals hold.

### Fixed

- **The Fisher exact test in the prompt-analysis scripts was wrong, and three
  published p-values were corrected.** `clarion.metrics.stats` had bootstrap,
  permutation, McNemar and Wilson but no Fisher test, so the two working-copy
  analysis scripts carried their own - and its combinatorial helper ignored the
  table it was asked for, returning the *observed* table's probability for every
  candidate table. The p-value was therefore that probability summed once per
  table with the same margins, capped at 1: for 9/48 against 0/48 (invented-key
  failures, 48 edits per condition) it reported **0.0129** where the answer is
  **0.0026**, and it could never report anything below that product - so it could
  only ever *understate* a difference, never invent one.
  - `fisher_exact` now lives in `clarion/metrics/stats.py`, next to the other
    exact tests, is enumerated over `fractions.Fraction` probabilities (exact, no
    approximation, no overflow), and is tested in `tests/clarion/test_stats.py`
    against hand-computed tables **and** against the shape of the defect: the test
    asserts both the corrected value and that it is not the observed probability
    times the table count.
  - Corrected in place: `docs/clarion-prompt-design.md` (the invented-key
    comparison, 0.0129 → **0.0026**; and the prompt pilot's per-file claim, which
    now quotes the two real values, 1.0000 over all files and 0.7319 for the worst
    file, instead of a saturated "1.000 throughout"),
    `docs/clarion-methodology.md` and `docs/acceptance-criteria.md` (0.0129 →
    0.0026). Every affected conclusion survives and one gets stronger: the
    corrected p is smaller than the published one, so a "no difference" claim that
    rested on the defective test was never in the dangerous direction, but it was
    unsupported by that number and is now stated with a correct one.
  - The working-copy scripts import the tested implementation instead of carrying
    copies, which is the same rule the tools directory follows.
- **The translation path ignored `prompt_style`.** `run_translation_task` called
  `build_translation_prompt` without the argument, so the dimension silently used
  `DEFAULT_PROMPT_STYLE` whatever the configuration said: a run whose config, run
  directory and report header all named `examples` actually sent the digest. Every
  translation number recorded so far, and every D3/D4 row, was measured on the
  digest prompt. `token_matrix` had the same omission, so the D1/D2 prompt-cost
  columns priced the digest too. This is the third instance of one shape — a setting
  the configuration carries, a code path that builds its own prompt and never reads
  it, and a run directory that records the configuration so nothing looks wrong. The
  first two were the edit path's temperature and the D1/D2 glossary arguments.
  - **Why the parity test did not catch it.** It rebuilt the prompt's argument list
    by hand and compared token counts, so it reproduced whatever the code omitted:
    both sides left out `prompt_style` and agreed. It now compares the matrix against
    a **real run** through a recording provider, and asserts that the style the
    configuration names is the style in the system message the run sends. The
    dry-run test for the final measurement (`test_cli.py`) does the same for the path
    the paid run takes.
- **A 4xx that is not a rate limit was retried like a transient failure.**
  `openai_compat.complete` catches `Exception` around `raise_for_status()`, so a
  401 or a 400 — a rejection that cannot change — was resent `max_retries` times,
  paying for the same refusal three times and delaying the failure. Only 5xx and
  429 are transient now; any other 4xx returns on its first attempt with the status
  and body in `error`. Found by `tests/clarion/test_openai_compat.py`, which was
  written to assert the retry policy the docstring already promised.
- **`scan_tree` had no way to tell generated test scratch from a real leak.** The
  suite that tests the scanner writes credential-shaped strings on purpose, so a
  project-tree scan reported the test that tests the scan and the pre-push gate
  could never pass. `GENERATED_DIR_NAMES` is now skipped in a tree scan while an
  explicit `root` is still read in full, which is what lets the scanner's own tests
  watch a planted credential be found. The test literals are assembled at run time
  so the test files themselves do not trip the scan either.

- **The edit dimension ignored the configured temperature.** `run_robustness`
  built its own `CompletionRequest` with a hard-coded `temperature=0.0`, and
  `build_provider` never passes a temperature to the provider at all, so
  `provider.temperature` reached the wire only through the translation path. Two
  consequences: **every D7 number published so far is a 0.0 number**, including the
  rows labelled as the deployment settings, and `d7_pilot.py --temperature 1.3`
  was a no-op that changed a `ProviderConfig` field nothing reads. The controlled
  CLIFF comparison survives (both its columns are the same model, the same `ui`
  stratum, the same 12 edits and an unedited `EDIT_SYSTEM`, so only the prompt
  differed), but no claim about D7 at 1.3 was ever supported, and a 1.3
  measurement is now owed. The temperature is a parameter of `run_robustness`,
  forwarded from the configuration, and
  `tests/clarion/test_edit_request.py` fails with `{0.0} == {1.3}` if the
  forward is dropped. Related corrections recorded in
  [docs/clarion-prompt-design.md](docs/clarion-prompt-design.md): the D7 pilot
  table's "temperature 1.3" heading, the "re-run at the shipped settings"
  section, and the attribution of the XLIFF row — the 100.0 % it was compared
  against belongs to the frozen `deepseek-v4-flash` benchmark, not to this model,
  whose same-run baseline is 57.1 %, so that difference is a model change rather
  than a temperature or prompt effect.
- **The published repair attribution for D7 counted re-counts as repairs.** A
  record's repair count is the count for the whole document at that step, and the
  answer text carries forward, so one deviation is counted again by every later
  step: the six CLIFF context cells sum to 44 per-step repair counts but the model
  introduced only **6** (`add-reference` 4, `set-emotion` 2). Attributing the sum
  per operation charged early operations for deviations introduced later.
  `.tools/d7_audit.py` now prints both figures and warns if the counts are not
  monotone within a cell.
- **`clarion/experiments/robustness.py` annotated `answer_dir` with `Path`
  without importing it.** It survived only because
  `from __future__ import annotations` defers evaluation; ruff's F821 reports it
  now that the annotated name is resolved.
- **`tests/clarion/test_prompt_v2.py`** had its first-party import in the
  third-party block, so `ruff check` failed on the file that guards the prompt.

- **`split_cliff_documents` only recognised `CLIFF 1.0`.** An answer holding a
  1.1 translation plus a glossary was handed to a single-document parser as one
  blob, which failed and was scored as a parse error against the format. The
  splitter now matches either version line and requires the line to hold nothing
  but the version, so a licence comment that mentions "CLIFF 1.1" in prose is
  never mistaken for a document start.
- **Every tolerant repair was reported twice.** `_check_cliff` appended one
  `correction` warning per repair on top of the ones `validate_document` already
  emits, which would have inflated the repair column of any report.
- **`corpus_version.py`'s guard replaced a wrong assumption.** The first plan for
  the 1.1 migration used `serialize(parse(text)) == text` as the safety gate; all
  18 files fail it, because the corpus intentionally keeps author field order,
  continuation lines and comment blocks. The guard now checks a semantic
  fingerprint plus a strict line-level diff instead, which is the property that
  actually matters and which the old gate would have "fixed" by destroying
  readability and attribution.
- The corpus authoring specification described the stratum glossary as
  `glossary.<lang>.cliff` and as loaded by file name; the loader keys on the
  `variant: glossary` header, and the real files are named after the clan they
  serve (`ui-console-terms.zh-CN.cliff`), as the specification recommends. The
  document now matches the implementation.
- Stale corpus figures in the README, the acceptance criteria and the
  methodology (6 files / 111 entries from version 0.1.0) replaced with the
  measured 16 files / 392 entries of 0.3.0, and the published
  `results/clarion-core-tokens.md` regenerated.

### Moved

- `tests/fixtures/invalid/uppercase-entry-id.zh-CN.cliff` and
  `underscore-entry-id.zh-CN.cliff` → `tests/fixtures/valid/`: 1.1 accepts both.
- `tests/fixtures/invalid/filename-mismatch.zh-CN.cliff` and the three
  `invalid/ja-JP/` fixtures → `tests/fixtures/layout/`: their finding is a
  warning in 1.1.


