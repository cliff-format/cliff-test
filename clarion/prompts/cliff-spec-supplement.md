# CLIFF generation supplement

## Ids

- Every id is a lowercase kebab-case name: `editors-note`, `the-block-of-grass`.
- Build an id from a source term by keeping lowercase letters and joining the
  remaining parts with hyphens: `editor's note` -> `editors-note`.

## Fields

- One field per line: `key: value`.
- Each entry has one `source`, one `target`, one `type`, and one `status`.
- Text values are quoted strings; tags are bare names; list fields keep their
  brackets.

## Strings

- The whole value stays one quoted string.
- Escape inner double quotes as `\"`, backslash as `\\`, newline as `\n`, and
  tab as `\t`.
- Apostrophes are ordinary characters inside double-quoted strings.
- Raw newline and raw tab are invalid inside strings.

## Glossary

- Use `variant: glossary` and clan `<clan>-terms`.
- One entry per term; glossary ids follow the same kebab-case rule and are
  unique.
- Keep the glossary concise.

## Serialization

- `key: value` with one space after the colon, LF endings, no trailing
  whitespace.
- The document ends after the last field.
