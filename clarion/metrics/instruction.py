"""Instruction-following checks - the part of quality a BLEU score cannot see.

A model can produce a fluent sentence and still fail the job: it transliterates
a name the brief said to translate semantically, drops the space between
Chinese and Latin text, overflows a button, rewrites an ICU placeholder, or
renders the same term three different ways. Each of those is machine
checkable, so CLARION checks them as rules attached to corpus items.

Every rule is declarative data (see the gold manifests of CLARION-Core), which
means the same rule set applies to every format arm without change - the point
of the benchmark is that context delivered by a format must actually reach the
model's output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .width import display_cells

CJK_CLASS = (
    "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af"
    "\u3000-\u303f\uff00-\uffef"
)
_CJK_RE = re.compile(f"[{CJK_CLASS}]")
_HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN_RUN = r"[A-Za-z0-9]"
_PUNCT_EXEMPT = set("（）【】《》，。、；：？！“”‘’…—·%°$￥#@/\\|~()[]{}<>,.;:?!\"'")
# An ICU argument is a name directly followed by ',' (a function call such as
# plural or select) or by '}' (a bare placeholder). Literal text inside a
# variant body, such as {No alerts}, is not an argument.
_ICU_ARG_RE = re.compile(r"\{\s*([A-Za-z0-9_$.-]+)\s*(?=[,}])")
_MF2_MARKERS = (".input", ".local", ".match", "{{", "}}")
_PLACEHOLDER_PATTERNS = (
    r"%\d+\$[sdf@]",
    r"%[sdf@]",
    r"\{\d+\}",
    r"\$\{[A-Za-z0-9_.]+\}",
    r"<[a-zA-Z/][^>]*>",
    r"\[\[[^\]]+\]\]",
)


@dataclass(frozen=True)
class Rule:
    """One machine-checkable instruction attached to a corpus item."""

    id: str
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    entry: str | None = None
    severity: str = "error"
    description: str = ""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Rule:
        """Build a rule from its manifest representation."""
        return Rule(
            id=str(data["id"]),
            kind=str(data["kind"]),
            params=dict(data.get("params", {})),
            entry=data.get("entry"),
            severity=str(data.get("severity", "error")),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class RuleResult:
    """Outcome of one rule against one entry."""

    rule_id: str
    kind: str
    entry: str
    passed: bool
    detail: str
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {
            "rule": self.rule_id,
            "kind": self.kind,
            "entry": self.entry,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class RuleContext:
    """Everything a checker may look at."""

    entry_id: str
    source: str
    target: str
    all_sources: dict[str, str]
    all_targets: dict[str, str]
    target_language: str = "zh-CN"
    max_width: int | None = None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _check_require(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    wanted = _as_list(rule.params.get("text") or rule.params.get("texts"))
    if not wanted:
        return True, "no text configured"
    any_of = bool(rule.params.get("any_of", True))
    hits = [item for item in wanted if item in ctx.target]
    if any_of:
        return bool(hits), f"expected one of {wanted}, found {hits or 'none'}"
    missing = [item for item in wanted if item not in ctx.target]
    return not missing, f"missing {missing}" if missing else "all present"


def _check_forbid(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    banned = _as_list(rule.params.get("text") or rule.params.get("texts"))
    hits = [item for item in banned if item in ctx.target]
    return not hits, f"found forbidden {hits}" if hits else "clean"


def _check_term(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    source_term = str(rule.params.get("source", ""))
    if source_term and source_term.lower() not in ctx.source.lower():
        return True, "term not present in source"
    expected = _as_list(rule.params.get("target"))
    forbidden = _as_list(rule.params.get("forbidden"))
    bad = [item for item in forbidden if item in ctx.target]
    if bad:
        return False, f"used discouraged rendering {bad}"
    if expected and not any(item in ctx.target for item in expected):
        return False, f"expected one of {expected}"
    return True, "term respected"


def _check_keep_verbatim(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    wanted = _as_list(rule.params.get("text"))
    missing = [item for item in wanted if item not in ctx.target]
    return not missing, f"not kept verbatim: {missing}" if missing else "kept verbatim"


def _check_name_policy(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    expected = _as_list(rule.params.get("expected"))
    rejected = _as_list(rule.params.get("rejected"))
    hit_rejected = [item for item in rejected if item in ctx.target]
    if hit_rejected:
        mode = rule.params.get("mode", "semantic")
        return False, f"used {hit_rejected}, which the {mode} policy rejects"
    if expected and not any(item in ctx.target for item in expected):
        return False, f"expected one of {expected}"
    return True, "name policy respected"


def _check_cjk_latin_space(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    exempt = set(_as_list(rule.params.get("exempt"))) | _PUNCT_EXEMPT
    text = ctx.target
    violations: list[str] = []
    for match in re.finditer(f"[{CJK_CLASS}]{_LATIN_RUN}|{_LATIN_RUN}[{CJK_CLASS}]", text):
        chunk = match.group(0)
        if any(char in exempt for char in chunk):
            continue
        violations.append(chunk)
    return not violations, f"missing space at {violations[:5]}" if violations else "spacing ok"


def _check_punctuation(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    style = str(rule.params.get("style", "fullwidth"))
    halfwidth = set(_as_list(rule.params.get("halfwidth_chars")) or [",", ".", ":", ";", "?", "!"])
    if style != "fullwidth":
        return True, "no fullwidth requirement"
    if not _HAN_RE.search(ctx.target):
        return True, "not a Han-script target"
    stray = [char for char in ctx.target if char in halfwidth]
    # A halfwidth mark inside a Latin run (URLs, version numbers, ICU) is fine.
    real: list[str] = []
    for index, char in enumerate(ctx.target):
        if char not in halfwidth:
            continue
        before = ctx.target[index - 1] if index else ""
        after = ctx.target[index + 1] if index + 1 < len(ctx.target) else ""
        if _CJK_RE.match(before or " ") or _CJK_RE.match(after or " "):
            real.append(char)
    if real:
        return False, f"halfwidth punctuation next to Han text: {real[:5]}"
    return True, f"ok ({len(stray)} halfwidth marks inside Latin runs)"


def _check_no_trailing(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    chars = _as_list(rule.params.get("chars")) or [".", "。", "!", "！"]
    stripped = ctx.target.rstrip()
    if stripped and stripped[-1] in chars:
        return False, f"ends with '{stripped[-1]}'"
    return True, "no trailing punctuation"


def _check_max_width(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    limit = rule.params.get("cells", ctx.max_width)
    if limit is None:
        return True, "no width limit"
    cells = display_cells(ctx.target)
    return cells <= int(limit), f"{cells} cells against a limit of {limit}"


def _icu_signature(text: str) -> tuple[int, int, tuple[str, ...], tuple[str, ...]]:
    args = tuple(sorted(_ICU_ARG_RE.findall(text)))
    markers = tuple(marker for marker in _MF2_MARKERS if marker in text)
    return text.count("{"), text.count("}"), args, markers


def _check_icu(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    if "{" not in ctx.source and "}" not in ctx.source:
        return True, "no ICU payload"
    source_signature = _icu_signature(ctx.source)
    target_signature = _icu_signature(ctx.target)
    if ctx.target.count("{") != ctx.target.count("}"):
        return False, "unbalanced braces in target"
    if source_signature[2] != target_signature[2]:
        return False, f"argument names changed: {source_signature[2]} -> {target_signature[2]}"
    if source_signature[3] != target_signature[3]:
        return False, "MessageFormat dialect markers changed"
    return True, "ICU preserved"


def _check_placeholders(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    patterns = _as_list(rule.params.get("patterns")) or list(_PLACEHOLDER_PATTERNS)
    missing: list[str] = []
    for pattern in patterns:
        source_hits = sorted(re.findall(pattern, ctx.source))
        target_hits = sorted(re.findall(pattern, ctx.target))
        if source_hits != target_hits:
            missing.append(f"{pattern}: {source_hits} -> {target_hits}")
    return not missing, "; ".join(missing) if missing else "placeholders preserved"


def _check_consistency(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    term = str(rule.params.get("source", ""))
    if not term:
        return True, "no term configured"
    renderings: set[str] = set()
    for entry_id, source_text in ctx.all_sources.items():
        if term.lower() not in source_text.lower():
            continue
        target_text = ctx.all_targets.get(entry_id)
        if target_text:
            renderings.add(target_text.strip())
    candidates = _as_list(rule.params.get("target"))
    if candidates:
        used = {c for c in candidates if any(c in t for t in renderings)}
        return len(used) <= 1, f"renderings used: {sorted(used)}"
    return True, f"{len(renderings)} occurrences observed"


def _check_numerals(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    source_numbers = re.findall(r"\d+(?:[.,]\d+)*", ctx.source)
    missing = [number for number in source_numbers if number not in ctx.target]
    return not missing, f"missing numbers {missing}" if missing else "numbers preserved"


def _check_length_ratio(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    if not ctx.source:
        return True, "no source"
    ratio = len(ctx.target) / len(ctx.source)
    low = float(rule.params.get("min", 0.2))
    high = float(rule.params.get("max", 3.0))
    return low <= ratio <= high, f"length ratio {ratio:.2f} (allowed {low}-{high})"


def _check_regex(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    pattern = str(rule.params.get("pattern", ""))
    if not pattern:
        return True, "no pattern"
    flags = re.IGNORECASE if rule.params.get("ignore_case") else 0
    found = re.search(pattern, ctx.target, flags) is not None
    mode = str(rule.params.get("mode", "match"))
    if mode == "forbid":
        return not found, "pattern found" if found else "pattern absent"
    return found, "pattern matched" if found else "pattern not matched"


def _check_translated(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    if not ctx.target.strip():
        return False, "empty target"
    if ctx.target.strip() == ctx.source.strip():
        allowed = _as_list(rule.params.get("allow_identical"))
        if ctx.source.strip() in allowed:
            return True, "identical by policy"
        return False, "target is a copy of the source"
    return True, "translated"


def _check_script(rule: Rule, ctx: RuleContext) -> tuple[bool, str]:
    script = str(rule.params.get("script", "Han"))
    if script != "Han":
        return True, f"unsupported script check '{script}'"
    minimum = float(rule.params.get("min_ratio", 0.3))
    if not ctx.target:
        return False, "empty target"
    han = len(_HAN_RE.findall(ctx.target))
    ratio = han / max(1, len(ctx.target.replace(" ", "")))
    return ratio >= minimum, f"Han ratio {ratio:.2f} (minimum {minimum})"


CHECKERS = {
    "require": _check_require,
    "forbid": _check_forbid,
    "term": _check_term,
    "keep-verbatim": _check_keep_verbatim,
    "name-policy": _check_name_policy,
    "cjk-latin-space": _check_cjk_latin_space,
    "punctuation": _check_punctuation,
    "no-trailing-punctuation": _check_no_trailing,
    "max-width": _check_max_width,
    "icu-preserve": _check_icu,
    "placeholder-preserve": _check_placeholders,
    "consistency": _check_consistency,
    "numerals": _check_numerals,
    "length-ratio": _check_length_ratio,
    "regex": _check_regex,
    "translated": _check_translated,
    "script": _check_script,
}


def rule_kinds() -> list[str]:
    """All supported rule kinds."""
    return sorted(CHECKERS)


def check_rules(
    rules: list[Rule],
    sources: dict[str, str],
    targets: dict[str, str],
    *,
    target_language: str = "zh-CN",
    widths: dict[str, int] | None = None,
) -> list[RuleResult]:
    """Run every rule against the entries it applies to."""
    widths = widths or {}
    results: list[RuleResult] = []
    for rule in rules:
        entry_ids = [rule.entry] if rule.entry else sorted(sources)
        for entry_id in entry_ids:
            if entry_id not in sources:
                continue
            target_text = targets.get(entry_id)
            if target_text is None:
                results.append(
                    RuleResult(
                        rule_id=rule.id,
                        kind=rule.kind,
                        entry=entry_id,
                        passed=False,
                        detail="entry missing from the answer",
                        severity=rule.severity,
                    )
                )
                continue
            checker = CHECKERS.get(rule.kind)
            if checker is None:
                results.append(
                    RuleResult(
                        rule_id=rule.id,
                        kind=rule.kind,
                        entry=entry_id,
                        passed=True,
                        detail=f"unknown rule kind '{rule.kind}' ignored",
                        severity="warning",
                    )
                )
                continue
            ctx = RuleContext(
                entry_id=entry_id,
                source=sources[entry_id],
                target=target_text,
                all_sources=sources,
                all_targets=targets,
                target_language=target_language,
                max_width=widths.get(entry_id),
            )
            passed, detail = checker(rule, ctx)
            results.append(
                RuleResult(
                    rule_id=rule.id,
                    kind=rule.kind,
                    entry=entry_id,
                    passed=passed,
                    detail=detail,
                    severity=rule.severity,
                )
            )
    return results


def instruction_score(results: list[RuleResult]) -> float:
    """Share of error-severity rule checks that passed, as a percentage."""
    hard = [result for result in results if result.severity == "error"]
    if not hard:
        return 100.0
    return 100.0 * sum(1 for result in hard if result.passed) / len(hard)
