# Validation Fixtures

- `valid/` — every file MUST validate with 0 errors.
- `invalid/` — every file MUST be rejected (non-zero exit) with at least one
  error of the intended class.

Run:

```bash
python tools/clif_validator.py --suite tests/fixtures/valid
python tools/clif_validator.py --suite tests/fixtures/invalid   # expect exit 1
```

## Valid fixture coverage

- minimal document
- group inheritance (type/emotion/max-width/context)
- tolerant syntax (`=` assignment, arbitrary whitespace, trailing commas,
  empty dependency list, `<id>` entry markers)
- adjacent strings on `info`/`context`/`source`/`target` (verbatim C-style concatenation)
- glossary variant
- ICU MF1/MF2 without `format`
- comments and blank lines
- reference/reviewer fields
- `x-` extension fields
- all four required header fields (`namespace`, `clan`, `source-language`,
  `target-language`) present exactly once
- folder layout `<target-language>/<clan>.clif` (`ja-JP/settings.clif` header
  values agree with the folder/file-name layout)

## Invalid fixture catalog

| File | Intended error |
| --- | --- |
| `bad-version.zh-CN.clif` | invalid version line |
| `missing-namespace.zh-CN.clif` | required header missing |
| `missing-clan.zh-CN.clif` | required header missing |
| `missing-source-language.zh-CN.clif` | required header missing |
| `missing-target-language.zh-CN.clif` | required header missing |
| `filename-mismatch.zh-CN.clif` | header/filename clan mismatch |
| `duplicate-section.zh-CN.clif` | duplicate section path |
| `duplicate-entry-id.zh-CN.clif` | duplicate entry id |
| `uppercase-entry-id.zh-CN.clif` | uppercase entry id |
| `underscore-entry-id.zh-CN.clif` | underscore entry id |
| `missing-source.zh-CN.clif` | required entry field |
| `missing-type.zh-CN.clif` | missing type and no group inheritance |
| `missing-status.zh-CN.clif` | required entry field |
| `invalid-type.zh-CN.clif` | fixed type vocabulary |
| `invalid-emotion.zh-CN.clif` | fixed emotion vocabulary |
| `invalid-status.zh-CN.clif` | fixed status vocabulary |
| `unknown-key.zh-CN.clif` | unknown non-`x-` header key |
| `unknown-entry-key.zh-CN.clif` | unknown non-`x-` entry key |
| `unknown-escape.zh-CN.clif` | unknown string escape |
| `bare-cr.zh-CN.clif` | bare CR line ending |
| `unclosed-string.zh-CN.clif` | unterminated string |
| `list-cross-line.zh-CN.clif` | list across lines |
| `max-width-zero.zh-CN.clif` | non-positive max-width |
| `reviewed-without-target.zh-CN.clif` | status/target consistency |
| `duplicate-source.zh-CN.clif` | duplicate single-valued field |
| `unbalanced-icu.zh-CN.clif` | ICU brace balance |
| `entry-before-section.zh-CN.clif` | entry outside group |
| `bare-entry-id.zh-CN.clif` | bare `entry <id>` syntax error |
| `old-entry-marker.zh-CN.clif` | legacy `entry: id` syntax (must use `<id>` entry markers) |
| `ja-JP/settings.zh-CN.clif` | folder candidate conflicts with file-name candidate |
| `ja-JP/settings.clif` | header target-language does not match folder language |
| `ja-JP/settings_bad.clif` | folder file name does not match header clan |
