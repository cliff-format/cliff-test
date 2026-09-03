# CLARION — the CLIF test suite and benchmark project

**CLARION** (*Contextual Localization Accuracy, Robustness, Instruction-following and Overhead beNchmark*) is the independent test, validation and measurement project for the CLIF format. Repository name: `clif-test`;
The format specification itself lives in **[clif](https://github.com/clif-format/clif)**; this project
contains everything needed to verify CLIF implementations and measure its
cost/quality properties.

## Contents

```
clif-test/
├── clarion/                      ← CLARION benchmark harness (Python package)
│   ├── formats/                  ← render, read back and validate every format
│   ├── metrics/                  ← tokens, chrF++/BLEU/TER, structure, rules,
│   │                                terminology, fidelity, controls, statistics
│   ├── prompts/                  ← prompt assembly and the CLIF spec digest
│   ├── providers/                ← mock and OpenAI-compatible endpoints
│   ├── experiments/              ← translation and cross-format edit robustness
│   └── policy/                   ← editable de-jargon policy per locale
├── datasets/
│   ├── clarion-core/             ← the benchmark corpus (5 strata, CC0)
│   └── recipes/                  ← licence-aware importers for external corpora
├── configs/                      ← run configurations
├── tools/
│   ├── clif_validator.py         ← reference validator
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
    └── clarion-prompting.md      ← LLM translation playbook for CLIF
```

## CLARION

**CLARION** (*Contextual Localization Accuracy, Robustness, Instruction-following
and Overhead beNchmark*) measures the format, not the model: the same content
and the same brief are delivered to the same model as CLIF, XLIFF, PO, Fluent,
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
python -m clarion glossary bootstrap path/to/file.clif --propose --attach

# Import an external corpus: convert, enrich with context, attribute, licence-route
python -m clarion corpus recipes
python -m clarion corpus fetch wmt24pp --limit 200 --revision <commit>
python -m clarion corpus license-check      # must pass before pushing
python -m clarion corpus review             # export the human sign-off sheet
```

An external machine-translation corpus is a list of sentence pairs with no
translator brief, so it cannot be used for the context arm as it stands. The
import pipeline converts it through pyclif, keeps any upstream translator
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
3. `clif-test/.secrets/deepseek.key` - gitignored.

Before pushing, prove the tree is clean:

```bash
python -m clarion secret-scan     # must print "0 findings"
```

The scan also runs as the first stage of `clarion pipeline`, which refuses to
start when it finds anything that looks like a credential.

Every fixture in every format is generated from the same CLIF corpus document
through pyclif, so no format has a hand-tuned advantage. See
[docs/clarion-methodology.md](docs/clarion-methodology.md).

## Quick start

```bash
# Valid fixtures
python tools/clif_validator.py --suite tests/fixtures/valid

# Invalid fixtures (must exit non-zero)
python tools/clif_validator.py --suite tests/fixtures/invalid

# Spec examples from the sibling clif repository (local checkouts)
python tools/clif_validator.py --suite ../clif/spec/examples/clif-1.0.0

# Token benchmark
python tools/token_benchmark.py

# Everything reproducible at once
python tests/run_all.py
python tests/run_all.py --quality --robustness
```

## Recorded results

| Criterion | Threshold | Recorded result |
| --- | --- | --- |
| Token savings vs XLIFF/JSON/CSV/PO/Fluent/YAML/TOML average | ≥ 30% | **36.3%** (1138 vs 1785.9, CLIF figure includes its glossary file; `tiktoken cl100k_base`, 16-unit corpus; regenerated by `tools/token_benchmark.py`) |
| AI translation reference accuracy | ≥ 90% | **99.17%** (119/120 rubric points, 48/48 objective constraints) |
| 100 sequential AI format edits valid | = 100% | **100/100 (100.0%)** |

Detailed protocols and artifact locations:
[docs/acceptance-criteria.md](docs/acceptance-criteria.md). The recorded C3
rubric score comes from the subagent models available when the suite was
recorded. Task files and prompts are model-agnostic and can be replayed with
any model class, including a Flash-class model.

### CLARION corpus-scale token cost

Measured over CLARION-Core (6 documents, 111 entries, `tiktoken o200k_base`,
`python -m clarion tokens`), counting the document payload only:

| Arm | CLIF | cheapest competitor | most expensive competitor |
| --- | ---: | --- | --- |
| plain (D1) | 4 907 | json-plain 3 873 (-21%) | android 7 815 (+59%) |
| context (D2) | 8 065 | yaml-clif 9 223 (+14%) | csv 23 331 (+189%) |

In the plain arm a bare key/value JSON file is cheaper than CLIF, because it
carries nothing else. As soon as the same translation brief has to travel with
the strings, CLIF is the cheapest format in the comparison, and the gap widens
with the amount of context. Full tables:
[results/clarion-core-tokens.md](results/clarion-core-tokens.md) after running
the command.

## Relation to the specification

- Normative spec: [clif-1.0.0.md](https://github.com/clif-format/clif/blob/main/spec/clif-1.0.0.md)
- Grammar: [clif-1.0.abnf](https://github.com/clif-format/clif/blob/main/spec/abnf/clif-1.0.abnf)
- Layout: both the canonical folder layout `<target-language>/<clan>.clif`
  and the flat layout `<clan>.<target-language>.clif` are accepted. The four
  header fields (`namespace`, `clan`, `source-language`, `target-language`)
  are required; layouts are checked for consistency with the header only.
- Emotion/status tag definitions:
  [content/emotion/status tag references](https://github.com/clif-format/clif/tree/main/references)
- Spec changes that affect parsing MUST be accompanied by validator and
  fixture changes in this project.

## License

[MIT License](LICENSE).
