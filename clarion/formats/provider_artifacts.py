"""Vendor markup that leaks into an answer, and what this harness does with it.

A model served by a chat-completions endpoint sometimes emits its **tool-call
delimiter as ordinary text**. For the DeepSeek models this suite measures, that
delimiter is ``｜DSML｜`` - full-width vertical bars around the letters, which is why a
leaked fragment reads as punctuation damage rather than as a token. The vendor's own
material calls it the DSML tool-calling format, and the documented client behaviour is
that the API does not turn it into ``tool_calls``: it arrives in the message content.

It is an **environment artifact, not a format deviation**, and this module keeps the
two apart:

* it is not an Appendix C relaxation. Appendix C is about CLIFF written imperfectly by
  an author; this is a transport-level fragment that has nothing to do with CLIFF, so
  it is stripped and reported under its own category (``provider-markup``) rather than
  being confused with a repair the specification permits.
* it is stripped **only in the tolerant reading**. The strict reading is the
  reference-toolchain reading of the grammar, and a fragment that is not CLIFF is an
  error there, exactly as any other non-CLIFF line is.
* the stripping is reported, never silent: a project needs to know that its provider
  emitted markup, because the fix (a different endpoint setting or client, or a retry)
  is theirs and not the format's.

The fragment is a run of lines: the delimiter line and whatever the model attaches to
it, which in the observed answers is an XML-ish attribute line
(``<parameter name="final">``). Stripping stops at the first line that is CLIFF again -
a field, a marker, a section, a version line or a blank - so nothing else is touched.
"""

from __future__ import annotations

import re

#: The delimiter, in the spellings a leaked fragment can carry it: full-width bars (the
#: vendor's own token), ASCII bars, and either doubled or single.
DSML_MARKER = re.compile(r"(?:｜|\|){1,2}\s*DSML\s*(?:｜|\|){1,2}", re.IGNORECASE)

#: The category reported for every stripped fragment.
CATEGORY = "provider-markup"

#: A line that continues a leaked fragment: an XML-ish tag, a closing tag, or an
#: attribute-only tail. A *valid* CLIFF entry marker or section line is deliberately
#: not one of these, so stripping can never eat structure.
_FRAGMENT_LINE = re.compile(
    r"^\s*(?:</?[A-Za-z_][A-Za-z0-9_.:-]*(\s[^<>]*)?/?>|[A-Za-z-]+=\"[^\"]*\"\s*/?>?)\s*$"
)
_ENTRY_LINE = re.compile(r"^\s*<[A-Za-z0-9_-]+>\s*$")
_FIELD_LINE = re.compile(r"^\s*[A-Za-z0-9_-]+\s*[:=]")


def _is_cliff_again(line: str) -> bool:
    """Whether *line* belongs to the document rather than to the fragment."""
    if not line.strip():
        return True
    if line.lstrip().startswith(("[", "CLIFF")):
        return True
    if _ENTRY_LINE.match(line) or _FIELD_LINE.match(line):
        return True
    return not _FRAGMENT_LINE.match(line)


def strip_provider_markup(text: str) -> tuple[str, list[tuple[int, list[str]]]]:
    """Remove leaked vendor fragments.

    Returns the text with those lines removed and one ``(line number, lines)`` entry
    per fragment, so the caller can report what was dropped and where.
    """
    lines = text.splitlines()
    kept: list[str] = []
    fragments: list[tuple[int, list[str]]] = []
    index = 0
    while index < len(lines):
        if not DSML_MARKER.search(lines[index]):
            kept.append(lines[index])
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not _is_cliff_again(lines[index]):
            index += 1
        fragments.append((start + 1, lines[start:index]))
    kept_text = "\n".join(kept)
    if text.endswith("\n") and kept_text:
        # Stripping must not touch a single byte anywhere else: a caller that compares
        # the text before and after needs the ending preserved.
        kept_text += "\n"
    return kept_text, fragments


def has_provider_markup(text: str) -> bool:
    """Whether the answer carries a leaked delimiter at all."""
    return bool(DSML_MARKER.search(text))
