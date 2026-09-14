"""Prompt assembly with component-level token accounting.

Every prompt is built from labelled blocks, and every block is measured. That
is what makes dimensions 1 and 2 answerable without extra model calls: the
report can subtract the specification block, the format notes or the glossary
from any measured prompt and state the difference exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..formats.registry import get_format
from ..metrics.tokens import PromptBudget, Tokenizer
from ..paths import SPEC_FILE
from ..providers.base import Message
from ..util import read_text
from . import templates
from .spec_digest import build_grammar_plus

if TYPE_CHECKING:  # pragma: no cover - typing only
    from cliff_format import CliffDocument

TRANSLATION_COMPONENTS = (
    "system.role",
    "task.rules",
    "format.notes",
    "spec.digest",
    "spec.reference",
    "policy.terminology",
    "glossary.workflow",
    "context.hint",
    "glossary",
    "cliff.edit_safety",
    "document",
)
INSTRUCTION_COMPONENTS = ("spec.digest", "format.notes")


@dataclass
class PromptBundle:
    """A ready-to-send prompt plus its measured cost."""

    system: str
    user: str
    budget: PromptBudget
    hint: dict[str, Any] = field(default_factory=dict)

    def messages(self) -> list[Message]:
        """Chat messages for a provider."""
        return [Message("system", self.system), Message("user", self.user)]

    @property
    def total_tokens(self) -> int:
        """Total prompt tokens."""
        return self.budget.total

    def tokens_without_format_instructions(self) -> int:
        """Prompt tokens if the CLIFF digest and format notes were removed."""
        return self.budget.without(*INSTRUCTION_COMPONENTS)


def build_translation_prompt(
    *,
    document_text: str,
    format_id: str,
    tokenizer: Tokenizer,
    source_language: str,
    target_language: str,
    arm: str = "context",
    spec_location: str = "split",
    spec_reference: bool = True,
    glossary_text: str = "",
    policy_fragment: str = "",
    allow_glossary_output: bool = False,
    workflow_style: str = "appendix",
    document: CliffDocument | None = None,
    references: dict[str, str] | None = None,
) -> PromptBundle:
    """Assemble the translation prompt for one file in one format and arm."""
    spec = get_format(format_id)
    budget = PromptBudget(tokenizer=tokenizer.name)

    # The CLIFF digest is split: core rules stay in system, the writer
    # supplement and edit-safety reminder are in the user message near the
    # file to edit.
    notes = templates.FORMAT_NOTES.get(format_id, "")
    digest = build_grammar_plus() if format_id == "cliff" else ""
    system_digest = ""
    user_digest = ""
    if digest:
        if spec_location == "user":
            user_digest = digest
        elif spec_location == "split":
            marker = "\n\n--- SPEC SUPPLEMENT ---"
            if marker in digest:
                head, tail = digest.split(marker, 1)
                system_digest = head.strip()
                user_digest = ("--- SPEC SUPPLEMENT ---" + tail).strip()
            else:
                system_digest = digest
        else:
            system_digest = digest

    system_parts = [templates.SYSTEM_ROLE]
    if system_digest:
        system_parts.append(system_digest)
    if notes:
        system_parts.append(notes)
    system = "\n\n".join(system_parts)
    budget.add("system.role", "system", templates.SYSTEM_ROLE, tokenizer)
    if system_digest:
        budget.add("spec.digest", "system", system_digest, tokenizer)
    if user_digest:
        budget.add("spec.digest", "user", user_digest, tokenizer)
    budget.add("format.notes", "system", notes, tokenizer)

    blocks: list[str] = []
    if user_digest:
        blocks.append(user_digest)
    rules = templates.TASK_RULES.format(
        source_language=source_language,
        target_language=target_language,
    )
    output_rules = (
        templates.OUTPUT_RULES_BILINGUAL
        if spec.bilingual
        else templates.OUTPUT_RULES_MONOLINGUAL.format(target_language=target_language)
    )
    # Where the terminology workflow is stated changes whether it is obeyed:
    # 'appendix' puts it after the format notes, 'deliverable' promotes it into
    # the numbered task rules, and 'front' additionally places it before the
    # specification block. The ablation behind the default is recorded in
    # docs/clarion-prompting.md.
    workflow_enabled = format_id == "cliff" and allow_glossary_output
    workflow_block = ""
    if workflow_enabled:
        workflow_block = templates.GLOSSARY_WORKFLOW
        if workflow_style in {"deliverable", "front"}:
            workflow_block = templates.GLOSSARY_DELIVERABLE + "\n\n" + workflow_block

    rules_block = f"{rules}\n\n{output_rules}"
    if workflow_block and workflow_style in {"deliverable", "front"}:
        rules_block = f"{rules_block}\n\n{templates.GLOSSARY_DELIVERABLE}"
    if format_id == "cliff" and document is not None:
        entry_count = sum(len(group.entries) for group in document.groups)
        group_count = len(document.groups)
        rules_block = (
            f"{rules_block}\n\n"
            f"The file below contains {entry_count} entries in {group_count} sections."
        )
    blocks.append(rules_block)
    budget.add("task.rules", "user", rules_block, tokenizer)



    if workflow_block and workflow_style == "front":
        blocks.append(workflow_block)

    if policy_fragment:
        blocks.append(policy_fragment)
    budget.add("policy.terminology", "user", policy_fragment, tokenizer)

    if workflow_block and workflow_style != "front":
        blocks.append(workflow_block)
    budget.add("glossary.workflow", "user", workflow_block, tokenizer)

    context_hint = templates.CONTEXT_HINT if arm == "context" else ""
    if context_hint:
        blocks.append(context_hint)
    budget.add("context.hint", "user", context_hint, tokenizer)

    glossary_block = ""
    if glossary_text:
        glossary_block = (
            f"{templates.GLOSSARY_HEADER}\n\n{glossary_text}\n{templates.GLOSSARY_FOOTER}"
        )
        blocks.append(glossary_block)
    budget.add("glossary", "user", glossary_block, tokenizer)

    if spec_reference and format_id == "cliff" and SPEC_FILE.exists():
        full_spec = read_text(SPEC_FILE)
        spec_ref = (
            "===== REFERENCE: FULL CLIFF SPECIFICATION =====\n"
            "Before writing the answer, consult the relevant sections of this "
            "full specification. For long files or dense context this is "
            "required.\n\n"
            + full_spec
        )
        blocks.append(spec_ref)
        budget.add("spec.reference", "user", spec_ref, tokenizer)

    if format_id == "cliff":
        blocks.append(templates.CLIFF_EDIT_SAFETY)
        budget.add("cliff.edit_safety", "user", templates.CLIFF_EDIT_SAFETY, tokenizer)

    document_block = f"{templates.DOCUMENT_HEADER}\n\n{document_text}"
    blocks.append(document_block)
    budget.add("document", "user", document_block, tokenizer)

    user = "\n\n".join(block for block in blocks if block).strip() + "\n"
    return PromptBundle(
        system=system,
        user=user,
        budget=budget,
        hint={
            "format": format_id,
            "arm": arm,
            "document": document,
            "references": references or {},
        },
    )


def build_judge_prompt(
    *,
    source: str,
    target: str,
    reference: str | None,
    context: str | None,
    source_language: str,
    target_language: str,
) -> list[Message]:
    """Assemble a GEMBA-MQM style evaluation prompt for one segment."""
    lines = [
        templates.JUDGE_TASK,
        "",
        f"Source language: {source_language}",
        f"Target language: {target_language}",
        f"Source: {source}",
    ]
    if context:
        lines.append(f"Translation brief: {context}")
    if reference:
        lines.append(f"Human reference translation: {reference}")
    lines.append(f"Translation to evaluate: {target}")
    return [Message("system", templates.JUDGE_SYSTEM), Message("user", "\n".join(lines))]
