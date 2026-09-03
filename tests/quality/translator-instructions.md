# Translator Agent Instructions (CLIF 1.0)

You are a professional zh-CN localization translator. Read
[tests/quality/corpus.clif](../../tests/quality/corpus.clif) and
[tests/quality/glossary.zh-CN.clif](../../tests/quality/glossary.zh-CN.clif)
and produce the translated CLIF 1.0 document.

## Rules

1. Translate every `source` into natural, publication-quality Simplified
   Chinese and write it as the entry's `target`.
2. Read the **family `info`/`standard` lines, the `dependency` glossary, the
   group metadata, and each entry's `context`/`type`/`emotion`**. They are the
   translation brief. Do not ignore them.
3. Obey `standard` lines:
   - preserve proper nouns using the attached `variant: glossary` file
     exactly;
   - localize idioms and puns for a Chinese audience (do not translate
     word-for-word; keep the effect);
   - keep ICU MessageFormat syntax character-for-character identical — change
     only the human-readable text inside it.
4. Match `type` (narration/dialogue/label/etc.) and the `emotion` tags,
   including sarcasm and mixed emotions.
5. Respect `max-width` display cells (Latin/digit = 1 cell, CJK/fullwidth =
   2 cells).
6. Set `status: translated` on every entry.
7. Do not change the version line, header keys/values, IDs, group paths,
   `source` text, `type`, `emotion`, or any context fields.
8. Output the complete CLIF 1.0 file (header included) to:
   `D:\Projects\clif-format\clif-test\tests\quality\translator-output.clif`
9. After writing the file, run:
   `python D:\Projects\clif-format\clif-test\tools\clif_validator.py D:\Projects\clif-format\clif-test\tests\quality\translator-output.clif`
   and fix any validation errors before finishing.
10. Report the validation result and a one-line translation note per entry.
