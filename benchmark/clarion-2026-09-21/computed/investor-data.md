# CLIFF investor data sheet (audited)

Source: run clarion-deepseek-flash-20260921T211031+0000-de29a5 (10 formats, 16 corpus files, 392 entries, 960 translation runs). All numbers below come from tools/audit_report.mjs; nothing is hand-written.

## 1. Token cost - plain (shipped) form

| format | doc tokens (corpus) | per entry | vs CLIFF | prompt + CLIFF spec | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 41228 | 105.2 | 69.5% | 50710 | 50054 |
| cliff | 24322 | 62.0 | - | 81455 | 34655 |
| csv | 28908 | 73.7 | 18.9% | 38073 | 37577 |
| fluent | 37099 | 94.6 | 52.5% | 46421 | 45925 |
| ios | 38794 | 99.0 | 59.5% | 48164 | 47620 |
| json-cliff | 26388 | 67.3 | 8.5% | 35537 | 35057 |
| json-plain | 20647 | 52.7 | -15.1% | 30177 | 29473 |
| po | 24218 | 61.8 | -0.4% | 33303 | 32887 |
| xliff-2.1 | 29848 | 76.1 | 22.7% | 39205 | 38517 |
| yaml-cliff | 23492 | 59.9 | -3.4% | 32641 | 32161 |

## 2. Token cost - same context payload carried (context form)

| format | doc tokens | per entry | vs CLIFF | prompt + spec | prompt w/o spec |
| --- | ---: | ---: | ---: | ---: | ---: |
| android | 77805 | 198.5 | 63.8% | 88231 | 87575 |
| cliff | 47499 | 121.2 | - | 105576 | 58776 |
| csv | 140693 | 358.9 | 196.2% | 150802 | 150306 |
| fluent | 74341 | 189.6 | 56.5% | 84607 | 84111 |
| ios | 75766 | 193.3 | 59.5% | 86080 | 85536 |
| json-cliff | 57696 | 147.2 | 21.5% | 67789 | 67309 |
| json-plain | 61805 | 157.7 | 30.1% | 72279 | 71575 |
| po | 61309 | 156.4 | 29.1% | 71338 | 70922 |
| xliff-2.1 | 106156 | 270.8 | 123.5% | 116457 | 115769 |
| yaml-cliff | 52753 | 134.6 | 11.1% | 62846 | 62366 |

## 3. Quality - plain form

| format | chrF++ (all, failures=0) | failed runs |
| --- | ---: | ---: |
| android | 51.77 | 0 |
| cliff | 46.47 | 4 |
| csv | 46.38 | 5 |
| fluent | 50.92 | 0 |
| ios | 50.34 | 1 |
| json-cliff | 50.59 | 0 |
| json-plain | 50.37 | 0 |
| po | 50.58 | 0 |
| xliff-2.1 | 50.75 | 0 |
| yaml-cliff | 50.69 | 0 |

## 4. Quality - same context payload carried (context form)

| format | chrF++ (all) | failed runs | real translation % |
| --- | ---: | ---: | ---: |
| android | 54.02 | 0 | 100.0% |
| cliff | 49.31 | 4 | 91.7% |
| csv | 41.76 | 12 | 82.4% |
| fluent | 53.54 | 0 | 100.0% |
| ios | 52.50 | 2 | 99.6% |
| json-cliff | 55.11 | 0 | 100.0% |
| json-plain | 53.39 | 0 | 100.0% |
| po | 53.53 | 1 | 100.0% |
| xliff-2.1 | 42.21 | 10 | 79.2% |
| yaml-cliff | 55.00 | 0 | 100.0% |

Note: the reading is the one the run configuration declares (`read_mode`); an answer the reader cannot read back without a translation scores 0, and a repair is reported as a cost rather than a failure.
**No QE pass was run for this bundle** (the reference-free MetricX-23-QE scoring needs `unbabel-comet` and its model weights, which were not available where this run was produced), so no QE column appears here and no reference-free quality figure is claimed. `python tools/qe_score.py <run-dir>` adds one to the run directory; re-running `tools/audit_report.mjs` then adds the column.

## 5. Latency - plain form

| format | ms/run | output tokens | | format | ms/run | output tokens |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| android | 49277 | 6286 | | json-cliff | 62042 | 9723 |
| cliff | 78420 | 12073 | | json-plain | 53266 | 7770 |
| csv | 100184 | 16281 | | po | 50312 | 7791 |
| fluent | 39347 | 6035 | | xliff-2.1 | 57298 | 8849 |
| ios | 64725 | 7949 | | yaml-cliff | 79645 | 11948 |

## 6. Latency - context form

| format | ms/run | output tokens | vs CLIFF ms |
| --- | ---: | ---: | ---: |
| android | 78929 | 11038 | -29.9% |
| cliff | 112516 | 17704 | - |
| csv | 161886 | 26866 | 43.9% |
| fluent | 69383 | 10127 | -38.3% |
| ios | 84751 | 12199 | -24.7% |
| json-cliff | 102470 | 14462 | -8.9% |
| json-plain | 63523 | 10644 | -43.5% |
| po | 74500 | 11149 | -33.8% |
| xliff-2.1 | 95180 | 15001 | -15.4% |
| yaml-cliff | 99282 | 15725 | -11.8% |

## 7. Post-LLM-edit validity / intent success

| format | arm | still valid % | intent applied % | checker strictness |
| --- | --- | ---: | ---: | --- |
| android | bare | 100.0 | 100.0 | XML well-formedness |
| android | context | 100.0 | 82.3 | XML well-formedness |
| cliff | bare | 100.0 | 95.2 | strict CLIFF validator (cliff-python) |
| cliff | context | 86.1 | 86.1 | strict CLIFF validator (cliff-python) |
| csv | bare | 100.0 | 100.0 | strict CSV parse |
| csv | context | 94.4 | 88.9 | strict CSV parse |
| fluent | bare | 100.0 | 100.0 | identifier grammar |
| fluent | context | 97.0 | 69.9 | identifier grammar |
| ios | bare | 100.0 | 100.0 | quoted-assignment grammar |
| ios | context | 100.0 | 88.1 | quoted-assignment grammar |
| json-cliff | bare | 100.0 | 100.0 | strict JSON parse |
| json-cliff | context | 100.0 | 86.1 | strict JSON parse |
| json-plain | bare | 100.0 | 100.0 | strict JSON parse |
| json-plain | context | 100.0 | 91.7 | strict JSON parse |
| po | bare | 100.0 | 100.0 | msgid/msgstr grammar |
| po | context | 100.0 | 80.6 | msgid/msgstr grammar |
| xliff-2.1 | bare | 71.4 | 71.4 |  |
| xliff-2.1 | context | 77.8 | 69.4 |  |
| yaml-cliff | bare | 100.0 | 100.0 | strict YAML parse |
| yaml-cliff | context | 100.0 | 86.1 | strict YAML parse |

Checkers are not of equal strictness: cross-format comparison of still valid % is not valid. CLIFF is checked by the official validator (strictest); other formats only need to parse.

