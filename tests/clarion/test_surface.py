"""Tests for :mod:`clarion.metrics.surface`."""

import pytest

from clarion.metrics.surface import (
    char_ngrams,
    corpus_bleu,
    corpus_chrf,
    edit_distance_ops,
    length_ratio,
    sentence_bleu,
    sentence_chrf,
    sentence_ter,
    tokenize_words,
    word_ngrams,
)

# --- tokenize_words -------------------------------------------------------


def test_tokenize_words_segments_cjk_run():
    assert tokenize_words("分辨率设置") == ["分", "辨", "率", "设", "置"]


def test_tokenize_words_keeps_latin_word():
    assert tokenize_words("OK 分辨率") == ["OK", "分", "辨", "率"]


def test_tokenize_words_keeps_digits_together():
    assert tokenize_words("123 分辨率") == ["123", "分", "辨", "率"]


def test_tokenize_words_space_delimited_punctuation():
    assert tokenize_words("Hello, world!") == ["Hello", ",", "world", "!"]


def test_tokenize_words_empty():
    assert tokenize_words("") == []


def test_tokenize_words_explicit_lang():
    # A non-CJK language hint keeps CJK characters grouped as one word.
    assert tokenize_words("分辨率", lang="en") == ["分辨率"]
    # A CJK hint is harmless for text with no CJK characters.
    assert tokenize_words("abc", lang="zh") == ["abc"]


# --- n-grams --------------------------------------------------------------


def test_char_ngrams():
    assert char_ngrams("abc", 2) == ["ab", "bc"]
    assert char_ngrams("a b c", 1) == ["a", "b", "c"]
    assert char_ngrams("a b", 2, remove_whitespace=False) == ["a ", " b"]
    assert char_ngrams("abc", 4) == []
    assert char_ngrams("", 2) == []


def test_word_ngrams():
    assert word_ngrams(["a", "b", "c"], 2) == ["a b", "b c"]
    assert word_ngrams(["a"], 2) == []
    assert word_ngrams([], 1) == []


# --- BLEU -----------------------------------------------------------------


def test_sentence_bleu_identical_is_100():
    assert sentence_bleu("the cat sat on the mat", ["the cat sat on the mat"]) == pytest.approx(
        100.0
    )


def test_sentence_bleu_no_overlap_none_is_0():
    assert sentence_bleu("a b c d", ["w x y z"], smooth="none") == 0.0


def test_sentence_bleu_brevity_penalty():
    full = sentence_bleu("a b c", ["a b c"], smooth="none")
    short = sentence_bleu("a b c", ["a b c d e"], smooth="none")
    assert full == pytest.approx(100.0)
    assert 0.0 < short < full


def test_sentence_bleu_multi_reference_picks_best():
    bad_only = sentence_bleu("a b c d", ["w x y z"], smooth="none")
    with_good = sentence_bleu("a b c d", ["w x y z", "a b c d"], smooth="none")
    assert bad_only == 0.0
    assert with_good == pytest.approx(100.0)


def test_sentence_bleu_exp_smoothing_nonzero_on_no_overlap():
    score = sentence_bleu("a b c d", ["w x y z"], smooth="exp")
    assert 0.0 < score < 100.0


def test_corpus_bleu_identical():
    hyps = ["the cat sat quietly", "a dog ran home fast"]
    refs = [["the cat sat quietly"], ["a dog ran home fast"]]
    assert corpus_bleu(hyps, refs) == pytest.approx(100.0)


def test_corpus_bleu_no_overlap_is_0():
    assert corpus_bleu(["a b c d"], [["w x y z"]]) == 0.0


# --- chrF -----------------------------------------------------------------


def test_sentence_chrf_identical_is_100():
    text = "the quick brown fox jumps over the lazy dog"
    assert sentence_chrf(text, [text]) == pytest.approx(100.0)


def test_sentence_chrf_identical_short_with_reduced_order():
    assert sentence_chrf("test", ["test"], char_order=4, word_order=0) == pytest.approx(100.0)


def test_sentence_chrf_symmetric_ish():
    a = "the cat sat on the mat"
    b = "the cat sits on a mat"
    ab = sentence_chrf(a, [b], word_order=0)
    ba = sentence_chrf(b, [a], word_order=0)
    assert 0.0 < ab < 100.0
    assert 0.0 < ba < 100.0
    assert ab == pytest.approx(ba, abs=15.0)


def test_sentence_chrf_handles_chinese_without_whitespace():
    assert sentence_chrf("分辨率设置", ["分辨率设置"], char_order=2, word_order=0) == pytest.approx(
        100.0
    )
    score = sentence_chrf("分辨率设置", ["设置分辨率"], char_order=2, word_order=0)
    assert 0.0 < score < 100.0


def test_sentence_chrf_plus_differs_from_chrf():
    hyp = "a b c"
    ref = "c b a"
    chrf_base = sentence_chrf(hyp, [ref], word_order=0)
    chrf_pp = sentence_chrf(hyp, [ref], word_order=2)
    assert chrf_base != chrf_pp


def test_corpus_chrf_identical():
    hyps = ["the quick brown fox", "a lazy dog"]
    refs = [["the quick brown fox"], ["a lazy dog"]]
    assert corpus_chrf(hyps, refs, char_order=4, word_order=1) == pytest.approx(100.0)


# --- TER ------------------------------------------------------------------


def test_sentence_ter_identical_is_0():
    assert sentence_ter("a b c d", "a b c d") == 0.0


def test_sentence_ter_deletion():
    # Hypothesis has one extra word -> one deletion, reference length 4.
    assert sentence_ter("a b c d e", "a b c d") == pytest.approx(100.0 / 4)


def test_sentence_ter_insertion():
    # Hypothesis is missing one word -> one insertion, reference length 4.
    assert sentence_ter("a b c", "a b c d") == pytest.approx(100.0 / 4)


def test_sentence_ter_substitution():
    assert sentence_ter("a b c x", "a b c d") == pytest.approx(100.0 / 4)


def test_sentence_ter_shift_reduces_edit_rate():
    # A rotated sentence is a single shift, not two deletions + two insertions.
    assert sentence_ter("c d a b", "a b c d") == pytest.approx(100.0 / 4)


def test_sentence_ter_empty_reference_is_0():
    assert sentence_ter("anything", "") == 0.0


def test_edit_distance_ops_identical():
    assert edit_distance_ops(["a", "b"], ["a", "b"]) == (0, 0, 0, 0)


def test_edit_distance_ops_shift():
    assert edit_distance_ops(["c", "d", "a", "b"], ["a", "b", "c", "d"]) == (0, 0, 0, 1)


def test_edit_distance_ops_substitution():
    assert edit_distance_ops(["a", "x"], ["a", "b"]) == (1, 0, 0, 0)


# --- length ratio ---------------------------------------------------------


def test_length_ratio():
    assert length_ratio("abcd", "ab") == pytest.approx(2.0)
    assert length_ratio("ab", "abcd") == pytest.approx(0.5)
    assert length_ratio("anything", "") == 0.0
