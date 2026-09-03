"""Experiment arms and the document projections they need.

An *arm* decides how much context a rendered file carries:

bare
    What a project normally ships: identifiers, source text, and nothing else.
    Family info, translation standards, group metadata, per-entry context,
    emotion, width limits and references are all removed.

context
    The same content plus the complete CLIF context payload, expressed in each
    format's own documented metadata channel by clif_format.

The projections below operate on the clif-python data model, never on text, so the
bare and context arms of every format are provably the same content.
"""

from __future__ import annotations

import copy
from enum import StrEnum
from typing import TYPE_CHECKING

from ..paths import ensure_clif_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument

# A neutral type used only where a format requires one but the bare arm
# carries no typing information. CLIF requires 'type' on every entry, so the
# bare CLIF arm cannot go below this floor - which is exactly what the
# methodology reports as CLIF's structural minimum.
NEUTRAL_TYPE = "sentence"


class Arm(StrEnum):
    """How much context a rendered document carries."""

    BARE = "bare"
    CONTEXT = "context"


def strip_context(document: ClifDocument) -> ClifDocument:
    """Return a copy with every context-carrying field removed."""
    ensure_clif_format()
    stripped = copy.deepcopy(document)
    header = stripped.header
    header.title = None
    header.info = None
    header.standard = None
    header.dependency = []
    header.version = None
    header.extensions = {}
    for group in stripped.groups:
        group.context = None
        group.type = None
        group.emotion = []
        group.max_width = None
        group.extensions = {}
        for entry in group.entries:
            entry.context = None
            entry.type = None
            entry.emotion = []
            entry.max_width = None
            entry.reference = []
            entry.reviewer = None
            entry.extensions = {}
            # Workflow state is metadata too: a plain resource file does not
            # carry it. CLIF refills it in ensure_required_fields because the
            # specification requires it.
            entry.status = None
    return stripped


def blank_targets(document: ClifDocument, *, status: str | None = "initial") -> ClifDocument:
    """Return a copy with no target text, ready to be handed to a translator."""
    ensure_clif_format()
    task = copy.deepcopy(document)
    for group in task.groups:
        for entry in group.entries:
            entry.target = None
            entry.status = status
            entry.reviewer = None
    return task


def ensure_required_fields(document: ClifDocument) -> ClifDocument:
    """Fill the fields CLIF requires but the bare arm removed.

    CLIF requires 'type' and 'status' on every entry, so a stripped document
    is completed with an information-free neutral type before serialization.
    """
    ensure_clif_format()
    filled = copy.deepcopy(document)
    for group in filled.groups:
        for entry in group.entries:
            # Only fill when the section does not already supply an inherited
            # value, because writing it onto the entry would change the document.
            # (Do not start this comment with the word 'type' followed by a
            # colon: mypy would read it as a type comment.)
            if not entry.type and not group.type:
                entry.type = NEUTRAL_TYPE
            if not entry.status:
                entry.status = "translated" if entry.target else "initial"
    return filled


def project(document: ClifDocument, arm: Arm | str, *, blank: bool = True) -> ClifDocument:
    """Project a corpus document into one experiment arm.

    blank=True produces the translation task document (no targets); blank=False
    keeps the reference targets, which is what the round-trip fidelity and
    edit-robustness experiments need.
    """
    arm = Arm(arm)
    bare = arm is Arm.BARE
    projected = strip_context(document) if bare else copy.deepcopy(document)
    if blank:
        projected = blank_targets(projected, status=None if bare else "initial")
    return projected
