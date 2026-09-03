"""Dependency-free surface metrics for machine-translation evaluation.

This module implements sentence- and corpus-level BLEU, chrF/chrF++, and TER,
together with the tokenization and n-gram primitives they build on, using only
the Python standard library. CJK text (Chinese, Japanese, Korean) is tokenized
by segmenting CJK characters into single-character tokens while keeping Latin
words, digit runs, and punctuation as separate tokens; this mirrors sacrebleu's
``zh`` tokenizer closely enough for benchmarking purposes.

All functions are deterministic and pure (no I/O, no third-party imports).
Empty inputs never raise: they return ``0.0`` (or an empty list) sensibly.
"""

import math
from collections import Counter

__all__ = [
    "char_ngrams",
    "corpus_bleu",
    "corpus_chrf",
    "edit_distance_ops",
    "length_ratio",
    "sentence_bleu",
    "sentence_chrf",
    "sentence_ter",
    "tokenize_words",
    "word_ngrams",
]

# Inclusive Unicode codepoint ranges treated as CJK for character segmentation:
# CJK symbols/punctuation, Hiragana, Katakana (+ phonetic extensions and
# halfwidth forms), CJK Unified Ideographs (+ extensions A-I and compatibility
# ideographs), and Hangul syllables.
_CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x31F0, 0x31FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xFF66, 0xFF9F),
    (0xAC00, 0xD7AF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x2EBF0, 0x2EE5F),
    (0x30000, 0x3134F),
    (0x31350, 0x323AF),
)

_CJK_LANG_CODES: frozenset[str] = frozenset(
    {
        "zh",
        "cmn",
        "yue",
        "wuu",
        "hak",
        "nan",
        "lzh",
        "ja",
        "jpn",
        "jp",
        "ko",
        "kor",
        "kr",
        "chinese",
        "mandarin",
        "cantonese",
        "japanese",
        "korean",
    }
)

_SMOOTH_METHODS: frozenset[str] = frozenset({"exp", "floor", "none"})
_SMOOTH_FLOOR: float = 0.1
_MAX_SHIFT_CANDIDATES: int = 500


def _is_cjk(char: str) -> bool:
    """Return whether *char* falls in any of the CJK codepoint ranges."""
    code = ord(char)
    return any(start <= code <= end for start, end in _CJK_RANGES)


def _has_cjk(text: str) -> bool:
    """Return whether *text* contains at least one CJK character."""
    return any(_is_cjk(char) for char in text)


def _is_cjk_lang(lang: str) -> bool:
    """Return whether the given language code denotes a CJK language."""
    code = lang.strip().lower().replace("_", "-")
    return code in _CJK_LANG_CODES or code.split("-")[0] in _CJK_LANG_CODES


def _scan_tokens(text: str, split_cjk: bool) -> list[str]:
    """Scan *text* into tokens, optionally splitting each CJK character."""
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if split_cjk and _is_cjk(char):
            tokens.append(char)
            i += 1
            continue
        if char.isalpha():
            j = i + 1
            while j < n and text[j].isalpha() and not (split_cjk and _is_cjk(text[j])):
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        if char.isdigit():
            j = i + 1
            while j < n and text[j].isdigit():
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        tokens.append(char)
        i += 1
    return tokens


def tokenize_words(text: str, *, lang: str | None = None) -> list[str]:
    """Split *text* into word tokens.

    Consecutive Unicode letters form one token, consecutive digits form one
    token, and every other non-whitespace character (punctuation, symbols)
    forms its own token. When *lang* is a CJK language code, or when *lang* is
    ``None`` and the text contains CJK characters (auto-detection), each CJK
    character becomes its own token while Latin words, digit runs, and
    punctuation remain separate tokens. This mirrors sacrebleu's ``zh``
    tokenizer (Post, 2018) for Chinese/Japanese/Korean benchmark purposes.

    Args:
        text: The input string.
        lang: Optional language hint (e.g. ``"zh"``, ``"ja"``, ``"en"``).
            ``None`` auto-detects CJK text.

    Returns:
        The list of tokens; an empty list for empty or whitespace-only input.
    """
    if not text:
        return []
    split_cjk = _has_cjk(text) if lang is None else _is_cjk_lang(lang)
    return _scan_tokens(text, split_cjk)


def char_ngrams(text: str, n: int, *, remove_whitespace: bool = True) -> list[str]:
    """Return the character n-grams of *text* as a list of strings.

    Follows the chrF definition (Popovic, 2015): character n-grams are computed
    after removing all whitespace by default, which is the standard chrF
    behaviour. Returns an empty list when *n* is less than 1 or the (possibly
    whitespace-stripped) text is shorter than *n*.
    """
    if n < 1:
        return []
    if remove_whitespace:
        text = "".join(text.split())
    if len(text) < n:
        return []
    return [text[i : i + n] for i in range(len(text) - n + 1)]


def word_ngrams(tokens: list[str], n: int) -> list[str]:
    """Return word n-grams of *tokens*, joining the words with a single space.

    Tokens are expected to contain no whitespace (as produced by
    :func:`tokenize_words`). Returns an empty list when *n* is less than 1 or
    *tokens* is shorter than *n*.
    """
    if n < 1:
        return []
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _brevity_penalty(hyp_len: int, ref_len: int) -> float:
    """Return the BLEU brevity penalty (Papineni et al., 2002)."""
    if hyp_len == 0:
        return 0.0
    if hyp_len > ref_len:
        return 1.0
    return math.exp(1.0 - ref_len / hyp_len)


def sentence_bleu(
    hypothesis: str,
    references: list[str],
    *,
    max_n: int = 4,
    smooth: str = "exp",
    lang: str | None = None,
) -> float:
    """Compute sentence-level BLEU in the range 0..100.

    Implements modified n-gram precision with the standard brevity penalty
    (Papineni et al., 2002, "BLEU: a Method for Automatic Evaluation of
    Machine Translation"). For multiple references the clipped n-gram counts are
    the maximum over references and the brevity penalty uses the closest
    reference length. Smoothing of zero precisions follows Chen & Cherry (2014):
    ``"exp"`` (NIST-style, sacrebleu's sentence-level default),
    ``"floor"`` (floor value 0.1), or ``"none"``. The geometric mean is
    taken over orders up to the shortest of ``max_n`` and the hypothesis
    length. Returns 0.0 for empty input or when a precision is zero with
    ``"none"`` smoothing.
    """
    if smooth not in _SMOOTH_METHODS:
        raise ValueError(f"smooth must be one of {sorted(_SMOOTH_METHODS)}")
    if max_n < 1:
        raise ValueError("max_n must be >= 1")
    hyp = tokenize_words(hypothesis, lang=lang)
    refs = [r for r in (tokenize_words(r, lang=lang) for r in references) if r]
    if not hyp or not refs:
        return 0.0

    hyp_len = len(hyp)
    ref_len = min((len(r) for r in refs), key=lambda rl: abs(rl - hyp_len))

    precisions: list[float] = []
    smooth_factor = 1.0
    for n in range(1, max_n + 1):
        hyp_ngrams = Counter(word_ngrams(hyp, n))
        total_n = sum(hyp_ngrams.values())
        if total_n == 0:
            break
        clipped = 0
        for ref in refs:
            ref_ngrams = Counter(word_ngrams(ref, n))
            matched = sum(min(hyp_ngrams[g], ref_ngrams[g]) for g in hyp_ngrams)
            clipped = max(clipped, matched)
        if clipped > 0:
            precisions.append(clipped / total_n)
        elif smooth == "exp":
            smooth_factor *= 2.0
            precisions.append(1.0 / (smooth_factor * total_n))
        elif smooth == "floor":
            precisions.append(_SMOOTH_FLOOR / total_n)
        else:  # smooth == "none"
            precisions.append(0.0)

    if not precisions:
        return 0.0
    if any(p <= 0.0 for p in precisions):
        geo_mean = 0.0
    else:
        geo_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))
    return 100.0 * geo_mean * _brevity_penalty(hyp_len, ref_len)


def corpus_bleu(
    hypotheses: list[str],
    references: list[list[str]],
    *,
    max_n: int = 4,
    lang: str | None = None,
) -> float:
    """Compute corpus-level BLEU in the range 0..100.

    Pools modified n-gram precisions across the whole corpus and applies the
    standard brevity penalty (Papineni et al., 2002), as in the original BLEU
    definition and sacrebleu's corpus mode (no smoothing). Each hypothesis's
    clipped counts are the maximum over its references, and its contribution to
    the brevity penalty uses the closest reference length. Returns 0.0 when any
    order's pooled precision is zero or the corpus is empty.
    """
    if len(hypotheses) != len(references):
        raise ValueError("hypotheses and references must have equal length")
    if max_n < 1:
        raise ValueError("max_n must be >= 1")
    if not hypotheses:
        return 0.0

    clipped = [0] * max_n
    total = [0] * max_n
    sys_len = 0
    ref_len = 0
    for hyp_text, ref_texts in zip(hypotheses, references, strict=True):
        hyp = tokenize_words(hyp_text, lang=lang)
        refs = [r for r in (tokenize_words(r, lang=lang) for r in ref_texts) if r]
        if not hyp:
            continue
        sys_len += len(hyp)
        if refs:
            ref_len += min((len(r) for r in refs), key=lambda rl: abs(rl - len(hyp)))
        for n in range(1, max_n + 1):
            hyp_ngrams = Counter(word_ngrams(hyp, n))
            total_n = sum(hyp_ngrams.values())
            if total_n == 0:
                continue
            best = 0
            for ref in refs:
                ref_ngrams = Counter(word_ngrams(ref, n))
                best = max(best, sum(min(hyp_ngrams[g], ref_ngrams[g]) for g in hyp_ngrams))
            clipped[n - 1] += best
            total[n - 1] += total_n

    precisions = [clipped[i] / total[i] if total[i] > 0 else 0.0 for i in range(max_n)]
    if any(p <= 0.0 for p in precisions):
        return 0.0
    geo_mean = math.exp(sum(math.log(p) for p in precisions) / max_n)
    return 100.0 * geo_mean * _brevity_penalty(sys_len, ref_len)


def _chr_f_score(correct: int, hyp_total: int, ref_total: int, beta: float) -> float:
    """Return the F-beta score for given n-gram counts (beta weights recall)."""
    precision = correct / hyp_total if hyp_total > 0 else 0.0
    recall = correct / ref_total if ref_total > 0 else 0.0
    denom = beta * beta * precision + recall
    if denom == 0.0:
        return 0.0
    return (1.0 + beta * beta) * precision * recall / denom


def _sentence_chrf_score(
    hyp: str, ref: str, char_order: int, word_order: int, beta: float
) -> float:
    """Compute chrF for a single hypothesis/reference pair in 0..100.

    Orders for which neither side has any n-gram are skipped and excluded from
    the average (sacrebleu's effective-order behaviour). Without that rule a
    short segment can never reach 100: a three-character Chinese label has no
    4-, 5- or 6-gram, and averaging those absent orders as zeros would score an
    exact match at 62.5.
    """
    f_scores: list[float] = []
    for n in range(1, char_order + 1):
        hyp_ngrams = Counter(char_ngrams(hyp, n, remove_whitespace=True))
        ref_ngrams = Counter(char_ngrams(ref, n, remove_whitespace=True))
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())
        if hyp_total == 0 and ref_total == 0:
            continue
        correct = sum((hyp_ngrams & ref_ngrams).values())
        f_scores.append(_chr_f_score(correct, hyp_total, ref_total, beta))
    hyp_tokens = tokenize_words(hyp)
    ref_tokens = tokenize_words(ref)
    for n in range(1, word_order + 1):
        hyp_ngrams = Counter(word_ngrams(hyp_tokens, n))
        ref_ngrams = Counter(word_ngrams(ref_tokens, n))
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())
        if hyp_total == 0 and ref_total == 0:
            continue
        correct = sum((hyp_ngrams & ref_ngrams).values())
        f_scores.append(_chr_f_score(correct, hyp_total, ref_total, beta))
    if not f_scores:
        return 0.0
    return 100.0 * sum(f_scores) / len(f_scores)


def sentence_chrf(
    hypothesis: str,
    references: list[str],
    *,
    char_order: int = 6,
    word_order: int = 2,
    beta: float = 2.0,
) -> float:
    """Compute sentence-level chrF in the range 0..100.

    Follows Popovic (2015, "chrF: character n-gram F-score for automatic MT
    evaluation") and Popovic (2017) for chrF++: character n-gram precision and
    recall are combined into an F-beta score (beta weights recall) and averaged
    over n=1..char_order; when word_order > 0 the word n-gram F-beta scores are
    averaged in as well (chrF++ is char_order=6, word_order=2). Whitespace is
    removed for character n-grams, the standard chrF behaviour. For multiple
    references the maximum score over references is returned, matching
    sacrebleu's sentence_chrf.
    """
    if char_order < 0 or word_order < 0:
        raise ValueError("char_order and word_order must be non-negative")
    if not references:
        return 0.0
    return max(
        _sentence_chrf_score(hypothesis, ref, char_order, word_order, beta)
        for ref in references
    )


def corpus_chrf(
    hypotheses: list[str],
    references: list[list[str]],
    *,
    char_order: int = 6,
    word_order: int = 2,
    beta: float = 2.0,
) -> float:
    """Compute corpus-level chrF in the range 0..100.

    Pools character and word n-gram counts across the corpus and computes a
    single F-beta score from the pooled counts (micro-average), following
    sacrebleu's corpus_chrf. Each hypothesis contributes the n-gram counts of
    its best reference (the reference with the highest sentence chrF), keeping
    multi-reference handling consistent with :func:`sentence_chrf`.
    """
    if len(hypotheses) != len(references):
        raise ValueError("hypotheses and references must have equal length")
    if char_order < 0 or word_order < 0:
        raise ValueError("char_order and word_order must be non-negative")

    char_correct = [0] * char_order
    char_hyp = [0] * char_order
    char_ref = [0] * char_order
    word_correct = [0] * word_order
    word_hyp = [0] * word_order
    word_ref = [0] * word_order

    for hyp, refs in zip(hypotheses, references, strict=True):
        if not refs:
            continue
        best_ref = max(
            refs, key=lambda r: _sentence_chrf_score(hyp, r, char_order, word_order, beta)
        )
        for n in range(1, char_order + 1):
            hyp_ngrams = Counter(char_ngrams(hyp, n, remove_whitespace=True))
            ref_ngrams = Counter(char_ngrams(best_ref, n, remove_whitespace=True))
            char_correct[n - 1] += sum((hyp_ngrams & ref_ngrams).values())
            char_hyp[n - 1] += sum(hyp_ngrams.values())
            char_ref[n - 1] += sum(ref_ngrams.values())
        hyp_tokens = tokenize_words(hyp)
        ref_tokens = tokenize_words(best_ref)
        for n in range(1, word_order + 1):
            hyp_ngrams = Counter(word_ngrams(hyp_tokens, n))
            ref_ngrams = Counter(word_ngrams(ref_tokens, n))
            word_correct[n - 1] += sum((hyp_ngrams & ref_ngrams).values())
            word_hyp[n - 1] += sum(hyp_ngrams.values())
            word_ref[n - 1] += sum(ref_ngrams.values())

    f_scores: list[float] = []
    for n in range(char_order):
        if char_hyp[n] == 0 and char_ref[n] == 0:
            continue
        f_scores.append(_chr_f_score(char_correct[n], char_hyp[n], char_ref[n], beta))
    for n in range(word_order):
        if word_hyp[n] == 0 and word_ref[n] == 0:
            continue
        f_scores.append(_chr_f_score(word_correct[n], word_hyp[n], word_ref[n], beta))

    if not f_scores:
        return 0.0
    return 100.0 * sum(f_scores) / len(f_scores)


def _levenshtein_ops(a: list[str], b: list[str]) -> tuple[int, int, int]:
    """Return (substitutions, insertions, deletions) from a Levenshtein alignment."""
    n = len(a)
    m = len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    subs = 0
    ins = 0
    dels = 0
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j - 1] + 1:
            subs += 1
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            dels += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    dels += i
    ins += j
    return subs, ins, dels


def _matching_blocks(a: list[str], b: list[str]) -> list[tuple[int, int, int]]:
    """Return contiguous matching blocks (i in a, k in b, length) with length >= 2.

    Only misaligned blocks (i != k) are returned; results are sorted by
    descending length, then by position in *a* and then *b* for determinism.
    """
    n = len(a)
    m = len(b)
    blocks: list[tuple[int, int, int]] = []
    for i in range(n):
        for k in range(m):
            if a[i] != b[k]:
                continue
            length = 1
            while i + length < n and k + length < m and a[i + length] == b[k + length]:
                length += 1
            if length >= 2 and i != k:
                blocks.append((i, k, length))
    blocks.sort(key=lambda t: (-t[2], t[0], t[1]))
    return blocks


def _move_block(
    tokens: list[str], i: int, length: int, k: int, ref: list[str]
) -> list[str]:
    """Move the block tokens[i:i+length] to align with ref[k:k+length].

    The insertion position is chosen so the block lands next to its neighbours
    in *ref*: after the token preceding the block (k > 0) or before the token
    following it, falling back to the front/end when those anchors are absent.
    """
    block = tokens[i : i + length]
    rest = tokens[:i] + tokens[i + length :]
    if k == 0:
        pos = 0
    else:
        pos = -1
        prev = ref[k - 1]
        for idx in range(len(rest) - 1, -1, -1):
            if rest[idx] == prev:
                pos = idx + 1
                break
        if pos == -1:
            nxt = ref[k + length] if k + length < len(ref) else None
            if nxt is not None:
                for idx, tok in enumerate(rest):
                    if tok == nxt:
                        pos = idx
                        break
            if pos == -1:
                pos = len(rest)
    return rest[:pos] + block + rest[pos:]


def edit_distance_ops(hyp: list[str], ref: list[str]) -> tuple[int, int, int, int]:
    """Count the TER edit operations transforming *hyp* into *ref*.

    Returns ``(substitutions, insertions, deletions, shifts)``. Substitutions,
    insertions, and deletions come from a standard Levenshtein alignment.
    Shifts follow a greedy approximation of TER's shift search (Snover et al.,
    2006, "A Study of Translation Edit Rate with Targeted Human Annotation"):
    the longest misaligned contiguous matching block (length >= 2) is moved to
    its reference position and counted as one shift whenever that move strictly
    reduces the total edit count. The search is deterministic but not guaranteed
    to find the globally optimal shift sequence (documented approximation).
    """
    hyp = list(hyp)
    ref = list(ref)
    if hyp == ref:
        return (0, 0, 0, 0)

    working = list(hyp)
    shifts = 0
    while True:
        current_distance = sum(_levenshtein_ops(working, ref))
        moved: list[str] | None = None
        tried = 0
        for i, k, length in _matching_blocks(working, ref):
            candidate = _move_block(working, i, length, k, ref)
            if candidate == working:
                continue
            if tried >= _MAX_SHIFT_CANDIDATES:
                break
            tried += 1
            if sum(_levenshtein_ops(candidate, ref)) + 1 < current_distance:
                moved = candidate
                break
        if moved is None:
            break
        working = moved
        shifts += 1

    subs, ins, dels = _levenshtein_ops(working, ref)
    return (subs, ins, dels, shifts)


def sentence_ter(hypothesis: str, reference: str, *, lang: str | None = None) -> float:
    """Compute sentence-level TER in the range 0..100 (lower is better).

    Translation Edit Rate (Snover et al., 2006) is
    ``(substitutions + insertions + deletions + shifts) / reference_length``.
    The shift count uses the documented greedy approximation of
    :func:`edit_distance_ops`. Returns 0.0 when the reference tokenizes to
    nothing (division-by-zero guard).
    """
    hyp = tokenize_words(hypothesis, lang=lang)
    ref = tokenize_words(reference, lang=lang)
    if not ref:
        return 0.0
    subs, ins, dels, shifts = edit_distance_ops(hyp, ref)
    return 100.0 * (subs + ins + dels + shifts) / len(ref)


def length_ratio(hypothesis: str, reference: str) -> float:
    """Return the character-length ratio ``len(hypothesis) / len(reference)``.

    Used for length/brevity reporting. Returns 0.0 when the reference is empty.
    """
    if not reference:
        return 0.0
    return len(hypothesis) / len(reference)
