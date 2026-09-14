# Translation Quality Test

This suite measures whether CLIFF's context model lets an AI translator reach
≥ 90% reference accuracy on a corpus that deliberately contains idioms,
sarcasm, puns, proper nouns, register shifts, ICU, word-order traps, and a
display-width constraint.

## Files

| File | Role |
| --- | --- |
| `corpus.cliff` | 12 context-rich source entries (en-US → zh-CN) |
| `gold-reference.md` | Human reference translations + rubric |
| `translator-instructions.md` | Prompt for the translator agent |
| `evaluator-instructions.md` | Prompt for the evaluator agent |
| `check_constraints.py` | Objective constraint checks (no LLM needed) |
| `translator-output.cliff` | Translator agent output (generated) |
| `quality-report.md` | Evaluator agent report (generated) |

## Run

1. Translator agent: follow `translator-instructions.md`.
2. Objective checks:
   `python tests/quality/check_constraints.py`
3. Evaluator agent: follow `evaluator-instructions.md`.

## Acceptance

- Objective constraints: 100% pass.
- Rubric average: ≥ 90% (score ≥ 9/10 per entry on average).
- ICU syntax preserved exactly; glossary terms exact; `max-width` respected.
