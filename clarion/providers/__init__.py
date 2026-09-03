"""Model providers for CLARION."""

from __future__ import annotations

from typing import Any

from .base import Completion, CompletionRequest, Message, Provider
from .mock import MockProvider
from .openai_compat import OpenAICompatibleProvider, reasoning_body


def build_provider(config: Any) -> Provider:
    """Instantiate the provider described by a ProviderConfig."""
    kind = getattr(config, "kind", "mock")
    if kind == "mock":
        return MockProvider(mode=getattr(config, "mode", "perfect"), model=config.model)
    if kind in {"openai", "openai-compatible", "deepseek"}:
        return OpenAICompatibleProvider(
            model=config.model,
            base_url=config.base_url,
            api_key_env=config.api_key_env,
            timeout_s=config.timeout_s,
            max_retries=config.max_retries,
            reasoning=config.reasoning,
            name=kind,
            extra_body=dict(config.extra_body),
        )
    raise ValueError(f"unknown provider kind '{kind}'")


__all__ = [
    "Completion",
    "CompletionRequest",
    "Message",
    "MockProvider",
    "OpenAICompatibleProvider",
    "Provider",
    "build_provider",
    "reasoning_body",
]
