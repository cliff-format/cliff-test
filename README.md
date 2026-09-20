# CLARION — the CLIFF test suite and benchmark project

**CLARION** (*Contextual Localization Accuracy, Robustness, Instruction-following and Overhead beNchmark*) is the independent test, validation and measurement project for the CLIFF format. Repository name: `cliff-test`;
The format specification itself lives in **[cliff](https://github.com/cliff-format/cliff)**; this project
contains everything needed to verify CLIFF implementations and measure its
cost/quality properties.

## Contents

```
cliff-test/
├── clarion/                      ← CLARION benchmark harness (Python package)
│   ├── formats/                  ← render, read back and validate every format
│   ├── metrics/                  ← tokens, chrF++/BLEU/TER, structure, rules,
│   │                                terminology, fidelity, controls, statistics
│   ├── prompts/                  ← prompt assembly and the CLIFF spec digest
│   ├── providers/                ← mock and OpenAI-compatible endpoints
│   ├── experiments/              ← translation and cross-format edit robustness
│   └── policy/                   ← editable de-jargon policy per locale
├── datasets/
│   ├── clarion-core/             ← the benchmark corpus (5 strata, CC0)
│   └── recipes/                  ← licence-aware importers for external corpora
├── configs/                      ← run configurations
├── tools/
│   ├── cliff_validator.py         ← reference validator
│   └── token_benchmark.py        ← original token-cost benchmark
├── tests/
│   ├── clarion/                  ← harness unit and pipeline tests
│   ├── fixtures/                 ← valid / invalid conformance fixtures
│   ├── benchmark/                ← benchmark report
│   ├── quality/                  ← translation-quality corpus, gold, rubric
│   └── edit-robustness/          ← 100-edit format robustness protocol
└── docs/
    ├── acceptance-criteria.md    ← acceptance criteria + recorded results
    ├── clarion-methodology.md    ← what CLARION measures and how
    ├── clarion-corpus-spec.md    ← how to author a corpus stratum
    ├── clarion-dataset-card.md   ← corpus provenance and limitations
    └── clarion-prompting.md      ← LLM translation playbook for CLIFF
```

## CLARION

**CLARION** (*Contextual Localization Accuracy, Robustness, Instruction-following
and Overhead beNchmark*) measures the format, not the model: the same content
and the same brief are delivered to the same model as CLIFF, XLIFF, PO, Fluent,
JSON, YAML, CSV, Android and iOS resources, and seven dimensions are compared -
token cost, quality, latency (each in a plain and a context-carrying arm) and
format validity after model edits.

```bash
# Everything in one command: fetch corpora, write the brief, validate,
# measure all seven dimensions, and write the report.
python -m clarion pipeline --config configs/deepseek-flash.json

# Offline end-to-end verification of the harness (no network, no API key)
python -m clarion selfcheck

# Corpus health and provenance
python -m clarion corpus validate
python -m clarion corpus stats

# Dimensions 1 and 2: token cost, no model calls
python -m clarion tokens --out results/tokens.md

# Round-trip context fidelity of every format
python -m clarion fidelity

# Dimension 7 without a model (deterministic replay)
python -m clarion robustness --deterministic

# Dimensions 1-6 against a real endpoint
$env:DEEPSEEK_API_KEY = "..."
python -m clarion translate --config configs/deepseek-flash.json

# Build a glossary for a file that has none
python -m clarion glossary bootstrap path/to/file.cliff --propose --attach

# Import an external corpus: convert, enrich with context, attribute, licence-route
python -m clarion corpus recipes
python -m clarion corpus fetch wmt24pp --limit 200 --revision <commit>
python -m clarion corpus license-check      # must pass before pushing
python -m clarion corpus review             # export the human sign-off sheet
```

An external machine-translation corpus is a list of sentence pairs with no
translator brief, so it cannot be used for the context arm as it stands. The
import pipeline converts it through cliff-python, keeps any upstream translator
comments, has a second model write the brief where the corpus is silent,
derives document and neighbour context deterministically, and writes the
licence header, attribution file and checksums that make the result
publishable.

### Credentials

No key is ever stored in this repository. The loader looks in, in order:

1. the environment variable named by the run configuration
   (`DEEPSEEK_API_KEY` in the shipped config);
2. `<workspace>/.clarion-secrets/deepseek.key` - outside every git repository,
   the recommended location;
3. `cliff-test/.secrets/deepseek.key` - gitignored.

Before pushing, prove the tree is clean:

```bash
python -m clarion secret-scan     # must print "0 findings"
```

The scan also runs as the first stage of `clarion pipeline`, which refuses to
start when it finds anything that looks like a credential.

Every fixture in every format is generated from the same CLIFF corpus document
through cliff-python, so no format has a hand-tuned advantage. See
[docs/clarion-methodology.md](docs/clarion-methodology.md).

## Quick start

```bash
# Valid fixtures
python tools/cliff_validator.py --suite tests/fixtures/valid

# Invalid fixtures (must exit non-zero)
python tools/cliff_validator.py --suite tests/fixtures/invalid

# Layout fixtures: warnings by default, errors when the convention is enforced
python tools/cliff_validator.py --suite tests/fixtures/layout
python tools/cliff_validator.py --check-layout --suite tests/fixtures/layout

# Style fixtures: warnings, never errors
python tools/cliff_validator.py --style --suite tests/fixtures/style

# Tolerant fixtures: repaired, with a report for every repair
python tools/cliff_validator.py --tolerant tests/fixtures/tolerant/*.zh-CN.cliff

# Spec examples from the sibling cliff repository (local checkouts)
python tools/cliff_validator.py --suite ../cliff/spec/examples/cliff-1.1.0

# Token benchmark
python tools/token_benchmark.py

# Everything reproducible at once
python tests/run_all.py
python tests/run_all.py --quality --robustness
```

## Recorded results

| Criterion | Threshold | Recorded result |
| --- | --- | --- |
| Token savings vs XLIFF/JSON/CSV/PO/Fluent/YAML/TOML average | ≥ 30% | **36.3%** (1138 vs 1785.9, CLIFF figure includes its glossary file; `tiktoken cl100k_base`, 16-unit corpus; regenerated by `tools/token_benchmark.py`) |
| AI translation reference accuracy | ≥ 90% | **99.17%** (119/120 rubric points, 48/48 objective constraints) |
| 100 sequential AI format edits valid | = 100% | **100/100 (100.0%)** |

Detailed protocols and artifact locations:
[docs/acceptance-criteria.md](docs/acceptance-criteria.md). The recorded C3
rubric score comes from the subagent models available when the suite was
recorded. Task files and prompts are model-agnostic and can be replayed with
any model class, including a Flash-class model.

### CLARION corpus-scale token cost

Measured over CLARION-Core 0.3.0 (16 standard documents, 392 entries, `tiktoken
o200k_base`, `python -m clarion tokens`), counting the document payload only:

| Arm | CLIFF | cheapest competitor | most expensive competitor |
| --- | ---: | --- | --- |
| plain (D1) | 24 322 | json-plain 20 647 (-15%) | android 41 228 (+70%) |
| context (D2) | 47 499 | yaml-cliff 52 753 (+11%) | csv 140 693 (+196%) |

In the plain arm a bare key/value JSON file is cheaper than CLIFF, because it
carries nothing else. As soon as the same translation brief has to travel with
the strings, CLIFF is the cheapest format in the comparison, and the gap widens
with the amount of context. Full tables:
[results/clarion-core-tokens.md](results/clarion-core-tokens.md) after running
the command.

The same command also prices the *prompt* each arm sends, component by
component. Read that column with care: CLIFF's prompt carries the specification
digest and the full reference specification, which no other format needs, so
CLIFF's prompt is the most expensive in both arms while its document is among
the cheapest. That asymmetry is measured and subtracted rather than hidden — and
it was under-measured until this revision (see the correction note in
[BENCHMARK.md](BENCHMARK.md)).

## Relation to the specification

- Normative spec: [cliff-1.1.0.md](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.1.0.md)
  ([1.0](https://github.com/cliff-format/cliff/blob/main/spec/cliff-1.0.0.md) is the frozen, superseded definition; every 1.0 document is a valid 1.1 document)
- Grammar: [cliff-1.1.abnf](https://github.com/cliff-format/cliff/blob/main/spec/abnf/cliff-1.1.abnf)
- Style guide (informative, never enforced): [style/README.md](https://github.com/cliff-format/cliff/blob/main/style/README.md)
- Identifiers: `A-Z a-z 0-9 _ -`, never `.`, case-sensitive, and never
  rewritten by a parser. A project's spelling habit is style, not validity.
- Terminators: one optional trailing `,` / `;` per line is standard CLIFF 1.1
  and never re-emitted; a second one is a syntax error.
- Layout: both the recommended folder layout `<target-language>/<clan>.cliff`
  and the flat layout `<clan>.<target-language>.cliff` are accepted. The four
  header fields (`namespace`, `clan`, `source-language`, `target-language`)
  are required; the layout is checked for consistency with the header and a
  mismatch is a **warning** unless `--check-layout` is passed.
- Tolerant parsing: `--tolerant` delegates to `cliff_format`, the single
  implementation of specification Appendix C, so this repository does not carry
  a second contract that could diverge from the reference one.
- Emotion/status tag definitions:
  [content/emotion/status tag references](https://github.com/cliff-format/cliff/tree/main/references)
- Spec changes that affect parsing MUST be accompanied by validator and
  fixture changes in this project.

## License

[MIT License](LICENSE).
