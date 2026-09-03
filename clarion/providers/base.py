"""Provider interface: everything CLARION needs from a model endpoint.

A provider receives a request and returns a completion with usage and latency.
The request also carries a hint dictionary that real providers ignore; it
exists so the deterministic mock provider can synthesize a well-formed answer
for offline self-tests without a network call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Message:
    """One chat message."""

    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        """Wire representation."""
        return {"role": self.role, "content": self.content}


@dataclass
class CompletionRequest:
    """A single model call."""

    messages: list[Message]
    temperature: float = 0.0
    top_p: float = 1.0
    max_output_tokens: int = 4096
    stop: list[str] = field(default_factory=list)
    extra_body: dict[str, Any] = field(default_factory=dict)
    hint: dict[str, Any] = field(default_factory=dict)

    def prompt_text(self) -> str:
        """Concatenated prompt text, used for token accounting."""
        return "\n\n".join(message.content for message in self.messages)


@dataclass
class Completion:
    """A single model answer with its measured cost."""

    text: str
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    finish_reason: str | None = None
    error: str | None = None
    attempts: int = 1
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when the call produced text."""
        return self.error is None and bool(self.text.strip())

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record without the raw payload."""
        return {
            "provider": self.provider,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 3),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "finish_reason": self.finish_reason,
            "attempts": self.attempts,
            "error": self.error,
        }


class Provider(Protocol):
    """Anything that can answer a completion request."""

    name: str
    model: str

    def complete(self, request: CompletionRequest) -> Completion:
        """Run one request and return the answer."""
