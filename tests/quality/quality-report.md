# CLIFF Translation Quality Report


**Candidate:** `tests/quality/translator-output.cliff`  
**Source corpus:** `tests/quality/corpus.cliff`  
**Glossary:** `tests/quality/glossary.zh-CN.cliff`  

**Rubric:** Meaning (信) 4 + Naturalness (达) 3 + Emotion/register/style (雅) 2 + Constraints 1 = 10 points per entry.

Objective constraint check (`tests/quality/check_constraints.py`): **48/48 PASS**.

## Entry scores

| Entry ID | Score (x/10) | Justification |
| --- | --- | --- |
| `table-this` | 10/10 | “暂缓此事” correctly localizes “table this” as postpone, and “再回头讨论” captures “circle back” as returning to the topic. No literal 桌子/转圈; the meeting register is neutral-formal and natural. |
| `ears` | 10/10 | “我洗耳恭听。” is the natural Chinese four-character idiom for attentive listening, exactly matching the gold reference. |
| `sarcastic-meeting` | 10/10 | “哦，可真行啊，又开会。” preserves the irony of “Oh, great” and the annoyance of “Another meeting.” The colloquial “可真行啊” reads as an ironic exclamation, matching the declared [angry, playful] emotion. |
| `window-please` | 10/10 | “麻烦您把窗户关上，好吗？” is a polite request using 您 and a soft question ending; there is no command tone. |
| `break-a-leg` | 10/10 | “在台上好好发挥，祝你演出成功！” is a natural backstage success wish, never a literal “摔断腿”; it keeps the playful encouraging register. |
| `kick-bucket` | 10/10 | “他去年春天去世了。” is a faithful, gentle euphemism for death, exactly matching the gold reference and preserving the sad, quiet family register. |
| `cats-dogs` | 10/10 | “外面正下着倾盆大雨！” is the standard idiomatic Chinese expression for very heavy rain, with no literal cats/dogs and natural word order. |
| `time-flies` | 10/10 | “时光飞逝如箭；果蝇喜欢香蕉。” keeps both readings of the pun (time flying, and fruit flies liking bananas) in natural Chinese; the juxtaposition is the wordplay signal requested by the context. |
| `proper-nouns` | 10/10 | “泽费尔舰长将奥蕾莉亚号降落在七号星港。” uses all glossary forms exactly: 泽费尔舰长 / 奥蕾莉亚号 / 七号星港. It is faithful and fits the serious sci-fi narration; the line is well within max-width 60. |
| `word-order` | 10/10 | “这把剑是在古老火山的中心为国王锻造的。” uses natural Chinese topic-comment order instead of English word order, while preserving the full meaning. |
| `icu-count` | 9/10 | The literal text is translated correctly and the ICU syntax/braces are valid, but the candidate retains the English-oriented `one {# 条新消息}` category. Chinese plural guidance expects only `=0` and `other`; the extra `one` branch is harmless but not fully constraint-optimized. |
| `accept-short` | 10/10 | “接受” is 2 Chinese characters = 4 display cells, comfortably within max-width 6, and is the standard neutral button label. |

## Average score

Sum: 10 + 10 + 10 + 10 + 10 + 10 + 10 + 10 + 10 + 10 + 9 + 10 = **119 / 120**

Average = 119 ÷ 12 = **9.9167 / 10** = **99.17%**

## Pass/fail

**PASS** — 99.17% ≥ 90% acceptance threshold.

## Strongest translation decisions

1. **`kick-bucket` — “他去年春天去世了。”** This is a textbook localization of a death euphemism: it keeps the gentle, sad register of the source and avoids every crude literal option (“kicked the bucket” → 去世, never 水桶/桶).
2. **`cats-dogs` — “外面正下着倾盆大雨！”** The English idiom is completely re-encoded into the standard Chinese heavy-rain idiom with no trace of cats/dogs, natural word order, and the right light conversational tone.
3. **`proper-nouns` — “泽费尔舰长将奥蕾莉亚号降落在七号星港。”** All three canonical glossary terms appear verbatim (泽费尔舰长 / 奥蕾莉亚号 / 七号星港) in a serious, fluid narration sentence.

## Weakest translation decisions

1. **`icu-count` — “{count, plural, =0 {没有消息} one {# 条新消息} other {# 条新消息}}”** This is the only actual deduction. The message is correct and valid ICU, but the `one` branch should be dropped for natural Chinese plural handling; the gold reference keeps only `=0` and `other`.
2. **`time-flies` — “时光飞逝如箭；果蝇喜欢香蕉。”** Both readings survive and the wording is natural, but among an otherwise very strong set this is the least punchy: the wordplay is conveyed mainly by juxtaposition, and the Chinese loses some of the syntactic ambiguity of “flies”/“like.”
3. **`sarcastic-meeting` — “哦，可真行啊，又开会。”** The sarcasm is clearly preserved and the [angry, playful] emotion is respected; this is listed only as a relative weakest point because “可真行啊” is a more colloquial ironic filler than the gold’s more direct “真棒,” a slight stylistic divergence rather than an error.

## Emotion tags, content type, and register statement

**Emotion tags (including sarcasm): respected overall.**  
- `sarcastic-meeting` preserves the sarcastic “Oh, great” as an ironic exclamation (“可真行啊”) plus the annoyed “又开会”; both [angry] and [playful] are honored.  
- `ears` uses the idiomatic, attentive-listening phrase appropriate to [informal].  
- `window-please` matches [polite] with 您 and a soft request form.  
- `break-a-leg`, `cats-dogs`, and `time-flies` keep [playful] by localizing idioms/puns rather than translating literally.  
- `kick-bucket` maintains the gentle [sad] euphemism.  
- `proper-nouns` and `word-order` use formal, weighty narration for [serious].  
- `icu-count` and `accept-short` use neutral/objective UI and label tone.

**Content type:** respected. Dialogue entries read as spoken Chinese; narration entries (“time-flies”, “proper-nouns”, “word-order”) have narrative flow; `accept-short` is a terse label; `icu-count` reads as a system notification.

**Register:** respected throughout. The office meeting stays neutral-formal, the office request stays politely deferential, the backstage/storm/pun contexts stay light and playful, the death euphemism stays gentle, and the sci-fi narration stays serious.
