"""Public-domain literary pairs from Project Gutenberg.

Classical Chinese novels and their early English translations are public domain
on both sides, so CLARION uses the real books rather than anything invented:

    三國志演義 (PG 23950)  <-> San kuo, Brewitt-Taylor 1925 (PG 77416)
    紅樓夢     (PG 24264)  <-> Hung Lou Meng, Joly 1892     (PG 9603)

Both translations are archaic in their own language, which is what the literary
stratum is for: a classical source rendered in a classical target register,
over a long continuous passage with an emotional arc.

Alignment is the hard part, and it is done honestly:

1. chapters are split on the markers both books actually carry
   (第N回 on the Chinese side, CHAPTER N on the English side) - exact;
2. paragraphs inside one chapter are aligned by a model, which only ever
   returns INDEX PAIRS - it cannot invent or edit text;
3. every proposed pair is verified: indices must exist, the mapping must be
   strictly increasing on both sides, and the length ratio must be plausible.
   Pairs that fail are dropped, not repaired.

The result is real human translation on both sides, with a recorded, checkable
alignment method.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..providers.base import CompletionRequest, Message, Provider

GUTENBERG_URLS = (
    "https://www.gutenberg.org/cache/epub/{book}/pg{book}.txt",
    "https://www.gutenberg.org/files/{book}/{book}-0.txt",
)
USER_AGENT = "CLARION-benchmark/0.1 (localization format research)"
_START_MARKERS = ("*** START OF THE PROJECT GUTENBERG", "***START OF THE PROJECT GUTENBERG")
_END_MARKERS = ("*** END OF THE PROJECT GUTENBERG", "***END OF THE PROJECT GUTENBERG")
_ZH_CHAPTER = re.compile(r"^\s*第[一二三四五六七八九十百零〇\d]+回[：:\s\u3000]", re.MULTILINE)
_EN_CHAPTER = re.compile(r"^\s*CHAPTER\s+[IVXLCDM]+\b", re.MULTILINE)
_JSON_RE = re.compile(r"\[.*\]", re.DOTALL)

ALIGN_SYSTEM = (
    "You align a Chinese classical novel with its English translation. You never "
    "write or edit text: you only report which numbered English paragraph "
    "corresponds to which numbered Chinese paragraph."
)
ALIGN_TASK = """Below are the numbered paragraphs of one chapter of a Chinese novel and the
numbered paragraphs of the same chapter in an early English translation. The
translation is faithful but not literal, and it sometimes merges or omits
paragraphs.

Return ONLY a JSON array of index pairs, in increasing order, for the
paragraphs you are confident correspond:
[[chinese_index, english_index], ...]

Skip anything you are not sure about. Never invent an index.

Chinese paragraphs:
{chinese}

English paragraphs:
{english}"""

VERIFY_SYSTEM = (
    "You check translation alignment. You answer only with JSON. A pair is correct "
    "only when the English paragraph really renders THAT Chinese paragraph, not the "
    "one before or after it."
)
VERIFY_TASK = """For each numbered pair below, decide whether the English text is a translation of
the Chinese text. Early translators omitted poems and merged paragraphs, so an
off-by-one pairing is common and must be rejected.

Return ONLY JSON: {{"results": {{"<pair number>": true|false}}}}

{pairs}"""


@dataclass
class Chapter:
    """One chapter of a book."""

    title: str
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class AlignmentReport:
    """How well a chapter aligned."""

    proposed: int = 0
    accepted: int = 0
    rejected_range: int = 0
    rejected_order: int = 0
    rejected_ratio: int = 0
    rejected_semantic: int = 0

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "proposed": self.proposed,
            "accepted": self.accepted,
            "rejected_range": self.rejected_range,
            "rejected_order": self.rejected_order,
            "rejected_ratio": self.rejected_ratio,
            "rejected_semantic": self.rejected_semantic,
        }


def download(book_id: int, *, attempts: int = 4) -> str:
    """Fetch a Gutenberg plain-text book, retrying transient TLS failures."""
    import time

    import httpx

    last_error = "no url tried"
    for attempt in range(1, attempts + 1):
        for template in GUTENBERG_URLS:
            url = template.format(book=book_id)
            try:
                response = httpx.get(
                    url, timeout=180.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
                )
            except Exception as exc:  # noqa: BLE001 - network errors are data, not crashes
                last_error = f"{type(exc).__name__}: {exc}"
                continue
            if response.status_code == 200 and len(response.text) > 1000:
                return response.text
            last_error = f"HTTP {response.status_code}"
        if attempt < attempts:
            time.sleep(2.0 * attempt)
    raise RuntimeError(f"could not download Gutenberg book {book_id}: {last_error}")


def strip_boilerplate(text: str) -> str:
    """Remove the Project Gutenberg header and licence footer."""
    body = text.replace("\r\n", "\n")
    for marker in _START_MARKERS:
        index = body.find(marker)
        if index >= 0:
            newline = body.find("\n", index)
            body = body[newline + 1 :]
            break
    for marker in _END_MARKERS:
        index = body.find(marker)
        if index >= 0:
            body = body[:index]
            break
    return body.strip()


_RULE_LINE = re.compile(r"^[\s\-_=*·]+$")


def paragraphs_of(block: str, *, minimum: int = 20) -> list[str]:
    """Split a chapter body into paragraphs.

    Two layouts occur in these books. Most are separated by blank lines. Others
    (the Chinese Dream of the Red Chamber among them) hard-wrap every line and
    mark a new paragraph with leading ideographic spaces, so blank-line
    splitting would return the whole chapter as one block. Separator rules of
    dashes are dropped in both cases.
    """
    lines = [line for line in block.split("\n") if not _RULE_LINE.match(line)]
    cleaned = "\n".join(lines)
    parts = [" ".join(part.split()) for part in re.split(r"\n\s*\n", cleaned)]
    parts = [part for part in parts if len(part) >= minimum]
    if len(parts) >= 3:
        return parts

    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        if line.startswith(("\u3000", "  ")) and current:
            paragraphs.append(" ".join(" ".join(current).split()))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(" ".join(current).split()))
    return [item for item in paragraphs if len(item) >= minimum]


def split_chapters(text: str, *, language: str) -> list[Chapter]:
    """Split a book into chapters using the markers it actually carries."""
    pattern = _ZH_CHAPTER if language.startswith("zh") else _EN_CHAPTER
    matches = list(pattern.finditer(text))
    chapters: list[Chapter] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end]
        newline = block.find("\n")
        title = " ".join(block[:newline].split()) if newline > 0 else f"chapter {index + 1}"
        chapters.append(Chapter(title=title, paragraphs=paragraphs_of(block[newline + 1 :])))
    return chapters


def _preview(items: list[str], limit: int) -> str:
    return "\n".join(f"{index}: {item[:limit]}" for index, item in enumerate(items))


def verify_pairs(
    candidates: list[tuple[str, str]],
    provider: Provider,
    *,
    batch_size: int = 6,
    max_output_tokens: int = 2048,
) -> list[bool]:
    """Second, independent check that each pair really is a translation.

    The structural checks (existence, monotonicity, length ratio) cannot see an
    off-by-one alignment, which is exactly what happens when a translator omits
    an opening poem. This pass reads the actual texts and rejects those pairs.
    """
    verdicts: list[bool] = []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start : start + batch_size]
        rendered = "\n\n".join(
            f"Pair {index}:\nChinese: {source[:400]}\nEnglish: {target[:400]}"
            for index, (source, target) in enumerate(batch, start=1)
        )
        completion = provider.complete(
            CompletionRequest(
                messages=[
                    Message("system", VERIFY_SYSTEM),
                    Message("user", VERIFY_TASK.format(pairs=rendered)),
                ],
                temperature=0.0,
                max_output_tokens=max_output_tokens,
            )
        )
        answer: dict[str, Any] = {}
        if not completion.error:
            match = re.search(r"\{.*\}", completion.text or "", re.DOTALL)
            if match:
                try:
                    answer = json.loads(match.group(0)).get("results", {}) or {}
                except json.JSONDecodeError:
                    answer = {}
        for index in range(1, len(batch) + 1):
            value = answer.get(str(index))
            verdicts.append(bool(value) if isinstance(value, bool) else False)
    return verdicts


def align_chapter(
    chinese: list[str],
    english: list[str],
    provider: Provider,
    *,
    max_output_tokens: int = 8192,
    verify: bool = True,
) -> tuple[list[tuple[int, int]], AlignmentReport]:
    """Ask a model for paragraph index pairs, then verify every one of them."""
    report = AlignmentReport()
    if not chinese or not english:
        return [], report
    user = ALIGN_TASK.format(
        chinese=_preview(chinese, 90),
        english=_preview(english, 140),
    )
    completion = provider.complete(
        CompletionRequest(
            messages=[Message("system", ALIGN_SYSTEM), Message("user", user)],
            temperature=0.0,
            max_output_tokens=max_output_tokens,
        )
    )
    if completion.error:
        return [], report
    match = _JSON_RE.search(completion.text or "")
    if not match:
        return [], report
    try:
        proposals = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], report

    accepted: list[tuple[int, int]] = []
    last_zh = -1
    last_en = -1
    for item in proposals:
        if not isinstance(item, list | tuple) or len(item) != 2:
            continue
        report.proposed += 1
        try:
            zh_index, en_index = int(item[0]), int(item[1])
        except (TypeError, ValueError):
            report.rejected_range += 1
            continue
        if not (0 <= zh_index < len(chinese) and 0 <= en_index < len(english)):
            report.rejected_range += 1
            continue
        if zh_index <= last_zh or en_index <= last_en:
            report.rejected_order += 1
            continue
        zh_text, en_text = chinese[zh_index], english[en_index]
        ratio = len(en_text) / max(1, len(zh_text))
        if not 0.8 <= ratio <= 8.0:
            report.rejected_ratio += 1
            continue
        accepted.append((zh_index, en_index))
        last_zh, last_en = zh_index, en_index

    if verify and accepted:
        verdicts = verify_pairs(
            [(chinese[zh], english[en]) for zh, en in accepted], provider
        )
        kept: list[tuple[int, int]] = []
        for pair, ok in zip(accepted, verdicts, strict=False):
            if ok:
                kept.append(pair)
            else:
                report.rejected_semantic += 1
        accepted = kept

    report.accepted = len(accepted)
    return accepted, report
