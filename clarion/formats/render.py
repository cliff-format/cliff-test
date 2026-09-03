"""Render one canonical CLIF document into any competing format.

Rendering always goes through clif-python (or, for the plain dialects, through
clarion.formats.plain, which is written against the same data model). A
format's fixture is therefore never hand-authored, and the bare and context
arms of two different formats always describe the same content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..paths import ensure_clif_format
from .arms import Arm, ensure_required_fields, project
from .plain import render_json_plain, render_yaml_plain
from .registry import get_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument


class FormatUnavailableError(RuntimeError):
    """Raised when a format needs an optional dependency that is missing."""


def _require(spec_requires: tuple[str, ...]) -> None:
    for requirement in spec_requires:
        if requirement == "yaml":
            try:
                import yaml  # noqa: F401
            except ModuleNotFoundError as exc:  # pragma: no cover - env specific
                raise FormatUnavailableError(
                    "PyYAML is required for the YAML formats (pip install PyYAML)"
                ) from exc


def render_document(document: ClifDocument, format_id: str, *, arm: Arm | str) -> str:
    """Serialize an already projected document into one format."""
    ensure_clif_format()
    import clif_format

    spec = get_format(format_id)
    _require(spec.requires)
    with_context = Arm(arm) is Arm.CONTEXT

    if spec.id == "clif":
        return clif_format.serialize(ensure_required_fields(document))
    if spec.id.startswith("xliff"):
        return clif_format.to_xliff(document, version=spec.xliff_version or "2.1")
    if spec.id == "po":
        return clif_format.to_po(document)
    if spec.id == "fluent":
        return clif_format.to_fluent(document)
    if spec.id == "json-clif":
        return clif_format.to_json(document) + "\n"
    if spec.id == "yaml-clif":
        return clif_format.to_yaml(document)
    if spec.id == "json-plain":
        return render_json_plain(document, with_context=with_context)
    if spec.id == "yaml-plain":
        return render_yaml_plain(document, with_context=with_context)
    if spec.id == "csv":
        return clif_format.to_csv(document)
    if spec.id == "android":
        return clif_format.to_android_strings(document)
    if spec.id == "ios":
        return clif_format.to_ios_strings(document)
    raise KeyError(f"no renderer for format '{format_id}'")


def render(
    document: ClifDocument,
    format_id: str,
    *,
    arm: Arm | str,
    blank: bool = True,
) -> str:
    """Project a corpus document into an arm and render it in one format."""
    projected = project(document, arm, blank=blank)
    return render_document(projected, format_id, arm=arm)
