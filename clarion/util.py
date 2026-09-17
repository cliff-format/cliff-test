"""Shared helpers: deterministic hashing, JSON and UTF-8 file IO."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string with second precision."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_text(text: str) -> str:
    """SHA-256 of the UTF-8 encoding of the text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str, length: int = 12) -> str:
    """Short, stable content hash used for cache keys and run ids."""
    return sha256_text(text)[:length]


def slug(text: str, fallback: str = "item") -> str:
    """Lowercase kebab-case slug that is also a valid CLIFF name.

    CLIFF 1.1 accepts a much wider identifier than this, and a real project may
    legitimately use PascalCase or snake_case. This helper keeps its narrow
    kebab-case output deliberately: it *generates* identifiers where the source
    format had none, and a generated corpus is the one place a tool gets to pick
    a style (style/README.md). Preserving the source spelling is the job of an
    importer, not of a slug used for cache keys.
    """
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    cleaned = _SLUG_RE.sub("-", normalized.lower()).strip("-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"{fallback}-{cleaned}".strip("-")
    return cleaned or fallback


def read_text(path: Path) -> str:
    """Read UTF-8 text, tolerating a BOM and normalizing CRLF to LF."""
    raw = path.read_text(encoding="utf-8-sig")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF endings, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    """Load a JSON document."""
    return json.loads(read_text(path))


def dump_json(path: Path, data: Any) -> None:
    """Write pretty, deterministic, UTF-8 JSON."""
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON record to a JSONL evidence file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL evidence file, skipping blank lines."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in read_text(path).split("\n"):
        if line.strip():
            records.append(json.loads(line))
    return records


def mean(values: Iterable[float]) -> float:
    """Arithmetic mean, 0.0 for an empty sequence."""
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def percent(part: float, whole: float) -> float:
    """Percentage of part in whole, 0.0 when whole is zero."""
    return 100.0 * part / whole if whole else 0.0


def truncate(text: str, limit: int = 200) -> str:
    """Shorten text for log lines and reports."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"
