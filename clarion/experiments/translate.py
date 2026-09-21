"""The translation experiment: dimensions 1 to 6 in one pass.

One task is one corpus file, in one format, in one arm. Running it produces
every measurement those six dimensions need:

* token cost, decomposed by prompt component (dimensions 1 and 2);
* wall-clock latency and output tokens (dimensions 5 and 6);
* structural survival, surface quality, instruction-following, terminology
  adherence and de-jargon cleanliness (dimensions 3 and 4).

The same function serves both arms, so a difference between arms can only come
from the context payload, never from the harness.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..config import RunConfig
from ..corpus.model import CorpusFile
from ..formats.arms import Arm, project
from ..formats.read_mode import DEFAULT_READ_MODE
from ..formats.registry import get_format
from ..formats.render import render_document
from ..metrics.instruction import check_rules, instruction_score
from ..metrics.structure import evaluate_structure
from ..metrics.surface import sentence_bleu, sentence_chrf, sentence_ter
from ..metrics.terminology import JargonPolicy, check_glossary, check_jargon, glossary_from_document
from ..metrics.tokens import Tokenizer
from ..prompts.assembly import build_translation_prompt
from ..providers.base import CompletionRequest, Provider
from ..util import mean


@dataclass
class TaskResult:
    """Everything measured for one file in one format and arm.

    answer_text holds the raw model output. It is kept out of the JSONL record
    (which stays readable) and written next to it as a file, so every number in
    a report can be traced back to the text that produced it.
    """

    file_id: str
    stratum: str
    format_id: str
    arm: str
    repeat: int = 0
    context_origin: str = "original"
    provider: str = ""
    model: str = ""
    tokenizer: str = ""
    prompt_tokens: int = 0
    prompt_tokens_reported: int | None = None
    prompt_tokens_without_instructions: int = 0
    document_tokens: int = 0
    glossary_tokens: int = 0
    spec_tokens: int = 0
    format_notes_tokens: int = 0
    output_tokens: int = 0
    output_tokens_reported: int | None = None
    reasoning_tokens: int | None = None
    finish_reason: str | None = None
    truncated: bool = False
    #: The temperature the request was actually SENT at, recorded per row. A run
    #: directory that only carries the configuration cannot show a divergence
    #: between the two, which is exactly how dimension 7 spent its whole history
    #: sending 0.0 while its config.json said 1.3.
    temperature: float = 0.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    entries: int = 0
    structure: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, float] = field(default_factory=dict)
    per_entry: list[dict[str, Any]] = field(default_factory=list)
    instruction: dict[str, Any] = field(default_factory=dict)
    terminology: dict[str, Any] = field(default_factory=dict)
    jargon: dict[str, Any] = field(default_factory=dict)
    prompt_components: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = "ok"
    glossary_emitted: bool = False
    glossary_terms: int = 0
    glossary_consistency: float = 0.0
    answer_text: str = ""
    prompt_text: str = ""
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record for the evidence log."""
        payload = {
            "file": self.file_id,
            "stratum": self.stratum,
            "format": self.format_id,
            "arm": self.arm,
            "repeat": self.repeat,
            "context_origin": self.context_origin,
            "provider": self.provider,
            "model": self.model,
            "tokenizer": self.tokenizer,
            "tokens": {
                "prompt": self.prompt_tokens,
                "prompt_reported": self.prompt_tokens_reported,
                "prompt_without_instructions": self.prompt_tokens_without_instructions,
                "document": self.document_tokens,
                "glossary": self.glossary_tokens,
                "spec": self.spec_tokens,
                "format_notes": self.format_notes_tokens,
                "output": self.output_tokens,
                "output_reported": self.output_tokens_reported,
                "reasoning": self.reasoning_tokens,
            },
            "finish_reason": self.finish_reason,
            "truncated": self.truncated,
            "temperature": self.temperature,
            # Which reading of the answer produced ``structure``, and how many
            # Appendix C repairs it needed. Recorded on every row so a report can
            # never mix two readings without saying so (specification C.1/C.6).
            "read_mode": self.structure.get("read_mode", DEFAULT_READ_MODE),
            "repairs": int(self.structure.get("repairs", 0) or 0),
            "latency_ms": round(self.latency_ms, 3),
            "cost_usd": round(self.cost_usd, 6),
            "entries": self.entries,
            "structure": self.structure,
            "quality": self.quality,
            "instruction": self.instruction,
            "terminology": self.terminology,
            "jargon": self.jargon,
            "prompt_components": self.prompt_components,
            "outcome": self.outcome,
            "failed": self.outcome != "ok",
            "glossary": {
                "emitted": self.glossary_emitted,
                "terms": self.glossary_terms,
                "consistency": round(self.glossary_consistency, 4),
            },
            "error": self.error,
        }
        return payload


def _glossary_text(corpus_file: CorpusFile, format_id: str, arm: Arm) -> str:
    if corpus_file.glossary_document is None or arm is not Arm.CONTEXT:
        return ""
    return render_document(corpus_file.glossary_document, format_id, arm=arm)


def run_translation_task(
    corpus_file: CorpusFile,
    *,
    format_id: str,
    arm: Arm | str,
    provider: Provider,
    tokenizer: Tokenizer,
    config: RunConfig,
    policy: JargonPolicy | None = None,
    repeat: int = 0,
) -> TaskResult:
    """Run one translation task end to end and score the answer."""
    arm_value = Arm(arm)
    spec = get_format(format_id)
    result = TaskResult(
        file_id=corpus_file.id,
        stratum=corpus_file.stratum,
        format_id=format_id,
        arm=arm_value.value,
        repeat=repeat,
        tokenizer=tokenizer.name,
        entries=corpus_file.entry_count,
        context_origin=(
            corpus_file.provenance.context_origin if corpus_file.provenance else "original"
        ),
    )

    task_document = project(corpus_file.document, arm_value, blank=True)
    document_text = render_document(task_document, format_id, arm=arm_value)
    glossary_text = ""
    if config.include_glossary:
        glossary_text = _glossary_text(corpus_file, format_id, arm_value)
    policy_fragment = policy.prompt_fragment() if (policy and config.include_policy) else ""

    bundle = build_translation_prompt(
        document_text=document_text,
        format_id=format_id,
        tokenizer=tokenizer,
        source_language=corpus_file.source_language,
        target_language=corpus_file.target_language,
        arm=arm_value.value,
        spec_location=config.spec_location,
        spec_reference=config.spec_reference,
        glossary_text=glossary_text,
        policy_fragment=policy_fragment,
        allow_glossary_output=config.allow_glossary_output,
        workflow_style=config.workflow_style,
        # Without this the dimension silently used DEFAULT_PROMPT_STYLE whatever the
        # configuration said, so a run whose config, run directory and report header
        # all named `examples` actually sent the digest - the same shape of gap the
        # edit path had with its temperature. Prompted by the dry-run test in
        # tests/clarion/test_cli.py, which asserts the style reaches the system
        # message rather than trusting the configuration.
        prompt_style=config.prompt_style,
        document=task_document,
        references=corpus_file.references(),
    )
    budget = bundle.budget
    result.prompt_tokens = budget.total
    result.prompt_tokens_without_instructions = bundle.tokens_without_format_instructions()
    result.document_tokens = budget.tokens_of("document")
    result.glossary_tokens = budget.tokens_of("glossary")
    result.spec_tokens = budget.tokens_of("spec.digest")
    result.format_notes_tokens = budget.tokens_of("format.notes")
    result.prompt_components = [component.as_dict() for component in budget.components]

    # Gold-leak guard. The task document is built by blanking every target, but
    # a benchmark must prove that rather than assume it: if any reference
    # translation appears in the prompt, the run is void.
    # The glossary legitimately contains canonical renderings, and a one-word UI
    # label may be exactly such a term; a leak is only a leak when the answer
    # sits inside the document the model has to translate.
    # A reference that is identical to its own source is not a leak: "keep this
    # term in Latin script" is a legitimate correct answer, and the term
    # necessarily appears in the file the model is given.
    sources_by_id = corpus_file.sources()
    leaked = [
        entry_id
        for entry_id, reference in corpus_file.references().items()
        if reference
        and len(reference) > 3
        and reference not in (sources_by_id.get(entry_id) or "")
        and reference in document_text
    ]
    if leaked:
        result.error = f"gold leak: {len(leaked)} reference translations appear in the prompt"
        result.outcome = "gold-leak"
        return result

    request = CompletionRequest(
        messages=bundle.messages(),
        temperature=config.provider.temperature,
        top_p=config.provider.top_p,
        max_output_tokens=config.provider.max_output_tokens,
        extra_body=dict(config.provider.extra_body),
        hint=bundle.hint,
    )
    started = time.perf_counter()
    completion = provider.complete(request)
    measured_ms = (time.perf_counter() - started) * 1000.0
    result.answer_text = completion.text
    # The whole prompt, not just the user message. The run keeps this as evidence,
    # and for CLIFF the half that was missing is the half the prompt design is
    # about: the field table and the closed vocabularies live in the system message.
    result.prompt_text = request.prompt_text()

    result.provider = completion.provider
    result.model = completion.model
    result.latency_ms = completion.latency_ms or measured_ms
    result.prompt_tokens_reported = completion.prompt_tokens
    result.output_tokens_reported = completion.completion_tokens
    result.reasoning_tokens = completion.reasoning_tokens
    result.finish_reason = completion.finish_reason
    result.truncated = completion.finish_reason == "length"
    result.temperature = request.temperature
    result.output_tokens = completion.completion_tokens or tokenizer.count(completion.text)
    result.cost_usd = config.provider.cost_usd(
        completion.prompt_tokens or result.prompt_tokens,
        completion.completion_tokens or result.output_tokens,
    )
    if completion.error:
        result.error = completion.error
        result.outcome = "api-error"
        return result
    if result.truncated and not completion.text.strip():
        # The answer hit the output ceiling before producing anything. That is
        # a budget failure of the run, not a property of the format, and it is
        # recorded as an error so it can never be averaged into a score.
        result.error = "output budget exhausted before any content was produced"
        result.outcome = "empty"
        return result

    structure, targets, glossary_document = evaluate_structure(
        corpus_file.document,
        completion.text,
        format_id,
        bilingual=spec.bilingual,
        read_mode=config.read_mode,
    )
    result.structure = structure.as_dict()

    # The terminology workflow: did the model produce a glossary, and did it
    # then actually use the renderings it wrote down?
    if glossary_document is not None:
        produced = glossary_from_document(glossary_document)
        result.glossary_emitted = True
        result.glossary_terms = len(produced)
        if produced:
            self_check = check_glossary(produced, corpus_file.sources(), targets)
            result.glossary_consistency = self_check.adherence

    # A file that no longer parses, or that lost entries, is a FAILED
    # translation of that format. Format fragility is exactly what this
    # benchmark measures, so it is scored, never excused: the surface metrics
    # run over whatever survived and the zeros for the rest stand.
    if result.truncated:
        # The answer ran into the output ceiling. With an unlimited budget this
        # means the model degenerated (it repeated itself until it ran out),
        # which is a property of the model, not of the format, and is reported
        # under its own name instead of being averaged into a format's failures.
        result.outcome = "degenerate"
    elif not structure.parsed:
        result.outcome = "parse-error"
    elif not structure.valid:
        result.outcome = "invalid"
    elif structure.coverage < 1.0:
        result.outcome = "incomplete"

    sources = corpus_file.sources()
    references = corpus_file.references()
    per_entry: list[dict[str, Any]] = []
    chrf_scores: list[float] = []
    bleu_scores: list[float] = []
    ter_scores: list[float] = []
    for entry_id, reference in references.items():
        target_text = targets.get(entry_id)
        if not target_text:
            continue
        gold = corpus_file.gold.get(entry_id)
        candidates = gold.references if gold and gold.references else [reference]
        chrf = sentence_chrf(target_text, candidates)
        bleu = sentence_bleu(target_text, candidates)
        ter = sentence_ter(target_text, candidates[0])
        chrf_scores.append(chrf)
        bleu_scores.append(bleu)
        ter_scores.append(ter)
        per_entry.append(
            {
                "entry": entry_id,
                "chrf": round(chrf, 4),
                "bleu": round(bleu, 4),
                "ter": round(ter, 4),
                "target": target_text,
            }
        )
    result.per_entry = per_entry
    result.quality = {
        "chrf": round(mean(chrf_scores), 4),
        "bleu": round(mean(bleu_scores), 4),
        "ter": round(mean(ter_scores), 4),
        "scored_entries": float(len(per_entry)),
    }

    rule_results = check_rules(
        corpus_file.rules(),
        sources,
        targets,
        target_language=corpus_file.target_language,
        widths=corpus_file.widths(),
    )
    result.instruction = {
        "score": round(instruction_score(rule_results), 4),
        "checks": len(rule_results),
        "failed": [item.as_dict() for item in rule_results if not item.passed][:20],
    }

    terms = (
        glossary_from_document(corpus_file.glossary_document)
        if corpus_file.glossary_document
        else []
    )
    result.terminology = check_glossary(terms, sources, targets).as_dict()
    if policy is not None:
        result.jargon = check_jargon(policy, targets).as_dict()
    return result
