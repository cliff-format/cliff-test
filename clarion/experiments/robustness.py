"""Dimension 7: does a file survive being edited by a model?

The original CLIF robustness protocol applied 100 realistic edits to a CLIF
file and validated the result after every one. That answers the question for
CLIF alone. To compare formats, the same edit INTENT has to be applied to every
format, so the intents here are declarative operations on the data model:

    set-target, set-context, set-status, set-type, set-emotion, set-max-width,
    add-reference, add-entry, delete-entry, rename-entry, move-entry,
    set-header-field, add-comment

Each intent is rendered as a natural-language instruction for the model, and
also applied deterministically to the pyclif data model so the harness can
verify the intent offline and produce a reference answer without a model.

Two numbers come out of a run:

validity rate
    share of edits after which the file was still a valid file of that format;
intent rate
    share of edits that actually took effect (the model did what was asked).

A format that survives every edit by ignoring the instruction is not robust,
which is why both numbers are always reported together.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..formats.arms import Arm
from ..formats.parse import parse_back
from ..formats.registry import get_format
from ..formats.render import render_document
from ..formats.validity import check_validity
from ..paths import ensure_pyclif
from ..providers.base import CompletionRequest, Message, Provider

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyclif import ClifDocument

METADATA_OPS = {
    "set-context",
    "set-status",
    "set-type",
    "set-emotion",
    "set-max-width",
    "add-reference",
}
HEADER_OPS = {"set-header-field"}
STATUS_FORMATS = {"clif", "xliff-2.1", "xliff-2.2", "csv", "json-clif", "yaml-clif"}
# Formats whose keys keep the group path, so "move this entry to another group"
# is a change the file can actually express. Android, iOS and Fluent resources
# are flat: their keys carry no group, so the intent is not applicable and is
# excluded from their denominator instead of counted as a failure.
GROUP_FORMATS = {
    "clif",
    "xliff-2.1",
    "xliff-2.2",
    "po",
    "csv",
    "json-clif",
    "yaml-clif",
    "json-plain",
    "yaml-plain",
}


@dataclass(frozen=True)
class EditTask:
    """One format-neutral edit intent."""

    id: int
    category: str
    op: str
    params: dict[str, Any] = field(default_factory=dict)

    def instruction(self) -> str:
        """Natural-language instruction handed to the model."""
        entry = self.params.get("entry", "")
        value = self.params.get("value", "")
        if self.op == "set-target":
            return f"Change the translation of entry '{entry}' to: {value}"
        if self.op == "set-context":
            return f"Set the translator context of entry '{entry}' to: {value}"
        if self.op == "set-status":
            return f"Set the workflow status of entry '{entry}' to '{value}'."
        if self.op == "set-type":
            return f"Set the content type of entry '{entry}' to '{value}'."
        if self.op == "set-emotion":
            return f"Set the emotion tags of entry '{entry}' to {value}."
        if self.op == "set-max-width":
            return f"Set the maximum display width of entry '{entry}' to {value} cells."
        if self.op == "add-reference":
            return f"Add the source reference '{value}' to entry '{entry}'."
        if self.op == "add-entry":
            return (
                f"Add a new entry with the identifier '{entry}' in group "
                f"'{self.params.get('group', '')}', with the source text "
                f"'{self.params.get('source', '')}' and the translation '{value}'."
            )
        if self.op == "delete-entry":
            return f"Delete the entry '{entry}' completely."
        if self.op == "rename-entry":
            return f"Rename the entry '{entry}' to '{value}', keeping everything else."
        if self.op == "move-entry":
            return f"Move the entry '{entry}' into the group '{value}'."
        if self.op == "set-header-field":
            return f"Set the file-level {self.params.get('field', 'title')} to: {value}"
        if self.op == "add-comment":
            return f"Add a comment line saying: {value}"
        return f"Apply the edit '{self.op}' to entry '{entry}'."

    def applicable(self, format_id: str, arm: Arm | str) -> bool:
        """Whether this intent is expressible in a format and arm."""
        spec = get_format(format_id)
        arm_value = Arm(arm)
        if self.op in METADATA_OPS:
            if self.op == "set-status" and arm_value is Arm.BARE:
                return format_id in STATUS_FORMATS
            return arm_value is Arm.CONTEXT and spec.context_capable
        if self.op in HEADER_OPS:
            return arm_value is Arm.CONTEXT and format_id in {
                "clif",
                "xliff-2.1",
                "xliff-2.2",
                "po",
                "csv",
                "json-clif",
                "yaml-clif",
            }
        if self.op == "add-comment":
            return format_id not in {"json-clif", "json-plain", "csv"}
        if self.op == "move-entry":
            return format_id in GROUP_FORMATS
        return True


def _entries(document: ClifDocument) -> list[tuple[Any, Any]]:
    return [(group, entry) for group in document.groups for entry in group.entries]


def default_tasks(document: ClifDocument, count: int = 30) -> list[EditTask]:
    """Generate a deterministic edit sequence for a document."""
    pairs = _entries(document)
    if not pairs:
        return []
    groups = [group.path for group in document.groups]
    tasks: list[EditTask] = []
    recipes: list[tuple[str, str, dict[str, Any]]] = []
    for index, (group, entry) in enumerate(pairs):
        entry_id = entry.id
        recipes.append(
            (
                "retranslate",
                "set-target",
                {"entry": entry_id, "value": f"{entry.target or entry.source}(修订)"},
            )
        )
        if index % 2 == 0:
            recipes.append(
                (
                    "context",
                    "set-context",
                    {"entry": entry_id, "value": "Reviewed in the 2026 audit."},
                )
            )
        if index % 3 == 0:
            recipes.append(("status", "set-status", {"entry": entry_id, "value": "reviewed"}))
        if index % 4 == 0:
            recipes.append(("width", "set-max-width", {"entry": entry_id, "value": 24}))
        if index % 5 == 0:
            recipes.append(("emotion", "set-emotion", {"entry": entry_id, "value": ["calm"]}))
        if index % 6 == 0:
            recipes.append(
                ("reference", "add-reference", {"entry": entry_id, "value": "src/ui/panel.cpp:42"})
            )
        # A move must be generated before a rename of the same entry: the
        # sequence is applied to the previous answer, so a move that names the
        # old identifier after a rename would be unsatisfiable by construction
        # and would put noise into the intent rate.
        if index % 8 == 0 and len(groups) > 1:
            other = groups[(groups.index(group.path) + 1) % len(groups)]
            recipes.append(("move", "move-entry", {"entry": entry_id, "value": other}))
        if index % 7 == 0:
            recipes.append(
                ("rename", "rename-entry", {"entry": entry_id, "value": f"{entry_id}-v2"})
            )

    recipes.append(
        (
            "add",
            "add-entry",
            {
                "entry": "clarion-added-one",
                "group": groups[0],
                "source": "Continue",
                "value": "继续",
            },
        )
    )
    recipes.append(("comment", "add-comment", {"value": "checked by the CLARION robustness run"}))
    recipes.append(
        ("header", "set-header-field", {"field": "title", "value": "CLARION robustness pass"})
    )
    recipes.append(("delete", "delete-entry", {"entry": pairs[-1][1].id}))

    for number, (category, op, params) in enumerate(recipes[:count], start=1):
        tasks.append(EditTask(id=number, category=category, op=op, params=params))
    return tasks


def apply_edit(document: ClifDocument, task: EditTask) -> ClifDocument:
    """Apply an edit deterministically to the data model (reference answer)."""
    ensure_pyclif()
    from pyclif import Entry, Group

    edited = copy.deepcopy(document)
    entry_id = str(task.params.get("entry", ""))
    value = task.params.get("value")

    def find(target_id: str) -> tuple[Any, Any] | None:
        for group in edited.groups:
            for entry in group.entries:
                if entry.id == target_id:
                    return group, entry
        return None

    found = find(entry_id)
    if task.op == "add-entry":
        path = str(task.params.get("group") or (edited.groups[0].path if edited.groups else "main"))
        group = next((item for item in edited.groups if item.path == path), None)
        if group is None:
            group = Group(path=path)
            edited.groups.append(group)
        group.entries.append(
            Entry(
                id=entry_id,
                source=str(task.params.get("source", "")),
                target=str(value or ""),
                type="label",
                status="translated",
            )
        )
        return edited
    if task.op == "set-header-field":
        field_name = str(task.params.get("field", "title"))
        setattr(edited.header, field_name, str(value))
        return edited
    if task.op == "add-comment":
        return edited  # comments are not part of the data model
    if found is None:
        return edited

    group, entry = found
    if task.op == "set-target":
        entry.target = str(value)
        entry.status = entry.status or "translated"
    elif task.op == "set-context":
        entry.context = str(value)
    elif task.op == "set-status":
        entry.status = str(value)
    elif task.op == "set-type":
        entry.type = str(value)
    elif task.op == "set-emotion":
        entry.emotion = [str(item) for item in (value or [])]
    elif task.op == "set-max-width":
        entry.max_width = int(value or 0)
    elif task.op == "add-reference":
        entry.reference = [*entry.reference, str(value)]
    elif task.op == "rename-entry":
        entry.id = str(value)
    elif task.op == "delete-entry":
        group.entries.remove(entry)
    elif task.op == "move-entry":
        destination = next((item for item in edited.groups if item.path == str(value)), None)
        if destination is None:
            destination = Group(path=str(value))
            edited.groups.append(destination)
        group.entries.remove(entry)
        destination.entries.append(entry)
    return edited


def verify_edit(document: ClifDocument, task: EditTask) -> bool:
    """Check whether an edited document actually carries the intent."""
    entry_id = str(task.params.get("entry", ""))
    value = task.params.get("value")
    index = {entry.id: (group, entry) for group in document.groups for entry in group.entries}

    if task.op == "delete-entry":
        return entry_id not in index
    if task.op == "rename-entry":
        return str(value) in index and entry_id not in index
    if task.op == "add-entry":
        return entry_id in index
    if task.op == "set-header-field":
        field_name = str(task.params.get("field", "title"))
        return str(getattr(document.header, field_name, "") or "") == str(value)
    if task.op == "add-comment":
        return True
    found = index.get(entry_id)
    if found is None:
        return False
    group, entry = found
    if task.op == "set-target":
        return (entry.target or "") == str(value)
    if task.op == "set-context":
        return str(value) in ((entry.context or "") + " " + (group.context or ""))
    if task.op == "set-status":
        return (entry.status or "") == str(value)
    if task.op == "set-type":
        return (entry.type or group.type or "") == str(value)
    if task.op == "set-emotion":
        return [str(item) for item in (value or [])] == (entry.emotion or group.emotion)
    if task.op == "set-max-width":
        width = entry.max_width if entry.max_width is not None else group.max_width
        return width == int(value or 0)
    if task.op == "add-reference":
        return str(value) in entry.reference
    if task.op == "move-entry":
        return group.path == str(value)
    return True


@dataclass
class EditOutcome:
    """Result of one edit on one format."""

    task_id: int
    category: str
    op: str
    applicable: bool
    valid: bool = False
    intent_ok: bool = False
    parsed: bool = False
    unwrapped: bool = False
    error: str | None = None
    latency_ms: float = 0.0
    output_tokens: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "task": self.task_id,
            "category": self.category,
            "op": self.op,
            "applicable": self.applicable,
            "valid": self.valid,
            "intent_ok": self.intent_ok,
            "parsed": self.parsed,
            "unwrapped": self.unwrapped,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 3),
        }


@dataclass
class RobustnessResult:
    """Edit robustness of one format and arm."""

    format_id: str
    arm: str
    file_id: str
    outcomes: list[EditOutcome] = field(default_factory=list)

    @property
    def applicable(self) -> int:
        """Number of edits that this format could express."""
        return sum(1 for outcome in self.outcomes if outcome.applicable)

    @property
    def validity_rate(self) -> float:
        """Share of applicable edits that left a valid file."""
        total = self.applicable
        if not total:
            return 0.0
        return 100.0 * sum(1 for o in self.outcomes if o.applicable and o.valid) / total

    @property
    def intent_rate(self) -> float:
        """Share of applicable edits that actually took effect."""
        total = self.applicable
        if not total:
            return 0.0
        return 100.0 * sum(1 for o in self.outcomes if o.applicable and o.intent_ok) / total

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "format": self.format_id,
            "arm": self.arm,
            "file": self.file_id,
            "edits_applicable": self.applicable,
            "validity_rate": round(self.validity_rate, 4),
            "intent_rate": round(self.intent_rate, 4),
            "outcomes": [outcome.as_dict() for outcome in self.outcomes],
        }


EDIT_SYSTEM = (
    "You are a localization engineer. You edit localization resource files "
    "surgically: you apply exactly the requested change and return the complete "
    "file, unchanged everywhere else, with no commentary and no code fence."
)


def run_robustness(
    document: ClifDocument,
    *,
    format_id: str,
    arm: Arm | str,
    provider: Provider | None,
    tasks: list[EditTask],
    file_id: str = "base",
    max_output_tokens: int = 8192,
) -> RobustnessResult:
    """Apply an edit sequence to one format, validating after every step.

    With provider=None the deterministic reference application is used, which
    is how the harness self-tests without a model.
    """
    arm_value = Arm(arm)
    result = RobustnessResult(format_id=format_id, arm=arm_value.value, file_id=file_id)
    current_document = copy.deepcopy(document)
    current_text = render_document(current_document, format_id, arm=arm_value)

    for task in tasks:
        applicable = task.applicable(format_id, arm_value)
        outcome = EditOutcome(
            task_id=task.id, category=task.category, op=task.op, applicable=applicable
        )
        if not applicable:
            result.outcomes.append(outcome)
            continue

        if provider is None:
            current_document = apply_edit(current_document, task)
            current_text = render_document(current_document, format_id, arm=arm_value)
            answer_text = current_text
            outcome.latency_ms = 0.0
        else:
            messages = [
                Message("system", EDIT_SYSTEM),
                Message(
                    "user",
                    f"{task.instruction()}\n\nFile:\n{current_text}",
                ),
            ]
            completion = provider.complete(
                CompletionRequest(
                    messages=messages,
                    temperature=0.0,
                    max_output_tokens=max_output_tokens,
                    hint={
                        "format": format_id,
                        "arm": arm_value.value,
                        "document": apply_edit(current_document, task),
                    },
                )
            )
            outcome.latency_ms = completion.latency_ms
            outcome.output_tokens = completion.completion_tokens
            if completion.error:
                outcome.error = completion.error
                result.outcomes.append(outcome)
                continue
            answer_text = completion.text

        report = check_validity(answer_text, format_id)
        outcome.valid = report.ok
        outcome.unwrapped = report.unwrapped
        parsed = parse_back(answer_text, format_id)
        outcome.parsed = parsed.ok
        if parsed.document is not None:
            outcome.intent_ok = verify_edit(parsed.document, task)
            current_document = parsed.document
            current_text = answer_text
        else:
            outcome.error = parsed.error
        result.outcomes.append(outcome)
    return result
