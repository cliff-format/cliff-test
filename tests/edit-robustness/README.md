# CLIFF 1.1 100-Edit Robustness Test

Acceptance criterion: **an AI performing 100 sequential modifications to a
CLIFF 1.1 translation file produces a structurally valid file after **all 100**
edits. Any invalid intermediate file fails the robustness run.**

## Artifacts

| File | Purpose |
| --- | --- |
| `base.cliff` | Valid CLIFF 1.1 starting document (10 entries, 3 groups) |
| `tasks.json` | 100 sequential, realistic model-style edit tasks (one sentence instruction each) |
| `apply_edits.py` | Deterministic agent-authored driver for the recorded 100-edit run |
| `edits/NNN/settings.zh-CN.cliff` | One full document after each edit (NNN = 001..100) |
| `report.md` | Validator results per edit |

## Task mix (CLIFF 1.1)

| Kind | Count | Exercises |
| --- | --- | --- |
| optional-field add/remove/update | 25 | context, max-width, reference, reviewer, emotion |
| fixed tags (`type`/`status`/`emotion`) | 15 | closed vocabularies, legal tag changes |
| comments / blank lines | 9 | insert and delete comments and blank lines |
| add new entries | 8 | structural insertion with source/type/status |
| retranslate `target` | 8 | string rewriting, quotes, CJK |
| group metadata | 6 | new groups and context/type/emotion/max-width edits |
| `:` / `=` separator swaps | 5 | tolerant field syntax |
| reindent entry fields | 4 | indented and non-indented field syntax |
| cross-group moves | 4 | line locality, no closing tags |
| reorder entries | 4 | stable IDs, line relocation |
| rename entries | 3 | canonical ID changes |
| source updates | 3 | source text rewrite |
| whitespace | 3 | extra/missing whitespace while staying valid |
| dependency list | 2 | header dependency list editing |
| ICU string rewrite | 1 | balanced braces inside strings |

## How to run the SubAgent test

1. Give an agent `base.cliff` and `tasks.json`.
2. The agent applies task 1 to `base.cliff` and writes
   `edits/001/settings.zh-CN.cliff`, then applies task 2 to that result and
   writes `edits/002/settings.zh-CN.cliff`, and so on.
3. The agent MUST NOT use `cliff_validator.py` while editing; validation happens
   only after every file is written.
4. Run:

```bash
python tools/cliff_validator.py --suite tests/edit-robustness/edits
```

5. Count valid files. Score = valid / 100. Threshold = **100% (all files must
   be VALID)**. The runner exits with FAIL if any file is INVALID.
