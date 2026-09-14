# CLIFF investor data sheet (audited)

Source: run clarion-deepseek-v4-flash-20260902T040228+0000-91f21a (10 formats, 16 corpus files, 392 entries, 960 translation runs). All numbers below come from tools/audit_report.mjs; nothing is hand-written.

## 1. Token cost - plain (shipped) form

| format | doc tokens (corpus) | per entry | vs CLIFF | prompt + CLIFF spec | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 41228 | 105.2 | 69.5% | 50630 | 49974 |
| cliff | 24322 | 62.0 | - | 263743 | 228559 |
| csv | 28908 | 73.7 | 18.9% | 37913 | 37417 |
| fluent | 37491 | 95.6 | 54.1% | 46733 | 46237 |
| ios | 39186 | 100.0 | 61.1% | 48476 | 47932 |
| json-cliff | 26388 | 67.3 | 8.5% | 35377 | 34897 |
| json-plain | 20647 | 52.7 | -15.1% | 30097 | 29393 |
| po | 24218 | 61.8 | -0.4% | 33143 | 32727 |
| xliff-2.1 | 29848 | 76.1 | 22.7% | 39045 | 38357 |
| yaml-cliff | 23492 | 59.9 | -3.4% | 32481 | 32001 |

## 2. Token cost - same context payload carried (context form)

| format | doc tokens | per entry | vs CLIFF | prompt + spec | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 77805 | 198.5 | 63.8% | 88151 | 87495 |
| cliff | 47499 | 121.2 | - | 287864 | 252680 |
| csv | 140693 | 358.9 | 196.2% | 150642 | 150146 |
| fluent | 75914 | 193.7 | 59.8% | 86100 | 85604 |
| ios | 75766 | 193.3 | 59.5% | 86000 | 85456 |
| json-cliff | 57696 | 147.2 | 21.5% | 67629 | 67149 |
| json-plain | 62986 | 160.7 | 32.6% | 73380 | 72676 |
| po | 62450 | 159.3 | 31.5% | 72319 | 71903 |
| xliff-2.1 | 106156 | 270.8 | 123.5% | 116297 | 115609 |
| yaml-cliff | 52753 | 134.6 | 11.1% | 62686 | 62206 |

## 3. Quality - plain form

| format | chrF++ (all, failures=0) | failed runs | QE error (lower better, n) |
| --- | ---: | ---: | ---: |
| android | 47.81 | 0 | 1.51 (435) |
| cliff | 49.15 | 0 | 1.46 (561) |
| csv | 36.39 | 11 | 1.10 (184) |
| fluent | 48.90 | 0 | 1.39 (561) |
| ios | 45.88 | 3 | 1.51 (435) |
| json-cliff | 48.53 | 0 | 1.47 (435) |
| json-plain | 44.53 | 4 | 1.53 (435) |
| po | 46.13 | 1 | 1.50 (561) |
| xliff-2.1 | 48.68 | 0 | 1.46 (561) |
| yaml-cliff | 45.93 | 6 | 1.50 (435) |

## 4. Quality - same context payload carried (context form)

| format | chrF++ (all) | failed runs | real translation % | QE error (n) |
| --- | ---: | ---: | ---: | ---: |
| android | 51.97 | 0 | 100.0% | 1.56 (435) |
| cliff | 53.46 | 0 | 100.0% | 1.48 (561) |
| csv | 7.73 | 41 | 92.9% | 0.59 (120) |
| fluent | 52.64 | 0 | 100.0% | 1.53 (508) |
| ios | 47.49 | 5 | 95.7% | 1.53 (435) |
| json-cliff | 18.37 | 0 | 25.0% | 0.59 (120) |
| json-plain | 48.50 | 3 | 93.8% | 1.54 (435) |
| po | 50.75 | 1 | 100.0% | 1.50 (561) |
| xliff-2.1 | 52.20 | 1 | 97.9% | 1.44 (519) |
| yaml-cliff | 33.62 | 4 | 93.8% | 1.36 (236) |

Note: strict reading is applied - an answer the official parser reads back without a translation scores 0; no repair loop and no permissive parsing. Shared-segment QE differences are <= 0.12 error points (noise): the format does not change translation quality, it changes delivery reliability and cost (see report.audited.md sections 9-10).

## 5. Latency - plain form

| format | ms/run | output tokens | | format | ms/run | output tokens |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| android | 30347 | 2513 | | json-cliff | 29685 | 2758 |
| cliff | 29330 | 2671 | | json-plain | 17906 | 1288 |
| csv | 26436 | 2242 | | po | 26845 | 2441 |
| fluent | 27263 | 2394 | | xliff-2.1 | 31056 | 3047 |
| ios | 30382 | 2382 | | yaml-cliff | 31753 | 2543 |

## 6. Latency - context form

| format | ms/run | output tokens | vs CLIFF ms |
| --- | ---: | ---: | ---: |
| android | 49618 | 4835 | 14.6% |
| cliff | 43297 | 4120 | - |
| csv | 81755 | 9623 | 88.8% |
| fluent | 49894 | 4739 | 15.2% |
| ios | 41822 | 3383 | -3.4% |
| json-cliff | 32707 | 3659 | -24.5% |
| json-plain | 38461 | 3965 | -11.2% |
| po | 48391 | 5029 | 11.8% |
| xliff-2.1 | 70364 | 7746 | 62.5% |
| yaml-cliff | 51268 | 6213 | 18.4% |

## 7. Post-LLM-edit validity / intent success

| format | arm | still valid % | intent applied % | checker strictness |
| --- | --- | ---: | ---: | --- |
| android | bare | 100.0 | 100.0 | XML well-formedness |
| android | context | 100.0 | 91.2 | XML well-formedness |
| cliff | bare | 100.0 | 95.2 | strict CLIFF validator (cliff-python) |
| cliff | context | 91.7 | 86.1 | strict CLIFF validator (cliff-python) |
| csv | bare | 76.2 | 76.2 | strict CSV parse |
| csv | context | 61.1 | 55.6 | strict CSV parse |
| fluent | bare | 100.0 | 100.0 | identifier grammar |
| fluent | context | 100.0 | 55.6 | identifier grammar |
| ios | bare | 100.0 | 100.0 | quoted-assignment grammar |
| ios | context | 33.1 | 41.4 | quoted-assignment grammar |
| json-cliff | bare | 100.0 | 100.0 | strict JSON parse |
| json-cliff | context | 100.0 | 86.1 | strict JSON parse |
| json-plain | bare | 100.0 | 94.4 | strict JSON parse |
| json-plain | context | 100.0 | 63.9 | strict JSON parse |
| po | bare | 100.0 | 94.4 | msgid/msgstr grammar |
| po | context | 100.0 | 80.6 | msgid/msgstr grammar |
| xliff-2.1 | bare | 100.0 | 95.2 |  |
| xliff-2.1 | context | 100.0 | 88.9 |  |
| yaml-cliff | bare | 100.0 | 95.2 | strict YAML parse |
| yaml-cliff | context | 100.0 | 86.1 | strict YAML parse |

Checkers are not of equal strictness: cross-format comparison of still valid % is not valid. CLIFF is checked by the official validator (strictest); other formats only need to parse.

