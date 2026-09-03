"""Deterministic offline provider used by the self-tests.

The mock answers in the same format it was asked in, which lets the whole
pipeline - prompt assembly, parsing, validity, structure, quality, rules and
reporting - be exercised with no network and no cost.

Two behaviours matter:

perfect
    Fill every target with the gold reference. Every metric must come out
    clean; anything else is a harness bug.

noisy
    Apply a deterministic set of realistic failures (a dropped entry, a broken
    ICU placeholder, a discouraged term, an over-wide label, a Markdown fence
    around the file). Every metric must detect its failure; anything else
    means the metric is asleep.
"""

from __future__ import annotations

import copy
import time
from typing import Any

from ..formats.render import render_document
from ..paths import ensure_pyclif
from .base import Completion, CompletionRequest


class MockProvider:
    """Answer requests from the hint payload instead of a network call."""

    def __init__(self, *, mode: str = "perfect", model: str = "mock-1", latency_ms: float = 5.0):
        self.name = "mock"
        self.model = f"{model}:{mode}"
        self.mode = mode
        self._latency_ms = latency_ms

    def complete(self, request: CompletionRequest) -> Completion:
        """Synthesize an answer for the document carried in the hint."""
        started = time.perf_counter()
        hint = request.hint
        document = hint.get("document")
        format_id = hint.get("format")
        arm = hint.get("arm", "context")
        references: dict[str, str] = dict(hint.get("references") or {})
        if document is None or format_id is None:
            return Completion(
                text="",
                provider=self.name,
                model=self.model,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                error="mock provider needs 'document' and 'format' in the request hint",
            )

        ensure_pyclif()
        answer = copy.deepcopy(document)
        entries = [(group, entry) for group in answer.groups for entry in group.entries]
        for index, (_group, entry) in enumerate(entries):
            reference = references.get(entry.id)
            entry.target = reference if reference else f"[{entry.source}]"
            entry.status = "translated"
            if self.mode == "noisy":
                self._degrade(index, entry)
        if self.mode == "noisy" and len(entries) > 1:
            group, entry = entries[-1]
            group.entries.remove(entry)

        text = render_document(answer, str(format_id), arm=arm)
        if self.mode == "noisy":
            text = f"Here is the translated file:\n\n```\n{text}\n```\n"
        elapsed = max((time.perf_counter() - started) * 1000.0, self._latency_ms)
        return Completion(
            text=text,
            provider=self.name,
            model=self.model,
            latency_ms=elapsed,
            prompt_tokens=None,
            completion_tokens=None,
            finish_reason="stop",
            raw={"mode": self.mode},
        )

    @staticmethod
    def _degrade(index: int, entry: Any) -> None:
        """Inject one deterministic, detectable failure per entry position."""
        target = entry.target or ""
        if index % 5 == 1 and "{" in (entry.source or ""):
            entry.target = target.replace("{", "(").replace("}", ")")
        elif index % 5 == 2:
            entry.target = target + "缺省"
        elif index % 5 == 3:
            entry.target = target + "AAAAAAAAAAAAAAAA"
        elif index % 5 == 4:
            entry.target = entry.source
