# CLIFF generation supplement

## Ids

- An id is a name: one or more of `A-Z`, `a-z`, `0-9`, `_`, `-`. It never
  contains `.`, and it is case-sensitive.
- **Copy every id you receive byte for byte.** Do not recapitalize it, do not
  add or remove underscores, and do not "tidy" it: the id is the translation
  match key, and a renamed id is a lost translation.
- When you must invent an id (a new entry, a glossary term), the recommended
  shapes are lowercase kebab-case (`editors-note`, `the-block-of-grass`) or
  PascalCase (`EditorsNote`, `TheBlockOfGrass`). Use one shape per file.

## Tags (not ids)

- `type`, `emotion`, `status`, and `variant` are tags, and their spelling is
  fixed: lowercase kebab-case words from the closed vocabularies, written bare.
- `status: Final` and `type: Noun` are errors, not aliases.

## Fields

- One field per line: `key: value`.
- Each entry has one `source`, one `target`, one `type`, and one `status`.
- Text values are quoted strings; tags are bare names; list fields keep their
  brackets.
- A field appears at most once per entry, group, or header. Two `reference:`
  lines are an error; one list holds both paths.

## Strings

- The whole value stays one quoted string.
- Escape inner double quotes as `\"`, backslash as `\\`, newline as `\n`, carriage
  return as `\r`, and tab as `\t` - those five are the whole escape set.
- Apostrophes are ordinary characters inside double-quoted strings.
- Raw newline and raw tab are invalid inside strings.

## Terminators

- A line may end with at most one `,` or `;`. It means nothing and the
  canonical form omits it; write `key: value`, not `key: value,`.

## Glossary

- Use `variant: glossary` and clan `<clan>-terms`.
- One entry per term; glossary ids follow the same identifier rule and are
  unique.

## Serialization

- `key: value` with one space after the colon, LF endings, no trailing
  whitespace.
- The document ends after the last field.
