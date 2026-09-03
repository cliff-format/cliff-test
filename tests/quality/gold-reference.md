# Gold Reference Translations

These are the human-curated reference translations for
[corpus.clif](corpus.clif). They are the scoring target for the translation
accuracy test. Equivalent natural phrasings are accepted; the *Key points*
column is what evaluators must verify.

| Entry | Reference target (zh-CN) | Key points |
| --- | --- | --- |
| `table-this` | 我们先把这件事放一放，演示结束后再回来讨论。 | "table" = postpone, not 桌子; "circle back" = return, not 转圈 |
| `ears` | 我洗耳恭听。 | Natural four-character idiom; attentive listening |
| `sarcastic-meeting` | 哦，真棒。又开会。 | Sarcasm preserved; "great" is ironic, not enthusiastic |
| `window-please` | 劳驾您把窗户关上，好吗？ | Polite request; 您; no command tone |
| `break-a-leg` | 祝你演出大获成功！ | Wishing success; never 摔断腿 |
| `kick-bucket` | 他去年春天去世了。 | Gentle euphemism for death; no crude literal |
| `cats-dogs` | 外面正下着倾盆大雨！ | Heavy rain idiom, not cats/dogs |
| `time-flies` | 时间如箭般飞逝；果蝇喜欢香蕉。 | Preserve both readings of the pun; natural Chinese wordplay signal |
| `proper-nouns` | 泽费尔舰长驾驶奥蕾莉亚号降落在七号星港。 | Glossary terms exactly: 泽费尔舰长 / 奥蕾莉亚号 / 七号星港 |
| `icu-count` | {count, plural, =0 {没有消息} other {# 条新消息}} | ICU syntax identical; only literal text translated; Chinese plural category |
| `word-order` | 这把剑是在古火山深处为国王锻造的。 | Chinese topic-comment order, not English order |
| `accept-short` | 接受 | 2 characters = 4 cells, fits max-width 6 |

## Scoring rubric (per entry, 10 points)

| Criterion | Points |
| --- | --- |
| Faithfulness (信): meaning complete and accurate | 4 |
| Expressiveness (达): natural expression, idiomatic target, correct word order | 3 |
| Elegance (雅): emotion/register/style matched | 2 |
| Constraints: glossary, ICU syntax, max-width | 1 |

A score of ≥ 9/10 is "reference-accurate". Corpus accuracy = average score.
Acceptance threshold: ≥ 90%.
