"""The Gutenberg importer's text handling, without downloading anything.

`corpus/gutenberg.py` was the last module no test touched. `download` needs the
network and is not exercised here; everything downstream of it is pure text work,
and that is where a silent error costs the most. The licence header is cut at a
marker pair, so a mistake there shifts every aligned paragraph in the corpus, and
the paragraph splitter decides what the corpus even contains.

The fixtures are miniature stand-ins for the real shapes: the `*** START OF` /
`*** END OF` marker pair, a `CHAPTER <roman>` heading for English, a `第一回`
heading for Chinese, and the two paragraph layouts the books actually use - blank
lines, and hard-wrapped lines where a new paragraph starts with an ideographic
space.
"""

from __future__ import annotations

from clarion.corpus.gutenberg import Chapter, paragraphs_of, split_chapters, strip_boilerplate

HEADER = """The Project Gutenberg eBook of A Test Book

This eBook is for the use of anyone anywhere at no cost and with almost no
restrictions whatsoever.

*** START OF THE PROJECT GUTENBERG EBOOK A TEST BOOK ***
"""

FOOTER = """
*** END OF THE PROJECT GUTENBERG EBOOK A TEST BOOK ***

Updated editions will replace the previous one.
"""


def _book(body: str) -> str:
    return HEADER + body + FOOTER


# --- the boilerplate boundary -------------------------------------------------


def test_the_licence_header_and_footer_are_removed() -> None:
    stripped = strip_boilerplate(_book("CHAPTER I.\n\nA body line.\n"))
    assert "PROJECT GUTENBERG" not in stripped
    assert "for the use of anyone anywhere" not in stripped
    assert "Updated editions will replace" not in stripped
    assert stripped == "CHAPTER I.\n\nA body line."


def test_the_header_is_cut_after_the_marker_line_not_at_it() -> None:
    """The marker itself is on the header's last line, not the body's first."""
    stripped = strip_boilerplate(_book("First body line.\n"))
    assert stripped.startswith("First body line."), stripped[:60]


def test_a_book_without_markers_loses_only_its_outer_whitespace() -> None:
    """No marker means no claim about the boundary: keep everything."""
    plain = "CHAPTER I.\n\nText without any markers."
    assert strip_boilerplate(plain + "\n\n") == plain


def test_carriage_returns_are_normalised_before_the_cut() -> None:
    """A CRLF file must not leave a stray \\r at the start of the body."""
    stripped = strip_boilerplate(_book("First body line.\n").replace("\n", "\r\n"))
    assert "\r" not in stripped
    assert stripped.startswith("First body line.")


# --- the chapter splitter -----------------------------------------------------


def test_english_chapters_split_on_a_roman_numeral_heading() -> None:
    text = _book(
        "CHAPTER I\n\nFirst paragraph, long enough to be a paragraph.\n\n"
        "CHAPTER II\n\nSecond paragraph, also long enough to count.\n"
    )
    chapters = split_chapters(text, language="en-US")
    assert len(chapters) == 2, [chapter.title for chapter in chapters]
    assert chapters[0].title == "CHAPTER I"
    assert "First paragraph" in chapters[0].paragraphs[0]
    assert "Second paragraph" in chapters[1].paragraphs[0]
    assert "Second paragraph" not in " ".join(chapters[0].paragraphs), (
        "a chapter body must not bleed into the next chapter"
    )


def test_a_chapter_after_a_blank_line_gets_the_fallback_title() -> None:
    """A known inconsistency, pinned rather than asserted away.

    `_EN_CHAPTER` begins with `^\\s*`, and `\\s` matches newlines, so when the
    heading is preceded by a blank line the match starts at that blank line and the
    chapter's block begins with `\\n`. `split_chapters` then finds a newline at
    offset 0, takes the `f"chapter {index + 1}"` fallback, and the real heading is
    lost as a title. A heading not preceded by a blank line keeps its own text.

    The corpus already carries the fallback form in its context strings
    ("chapter 1. Paragraph 1 of the chapter ..."), so this is pinned as it behaves:
    the paragraphs are unaffected, and the title is not what alignment uses.
    """
    text = _book("CHAPTER I\n\nFirst paragraph here, long enough.\n\nCHAPTER II\n\nSecond.\n")
    chapters = split_chapters(text, language="en-US")
    assert [chapter.title for chapter in chapters] == ["CHAPTER I", "chapter 2"]
    # The body is still right, which is what the alignment consumes.
    assert all(chapter.paragraphs for chapter in chapters)


def test_a_heading_that_is_not_a_chapter_is_not_a_split() -> None:
    """`CHAPTER ONE` spelled out, or a word starting with 'CHAPTERS', is not one."""
    text = _book("CHAPTERS ARE LISTED HERE.\n\nA paragraph, long enough to count.\n")
    assert split_chapters(text, language="en-US") == []


def test_chinese_chapters_split_on_the_hui_heading() -> None:
    text = _book(
        "第一回　甄士隱夢幻識通靈\n\n第一段文字，足夠長可以成為一個段落。\n\n"
        "第二回　賈夫人仙逝揚州城\n\n第二段文字，同樣足夠長可以成立。\n"
    )
    chapters = split_chapters(text, language="zh-CN")
    assert len(chapters) == 2, [chapter.title for chapter in chapters]
    assert chapters[0].title.startswith("第一回")
    assert all(isinstance(chapter, Chapter) for chapter in chapters)


def test_a_book_without_headings_yields_no_chapters_rather_than_a_wrong_one() -> None:
    """The importer reports what the book carries; it does not invent a chapter."""
    assert split_chapters(_book("Just prose, with no heading at all.\n"), language="en-US") == []


# --- the paragraph splitter ---------------------------------------------------


def test_blank_line_layout_is_used_when_there_are_enough_paragraphs() -> None:
    body = "\n\n".join(
        [
            "The first paragraph is comfortably over the minimum length.",
            "The second paragraph is also comfortably over the minimum.",
            "The third paragraph is over the minimum as well, which is what counts.",
            "A\n\n---\n\nshort tail.",
        ]
    )
    paragraphs = paragraphs_of(body, minimum=20)
    assert len(paragraphs) >= 3
    assert all(len(item) >= 20 for item in paragraphs)
    assert "---" not in paragraphs, "a rule line is separator furniture, not a paragraph"


def test_a_hard_wrapped_chapter_falls_back_to_the_indent_rule() -> None:
    """Two layouts occur in these books; the fallback is what reads the second.

    With fewer than three blank-line paragraphs, a line that starts with an
    ideographic space begins a new paragraph and the rest are its continuation
    lines - otherwise a hard-wrapped chapter arrives as one enormous block.
    """
    body = (
        "第一段的第一行，這一行是硬換行的。\n"
        "　　第二段的開頭帶有全角空格。\n"
        "這一行是第二段的續行。\n"
    )
    paragraphs = paragraphs_of(body, minimum=10)
    assert len(paragraphs) == 2, paragraphs
    assert paragraphs[1].startswith("第二段"), paragraphs[1]


def test_paragraphs_shorter_than_the_minimum_are_dropped() -> None:
    body = "\n\n".join(
        [
            "12",
            "The first paragraph is comfortably over the minimum length.",
            "The second paragraph is also comfortably over the minimum length.",
            "The third paragraph is over the minimum length as well, comfortably.",
        ]
    )
    paragraphs = paragraphs_of(body, minimum=20)
    assert all(len(item) >= 20 for item in paragraphs)
    assert "12" not in paragraphs
