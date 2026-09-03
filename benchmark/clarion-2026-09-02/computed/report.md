# CLARION run: clarion-deepseek-v4-flash

- Corpus: clarion-core
- Formats: clif, xliff-2.1, po, fluent, json-clif, json-plain, yaml-clif, csv, android, ios
- Arms: bare, context
- Tokenizer: o200k_base
- Model: openai:deepseek-v4-flash (reasoning off, temperature 0.0)
- CLIF specification injection: production digest, split
- Repeats per cell: 3

Every arm of every format is generated from the same CLIF corpus documents through clif-python, so a difference between two rows is a property of the format, not of the fixture.

### D1 - token cost, plain formats

| format | document tokens | per entry | vs CLIF (doc) | glossary tokens | format instructions | prompt total | prompt without format instructions | vs CLIF (prompt) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | 24322 | 62.0 | +0.0% | 0 | 35184 | 259103 | 223919 | +0.0% |
| android | 41228 | 105.2 | +69.5% | 0 | 656 | 50630 | 49974 | -80.5% |
| csv | 28908 | 73.7 | +18.9% | 0 | 496 | 37913 | 37417 | -85.4% |
| fluent | 37491 | 95.6 | +54.1% | 0 | 496 | 46733 | 46237 | -82.0% |
| ios | 39186 | 100.0 | +61.1% | 0 | 544 | 48476 | 47932 | -81.3% |
| json-clif | 26388 | 67.3 | +8.5% | 0 | 480 | 35377 | 34897 | -86.3% |
| json-plain | 20647 | 52.7 | -15.1% | 0 | 704 | 30097 | 29393 | -88.4% |
| po | 24218 | 61.8 | -0.4% | 0 | 416 | 33143 | 32727 | -87.2% |
| xliff-2.1 | 29848 | 76.1 | +22.7% | 0 | 688 | 39045 | 38357 | -84.9% |
| yaml-clif | 23492 | 59.9 | -3.4% | 0 | 480 | 32481 | 32001 | -87.5% |

Tokenizer: o200k_base. 'format instructions' is the CLIF specification digest plus the per-format notes; subtracting it gives the 'without' column, so the with/without comparison needs no extra model run.

### D2 - token cost, context-carrying formats

| format | document tokens | per entry | vs CLIF (doc) | glossary tokens | format instructions | prompt total | prompt without format instructions | vs CLIF (prompt) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | 47499 | 121.2 | +0.0% | 0 | 35184 | 283224 | 248040 | +0.0% |
| android | 77805 | 198.5 | +63.8% | 0 | 656 | 88151 | 87495 | -68.9% |
| csv | 140693 | 358.9 | +196.2% | 0 | 496 | 150642 | 150146 | -46.8% |
| fluent | 75914 | 193.7 | +59.8% | 0 | 496 | 86100 | 85604 | -69.6% |
| ios | 75766 | 193.3 | +59.5% | 0 | 544 | 86000 | 85456 | -69.6% |
| json-clif | 57696 | 147.2 | +21.5% | 0 | 480 | 67629 | 67149 | -76.1% |
| json-plain | 62986 | 160.7 | +32.6% | 0 | 704 | 73380 | 72676 | -74.1% |
| po | 62450 | 159.3 | +31.5% | 0 | 416 | 72319 | 71903 | -74.5% |
| xliff-2.1 | 106156 | 270.8 | +123.5% | 0 | 688 | 116297 | 115609 | -58.9% |
| yaml-clif | 52753 | 134.6 | +11.1% | 0 | 480 | 62686 | 62206 | -77.9% |

Tokenizer: o200k_base. 'format instructions' is the CLIF specification digest plus the per-format notes; subtracting it gives the 'without' column, so the with/without comparison needs no extra model run.

### D3 - quality, plain formats

| format | context source | runs | chrF++ (all) | chrF++ (ok) | BLEU | TER (lower better) | instruction % | glossary % | de-jargon % | coverage % | valid answer % | failed % | truncated % | glossaries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | annotated/native/original | 48 | 49.2 (44.6-54.1) | 49.2 | 42.9 | 61.4 | 77.4 | 94.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 12 |
| android | annotated/native/original | 48 | 47.8 (43.6-52.5) | 47.8 | 41.4 | 63.6 | 74.6 | 94.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| csv | annotated/native/original | 48 | 36.4 (29.3-43.9) | 47.2 | 34.1 | 39.2 | 63.6 | 95.8 | 100.0 | 77.1 | 77.1 | 22.9 | 0.0 | 0 |
| fluent | annotated/native/original | 48 | 48.9 (44.4-53.8) | 48.9 | 42.6 | 63.1 | 75.7 | 92.4 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| ios | annotated/native/original | 48 | 47.8 (43.4-52.7) | 48.9 | 41.3 | 59.9 | 76.4 | 93.9 | 100.0 | 95.2 | 93.8 | 6.2 | 0.0 | 0 |
| json-clif | annotated/native/original | 48 | 48.5 (44.2-53.3) | 48.5 | 42.2 | 62.8 | 75.7 | 93.8 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| json-plain | annotated/native/original | 48 | 44.5 (39.5-50.1) | 48.6 | 40.6 | 46.9 | 75.8 | 93.5 | 100.0 | 91.7 | 91.7 | 8.3 | 0.0 | 0 |
| po | annotated/native/original | 48 | 46.8 (41.5-52.3) | 47.1 | 42.1 | 61.5 | 76.1 | 94.0 | 100.0 | 100.0 | 97.9 | 2.1 | 0.0 | 0 |
| xliff-2.1 | annotated/native/original | 48 | 48.7 (44.4-53.4) | 48.7 | 42.2 | 63.9 | 75.3 | 93.8 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| yaml-clif | annotated/native/original | 48 | 45.9 (39.9-52.5) | 52.5 | 42.9 | 36.0 | 76.1 | 94.0 | 100.0 | 87.5 | 87.5 | 12.5 | 0.0 | 0 |

'chrF++ (all)' scores a failed run as zero, which is what a project would experience; 'chrF++ (ok)' averages only the runs that produced a usable file, which is translation quality with format survival factored out. Read them together: the gap between the two columns IS the cost of format fragility.

'glossaries' counts answers that also produced a CLIF glossary through the terminology workflow. Those answers are longer by design, so their cost shows up in the latency and output-token tables; the surface metrics do not credit them, and a comparison that ignores this understates the format.

'failed %' counts runs whose answer did not parse, did not validate or lost entries. A parse error is a failure OF THE FORMAT, not an excluded sample: its quality scores stay in the average as zeros.

A non-zero 'truncated %' means answers hit the output ceiling: those runs measure the token budget, not the format, and the run configuration must be fixed before the row is read as a result.

'context source' is where the context payload came from: original (written by hand with the corpus), native (written by the upstream project), derived (computed deterministically from corpus metadata) or annotated (written by a model and pending human sign-off). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

### D4 - quality, context-carrying formats

| format | context source | runs | chrF++ (all) | chrF++ (ok) | BLEU | TER (lower better) | instruction % | glossary % | de-jargon % | coverage % | valid answer % | failed % | truncated % | glossaries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | annotated/native/original | 48 | 53.5 (49.4-57.8) | 53.5 | 46.9 | 58.6 | 85.3 | 95.7 | 99.9 | 100.0 | 100.0 | 0.0 | 0.0 | 9 |
| android | annotated/native/original | 48 | 52.0 (48.1-56.5) | 52.0 | 45.5 | 58.7 | 78.5 | 94.3 | 99.9 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| csv | annotated/native/original | 48 | 13.6 (6.8-21.3) | 53.0 | 11.7 | 14.9 | 36.8 | 97.5 | 100.0 | 27.1 | 66.7 | 85.4 | 0.0 | 0 |
| fluent | annotated/native/original | 48 | 52.6 (48.8-56.8) | 52.6 | 46.2 | 59.1 | 81.0 | 94.1 | 99.9 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| ios | annotated/native/original | 48 | 50.9 (46.8-55.2) | 53.0 | 44.5 | 56.8 | 79.4 | 94.0 | 99.9 | 95.7 | 89.6 | 10.4 | 0.0 | 0 |
| json-clif | annotated/native/original | 48 | 18.4 (11.4-26.1) | 18.4 | 17.3 | 94.6 | 72.2 | 82.9 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0 |
| json-plain | annotated/native/original | 48 | 48.5 (43.2-53.7) | 51.7 | 43.5 | 46.0 | 78.3 | 94.0 | 99.9 | 93.8 | 93.8 | 6.2 | 0.0 | 0 |
| po | annotated/native/original | 48 | 51.5 (47.6-55.8) | 51.8 | 44.8 | 60.1 | 80.6 | 94.0 | 99.9 | 100.0 | 97.9 | 2.1 | 0.0 | 0 |
| xliff-2.1 | annotated/native/original | 48 | 52.2 (47.3-57.1) | 53.3 | 45.8 | 57.4 | 85.9 | 96.8 | 99.9 | 97.9 | 97.9 | 2.1 | 0.0 | 0 |
| yaml-clif | annotated/native/original | 48 | 33.6 (25.8-41.3) | 36.7 | 31.0 | 64.4 | 80.5 | 91.7 | 99.9 | 93.8 | 93.8 | 8.3 | 2.1 | 0 |

'chrF++ (all)' scores a failed run as zero, which is what a project would experience; 'chrF++ (ok)' averages only the runs that produced a usable file, which is translation quality with format survival factored out. Read them together: the gap between the two columns IS the cost of format fragility.

'glossaries' counts answers that also produced a CLIF glossary through the terminology workflow. Those answers are longer by design, so their cost shows up in the latency and output-token tables; the surface metrics do not credit them, and a comparison that ignores this understates the format.

'failed %' counts runs whose answer did not parse, did not validate or lost entries. A parse error is a failure OF THE FORMAT, not an excluded sample: its quality scores stay in the average as zeros.

A non-zero 'truncated %' means answers hit the output ceiling: those runs measure the token budget, not the format, and the run configuration must be fixed before the row is read as a result.

'context source' is where the context payload came from: original (written by hand with the corpus), native (written by the upstream project), derived (computed deterministically from corpus metadata) or annotated (written by a model and pending human sign-off). A context-arm gain measured on annotated context is a weaker claim than one measured on native context.

### D5 - latency, plain formats

| format | runs | latency ms | ms per entry | output tokens | entries | vs CLIF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | 48 | 29330 | 1620.3 | 2671 | 24.5 | +0.0% |
| android | 48 | 30347 | 1626.2 | 2513 | 24.5 | +3.5% |
| csv | 48 | 26436 | 1392.0 | 2242 | 24.5 | -9.9% |
| fluent | 48 | 27263 | 1504.9 | 2394 | 24.5 | -7.0% |
| ios | 48 | 30382 | 1528.7 | 2382 | 24.5 | +3.6% |
| json-clif | 48 | 29685 | 1658.2 | 2758 | 24.5 | +1.2% |
| json-plain | 48 | 17906 | 1016.7 | 1288 | 24.5 | -39.0% |
| po | 48 | 26845 | 1446.8 | 2441 | 24.5 | -8.5% |
| xliff-2.1 | 48 | 31056 | 1659.4 | 3047 | 24.5 | +5.9% |
| yaml-clif | 48 | 31753 | 1714.4 | 2543 | 24.5 | +8.3% |

Latency is dominated by output tokens and by provider load; it is only comparable inside one run against one endpoint.

### D6 - latency, context-carrying formats

| format | runs | latency ms | ms per entry | output tokens | entries | vs CLIF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| clif | 48 | 43297 | 2223.0 | 4120 | 24.5 | +0.0% |
| android | 48 | 49618 | 2300.7 | 4835 | 24.5 | +14.6% |
| csv | 48 | 81755 | 3544.1 | 9623 | 24.5 | +88.8% |
| fluent | 48 | 49894 | 2547.9 | 4738 | 24.5 | +15.2% |
| ios | 48 | 41822 | 1891.4 | 3383 | 24.5 | -3.4% |
| json-clif | 48 | 32707 | 1634.2 | 3659 | 24.5 | -24.5% |
| json-plain | 48 | 38461 | 1907.2 | 3965 | 24.5 | -11.2% |
| po | 48 | 48391 | 2433.7 | 5029 | 24.5 | +11.8% |
| xliff-2.1 | 48 | 70364 | 3254.3 | 7746 | 24.5 | +62.5% |
| yaml-clif | 48 | 51268 | 2448.3 | 6213 | 24.5 | +18.4% |

Latency is dominated by output tokens and by provider load; it is only comparable inside one run against one endpoint.

### D7 - format validity after model edits

| format | arm | applicable edits | still valid % | intent applied % |
| --- | ---: | ---: | ---: | ---: |
| clif | bare | 21 | 100.0 | 95.2 |
| clif | context | 36 | 91.7 | 86.1 |
| android | bare | 15 | 100.0 | 100.0 |
| android | context | 34 | 100.0 | 91.2 |
| csv | bare | 21 | 76.2 | 76.2 |
| csv | context | 36 | 61.1 | 55.6 |
| fluent | bare | 15 | 100.0 | 100.0 |
| fluent | context | 34 | 100.0 | 55.6 |
| ios | bare | 15 | 100.0 | 100.0 |
| ios | context | 34 | 33.1 | 41.4 |
| json-clif | bare | 21 | 100.0 | 100.0 |
| json-clif | context | 36 | 100.0 | 86.1 |
| json-plain | bare | 17 | 100.0 | 94.4 |
| json-plain | context | 36 | 100.0 | 63.9 |
| po | bare | 17 | 100.0 | 94.4 |
| po | context | 36 | 100.0 | 80.6 |
| xliff-2.1 | bare | 21 | 100.0 | 95.2 |
| xliff-2.1 | context | 36 | 100.0 | 88.9 |
| yaml-clif | bare | 21 | 100.0 | 95.2 |
| yaml-clif | context | 36 | 100.0 | 86.1 |

An edit that a format cannot express is excluded from its denominator and counted in 'applicable edits', so a format is never penalised for lacking a field, only for breaking when it has one.

### Round-trip context fidelity

| format | context facts | kept | retention % | most lost fields |
| --- | ---: | ---: | ---: | ---: |
| clif | 2464 | 2464 | 100.0 | - |
| android | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| csv | 2464 | 2464 | 100.0 | - |
| fluent | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| ios | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| json-clif | 2464 | 2464 | 100.0 | - |
| json-plain | 2464 | 1709 | 67.3 | header.title (16), header.info (16), header.standard (16) |
| po | 2464 | 2414 | 97.6 | header.title (16), header.info (16), header.standard (16) |
| xliff-2.1 | 2464 | 2464 | 100.0 | - |
| yaml-clif | 2464 | 2464 | 100.0 | - |
