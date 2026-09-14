"""Display width in cells, following CLIFF specification section 15 / UAX 11.

Implemented independently of cliff-python on purpose: the harness must be able to
disagree with the implementation it is testing. The unit tests assert that both
agree on the specification's own examples.
"""

from __future__ import annotations

import unicodedata

_ZERO_WIDTH_CATEGORIES = {"Mn", "Mc", "Me", "Cf"}
_WIDE = {"W", "F"}
_VARIATION_SELECTOR_16 = "\ufe0f"
_ZWJ = "\u200d"


def _is_emoji_presentation(char: str, following: str) -> bool:
    if unicodedata.category(char) == "So" and following.startswith(_VARIATION_SELECTOR_16):
        return True
    point = ord(char)
    return (
        0x1F300 <= point <= 0x1FAFF
        or 0x1F000 <= point <= 0x1F2FF
        or point in {0x231A, 0x231B, 0x23E9, 0x23F0, 0x23F3}
    )


def display_cells(text: str) -> int:
    """Rendered width of text in display cells.

    Wide and fullwidth characters and emoji count 2, combining marks and
    format characters count 0, everything else counts 1. An emoji ZWJ sequence
    renders as one glyph and therefore counts 2 cells in total.
    """
    total = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        following = text[index + 1 : index + 3]
        if char == _ZWJ:
            # Zero-width joiner: skip the joiner and the joined member, the
            # sequence already contributed its two cells.
            index += 2
            while index < length and text[index] == _VARIATION_SELECTOR_16:
                index += 1
            continue
        if unicodedata.category(char) in _ZERO_WIDTH_CATEGORIES:
            index += 1
            continue
        if _is_emoji_presentation(char, following):
            total += 2
            index += 1
            while index < length and text[index] == _VARIATION_SELECTOR_16:
                index += 1
            continue
        total += 2 if unicodedata.east_asian_width(char) in _WIDE else 1
        index += 1
    return total
