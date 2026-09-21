# CLARION run: clarion-deepseek-flash

- Corpus: clarion-core
- Formats: cliff, xliff-2.1, po, fluent, json-cliff, json-plain, yaml-cliff, csv, android, ios
- Arms: bare, context
- Tokenizer: o200k_base
- Model: openai:deepseek-flash (reasoning low, temperature 1.3)
- CLIFF specification injection: spec (split)
- Answer read mode: tolerant
- Repeats per cell: 3

Every arm of every format is generated from the same CLIFF corpus documents through cliff-python, so a difference between two rows is a property of the format, not of the fixture.

### D1 - token cost, plain formats

| format | document tokens | per entry | vs CLIFF (doc) | glossary tokens | format instructions | prompt total | prompt without format instructions | vs CLIFF (prompt) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | 24322 | 62.0 | +0.0% | 0 | 46800 | 81455 | 34655 | +0.0% |
| android | 41228 | 105.2 | +69.5% | 0 | 656 | 50710 | 50054 | -37.7% |
| csv | 28908 | 73.7 | +18.9% | 0 | 496 | 38073 | 37577 | -53.3% |
| fluent | 37099 | 94.6 | +52.5% | 0 | 496 | 46421 | 45925 | -43.0% |
| ios | 38794 | 99.0 | +59.5% | 0 | 544 | 48164 | 47620 | -40.9% |
| json-cliff | 26388 | 67.3 | +8.5% | 0 | 480 | 35537 | 35057 | -56.4% |
| json-plain | 20647 | 52.7 | -15.1% | 0 | 704 | 30177 | 29473 | -63.0% |
| po | 24218 | 61.8 | -0.4% | 0 | 416 | 33303 | 32887 | -59.1% |
| xliff-2.1 | 29848 | 76.1 | +22.7% | 0 | 688 | 39205 | 38517 | -51.9% |
| yaml-cliff | 23492 | 59.9 | -3.4% | 0 | 480 | 32641 | 32161 | -59.9% |

Tokenizer: o200k_base. 'format instructions' is the CLIFF specification digest plus the per-format notes; subtracting it gives the 'without' column, so the with/without comparison needs no extra model run.

### D2 - token cost, context-carrying formats

| format | document tokens | per entry | vs CLIFF (doc) | glossary tokens | format instructions | prompt total | prompt without format instructions | vs CLIFF (prompt) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | 47499 | 121.2 | +0.0% | 0 | 46800 | 105576 | 58776 | +0.0% |
| android | 77805 | 198.5 | +63.8% | 0 | 656 | 88231 | 87575 | -16.4% |
| csv | 140693 | 358.9 | +196.2% | 0 | 496 | 150802 | 150306 | +42.8% |
| fluent | 74341 | 189.6 | +56.5% | 0 | 496 | 84607 | 84111 | -19.9% |
| ios | 75766 | 193.3 | +59.5% | 0 | 544 | 86080 | 85536 | -18.5% |
| json-cliff | 57696 | 147.2 | +21.5% | 0 | 480 | 67789 | 67309 | -35.8% |
| json-plain | 61805 | 157.7 | +30.1% | 0 | 704 | 72279 | 71575 | -31.5% |
| po | 61309 | 156.4 | +29.1% | 0 | 416 | 71338 | 70922 | -32.4% |
| xliff-2.1 | 106156 | 270.8 | +123.5% | 0 | 688 | 116457 | 115769 | +10.3% |
| yaml-cliff | 52753 | 134.6 | +11.1% | 0 | 480 | 62846 | 62366 | -40.5% |

Tokenizer: o200k_base. 'format instructions' is the CLIFF specification digest plus the per-format notes; subtracting it gives the 'without' column, so the with/without comparison needs no extra model run.

### D3 - quality, plain formats

| format | context source | read mode | runs | chrF++ (all runs) | chrF++ (survivors) | BLEU | TER (lower better) | instruction % | glossary % | de-jargon % | coverage % | valid answer % | repairs/run | failed % | truncated % | glossaries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | annotated/native/original | tolerant | 48 | 46.5 (40.8-52.0) | 50.7 | 41.4 | 53.4 | 78.7 | 94.5 | 99.9 | 91.7 | 91.7 | 0.04 | 8.3 | 0.0 | 28 |
| android | annotated/native/original | tolerant | 48 | 51.8 (47.4-56.7) | 51.8 | 45.3 | 63.3 | 78.5 | 94.3 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| csv | annotated/native/original | tolerant | 48 | 46.4 (40.5-52.6) | 51.8 | 42.5 | 43.9 | 76.1 | 94.4 | 99.7 | 89.6 | 89.6 | 0.00 | 10.4 | 0.0 | 0 |
| fluent | annotated/native/original | tolerant | 48 | 50.9 (46.9-55.4) | 50.9 | 44.6 | 63.3 | 79.3 | 94.5 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| ios | annotated/native/original | tolerant | 48 | 51.0 (46.7-55.6) | 51.4 | 44.7 | 63.4 | 78.7 | 93.2 | 99.8 | 99.8 | 97.9 | 0.00 | 2.1 | 0.0 | 0 |
| json-cliff | annotated/native/original | tolerant | 48 | 50.6 (46.6-55.0) | 50.6 | 44.2 | 61.5 | 77.8 | 94.4 | 99.9 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| json-plain | annotated/native/original | tolerant | 48 | 50.4 (46.5-54.8) | 50.4 | 44.1 | 62.1 | 77.9 | 94.6 | 99.7 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| po | annotated/native/original | tolerant | 48 | 50.6 (46.6-55.0) | 50.6 | 44.2 | 62.6 | 78.9 | 94.5 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| xliff-2.1 | annotated/native/original | tolerant | 48 | 50.8 (46.9-55.3) | 50.8 | 44.4 | 63.0 | 78.2 | 95.0 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| yaml-cliff | annotated/native/original | tolerant | 48 | 50.7 (46.7-55.3) | 50.7 | 44.2 | 61.7 | 78.3 | 94.6 | 99.9 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |

'chrF++ (all runs)' counts every run once, at the score its answer earned - a run that did not parse usually earns 0, and an answer that parses far enough to be scored keeps its partial score; 'chrF++ (survivors)' averages only the runs that produced a usable file, which is translation quality with format survival factored out. Read them together: the gap between the two columns IS the cost of format fragility. `tools/audit_report.mjs` publishes the other convention, in which every failure is scored as zero.

'read mode' is how the answer was read back: 'tolerant' applies the documented relaxations of CLIFF 1.1 Appendix C, 'strict' is the reference-toolchain reading. 'repairs/run' is the mean number of Appendix C repairs a CLIFF answer needed under the tolerant reading, so the two readings can be compared instead of confused: the same answers score 'valid answer %' 100 with repairs and 100 without.

'glossaries' counts answers that also produced a CLIFF glossary through the terminology workflow. Those answers are longer by design, so their cost shows up in the latency and output-token tables; the surface metrics do not credit them, and a comparison that ignores this understates the format.

'failed %' counts runs whose answer did not parse, did not validate or lost entries. A parse error is a failure OF THE FORMAT, not an excluded sample: its quality scores stay in the average as zeros.

A non-zero 'truncated %' means answers hit the output ceiling: those runs measure the token budget, not the format, and the run configuration must be fixed before the row is read as a result.

'context source' is where the context payload came from: original (written by hand with the corpus), native (written by the upstream project), derived (computed deterministically from corpus metadata) or annotated (written by a model and pending human sign-off). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

### D4 - quality, context-carrying formats

| format | context source | read mode | runs | chrF++ (all runs) | chrF++ (survivors) | BLEU | TER (lower better) | instruction % | glossary % | de-jargon % | coverage % | valid answer % | repairs/run | failed % | truncated % | glossaries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | annotated/native/original | tolerant | 48 | 49.3 (43.0-55.4) | 53.8 | 43.7 | 54.0 | 81.2 | 97.0 | 99.7 | 91.7 | 91.7 | 0.27 | 8.3 | 0.0 | 37 |
| android | annotated/native/original | tolerant | 48 | 54.0 (50.2-58.3) | 54.0 | 47.3 | 60.4 | 83.4 | 95.6 | 99.7 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| csv | annotated/native/original | tolerant | 48 | 45.6 (38.3-53.1) | 55.7 | 40.9 | 39.6 | 76.8 | 96.8 | 99.9 | 80.6 | 85.4 | 0.00 | 25.0 | 0.0 | 0 |
| fluent | annotated/native/original | tolerant | 48 | 53.5 (49.6-58.0) | 53.5 | 47.1 | 59.4 | 82.8 | 95.3 | 99.9 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| ios | annotated/native/original | tolerant | 48 | 53.8 (50.0-58.2) | 54.8 | 47.2 | 59.2 | 82.1 | 95.5 | 99.8 | 99.6 | 95.8 | 0.00 | 4.2 | 0.0 | 0 |
| json-cliff | annotated/native/original | tolerant | 48 | 55.1 (51.0-59.5) | 55.1 | 48.8 | 58.1 | 86.4 | 96.8 | 99.9 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| json-plain | annotated/native/original | tolerant | 48 | 53.4 (49.6-57.7) | 53.4 | 47.0 | 58.9 | 83.0 | 95.5 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |
| po | annotated/native/original | tolerant | 48 | 54.2 (50.5-58.7) | 54.7 | 47.7 | 58.1 | 83.0 | 95.9 | 99.7 | 100.0 | 97.9 | 0.00 | 2.1 | 0.0 | 0 |
| xliff-2.1 | annotated/native/original | tolerant | 48 | 42.2 (34.7-50.2) | 53.3 | 36.0 | 51.9 | 70.6 | 99.4 | 99.8 | 79.2 | 79.2 | 0.00 | 20.8 | 0.0 | 0 |
| yaml-cliff | annotated/native/original | tolerant | 48 | 55.0 (51.1-59.4) | 55.0 | 48.5 | 59.6 | 87.0 | 97.0 | 99.8 | 100.0 | 100.0 | 0.00 | 0.0 | 0.0 | 0 |

'chrF++ (all runs)' counts every run once, at the score its answer earned - a run that did not parse usually earns 0, and an answer that parses far enough to be scored keeps its partial score; 'chrF++ (survivors)' averages only the runs that produced a usable file, which is translation quality with format survival factored out. Read them together: the gap between the two columns IS the cost of format fragility. `tools/audit_report.mjs` publishes the other convention, in which every failure is scored as zero.

'read mode' is how the answer was read back: 'tolerant' applies the documented relaxations of CLIFF 1.1 Appendix C, 'strict' is the reference-toolchain reading. 'repairs/run' is the mean number of Appendix C repairs a CLIFF answer needed under the tolerant reading, so the two readings can be compared instead of confused: the same answers score 'valid answer %' 100 with repairs and 100 without.

'glossaries' counts answers that also produced a CLIFF glossary through the terminology workflow. Those answers are longer by design, so their cost shows up in the latency and output-token tables; the surface metrics do not credit them, and a comparison that ignores this understates the format.

'failed %' counts runs whose answer did not parse, did not validate or lost entries. A parse error is a failure OF THE FORMAT, not an excluded sample: its quality scores stay in the average as zeros.

A non-zero 'truncated %' means answers hit the output ceiling: those runs measure the token budget, not the format, and the run configuration must be fixed before the row is read as a result.

'context source' is where the context payload came from: original (written by hand with the corpus), native (written by the upstream project), derived (computed deterministically from corpus metadata) or annotated (written by a model and pending human sign-off). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

### D3/D4 - structural integrity of the rewrite

| format | arm | read mode | answers | valid % | ids kept % | coverage % | source kept % | repairs/answer | extra ids | missing ids | drifted sources | untranslated | failed % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | bare | tolerant | 48 | 91.7 | 91.7 | 91.7 | 91.7 | 0.04 | 0 | 126 | 0 | 0 | 8.3 |
| cliff | context | tolerant | 48 | 91.7 | 91.7 | 91.7 | 91.6 | 0.27 | 0 | 85 | 2 | 0 | 8.3 |
| android | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| android | context | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| csv | bare | tolerant | 48 | 89.6 | 89.6 | 89.6 | 89.3 | 0.00 | 0 | 98 | 2 | 0 | 10.4 |
| csv | context | tolerant | 48 | 87.2 | 80.6 | 80.6 | 80.9 | 0.00 | 1 | 228 | 0 | 0 | 25.0 |
| fluent | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| fluent | context | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| ios | bare | tolerant | 48 | 97.9 | 99.8 | 99.8 | 100.0 | 0.00 | 0 | 2 | 0 | 0 | 2.1 |
| ios | context | tolerant | 48 | 95.8 | 99.6 | 99.6 | 100.0 | 0.00 | 0 | 4 | 0 | 0 | 4.2 |
| json-cliff | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 99.9 | 0.00 | 0 | 0 | 1 | 0 | 0.0 |
| json-cliff | context | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| json-plain | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| json-plain | context | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| po | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 99.9 | 0.00 | 0 | 0 | 1 | 0 | 0.0 |
| po | context | tolerant | 48 | 97.9 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 2.1 |
| xliff-2.1 | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| xliff-2.1 | context | tolerant | 48 | 79.2 | 79.2 | 79.2 | 79.2 | 0.00 | 0 | 270 | 0 | 0 | 20.8 |
| yaml-cliff | bare | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |
| yaml-cliff | context | tolerant | 48 | 100.0 | 100.0 | 100.0 | 100.0 | 0.00 | 0 | 0 | 0 | 0 | 0.0 |

A row is one cell of the single-pass translation task - one document in, one complete file out. `valid %` uses the reading named in the `read mode` column. `ids kept %` is the share of the entries the document had whose identifier came back, so a drop means the answer renamed or dropped an entry and every translation memory keyed on it would miss. `source kept %` is the share of matched entries whose source text was left byte-for-byte alone. `repairs/answer` is untidiness the reader absorbed rather than a failure, which is why it sits beside the failure columns instead of replacing them.

### D5 - latency, plain formats

| format | runs | latency ms | ms per entry | output tokens | entries | vs CLIFF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | 48 | 78420 | 4348.0 | 12073 | 24.5 | +0.0% |
| android | 48 | 49277 | 2616.9 | 6286 | 24.5 | -37.2% |
| csv | 48 | 100184 | 5013.6 | 16281 | 24.5 | +27.8% |
| fluent | 48 | 39347 | 2183.2 | 6035 | 24.5 | -49.8% |
| ios | 48 | 64725 | 3290.4 | 7949 | 24.5 | -17.5% |
| json-cliff | 48 | 62042 | 3336.3 | 9723 | 24.5 | -20.9% |
| json-plain | 48 | 53266 | 2774.2 | 7770 | 24.5 | -32.1% |
| po | 48 | 50312 | 2888.0 | 7791 | 24.5 | -35.8% |
| xliff-2.1 | 48 | 57298 | 3110.3 | 8849 | 24.5 | -26.9% |
| yaml-cliff | 48 | 79645 | 4197.5 | 11948 | 24.5 | +1.6% |

Latency is dominated by output tokens and by provider load; it is only comparable inside one run against one endpoint.

### D6 - latency, context-carrying formats

| format | runs | latency ms | ms per entry | output tokens | entries | vs CLIFF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | 48 | 112516 | 5727.3 | 17704 | 24.5 | +0.0% |
| android | 48 | 78929 | 3901.3 | 11038 | 24.5 | -29.9% |
| csv | 48 | 161886 | 7739.7 | 26866 | 24.5 | +43.9% |
| fluent | 48 | 69383 | 3556.9 | 10127 | 24.5 | -38.3% |
| ios | 48 | 84751 | 4247.2 | 12199 | 24.5 | -24.7% |
| json-cliff | 48 | 102470 | 5393.7 | 14462 | 24.5 | -8.9% |
| json-plain | 48 | 63523 | 3455.4 | 10644 | 24.5 | -43.5% |
| po | 48 | 74500 | 3584.0 | 11149 | 24.5 | -33.8% |
| xliff-2.1 | 48 | 95180 | 4441.0 | 15001 | 24.5 | -15.4% |
| yaml-cliff | 48 | 99282 | 5211.2 | 15725 | 24.5 | -11.8% |

Latency is dominated by output tokens and by provider load; it is only comparable inside one run against one endpoint.

### D7 - format validity after model edits

| format | arm | read mode | applicable edits | still valid % | intent applied % | repairs/edit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cliff | bare | tolerant | 21 | 100.0 | 95.2 | 0.00 |
| cliff | context | tolerant | 36 | 86.1 | 86.1 | 0.17 |
| android | bare | tolerant | 15 | 100.0 | 100.0 | 0.00 |
| android | context | tolerant | 34 | 100.0 | 82.3 | 0.00 |
| csv | bare | tolerant | 21 | 100.0 | 100.0 | 0.00 |
| csv | context | tolerant | 36 | 94.4 | 88.9 | 0.00 |
| fluent | bare | tolerant | 15 | 100.0 | 100.0 | 0.00 |
| fluent | context | tolerant | 34 | 97.0 | 69.9 | 0.00 |
| ios | bare | tolerant | 15 | 100.0 | 100.0 | 0.00 |
| ios | context | tolerant | 34 | 100.0 | 88.1 | 0.00 |
| json-cliff | bare | tolerant | 21 | 100.0 | 100.0 | 0.00 |
| json-cliff | context | tolerant | 36 | 100.0 | 86.1 | 0.00 |
| json-plain | bare | tolerant | 17 | 100.0 | 100.0 | 0.00 |
| json-plain | context | tolerant | 36 | 100.0 | 91.7 | 0.00 |
| po | bare | tolerant | 17 | 100.0 | 100.0 | 0.00 |
| po | context | tolerant | 36 | 100.0 | 80.6 | 0.00 |
| xliff-2.1 | bare | tolerant | 21 | 71.4 | 71.4 | 0.00 |
| xliff-2.1 | context | tolerant | 36 | 77.8 | 69.4 | 0.00 |
| yaml-cliff | bare | tolerant | 21 | 100.0 | 100.0 | 0.00 |
| yaml-cliff | context | tolerant | 36 | 100.0 | 86.1 | 0.00 |

An edit that a format cannot express is excluded from its denominator and counted in 'applicable edits', so a format is never penalised for lacking a field, only for breaking when it has one.

'read mode' is how the edited file was read back: 'tolerant' applies the documented relaxations of CLIFF 1.1 Appendix C and 'repairs/edit' is the mean number of repairs that took. Under 'strict' the same edits are rejected instead of repaired, so the two readings bracket what a project's own toolchain would do.

### Round-trip context fidelity

| format | context facts | kept | retention % | most lost fields |
| --- | ---: | ---: | ---: | ---: |
| cliff | 2464 | 2464 | 100.0 | - |
| android | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| csv | 2464 | 2464 | 100.0 | - |
| fluent | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| ios | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| json-cliff | 2464 | 2464 | 100.0 | - |
| json-plain | 2464 | 1709 | 67.3 | header.title (16), header.info (16), header.standard (16) |
| po | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| xliff-2.1 | 2464 | 2464 | 100.0 | - |
| yaml-cliff | 2464 | 2464 | 100.0 | - |

Read back in 'tolerant' mode; repairs per round trip: 0.00. This direction renders canonical CLIFF with cliff-python itself and reads it back, so a tolerant read of a format that claims to be lossless must find nothing to repair.
