"""Measurement layer of CLARION.

Tier 1 (always on, dependency free)
    surface metrics (chrF++, BLEU, TER), structural scoring, round-trip
    fidelity, instruction-following rules, terminology and de-jargon checks,
    token accounting and statistics.

Tier 2 (optional, costs tokens)
    MQM-style LLM judge.

Tier 3 (optional, needs torch)
    neural metrics such as COMET and CometKiwi.
"""

from __future__ import annotations

from .controls import CONTROL_NAMES, ControlReport, build_controls, evaluate_controls
from .fidelity import FidelityReport, roundtrip_fidelity
from .instruction import Rule, RuleResult, check_rules, instruction_score, rule_kinds
from .judge import JudgeResult, MqmError, judge_entry, judge_score
from .structure import StructureReport, evaluate_structure
from .surface import corpus_bleu, corpus_chrf, sentence_bleu, sentence_chrf, sentence_ter
from .terminology import (
    GlossaryTerm,
    JargonPolicy,
    JargonReport,
    TerminologyReport,
    check_glossary,
    check_jargon,
    glossary_from_document,
    load_glossary,
    load_policy,
)
from .tokens import ComponentCost, PromptBudget, Tokenizer, count_text, get_tokenizer
from .width import display_cells

__all__ = [
    "CONTROL_NAMES",
    "ComponentCost",
    "ControlReport",
    "FidelityReport",
    "GlossaryTerm",
    "JargonPolicy",
    "JargonReport",
    "JudgeResult",
    "MqmError",
    "PromptBudget",
    "Rule",
    "RuleResult",
    "StructureReport",
    "TerminologyReport",
    "Tokenizer",
    "build_controls",
    "check_glossary",
    "check_jargon",
    "check_rules",
    "corpus_bleu",
    "corpus_chrf",
    "count_text",
    "display_cells",
    "evaluate_controls",
    "evaluate_structure",
    "get_tokenizer",
    "glossary_from_document",
    "instruction_score",
    "judge_entry",
    "judge_score",
    "load_glossary",
    "load_policy",
    "roundtrip_fidelity",
    "rule_kinds",
    "sentence_bleu",
    "sentence_chrf",
    "sentence_ter",
]
