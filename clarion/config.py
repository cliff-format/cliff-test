"""Run configuration for CLARION experiments.

Configuration is data: a JSON or YAML file that names the corpus, the formats,
the arms, the provider and the metric tiers. Nothing about a run is implicit,
because a benchmark number is only meaningful together with the exact
configuration that produced it - which is why every result record embeds the
resolved configuration.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .formats.registry import DEFAULT_FORMATS
from .util import read_text


@dataclass
class ProviderConfig:
    """How to reach a model."""

    kind: str = "mock"
    model: str = "mock-1"
    mode: str = "perfect"
    base_url: str | None = None
    api_key_env: str = "CLARION_API_KEY"
    temperature: float = 0.0
    top_p: float = 1.0
    max_output_tokens: int = 8192
    timeout_s: float = 180.0
    max_retries: int = 3
    reasoning: str = "off"
    extra_body: dict[str, Any] = field(default_factory=dict)
    price_input_per_mtok: float = 0.0
    price_output_per_mtok: float = 0.0

    def cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Cost of one call, given the configured prices."""
        return (
            prompt_tokens * self.price_input_per_mtok
            + completion_tokens * self.price_output_per_mtok
        ) / 1_000_000.0


@dataclass
class JudgeConfig:
    """Optional LLM-as-judge scoring (metric tier 2)."""

    enabled: bool = False
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    use_reference: bool = True
    max_entries: int = 0


@dataclass
class FetchStep:
    """One corpus import inside the one-command pipeline."""

    recipe: str
    stratum: str | None = None
    limit: int = 60
    annotate: bool = False
    annotator_model: str = ""
    propose_width: bool = False
    revision: str = ""


@dataclass
class PipelineConfig:
    """What 'clarion pipeline' runs, end to end."""

    fetch: list[FetchStep] = field(default_factory=list)
    robustness_edits: int = 20
    robustness_strata: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


@dataclass
class RunConfig:
    """One complete experiment."""

    name: str = "clarion-run"
    corpus: str = "clarion-core"
    strata: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=lambda: list(DEFAULT_FORMATS))
    arms: list[str] = field(default_factory=lambda: ["bare", "context"])
    spec_location: str = "split"
    spec_reference: bool = True
    repeats: int = 1
    concurrency: int = 4
    isolation: str = "per-file"
    tokenizer: str = "o200k_base"
    target_language: str = "zh-CN"
    include_policy: bool = True
    # The standard protocol hands every format the same thing: a source file
    # with no glossary, because a real project rarely ships one. CLIF may then
    # PRODUCE one through its terminology workflow, which is measured
    # separately - that is what allow_glossary_output enables.
    include_glossary: bool = False
    allow_glossary_output: bool = True
    # Chosen by ablation: stating the glossary as a conditional deliverable in
    # the numbered task rules is what makes a model use the workflow when the
    # file warrants one and skip it when it does not.
    workflow_style: str = "deliverable"
    surface_metrics: bool = True
    neural_metrics: bool = False
    seed: int = 20260101
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    judge: JudgeConfig = field(default_factory=JudgeConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    output_dir: str = "results"

    def as_dict(self) -> dict[str, Any]:
        """Serializable copy of the resolved configuration."""
        return asdict(self)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def from_dict(data: dict[str, Any]) -> RunConfig:
    """Build a RunConfig from a plain dictionary."""
    payload = dict(data)
    provider = ProviderConfig(**payload.pop("provider", {}))
    judge_data = dict(payload.pop("judge", {}))
    judge_provider = ProviderConfig(**judge_data.pop("provider", {})) if judge_data else provider
    judge = JudgeConfig(provider=judge_provider, **judge_data) if judge_data else JudgeConfig()
    pipeline_data = dict(payload.pop("pipeline", {}))
    steps = [FetchStep(**item) for item in pipeline_data.pop("fetch", [])]
    pipeline = PipelineConfig(fetch=steps, **pipeline_data)
    return RunConfig(provider=provider, judge=judge, pipeline=pipeline, **payload)


def load_config(path: Path | str | None = None, **overrides: Any) -> RunConfig:
    """Load a configuration file (JSON or YAML) and apply overrides."""
    data: dict[str, Any] = {}
    if path is not None:
        file_path = Path(path)
        text = read_text(file_path)
        if file_path.suffix in {".yaml", ".yml"}:
            try:
                import yaml
            except ModuleNotFoundError as exc:  # pragma: no cover - env specific
                raise RuntimeError("PyYAML is required to read YAML configs") from exc
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
    if overrides:
        data = _merge(data, {key: value for key, value in overrides.items() if value is not None})
    return from_dict(data)
