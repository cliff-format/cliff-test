# Validation Fixtures

Each directory is a suite, and each suite is checked in the mode it is about — a
suite that passes under the wrong mode is not evidence of anything.

```bash
python tools/cliff_validator.py --suite tests/fixtures/valid
python tools/cliff_validator.py --suite tests/fixtures/invalid        # expect exit 1
python tools/cliff_validator.py --suite tests/fixtures/layout         # warnings only
python tools/cliff_validator.py --check-layout --suite tests/fixtures/layout  # expect exit 1
python tools/cliff_validator.py --style --suite tests/fixtures/style  # warnings only
python tools/cliff_validator.py --tolerant tests/fixtures/tolerant/*.zh-CN.cliff
```

| Suite | Expectation |
| --- | --- |
| `valid/` | Every file MUST validate with 0 errors in the strict grammar. |
| `invalid/` | Every file MUST be rejected (non-zero exit) with at least one error of the intended class. |
| `layout/` | 0 errors by default — CLIFF 1.1 recommends a layout rather than requiring it — and at least one error under `--check-layout`. |
| `style/` | Valid CLIFF with 0 errors, and at least one `STYLE` warning under `--style`. A style deviation is never an error. |
| `tolerant/` | Rejected by the strict grammar and repaired under `--tolerant`, with a repair report. Files named in `UNREPAIRABLE` (`unrepairable.zh-CN.cliff`) must still be refused, because tolerant parsing repairs shape and never guesses content (specification Appendix C.5). |

## Valid fixture coverage

- minimal document
- group inheritance (type/emotion/max-width/context)
- tolerant syntax (`=` assignment, arbitrary whitespace, trailing commas,
  empty dependency list, `<id>` entry markers)
- **relaxed identifiers (CLIFF 1.1)**: `<BadID>` (uppercase, in
  `mixed-shape-ids.zh-CN.cliff`), `<bad_id>` (underscore), and
  `namespace: Demo` / `clan: Act3_Strings` (mixed case, in
  `relaxed-ids.zh-CN.cliff` of the specification examples)
- **optional line terminators (CLIFF 1.1 §5.6)**: `valid-terminators.zh-CN.cliff`
  ends section, entry, field, and version lines with `,` or `;`, including a
  string whose own value contains `,` and `;`
- adjacent strings on `info`/`context`/`source`/`target` (verbatim C-style concatenation)
- glossary variant
- ICU MF1/MF2 without `format`
- comments and blank lines
- reference/reviewer fields
- `x-` extension fields
- all four required header fields (`namespace`, `clan`, `source-language`,
  `target-language`) present exactly once
- folder layout `<target-language>/<clan>.cliff` (`ja-JP/settings.cliff` header
  values agree with the folder/file-name layout)

## Layout fixture catalog

| File | Layout finding (warning by default, error under `--check-layout`) |
| --- | --- |
| `filename-mismatch.zh-CN.cliff` | file-name clan does not match the header |
| `ja-JP/settings.cliff` | header target-language does not match the folder language |
| `ja-JP/settings.zh-CN.cliff` | folder candidate conflicts with the file-name candidate |
| `ja-JP/settings_bad.cliff` | folder file name does not match the header clan |

## Style fixture catalog

| File | Style warning |
| --- | --- |
| `identifier-shapes.zh-CN.cliff` | `Style_Check` and `bad_id` are valid CLIFF but not a recommended shape |
| `terminators.zh-CN.cliff` | every line ends with an accepted `,` / `;` that the guide recommends not writing |

## Tolerant fixture catalog

| File | Repair (specification Appendix C) |
| --- | --- |
| `bare-list.zh-CN.cliff` | C.2.1 — bare scalar in the list-typed fields `dependency`, `emotion`, `reference` |
| `repeated-field.zh-CN.cliff` | C.2.2 — `info`, `target`, and `reference` repeated in one scope |
| `quoted-tags.zh-CN.cliff` | C.2.3 — `type` / `emotion` / `status` written with quotes |
| `quoted-and-normalized-ids.zh-CN.cliff` | C.2.4 / C.2.5 — quoted entry id and a group path containing spaces and `&` |
| `collision.zh-CN.cliff` | C.2.5 / C.4 — two spellings that normalize to the same id |
| `version-line.zh-CN.cliff` | C.2.6 — `cliff 1.1.0` |
| `terminators-and-quoted-tags.zh-CN.cliff` | C.2.3 + C.2.1 — a quoted tag, and the same tag inside a list-typed field; every line also ends with `,` / `;`, which is 1.1 syntax (5.6) and MUST NOT be counted as a repair |
| `quoted-id-and-bare-list.zh-CN.cliff` | C.2.4 + C.2.1 — a quoted entry id and bare values in `emotion` / `reference`; the ids must come back verbatim |
| `unrepairable.zh-CN.cliff` | **must be refused**: C.5 forbids guessing `type: Nown` |

## Invalid fixture catalog

| File | Intended error |
| --- | --- |
| `bad-version.zh-CN.cliff` | invalid version line |
| `missing-namespace.zh-CN.cliff` | required header missing |
| `missing-clan.zh-CN.cliff` | required header missing |
| `missing-source-language.zh-CN.cliff` | required header missing |
| `missing-target-language.zh-CN.cliff` | required header missing |
| `duplicate-section.zh-CN.cliff` | duplicate section path |
| `duplicate-entry-id.zh-CN.cliff` | duplicate entry id |
| `missing-source.zh-CN.cliff` | required entry field |
| `missing-type.zh-CN.cliff` | missing type and no group inheritance |
| `missing-status.zh-CN.cliff` | required entry field |
| `invalid-type.zh-CN.cliff` | fixed type vocabulary |
| `invalid-emotion.zh-CN.cliff` | fixed emotion vocabulary |
| `invalid-status.zh-CN.cliff` | fixed status vocabulary |
| `unknown-key.zh-CN.cliff` | unknown non-`x-` header key |
| `unknown-entry-key.zh-CN.cliff` | unknown non-`x-` entry key |
| `unknown-escape.zh-CN.cliff` | unknown string escape |
| `bare-cr.zh-CN.cliff` | bare CR line ending |
| `unclosed-string.zh-CN.cliff` | unterminated string |
| `list-cross-line.zh-CN.cliff` | list across lines |
| `max-width-zero.zh-CN.cliff` | non-positive max-width |
| `reviewed-without-target.zh-CN.cliff` | status/target consistency |
| `duplicate-source.zh-CN.cliff` | duplicate single-valued field |
| `unbalanced-icu.zh-CN.cliff` | ICU brace balance |
| `entry-before-section.zh-CN.cliff` | entry outside group |
| `bare-entry-id.zh-CN.cliff` | bare `entry <id>` syntax error |
| `old-entry-marker.zh-CN.cliff` | legacy `entry: id` syntax (must use `<id>` entry markers) |
| `double-terminator.zh-CN.cliff` | two trailing terminators (`;;`) — the grammar permits at most one |

## Fixtures that left this suite in CLIFF 1.1

`uppercase-entry-id.zh-CN.cliff` and `underscore-entry-id.zh-CN.cliff` moved to
`valid/`: 1.1's relaxed `name` accepts uppercase letters and underscores, so a
fixture asserting they are errors would now assert the opposite of the
specification. The four layout fixtures moved to `layout/` for the same reason
— their finding is a warning in 1.1, not an error.
