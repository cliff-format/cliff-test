# Validation Fixtures

- `valid/` — every file MUST validate with 0 errors.
- `invalid/` — every file MUST be rejected (non-zero exit) with at least one
  error of the intended class.

Run:

```bash
python tools/cliff_validator.py --suite tests/fixtures/valid
python tools/cliff_validator.py --suite tests/fixtures/invalid   # expect exit 1
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
- folder layout `<target-language>/<clan>.cliff` (`ja-JP/settings.cliff` header
  values agree with the folder/file-name layout)

## Invalid fixture catalog

| File | Intended error |
| --- | --- |
| `bad-version.zh-CN.cliff` | invalid version line |
| `missing-namespace.zh-CN.cliff` | required header missing |
| `missing-clan.zh-CN.cliff` | required header missing |
| `missing-source-language.zh-CN.cliff` | required header missing |
| `missing-target-language.zh-CN.cliff` | required header missing |
| `filename-mismatch.zh-CN.cliff` | header/filename clan mismatch |
| `duplicate-section.zh-CN.cliff` | duplicate section path |
| `duplicate-entry-id.zh-CN.cliff` | duplicate entry id |
| `uppercase-entry-id.zh-CN.cliff` | uppercase entry id |
| `underscore-entry-id.zh-CN.cliff` | underscore entry id |
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
| `ja-JP/settings.zh-CN.cliff` | folder candidate conflicts with file-name candidate |
| `ja-JP/settings.cliff` | header target-language does not match folder language |
| `ja-JP/settings_bad.cliff` | folder file name does not match header clan |
