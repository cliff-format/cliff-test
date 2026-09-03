# CLARION translation phenomena, v0.3

This table defines the **translation phenomena** CLARION-Core must cover, and
which CLIF field is responsible for carrying each one. It replaces the older
"collect text per domain" approach: the domain decides what the text looks
like, **the phenomenon decides what the benchmark can measure**.

## Whether an item earns its place

An item is worth collecting only if it satisfies one of these:

| Class | Test | Example |
| --- | --- | --- |
| **A decisive** | the source **cannot** be translated correctly on its own; the answer depends on a CLIF field | irony, homograph, width budget, naming policy |
| **B high risk** | inferable from the source, but models get it systematically wrong | textbook jargon, CJK/Latin spacing, ICU placeholders |
| **C cross-entry** | the correct rendering depends on **another entry in the same file** | pronoun antecedent, callback, terminology consistency |
| **D normal text** | ordinary prose any competent translator renders correctly | plain statements, description paragraphs |

**Quota**: A 30-40%, B 20-25%, C 15-20%, **D 25-30%**.

D is not filler, it is the **baseline**: without ordinary text the corpus is
nothing but traps, a reference metric loses its meaning, and there is no way to
show that a format did not damage ordinary translation. The opposite failure is
what the earlier corpus suffered from - close to 70% D, which diluted the value
of context into noise. Both extremes are wrong.

## The phenomena

### 1. Decided by emotion (class A)

| Phenomenon | Description | Consequence of ignoring emotion |
| --- | --- | --- |
| Irony, praise that means its opposite | "Oh, that's just wonderful." said after the plan failed | rendered as genuine praise; the meaning inverts |
| Politely phrased threat | courteous surface, coercive intent | rendered as courtesy; the tension is lost |
| Forced agreement | agrees on the surface, resigned underneath | rendered as enthusiasm |
| Comfort versus restraint | "Relax." can soothe or reprimand | the register lands on the wrong side |
| Dry humour, self-deprecation | literal self-criticism, actually a joke | rendered as real self-criticism |
| Deliberately mechanical delivery | system announcement, must not sound human | rendered too colloquially |

### 2. Decided by type (class A)

| Phenomenon | Description | Consequence |
| --- | --- | --- |
| Label versus sentence | "Save" as a button versus as an instruction | a button becomes a full sentence with a full stop |
| Proper noun versus common word | Forge the place versus forge the verb | a place name is translated |
| Idiom versus literal | "Break a leg!" as a wish versus an injury report | a blessing becomes a broken leg |
| Subtitle versus narration | different reading-speed constraints | the subtitle is too long |
| Accessibility cue | a sound-effect caption keeps its bracket convention | rendered as an ordinary sentence |
| Term position versus running text | the same word as a glossary term and in prose | the term is rewritten to fit the sentence |

### 3. Decided by context (class A)

| Phenomenon | Description | Consequence |
| --- | --- | --- |
| Homograph | rate = billing rate / frame rate / rate limit | the wrong sense is chosen |
| Pronoun antecedent | the referent of "it" is only in the previous line | the reference is wrong |
| Speaker identity | the same line spoken by different characters | the register is wrong |
| Scene sets the register | the same sentence in a courtroom and in a bar | register mismatch |
| Ellipsis | "Yes, please." completes the previous line | the sentence does not stand |
| Culture-specific item | domesticate or foreignize depends on the audience | the reader does not understand it |

### 4. Decided by standard or info (class A)

| Phenomenon | Description | Consequence |
| --- | --- | --- |
| Naming policy | Ash must be translated semantically, Flint transliterated | names drift across the file |
| Keep untranslated | brand and API names stay in Latin script | they get translated |
| Register directive | the whole file uses one form of address | the person shifts mid-file |
| Enforced terminology | default is 默认, never 缺省 | textbook jargon |
| Typographic convention | space between Han and Latin, fullwidth punctuation | the file breaks house style |
| Unit conversion | whether to convert measurements | the numbers become wrong |

### 5. Decided by max-width (class A)

| Phenomenon | Description |
| --- | --- |
| Width forces a shorter rendering | the same label at 14 cells and at 8 cells needs different wording |
| Subtitle reading speed | a cell budget per line |
| Truncation risk | the natural rendering overflows and the phrasing must be rebuilt |

### 6. Cross-entry dependence (class C)

| Phenomenon | Description |
| --- | --- |
| Terminology consistency | one term across five or more entries must be identical |
| Callback | a later line quotes an earlier one verbatim |
| Form of address evolves | the relationship changes and the address changes with it |
| Numbered cross-reference | "see Section 4.2" must match the actual clause number |
| Dialogue turns | a reply depends on the previous turn |

### 7. Systematic model bias (class B)

| Phenomenon | Description |
| --- | --- |
| Textbook jargon | 缺省 / 鲁棒 / 词元 / 解析度 |
| CJK-Latin spacing | between Han text and Latin letters or digits |
| Punctuation width | halfwidth marks inside Han sentences |
| ICU and placeholders | structure and argument names must survive |
| Numbers and units | thousands separators, date formats, units |
| Word-order calque | English relative clauses transplanted whole |
| Over-domestication | proper nouns replaced by local equivalents |

## Minimal-pair design rules (mandatory)

1. **Same source**: identical, or differing by a single word.
2. **Neutral identifiers**: `probe-07a` / `probe-07b`. Suffixes that encode the
   answer, such as `-sincere` / `-sarcastic`, are **forbidden**.
   *This is the defect v0.2 exposed in measurement: once the id leaked the
   answer, the plain arm distinguished 12 of 12 pairs and the value of context
   was measured far below its real size.*
3. **Mutually exclusive rules**: each member forbids the other's rendering, so
   ignoring the deciding field necessarily fails at least one of them.
4. **The context must not contain the answer**: no target-language text.
5. **One deciding field per pair**, otherwise the result cannot be attributed.

## What the benchmark focuses on, in order

1. **The bare-to-context difference in class A pass rate** - the core claim, and
   now the primary metric;
2. **Minimal-pair distinguishability** - the plain arm should be *unable* to
   distinguish (ideally 0), the context arm should distinguish;
3. **Format failure rate** - already demonstrated, kept under watch;
4. **Token cost of carrying the same context** - already demonstrated, kept
   under watch;
5. Class B pass rate - independent of format; it measures the prompt and the
   de-jargon policy;
6. Class D - only to confirm that nothing over-corrected ordinary translation.
