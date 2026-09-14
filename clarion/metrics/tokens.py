"""Token accounting - dimensions 1 and 2.

Two rules make the numbers defensible:

1. Every prompt is measured as a list of labelled components (system rules,
   format notes, the CLIFF specification digest, the document itself, the
   glossary). A report can therefore add or remove any component
   arithmetically - the 'with and without the CLIFF specification' comparison
   never needs a second run against a model.
2. The tokenizer is named in every record. tiktoken is used when available;
   otherwise a documented deterministic heuristic is used and every report
   states which one produced the numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

_CJK_RANGES = (
    (0x3040, 0x30FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xAC00, 0xD7AF),
    (0x20000, 0x2FA1F),
)
_WORD_RE = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]")


class Tokenizer(Protocol):
    """Anything that can count tokens deterministically."""

    name: str

    def count(self, text: str) -> int:
        """Number of tokens in the text."""


def _is_cjk(char: str) -> bool:
    point = ord(char)
    return any(low <= point <= high for low, high in _CJK_RANGES)


class HeuristicTokenizer:
    """Deterministic fallback used when tiktoken is not installed.

    Approximates byte-pair encoders: every CJK character counts as one token,
    Latin words count as one token per four characters (rounded up), digits
    per three characters, and every other non-space character counts as one.
    Numbers produced this way are labelled 'heuristic' in every report and must
    never be mixed with tiktoken numbers in the same table.
    """

    name = "heuristic"

    def count(self, text: str) -> int:
        total = 0
        for chunk in _WORD_RE.findall(text):
            if chunk.isalpha() and chunk.isascii():
                total += max(1, -(-len(chunk) // 4))
            elif chunk.isdigit():
                total += max(1, -(-len(chunk) // 3))
            else:
                total += sum(1 for char in chunk if not char.isspace() or _is_cjk(char)) or 1
        return total


class TiktokenTokenizer:
    """Byte-pair tokenizer from tiktoken (o200k_base, cl100k_base, ...)."""

    def __init__(self, encoding_name: str) -> None:
        import tiktoken

        self.name = encoding_name
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text, disallowed_special=()))


def get_tokenizer(name: str = "o200k_base") -> Tokenizer:
    """Return a tokenizer by encoding name, falling back to the heuristic."""
    if name == "heuristic":
        return HeuristicTokenizer()
    try:
        return TiktokenTokenizer(name)
    except Exception:  # noqa: BLE001 - missing package or unknown encoding
        return HeuristicTokenizer()


@dataclass(frozen=True)
class ComponentCost:
    """Token cost of one labelled part of a prompt."""

    id: str
    role: str
    tokens: int
    characters: int

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "id": self.id,
            "role": self.role,
            "tokens": self.tokens,
            "characters": self.characters,
        }


@dataclass
class PromptBudget:
    """Token cost of a whole prompt, decomposed by component."""

    tokenizer: str
    components: list[ComponentCost] = field(default_factory=list)

    def add(self, component_id: str, role: str, text: str, tokenizer: Tokenizer) -> ComponentCost:
        """Measure one component and remember it."""
        cost = ComponentCost(
            id=component_id,
            role=role,
            tokens=tokenizer.count(text),
            characters=len(text),
        )
        self.components.append(cost)
        return cost

    @property
    def total(self) -> int:
        """Total prompt tokens."""
        return sum(component.tokens for component in self.components)

    def tokens_of(self, *component_ids: str) -> int:
        """Tokens contributed by the named components."""
        wanted = set(component_ids)
        return sum(c.tokens for c in self.components if c.id in wanted)

    def without(self, *component_ids: str) -> int:
        """Total tokens if the named components were not sent.

        This is what makes the 'with and without the CLIFF specification'
        comparison free: the specification digest is a constant component, so
        its cost can be subtracted instead of re-running the experiment.
        """
        return self.total - self.tokens_of(*component_ids)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "tokenizer": self.tokenizer,
            "total": self.total,
            "components": [component.as_dict() for component in self.components],
        }


def count_text(text: str, tokenizer: Tokenizer) -> dict[str, int]:
    """Tokens, characters and UTF-8 bytes of a piece of text."""
    return {
        "tokens": tokenizer.count(text),
        "characters": len(text),
        "bytes": len(text.encode("utf-8")),
    }
