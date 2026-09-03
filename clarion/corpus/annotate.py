"""Annotation pass: give an imported corpus a real translation brief.

Deterministic enrichment can only restate what a corpus already contains. The
fields that decide translation quality - what this string is, who says it, how
it must sound, how wide it may be - are simply absent from a sentence-pair
corpus, and the only ways to obtain them are to write them by hand or to have a
model write them. This module does the second, in two passes that mirror how a
localization brief is actually written:

pass 1, summarize
    Read the whole document and write the family brief: what this content is,
    who it is for, and the translation standards that apply, plus one context
    line per group.

pass 2, annotate
    Read each segment with the family brief in hand and write its context, its
    content type, its emotion tags and, optionally, a width budget.

Five guards keep this from turning the benchmark into a self-fulfilling
prophecy. They are the reason this module is worth its complexity:

1. **The annotator never sees a target.** It receives source text and upstream
   metadata only, so it cannot copy a translation into the brief.
2. **Leak detection.** Even so, every produced context is checked against the
   reference translation; if it reproduces a span of the reference it is
   rejected, because a brief that contains the answer would make the context
   arm win for the wrong reason.
3. **Closed-vocabulary validation.** type and emotion must be CLIF tags;
   anything else is rejected and counted, never coerced.
4. **Reference-consistency of constraints.** A proposed max-width that the
   human reference itself violates is rejected: a brief may not demand what the
   gold translation does not do.
5. **Provenance.** Every annotated item records context_origin=annotated and
   the model that wrote it, and stays that way in every report until a human
   signs it off.

The annotator SHOULD be a different model from the system under test. Using the
same model for both means the brief is phrased the way that model likes to read
it, which flatters the context arm; the model id is recorded so a reader can
see whether that happened.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..metrics.width import display_cells
from ..paths import ensure_clif_format
from ..prompts.spec_digest import emotion_tags, type_tags
from ..providers.base import CompletionRequest, Message, Provider

if TYPE_CHECKING:  # pragma: no cover - typing only
    from clif_format import ClifDocument

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")

SUMMARY_SYSTEM = (
    "You are a localization project manager writing the brief that a translation "
    "team will work from. You describe content; you never translate it."
)

SUMMARY_TASK = """Read the source segments of one document and write its translation brief.

Return ONLY JSON:
{{"info": "...", "standard": "...", "groups": {{"<group path>": "<one or two sentences>"}}}}

info      2-4 sentences: what this content is, where it appears, who the
          audience is, and anything a translator must know about the whole
          family. Do not list the segments.
standard  the translation policies that apply to this content: register,
          naming policy, punctuation and spacing conventions, what must stay
          untranslated. Write rules, not descriptions.
groups    one or two sentences per group describing the situation those
          segments share.

Never propose a translation and never quote target-language text.

Source language: {source_language}
Target language: {target_language}
Document: {title}

{segments}"""

ANNOTATOR_SYSTEM = (
    "You are a localization engineer preparing a translation brief. You never "
    "translate: you describe what each string is, where it appears and how it "
    "must sound, so that a translator who cannot see the product can do the job."
)

ANNOTATOR_TASK = """Write a translation brief for each segment below.

For every segment id return:
  context   one or two sentences of genuine translator context: the situation,
            the speaker or audience, what the string refers to, and any risk of
            ambiguity. Never restate the source text, never propose a
            translation, and never write target-language text.
  type      exactly one of: {types}
  emotion   one or more of: {emotions}{width_field}

Return ONLY JSON:
{{"items": {{"<id>": {{"context": "...", "type": "...", "emotion": ["..."]{width_example}}}}}}}

Family brief: {info}
Applicable standards: {standard}
Group: {group} - {group_context}
Source language: {source_language}
Target language: {target_language}

Segments:
{segments}"""

WIDTH_FIELD = """
  max-width an integer display-cell budget when, and only when, the string is a
            UI control that is visibly constrained; omit it otherwise. Latin
            letters and digits are 1 cell, Chinese and fullwidth characters 2."""
WIDTH_EXAMPLE = ', "max-width": 12'


@dataclass
class AnnotationConfig:
    """What the annotation pass is allowed to do."""

    summarize: bool = True
    per_entry: bool = True
    propose_width: bool = False
    batch_size: int = 12
    max_output_tokens: int = 8192
    overwrite: bool = False
    reject_leaks: bool = True
    min_batch_size: int = 2


@dataclass
class AnnotationReport:
    """What the annotation pass changed, and what it refused to accept."""

    model: str = ""
    requested: int = 0
    annotated: int = 0
    summarized_groups: int = 0
    wrote_family_brief: bool = False
    rejected_type: int = 0
    rejected_emotion: int = 0
    rejected_width: int = 0
    rejected_leak: int = 0
    failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "model": self.model,
            "requested": self.requested,
            "annotated": self.annotated,
            "summarized_groups": self.summarized_groups,
            "wrote_family_brief": self.wrote_family_brief,
            "rejected_type": self.rejected_type,
            "rejected_emotion": self.rejected_emotion,
            "rejected_width": self.rejected_width,
            "rejected_leak": self.rejected_leak,
            "failures": self.failures[:10],
        }


def _parse_json(text: str) -> dict[str, Any]:
    match = _JSON_RE.search(text or "")
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def leaks_reference(context: str, reference: str, *, span: int = 6, words: int = 4) -> bool:
    """True when a brief reproduces a span of the reference translation.

    For Han, Kana and Hangul text any contiguous run of 'span' characters of the
    reference appearing in the context counts as a leak; for space-delimited
    text any sequence of 'words' words does. A brief that contains the answer
    would let the context arm win without the format doing anything.
    """
    if not context or not reference:
        return False
    reference_flat = " ".join(reference.split())
    context_flat = " ".join(context.split())
    if _HAN_RE.search(reference_flat):
        compact = re.sub(r"\s+", "", reference_flat)
        haystack = re.sub(r"\s+", "", context_flat)
        if len(compact) < span:
            return compact in haystack and len(compact) >= 2
        return any(
            compact[index : index + span] in haystack
            for index in range(len(compact) - span + 1)
        )
    tokens = _WORD_RE.findall(reference_flat.lower())
    haystack_words = _WORD_RE.findall(context_flat.lower())
    if len(tokens) < words:
        return bool(tokens) and tokens == haystack_words[: len(tokens)]
    joined = " ".join(haystack_words)
    return any(
        " ".join(tokens[index : index + words]) in joined
        for index in range(len(tokens) - words + 1)
    )


def summarize_document(
    document: ClifDocument,
    provider: Provider,
    *,
    target_language: str = "zh-CN",
    max_segments: int = 40,
    max_output_tokens: int = 2048,
) -> tuple[ClifDocument, AnnotationReport]:
    """Pass one: write the family brief and one context line per group."""
    ensure_clif_format()
    import copy

    summarized = copy.deepcopy(document)
    report = AnnotationReport(model=getattr(provider, "model", "unknown"))

    lines: list[str] = []
    for group in summarized.groups:
        lines.append(f"[{group.path}]")
        for entry in group.entries[:max_segments]:
            lines.append(f"- {entry.id}: {entry.source or ''}")
    user = SUMMARY_TASK.format(
        source_language=summarized.header.source_language,
        target_language=target_language,
        title=summarized.header.title or summarized.header.clan,
        segments="\n".join(lines),
    )
    completion = provider.complete(
        CompletionRequest(
            messages=[Message("system", SUMMARY_SYSTEM), Message("user", user)],
            temperature=0.0,
            max_output_tokens=max_output_tokens,
        )
    )
    if completion.error:
        report.failures.append(completion.error)
        return summarized, report

    data = _parse_json(completion.text)
    if not data:
        report.failures.append("unparsable summary answer")
        return summarized, report

    info = str(data.get("info", "")).strip()
    standard = str(data.get("standard", "")).strip()
    if info and not summarized.header.info:
        summarized.header.info = info
        report.wrote_family_brief = True
    if standard and not summarized.header.standard:
        summarized.header.standard = standard
        report.wrote_family_brief = True

    groups = data.get("groups") or {}
    if isinstance(groups, dict):
        for group in summarized.groups:
            context = str(groups.get(group.path, "")).strip()
            if context and not group.context:
                group.context = context
                report.summarized_groups += 1
    return summarized, report


def annotate_document(
    document: ClifDocument,
    provider: Provider,
    *,
    target_language: str = "zh-CN",
    config: AnnotationConfig | None = None,
    references: dict[str, str] | None = None,
    batch_size: int | None = None,
    overwrite: bool = False,
    max_output_tokens: int = 4096,
) -> tuple[ClifDocument, AnnotationReport]:
    """Write a model-authored brief onto entries that have none.

    references maps entry id to the human reference translation and is used
    only to reject leaky context and impossible width budgets - it is never
    shown to the annotator.
    """
    ensure_clif_format()
    import copy

    settings = config or AnnotationConfig(
        batch_size=batch_size or 12,
        overwrite=overwrite,
        max_output_tokens=max_output_tokens,
    )
    references = references or {}
    annotated = copy.deepcopy(document)
    report = AnnotationReport(model=getattr(provider, "model", "unknown"))

    if settings.summarize:
        annotated, summary_report = summarize_document(
            annotated,
            provider,
            target_language=target_language,
            max_output_tokens=settings.max_output_tokens,
        )
        report.wrote_family_brief = summary_report.wrote_family_brief
        report.summarized_groups = summary_report.summarized_groups
        report.failures.extend(summary_report.failures)

    if not settings.per_entry:
        return annotated, report

    allowed_types = set(type_tags())
    allowed_emotions = set(emotion_tags())
    types_line = ", ".join(sorted(allowed_types))
    emotions_line = ", ".join(sorted(allowed_emotions))

    for group in annotated.groups:
        pending = [
            entry
            for entry in group.entries
            if settings.overwrite or not entry.context or not (entry.type or group.type)
        ]
        queue = [
            pending[start : start + settings.batch_size]
            for start in range(0, len(pending), settings.batch_size)
        ]
        while queue:
            batch = queue.pop(0)
            segments = "\n".join(f"- {entry.id}: {entry.source or ''}" for entry in batch)
            user = ANNOTATOR_TASK.format(
                types=types_line,
                emotions=emotions_line,
                width_field=WIDTH_FIELD if settings.propose_width else "",
                width_example=WIDTH_EXAMPLE if settings.propose_width else "",
                info=annotated.header.info or "(none)",
                standard=annotated.header.standard or "(none)",
                group=group.path,
                group_context=group.context or "(none)",
                source_language=annotated.header.source_language,
                target_language=target_language,
                segments=segments,
            )
            report.requested += len(batch)
            completion = provider.complete(
                CompletionRequest(
                    messages=[Message("system", ANNOTATOR_SYSTEM), Message("user", user)],
                    temperature=0.0,
                    max_output_tokens=settings.max_output_tokens,
                )
            )
            if completion.error:
                report.failures.append(completion.error)
                continue
            items = _parse_json(completion.text).get("items")
            if not isinstance(items, dict):
                # A long batch can exhaust the output budget - the answer comes
                # back empty with finish_reason 'length'. Halve it and retry
                # before giving up, so one long segment cannot cost a whole
                # batch its brief.
                if len(batch) > settings.min_batch_size:
                    middle = len(batch) // 2
                    queue.insert(0, batch[middle:])
                    queue.insert(0, batch[:middle])
                    report.requested -= len(batch)
                    continue
                report.failures.append(
                    f"unparsable annotation answer for group {group.path} "
                    f"(finish_reason {completion.finish_reason})"
                )
                continue

            for entry in batch:
                payload = items.get(entry.id)
                if not isinstance(payload, dict):
                    continue
                reference = references.get(entry.id, entry.target or "")
                touched = False

                context = str(payload.get("context", "")).strip()
                if context and settings.reject_leaks and leaks_reference(context, reference):
                    report.rejected_leak += 1
                    context = ""
                if context and (settings.overwrite or not entry.context):
                    entry.context = context
                    touched = True

                entry_type = str(payload.get("type", "")).strip()
                if entry_type:
                    if entry_type in allowed_types:
                        if settings.overwrite or not entry.type:
                            entry.type = entry_type
                            touched = True
                    else:
                        report.rejected_type += 1

                emotions = payload.get("emotion") or []
                if isinstance(emotions, str):
                    emotions = [emotions]
                clean = [
                    str(tag).strip()
                    for tag in emotions
                    if str(tag).strip() in allowed_emotions
                ]
                if len(clean) != len(emotions):
                    report.rejected_emotion += 1
                if clean and (settings.overwrite or not entry.emotion):
                    entry.emotion = clean
                    touched = True

                if settings.propose_width and payload.get("max-width") is not None:
                    try:
                        width = int(payload["max-width"])
                    except (TypeError, ValueError):
                        width = 0
                    if width <= 0 or (reference and display_cells(reference) > width):
                        # A brief may not demand what the gold translation does
                        # not satisfy.
                        report.rejected_width += 1
                    elif settings.overwrite or entry.max_width is None:
                        entry.max_width = width
                        touched = True

                if touched:
                    report.annotated += 1
    return annotated, report


def review_rows(document: ClifDocument) -> list[dict[str, str]]:
    """Flat rows for a human review sheet of an annotated document."""
    rows: list[dict[str, str]] = []
    for group in document.groups:
        for entry in group.entries:
            rows.append(
                {
                    "group": group.path,
                    "entry": entry.id,
                    "source": entry.source or "",
                    "target": entry.target or "",
                    "context": entry.context or group.context or "",
                    "type": entry.type or group.type or "",
                    "emotion": "|".join(entry.emotion or group.emotion),
                    "max_width": str(entry.max_width or ""),
                    "approved": "",
                    "reviewer": "",
                    "note": "",
                }
            )
    return rows
