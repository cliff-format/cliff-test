# cliff-test Changelog

cliff-test is versioned with CLIFF 1.1.0. See the Git history for the complete record of changes.

## 1.1.0 — 2026

The suite follows CLIFF 1.1, which is a pure relaxation of 1.0: every 1.0
fixture still passes, and the checks below answer the 1.1 questions.

### Recorded

**The final measurement: the shipped protocol, ten formats, one pass.**
`python -m clarion pipeline --config configs/deepseek-flash.json --skip fetch`,
model `deepseek-flash`, **reasoning `low`**, temperature 1.3, `prompt_style: spec`,
`read_mode: tolerant`, 3 repeats, corpus CLARION-Core 0.3.0 (16 documents, 392
entries), revision `b81d3e6`, prompt fingerprint `6ef59ba44d454294`. Run
`results/clarion-deepseek-flash-20260921T211031+0000-de29a5`: 1 180 records, exit 0,
960 translation runs + 60 robustness chains + 160 fidelity conversions,
**3 993 022 prompt + 11 501 757 output tokens**, ≈ 57 minutes wall clock, **0
truncated answers in any cell**. Published as the bundle
`benchmark/clarion-2026-09-21`.

- **CLIFF's single-pass rewrite: 91.7 % valid, 91.7 % ids kept, 91.7 % coverage in
  both arms.** The other nine formats' rows are in `BENCHMARK.md`; CLIFF is above
  csv's bare arm (89.6 %) and xliff-2.1's context arm (79.2 %) under those formats'
  own, laxer checkers, and its own checker is the official validator — the strictest
  of the ten, so the column is comparable within a row and not across formats.
- **The two readings, same 96 answers, no model call** (`python
  tools/compare_readings.py`): bare strict 87.5 % / tolerant 91.7 % at 2 repairs;
  context strict 85.4 % / tolerant 91.7 % at 13. Every repair was a shape repair
  (C.2.5 identifier with a reserved character; one C.2.2 repeated field); none was
  salvaged by inventing content, which is what Appendix C.5 forbids.
- **After twelve sequential model edits**: 100.0 % valid / 95.2 % intent bare,
  86.1 % / 86.1 % context; mean over the 60 chains 96.3 %; xliff-2.1 is the only
  format below it. **Round-trip fidelity 100 %**, repairs per round trip 0.00.
- **The eight answers in 96 that still fail to parse are file-clustered**, six
  documents' worth, three of them the same classical-Chinese document; one failure
  is the `status`-in-a-group-section shape Appendix C.5 forbids a parser from
  repairing. `BENCHMARK.md` §11 lists them with the reader's own rejection message.
- **No reference-free QE pass**: `tools/qe_score.py` needs `unbabel-comet` and its
  weights, which were unavailable here, so no QE figure is claimed anywhere and the
  bundle carries no `qe_scores.jsonl`. `tools/audit_report.mjs` now omits the column
  rather than printing `0.00 (0)`, which is how a missing measurement was being
  published as a perfect score.

**What the exploration established, and the decisions it produced.** The rounds
that led here were per-cell experiments whose run directories are not kept; what
survives of them is this list, and every number above is from the run named in it.

- **The decoder regime is a lever, and it is not the prompt's.** `reasoning: low`
  moved both survival and quality where four prompt edits had moved quality not at
  all. It is what the shipped configuration selects, and it is why the output-token
  column has to be read as the decoder regime rather than as the format.
- **Removing content beats adding it.** The single largest prompt finding was that
  **this project had been injecting the failure it was trying to prevent**: the
  ABNF's comment block — which a prompt injects when it carries the compressed
  specification — said *"single-line marker; no closing tag exists"*, attributed the
  status tags to *"(XLIFF 2.x state model)"*, and spelled a stray closing tag
  literally in the C.5 note. De-cued, the answered-with-a-closing-tag rate fell to
  zero in the cell that measured it and came back at a few per cent in the next one,
  so the honest reading is that the cues were ours and a residual rate survives
  every variant measured. `cliff`'s CHANGELOG records the same finding.
- **The compressed specification is the shipped prompt.** `prompt_style: spec`
  renders the specification's own rules — ABNF, semantic constraints, field tables,
  closed vocabularies — extracted at build time, 2 925 tokens per cell against
  16 838 for the full text. It is the cheap prompt that still carries the rules, and
  `tools/prompt_cost.py` prices all three styles so the shipped one is never the one
  nothing measures.
- **Three prompt edits after that were measured, and two of them hurt**: a firmer
  restatement of the escape rule, a sentence stating the bare-word tag rule whose
  target it fixed while reintroducing stray closing tags elsewhere, and a third
  injection of the marker rule that changed nothing distinguishable. All were
  reverted or kept on that evidence, and the prompt now carries only what the
  specification requires and what the deliverable needs.
- **The prompt has a floor.** The residual failures are the corpus's own content
  rules (`instruction %` 78.7 — `require`, `forbid`, `max-width`, `name-policy`,
  `cjk-latin-space`, `regex`, `term`, `keep-verbatim`, `length-ratio`) in answers
  that parse, validate and carry every identifier, and a few per cent of shape
  slips concentrated in the longest classical-Chinese document. Neither is a
  prompt-shaped problem.
- **Vendor markup is real and is stripped.** Some answers arrive carrying the
  provider's own `｜DSML｜` tool-call delimiter at the document boundary — it is in
  no corpus and no prompt, and the request carries no tools. The tolerant reader
  strips it and reports a `provider-markup` repair, so it is priced rather than
  silently absorbed.
- **Two tools were wrong and are fixed**, both of which had published numbers: the
  edited `prompt_block_delta.py` compared a template's source against a live
  rendered value and invented a 107-token difference in a block that had not grown,
  and `clarion.metrics.stats.fisher_exact` summed the observed table's probability
  once per table, reporting 0.0129 where the answer is 0.0026. Both are held by
  tests now.

**Recorded this revision, in the harness's own words.**

- `python -m clarion corpus validate` — **16 files, 392 entries, 0 problems**.
- `python -m clarion corpus stats` — CLARION-Core **0.3.0**, six strata, 18
  `.cliff` files in the tree (16 standard documents plus two `variant: glossary`
  term files); 118 of 392 items `human_verified` (the imported corpora); the
  authored items are CC0 and still await sign-off.
- `python -m clarion tokens` — CLARION-Core document payload, `o200k_base`:
  CLIFF **24 322** tokens in the plain arm and **47 499** in the context arm,
  against 20 647–41 228 (plain) and 52 753–140 693 (context) for the other nine
  formats. The command also prices each prompt and its components.
- `python -m clarion selfcheck` — **SELF-CHECK PASS**, including the strict and
  tolerant readings differing exactly as Appendix C documents, and a repaired
  document serializing into one the strict grammar accepts.
- `python -m pytest` — **512 passed, 2 xfailed**; `python tests/run_all.py` and
  `python tests/run_all.py --quality --robustness` — **ALL PASS** (100/100 edits);
  `python tools/token_benchmark.py --check` — every tracked artefact matches what
  the tool renders; `ruff check .` clean; `python -m clarion secret-scan` — 0
  findings.

### Changed

- **The shipped protocol is now the one that was measured.** `configs/deepseek-flash.json`
  selects `prompt_style: spec` and `reasoning: low`, and `DEFAULT_PROMPT_STYLE` moves
  with it: the configuration had named `examples` with thinking off while every
  measured cell of the last round reached the compressed specification through
  `--prompt-style spec --reasoning low` on the command line, so a run started as
  documented measured a prompt the design work had moved past. The default matters
  for the same reason in the other direction — a configuration that names no style
  used to get `digest`, the 21 393-token legacy prompt, which is the one style that
  still sends the full specification text and with it the markup vocabulary removed
  from the other two. `tests/clarion/test_cli.py` asserts the shipped style, the
  shipped reasoning tier and the temperature that reaches the wire, so a silent
  revert to the old protocol fails the suite rather than the paid run.
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
    `tools/prompt_block_delta.py <ref>` prints the delta per block against a git
    revision, and against the state before the rewrite it showed the prompt was
    *cheaper* after the rewrite, not dearer. The original figures in this entry were
    wrong in a way worth recording: the tool compared each block's *template source*
    against the live *rendered* string, and `CLIFF_FACTS` is an f-string whose
    `{_row(...)}` calls are long in the source and short in the value, so it invented
    a 107-token difference in a block that had barely moved. The tool now executes the
    previous revision and reads the attribute, prices the composed specification
    block and the hand-written paragraphs inside it as well as the module strings, and
    counts each block once rather than counting a paragraph and the block containing
    it twice; `tests/test_prompt_cost_tool.py` holds both ends together.
    The prompt-cost table in `docs/clarion-prompt-design.md` is re-measured through
    the assembly path: for the `ui-console` plain cell, `digest` **21 393**,
    `examples` **2 417**, `spec` **4 142**, against a 16 838-token reference-specification
    block for the `digest` style.
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
  - **Measured at last.** The final run at the head of this entry is the first
    protocol carrying this wording, so the CLIFF numbers above are its numbers. The
    earlier deployment run sent the previous wording, which is why the rounds in
    between are recorded in this file as decisions rather than as results.
- **A paragraph for the rule the ABNF comment carried, which comment-stripping had
  been deleting.** `grammar_only()` removes every `;` comment, and one of them states
  a rule the prompt therefore never made: the ABNF says of `entry-line` that it is a
  *"single-line marker; no closing tag exists"*. The compressed block now states it
  affirmatively (`SECTIONS AND ENTRIES ARE SINGLE LINES`: a marker stands alone and
  what it opens runs to the next marker or the end of the file), injected at the top
  and the end of the block and once more in the user message immediately before the
  file, so primacy and recency both apply.
  - **Stating it did not remove the behaviour, and that is the finding.** Answers
    that close what they open appeared in every prompt variant this project measured
    — from a few per cent of answers up to one answer that closed every entry it had
    written. What moved the rate was the prompt's *vocabulary* rather than the
    statement of the rule (the de-cueing finding recorded at the head of this entry),
    and a residual rate
    survived every variant: the model closes what it opens, and the prompt side has
    reached its floor on it.
  - The cost of the class is out of proportion to its content: a closing tag carries
    no information, but the tolerant reader used to normalize `</terms>` into the
    entry id `terms` (C.2.5 lists `/` among its reserved characters, C.3 strips it)
    and then fail the document on `entry 'terms' is missing required field 'source'`
    — an entry the answer does not contain. The fix belonged in the reader, and it is
    the C.2.5 clarification below. A wrapper relaxation was the other option
    considered and was **not** made.
- **Appendix C.2.5 clarified: markup is not an identifier, so the reading no longer
  manufactures entries.** The relaxation applies to an identifier that begins with a
  name character (or the quoted form of C.2.4); a stray closing tag `</terms>` is
  **not an entry marker**, and C.5 rejects the line. Found by measurement: the model
  closes what it opens, so answers arrive with `</terms>`, `</result>`, `</preset>`
  after the glossary, and the reading normalized `/terms` into the entry `terms`
  (C.3 step 4 replaces the slash, step 6 strips it) and then failed the document on
  `entry 'terms' is missing required field 'source'` — an entry the answer never had.
  The diagnostic pointed at the invented entry instead of at the stray line, and
  manufacturing data out of markup is what C.5 forbids.
  - Synced across the three repositories: the specification's C.2.5, its ABNF
    semantic-constraint block (which reaches a prompt that injects that block), the
    `cliff.zh-CN` mirrors of both, the Python parser
    (`_marker_begins_with_identifier`, with the same test for a group path's first
    segment), the parser's README table, and this suite.
  - New fixture `tests/fixtures/tolerant/closing-tag.zh-CN.cliff`, listed in
    `UNREPAIRABLE`: refused in both readings, strict reporting `invalid entry id
    '/terms'` and tolerant reporting that the line is neither a field, a section nor
    an entry marker. `tests/clarion/test_read_modes.py` asserts both halves — refused,
    and **no entry produced**. `cliff-python` gained three tests covering the same
    boundary plus the two cases that must keep working (`<  resolution  >` still
    normalizes; an empty marker still takes C.3's fallback name).
  - **No validity rate changed.** Those answers really do contain an invalid line,
    and they now fail *at it* rather than at an entry the reader invented. The repair
    count moved instead, because the reading no longer reports a repair for a line it
    rejects; `tests/test_compare_readings_tool.py` carries the reason next to the
    figures, and the final run's two-readings table is in the acceptance criteria.
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
  the specification block that only the CLIFF prompt carries (16 838 tokens per
  cell as the reference text, 2 925 as the compressed block the shipped style
  sends). CLIFF's D1/D2 prompt totals were therefore roughly half of what the
  translation arms actually send; the other nine formats were correct, and the
  document-token columns were never affected.
- **The two tools that produce a published bundle no longer carry a run id.** The
  provenance line is the first thing a reader checks, and it was the one string
  neither tool derived: `audit_report.mjs` wrote one particular run's id into every
  `investor-data.md` it generated, and `package_benchmark.py` both packed into a
  hard-coded bundle directory and described the bundle with a hard-coded run id and
  counts, so auditing or packing a *new* run produced evidence about the *old* one.
  The audit tool reads the id from the directory it is given, the packer derives the
  bundle name from the run id's own timestamp and writes its README — protocol, model,
  formats, arms, task counts — out of the run it packs. The audit's corpus index also
  filtered the two `variant: glossary` term files by **file name**, so the run line
  read one count of corpus files where the corpus has another; it filters on the
  variant header now, and `tests/test_benchmark_bundle_tool.py` runs the tool on a
  real bundled run and asserts the line it produces. Both tools also survive a run
  that did not measure every format or every arm instead of throwing.
- **A run directory now records the revision and the rendered prompt behind its
  answers.** `summary.json` gained `revision` and `prompt_fingerprint`: the stored
  configuration names a *style*, and a style is not a text, so two runs recorded as
  "the same settings" could differ in the words sent with nothing on disk to say so.
  The fingerprint is of the block itself, and a test fails if it stops moving when
  the block does.
- **The prompt blocks are held to rules the tests can see.** `CLIFF_ANSWER_REMINDER`
  named the failure shape it exists to prevent (*"nothing in a CLIFF file is closed"*)
  and restated the extent of the answer that the shared task rules already state in
  the same message; it now states the marker rule and nothing else, and both tests
  that forbid a named failure and a repeated paragraph scan it. The digest style's
  supplement carried *"Keep the glossary concise."* — the house cap the same test
  forbids by name — in a block nothing scanned; it is gone, the scan covers the
  supplement and the composed specification block, and the supplement's escape list
  gained the `\r` the ABNF has always had. `spec_digest.semantic_constraints()` used
  to return an empty string if the ABNF's marker wording changed, silently dropping
  the constraint block from the prompt; it raises.
- **The generated artefacts that are tracked are now compared with what generates
  them.** `tools/token_benchmark.py --check` renders every artefact in memory and
  compares it byte for byte with the committed copy, and the step runs in `make check`
  and in CI — the counterpart of `cliff-python`'s `regenerate_examples.py --check`.
  The writer also emits LF explicitly: the default text-mode write on Windows turned
  every newline into CRLF, which left the tracked reports looking modified after every
  run and made the committed bytes platform-dependent.

### Added

- **`prompt_style: spec` — the specification compressed to its rules, assembled
  from the specification repository.** The format's own text is 16 803 tokens, of
  which only **2 492 tokens are lines that state a rule** (`MUST` / `SHOULD` / `MAY`
  / `REQUIRED`); the rest is motivation, examples, comparisons and migration notes.
  `clarion/prompts/cliff_rules.py` builds a **2 925-token** prompt block out of the
  parts that state rules and nothing else, and
  `python tools/prompt_cost.py --decomposition` prints the decomposition: the title
  (17), the marker rule stated
  at each end of the block (99 + 99), the intro (65), the ABNF with comments stripped
  (625), the ABNF's semantic-constraint block (941, where required fields, the
  `status`/`target` dependency, the escape rules, brace balance, list-typed fields
  and identifier case already live), the field tables of sections 7-9 (258, extracted
  from the specification's own markdown), the closed vocabularies (163), the
  specification's own quick example (190), the escape paragraph (158) and the
  `variant: glossary` section (307). The parts sum to 2 922 against a block of 2 925,
  because a token boundary at a join is shared.
  - **The extracted parts cannot drift; the written ones are named.** The grammar,
    the semantic constraints, the field tables, the vocabularies and the quick example
    are read out of the specification repository at prompt-build time, so they cannot
    become a second source of truth. The framing paragraphs that exist only because a
    *prompt* needs them — the intro, the marker rule, the vocabularies' framing line,
    the group note, the escaping paragraph and the glossary section — are written in
    the module and listed in `cliff_rules.WRITTEN_HERE` with the section each carries.
    An earlier version of the module claimed *nothing* in the block was hand-written,
    which is the kind of claim that stops a reader reviewing the paragraphs that need
    it. `tests/clarion/test_spec_digest.py` holds both halves: the extracted key
    tables are compared against the key sets the parser accepts
    (`HEADER_KEYS`/`ENTRY_KEYS`), the inherited set against section 9, the
    vocabularies against the implementation, `SECTION_COVERAGE` must account for every
    section of the specification that states a rule (represented, or excluded with a
    reason, and the reason's kind is a closed vocabulary) — and every declared
    hand-written part must really be in the block.
  - The style is reachable per run without editing a configuration:
    `--prompt-style {digest,examples,spec}` on `pipeline` and `translate`, because a
    run directory records the configuration it was started with and two styles have
    to be switchable inside one session to be comparable.
  - Assembly fixes that came with it: the `spec` style no longer appends the full
    specification text (the first assembled `spec` prompt came out at 20 016 tokens
    - the digest *plus* the text it replaces), and it drops the hand-written
    `FORMAT_NOTES`, `CLIFF_TASK_RULES`, `GLOSSARY_WORKFLOW` and edit-safety blocks,
    each of which restates rules the specification block already carries.
  - **Measured, twice, and neither measurement was a result.** Two single-repeat
    sixteen-file cells were run to compare the compressed block against the
    example-driven style, one of them with the answer-extent sentence added, and the
    valid rate did not move in either. What they produced is the *decision*: the
    remaining failures are not a missing instruction, and two prompt-content levers
    had now been tested in the same cell without moving the number, which left the
    decoding regime as the only variable still standing. Both cells' run directories
    are pruned; the finding survives in `docs/clarion-prompt-design.md`.
- **`tools/prompt_cost.py` and `tools/prompt_block_delta.py`, with
  `tests/test_prompt_cost_tool.py`.** The prompt-cost table in
  `docs/clarion-prompt-design.md` is quoted in this changelog and in the acceptance
  criteria, and until now the instrument that produced it lived in the working-copy
  `.tools/` directory outside the repository — a number a reader cannot reproduce is
  a number they have to take on trust. `prompt_cost.py` prints the per-component
  table for one cell (`--pilot` for the four pilot files, `--decomposition` for the
  compressed block part by part, `--block-delta` for the per-block token delta
  against a git revision, which `prompt_block_delta.py` also does on its own), and it
  prices **all three** styles: for the `ui-console` plain cell, `digest` **21 393**,
  `examples` **2 417**, `spec` **4 142**, a per-cell saving of **18 976** tokens and
  **75 904** over the four pilot files. Everything is assembled through
  `build_translation_prompt`, the call path a run uses; the earlier measurement
  projected the example-driven side arithmetically and drifted the moment the
  assembly changed. It used to price only `digest` and `examples`, so the style the
  shipped configuration actually sends was the one published figure nothing measured
  — `tests/test_prompt_cost_tool.py` now asserts that the shipped style is one of
  the priced ones, pins the three totals **read out of the document**, recomputes the
  published decomposition, and checks the invariant that catches this table's own
  failure mode: every column's rows sum to that column's total.
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
  the repairable phrasings are absent. It is priced with everything else in the table
  `docs/clarion-prompt-design.md` publishes.
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
  it holds far too few entries with a multi-valued list for the loss of a second
  element to move the aggregate, so a codec that drops one still scores in the high
  nineties. The two json-plain cases where a
  `|` separates both list items and fields are pinned with a **strict** xfail, so
  fixing that codec becomes an XPASS failure rather than passing quietly.
- **CI runs the whole suite.** The workflow ran `python tests/run_all.py` and
  nothing else, so the harness tests, the lint gate, the corpus guard and the
  offline self-check never ran on a push. It now checks out the sibling `cliff` and
  `cliff-python` repositories and runs the conformance suites, the generated-artefact
  check, the specification's own `check_examples.py` against that checkout, the corpus
  guard, `ruff check .`, `pytest`, the offline self-check, the credential scan, and
  the two on-request batteries. `make check` runs the same steps in the same order.
- **`testpaths` is `tests/`, not `tests/clarion/`.** A bare `pytest` collected 245
  tests and silently never collected `tests/test_validator_tool.py` or
  `tests/test_edit_robustness.py` — eleven tests that existed and did not run. It
  collects the whole tree now (**512 passed, 2 xfailed** at this revision).
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
  `tools/coverage_audit.py`, which reports **55 of 55** modules under `clarion/`
  reachable from the suite (the count moves with every new module;
  `tests/clarion/test_coverage_audit.py` reads this claim and asserts the
  reachability property behind it rather than the pair):
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
- **`make check` and CI now run the same steps**, in the same order, including
  the credential scan: a key pasted into a test can no longer reach a commit
  unnoticed. The step that compares the tracked generated artefacts against what
  their generator renders (`tools/token_benchmark.py --check`) is part of both, so a
  stale report fails locally before it fails on a push.
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
  every suite, checks both spec example directories, and **fails** when the tolerant
  refusal set (Appendix C.5) is empty — a warning that left the battery green while
  it tested nothing. A validator usage error (exit 2, which an empty file list
  produces) can no longer satisfy a non-zero expectation, the 100 gitignored edits
  are generated rather than demanded, and a missing sibling checkout fails when
  `CLIFF_REQUIRE_SIBLINGS=1` instead of turning into a skip.
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
- **Nine tolerant fixtures** pinning the repair set by category — the count, not
  just the exit code, so one relaxation cannot silently become another. The first
  three are `terminators-and-quoted-tags.zh-CN.cliff`, whose every line ends with
  `,` / `;` to assert that a line terminator is syntax and not a repair,
  `quoted-id-and-bare-list.zh-CN.cliff` and `two-documents.txt`; the six added later
  are the C.2.1, C.2.2, C.2.3, C.2.4, C.2.5/§C.4 and C.2.6 cases, each measured by
  reading the fixture through the tolerant reader rather than copied from the
  fixtures' README.
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

- **Two rules the specification compression had dropped, found from failures and
  from a measurement that had silently stopped happening.**
  - **The escape rule was only implied.** The `spec` style stated the escape set
    only as the grammar's `double-escape` production. Two answers failed on exactly
    that, and the character-level read is unambiguous: a long classical-Chinese
    `source` value in which the model escaped two of the three inner ASCII quotes and
    missed the third (the same value also carries CJK curly quotes, which take no
    backslash), and a long `target` in which it escaped none of two. A 158-token
    paragraph now states the escape set and the curly-quote case — and the useful part
    is *how* it states it: it **names the convention** ("a value is a C-style string
    literal", five escapes, the whole set) and says the file you were given already
    spells it that way, rather than listing the escapes for the model to apply.
    Listing them was what the grammar already did and what the model was already
    ignoring: the byte-level read of the failing answers showed the model copying a
    corpus line that already carried `\"` and tidying the backslashes out of it, which
    a stated convention prevents and a list does not.
    `test_the_escape_rule_is_stated_as_prose_and_not_only_as_a_production` holds both
    halves.
  - **The glossary lost its trigger and its shape, and the trigger alone is worse
    than neither.** `glossary emitted` fell to nothing when the `spec` style replaced
    the hand-written workflow blocks: the block stated what a glossary *is* and when
    one is warranted, and never said this task expects one. The ablation, same cell,
    one repeat, `reasoning: low`, is the finding: with the trigger added back but no
    shape, answers appended a glossary **and invented their own separator line**
    (`===== OPTIONAL DELIVERABLE: CLIFF GLOSSARY (variant: glossary) =====` and two
    other spellings), which the parser reads as an invalid field name and which fails
    the whole answer — so stating the deliverable without stating how a second
    document is recognised made the cell *worse* than saying nothing. Trigger plus the
    shape of 13.2.1 plus the two-document boundary of 13.2.2 fixed it. Both halves are
    now in the specification block, and the ablation's run directories are pruned.
  - The boundary statement had to be phrased affirmatively too: the first version
    read *"no heading, no separator, no line of explanation"*, which names the
    banner it was meant to prevent.
    `test_the_two_document_boundary_is_stated_where_the_glossary_is` rejects the
    prohibitions.
  - The compressed block is **2 925 tokens** against the 16 803-token specification
    text, and the design document carries the decomposition and the ablation table.
- **The Fisher exact test in the prompt-analysis scripts was wrong, and three
  published p-values were corrected.** `clarion.metrics.stats` had bootstrap,
  permutation, McNemar and Wilson but no Fisher test, so the two working-copy
  analysis scripts carried their own - and its combinatorial helper ignored the
  table it was asked for, returning the *observed* table's probability for every
  candidate table. The p-value was therefore that probability summed once per
  table with the same margins, capped at 1: for the invented-key table (48 edits per
  condition) it reported **0.0129** where the exact answer is **0.0026**, and it could
  never report anything below that product - so it could
  only ever *understate* a difference, never invent one.
  - `fisher_exact` now lives in `clarion/metrics/stats.py`, next to the other
    exact tests, is enumerated over `fractions.Fraction` probabilities (exact, no
    approximation, no overflow), and is tested in `tests/clarion/test_stats.py`
    against hand-computed tables **and** against the shape of the defect: the test
    asserts both the corrected value and that it is not the observed probability
    times the table count.
  - Corrected in place: `docs/clarion-prompt-design.md` (the invented-key
    comparison, 0.0129 → **0.0026**; and the prompt pilot's per-file claim, which
    quotes the worst file's corrected value, **0.7319**, pinned in
    `tests/clarion/test_stats.py`, instead of a saturated "1.000 throughout"),
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
  consequences: **every D7 number published before this fix is a 0.0 number**,
  including the rows labelled as the deployment settings, and `d7_pilot.py
  --temperature 1.3` was a no-op that changed a `ProviderConfig` field nothing reads.
  The controlled CLIFF comparison survives (both its columns are the same model, the
  same `ui` stratum, the same 12 edits and an unedited `EDIT_SYSTEM`, so only the
  prompt differed), but no claim about D7 at the shipped decoder settings was ever
  supported by those runs, and that measurement is now made by the final run at the
  head of this file. The temperature is a parameter of `run_robustness`, forwarded
  from the configuration, and `tests/clarion/test_edit_request.py` fails with
  `{0.0} == {1.3}` if the forward is dropped. Related corrections recorded in
  [docs/clarion-prompt-design.md](docs/clarion-prompt-design.md): the D7 pilot
  table's "temperature 1.3" heading, the "re-run at the shipped settings" section,
  and the attribution of the XLIFF row — the 100.0 % it was compared against belongs
  to an earlier benchmark run on a different model, not to this one, so that difference
  is a model change rather than a temperature or prompt effect.
- **The published repair attribution for D7 counted re-counts as repairs.** A
  record's repair count is the count for the whole document at that step, and the
  answer text carries forward, so one deviation is counted again by every later
  step: the per-step repair counts across the CLIFF context cells summed to many
  times the number of repairs the model actually introduced (the two operations that
  create a field not already on the page, `add-reference` and `set-emotion`).
  Attributing the sum per operation charged early operations for deviations
  introduced later. `.tools/d7_audit.py` now prints both figures and warns if the
  counts are not monotone within a cell.
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
  measured 16 files / 392 entries of 0.3.0. The token table the README cites is
  printed by `python -m clarion tokens` rather than linked, because `results/` is
  gitignored and a link into it is a dead link in every fresh clone.

### Moved

- `tests/fixtures/invalid/uppercase-entry-id.zh-CN.cliff` and
  `underscore-entry-id.zh-CN.cliff` → `tests/fixtures/valid/`: 1.1 accepts both.
- `tests/fixtures/invalid/filename-mismatch.zh-CN.cliff` and the three
  `invalid/ja-JP/` fixtures → `tests/fixtures/layout/`: their finding is a
  warning in 1.1.


