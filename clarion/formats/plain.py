"""Plain key/value localization dialects (i18n JSON and YAML).

clif-python converts CLIF to JSON and YAML shaped like the CLIF data model, which
is the right interchange target but is not what a web or mobile project
actually ships. The plain dialects here are the realistic competitors:

* bare arm - a nested object of key to source string, the shape used by
  i18next, Rails locale files and Minecraft-style resource bundles;
* context arm - the Chrome extension messages.json convention, where every key
  maps to an object with a message and a description. The description carries
  the same CLIF metadata payload that clif-python writes into PO and Fluent
  comments, so the arms stay comparable across formats.

Both dialects round-trip through parse_json_plain / parse_yaml_plain.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from ..paths import ensure_clif_format

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument, Entry, Group

META_PREFIX = "clif:"
_COMMENT_RE = re.compile(r"^\s*#\s?(.*)$")
_YAML_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+):\s*(.*)$")


def entry_metadata(group: Group, entry: Entry, *, include_source: bool) -> dict[str, str]:
    """CLIF metadata for one entry, in the same shape clif-python writes.

    Uses the public effective_* helpers so inheritance is resolved exactly as
    the specification requires (group value first, entry value overrides).
    """
    ensure_clif_format()
    from clif_format import effective_context, effective_max_width

    meta: dict[str, str] = {}
    if include_source and entry.source:
        meta["source"] = entry.source
    resolved_type = entry.type or group.type
    if resolved_type:
        meta["type"] = resolved_type
    emotion = entry.emotion or group.emotion
    if emotion:
        meta["emotion"] = "|".join(emotion)
    if entry.status:
        meta["status"] = entry.status
    width = effective_max_width(entry, group)
    if width is not None:
        meta["max-width"] = str(width)
    if entry.reference:
        meta["reference"] = "|".join(entry.reference)
    if entry.reviewer:
        meta["reviewer"] = entry.reviewer
    context = effective_context(entry, group)
    if context:
        meta["context"] = context
    return meta


def _description(meta: dict[str, str]) -> str:
    """Render metadata as a single human-readable description string."""
    context = meta.get("context", "")
    parts = [f"{META_PREFIX}{key}: {value}" for key, value in meta.items() if key != "context"]
    joined = " | ".join(parts)
    if context and joined:
        return f"{context} | {joined}"
    return context or joined


def _parse_description(text: str) -> dict[str, str]:
    """Recover the metadata dictionary from a description string."""
    meta: dict[str, str] = {}
    context_parts: list[str] = []
    for chunk in text.split("|"):
        piece = chunk.strip()
        if not piece:
            continue
        if piece.startswith(META_PREFIX):
            key, _, value = piece[len(META_PREFIX) :].partition(":")
            meta[key.strip()] = value.strip()
        else:
            context_parts.append(piece)
    if context_parts:
        meta.setdefault("context", " ".join(context_parts))
    return meta


def _flat_key(group: Group, entry: Entry) -> str:
    return f"{group.path}.{entry.id}" if group.path else entry.id


def render_json_plain(document: ClifDocument, *, with_context: bool) -> str:
    """Serialize to a plain i18n JSON resource."""
    ensure_clif_format()
    if with_context:
        flat: dict[str, Any] = {}
        for group in document.groups:
            for entry in group.entries:
                meta = entry_metadata(group, entry, include_source=False)
                payload: dict[str, str] = {"message": entry.target or entry.source or ""}
                description = _description(meta)
                if description:
                    payload["description"] = description
                flat[_flat_key(group, entry)] = payload
        return json.dumps(flat, ensure_ascii=False, indent=2) + "\n"

    nested: dict[str, Any] = {}
    for group in document.groups:
        bucket = nested
        for segment in (group.path.split(".") if group.path else []):
            bucket = bucket.setdefault(segment, {})
        for entry in group.entries:
            bucket[entry.id] = entry.target or entry.source or ""
    return json.dumps(nested, ensure_ascii=False, indent=2) + "\n"


def render_yaml_plain(document: ClifDocument, *, with_context: bool) -> str:
    """Serialize to a plain YAML resource, with metadata in comments."""
    ensure_clif_format()
    lines: list[str] = []
    for group in document.groups:
        for entry in group.entries:
            if with_context:
                meta = entry_metadata(group, entry, include_source=False)
                context = meta.pop("context", "")
                if context:
                    lines.append(f"# {context}")
                for key, value in meta.items():
                    lines.append(f"# {META_PREFIX}{key}: {value}")
            value_text = entry.target or entry.source or ""
            lines.append(f"{_flat_key(group, entry)}: {json.dumps(value_text, ensure_ascii=False)}")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _document_from_items(
    items: list[tuple[str, str, dict[str, str]]],
    *,
    namespace: str,
    clan: str,
) -> ClifDocument:
    """Build a CLIF document from (flat key, value, metadata) triples."""
    ensure_clif_format()
    from clif_format import ClifDocument, Entry, Group, Header

    document = ClifDocument(header=Header(namespace=namespace, clan=clan))
    groups: dict[str, Group] = {}
    for flat_key, value, meta in items:
        path, _, entry_id = flat_key.rpartition(".")
        path = path or "imported"
        group = groups.get(path)
        if group is None:
            group = Group(path=path)
            groups[path] = group
            document.groups.append(group)
        width = meta.get("max-width")
        emotion = [tag for tag in meta.get("emotion", "").split("|") if tag]
        reference = [ref for ref in meta.get("reference", "").split("|") if ref]
        group.entries.append(
            Entry(
                id=entry_id or flat_key,
                source=meta.get("source") or value,
                target=value or None,
                type=meta.get("type"),
                emotion=emotion,
                status=meta.get("status") or ("translated" if value else "initial"),
                context=meta.get("context"),
                max_width=int(width) if width and width.isdigit() else None,
                reference=reference,
                reviewer=meta.get("reviewer"),
            )
        )
    return document


def parse_json_plain(text: str, *, namespace: str = "json", clan: str = "imported") -> ClifDocument:
    """Read either plain dialect (nested strings or message/description objects)."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("plain JSON root must be an object")

    items: list[tuple[str, str, dict[str, str]]] = []

    def walk(node: dict[str, Any], prefix: str) -> None:
        for key, value in node.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                items.append((full, value, {}))
            elif isinstance(value, dict) and "message" in value:
                message = value.get("message")
                description = value.get("description", "")
                items.append(
                    (
                        full,
                        message if isinstance(message, str) else "",
                        _parse_description(description) if isinstance(description, str) else {},
                    )
                )
            elif isinstance(value, dict):
                walk(value, full)
    walk(data, "")
    return _document_from_items(items, namespace=namespace, clan=clan)


def parse_yaml_plain(text: str, *, namespace: str = "yaml", clan: str = "imported") -> ClifDocument:
    """Read the plain YAML dialect, recovering metadata from comments."""
    items: list[tuple[str, str, dict[str, str]]] = []
    pending_context: list[str] = []
    pending_meta: dict[str, str] = {}
    for raw_line in text.split("\n"):
        comment = _COMMENT_RE.match(raw_line)
        if comment:
            body = comment.group(1).strip()
            if body.startswith(META_PREFIX):
                key, _, value = body[len(META_PREFIX) :].partition(":")
                pending_meta[key.strip()] = value.strip()
            elif body:
                pending_context.append(body)
            continue
        if not raw_line.strip():
            continue
        match = _YAML_KEY_RE.match(raw_line)
        if not match:
            continue
        key, raw_value = match.group(1), match.group(2).strip()
        if raw_value.startswith('"'):
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                value = raw_value.strip('"')
        else:
            value = raw_value
        meta = dict(pending_meta)
        if pending_context:
            meta.setdefault("context", " ".join(pending_context))
        items.append((key, value, meta))
        pending_context = []
        pending_meta = {}
    return _document_from_items(items, namespace=namespace, clan=clan)
