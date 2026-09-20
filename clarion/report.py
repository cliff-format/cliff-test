"""Turn evidence records into Markdown reports.

Every table names the tokenizer, the model, the arm and the number of samples
that produced it. A benchmark table without those four facts is decoration, not
evidence.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .metrics.stats import bootstrap_mean
from .util import mean

BASELINE = "cliff"


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def _delta(value: float, baseline: float) -> str:
    if not baseline:
        return "n/a"
    change = 100.0 * (value - baseline) / baseline
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def _table(headers: list[str], rows: list[list[str]], align: str = "left") -> str:
    if not rows:
        return "_no data_\n"
    separator = ["---"] * len(headers)
    if align == "right":
        separator = ["---"] + ["---:"] * (len(headers) - 1)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


@dataclass
class Group:
    """Accumulated records for one (format, arm) cell."""

    format_id: str
    arm: str
    records: list[dict[str, Any]]


def _group(records: list[dict[str, Any]], kind: str) -> dict[tuple[str, str], Group]:
    buckets: dict[tuple[str, str], Group] = {}
    for record in records:
        if record.get("kind") != kind:
            continue
        key = (str(record.get("format")), str(record.get("arm")))
        bucket = buckets.get(key)
        if bucket is None:
            bucket = Group(format_id=key[0], arm=key[1], records=[])
            buckets[key] = bucket
        bucket.records.append(record)
    return buckets


def token_report(rows: list[dict[str, Any]], *, arm: str, title: str) -> str:
    """Dimension 1 or 2: prompt cost per format for one arm."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("kind") == "tokens" and row.get("arm") == arm:
            buckets[str(row["format"])].append(row)
    if not buckets:
        return f"### {title}\n\n_no data_\n"

    tokenizer = next(iter(next(iter(buckets.values()))))
    tokenizer_name = rows[0].get("tokenizer", "unknown") if rows else "unknown"
    del tokenizer

    totals = {
        format_id: {
            "document": sum(int(r["document_tokens"]) for r in items),
            "glossary": sum(int(r["glossary_tokens"]) for r in items),
            "spec": sum(int(r["spec_tokens"]) for r in items),
            "notes": sum(int(r["format_notes_tokens"]) for r in items),
            "prompt": sum(int(r["prompt_tokens"]) for r in items),
            "without": sum(int(r["prompt_tokens_without_format_instructions"]) for r in items),
            "entries": sum(int(r["entries"]) for r in items),
            "files": len(items),
        }
        for format_id, items in buckets.items()
    }
    baseline = totals.get(BASELINE, {}).get("document", 0)
    baseline_prompt = totals.get(BASELINE, {}).get("prompt", 0)

    rows_out: list[list[str]] = []
    for format_id in sorted(totals, key=lambda key: (key != BASELINE, key)):
        data = totals[format_id]
        per_entry = data["document"] / data["entries"] if data["entries"] else 0.0
        rows_out.append(
            [
                format_id,
                str(data["document"]),
                _fmt(per_entry, 1),
                _delta(data["document"], baseline),
                str(data["glossary"]),
                str(data["spec"] + data["notes"]),
                str(data["prompt"]),
                str(data["without"]),
                _delta(data["prompt"], baseline_prompt),
            ]
        )
    headers = [
        "format",
        "document tokens",
        "per entry",
        "vs CLIFF (doc)",
        "glossary tokens",
        "format instructions",
        "prompt total",
        "prompt without format instructions",
        "vs CLIFF (prompt)",
    ]
    note = (
        f"\nTokenizer: {tokenizer_name}. 'format instructions' is the CLIFF specification "
        "digest plus the per-format notes; subtracting it gives the 'without' column, so the "
        "with/without comparison needs no extra model run.\n"
    )
    return f"### {title}\n\n" + _table(headers, rows_out, align="right") + note


def quality_report(records: list[dict[str, Any]], *, arm: str, title: str) -> str:
    """Dimension 3 or 4: quality per format for one arm."""
    buckets = _group(records, "translation")
    selected = {key: value for key, value in buckets.items() if key[1] == arm}
    if not selected:
        return f"### {title}\n\n_no data_\n"

    rows_out: list[list[str]] = []
    order = sorted(selected, key=lambda key: (key[0] != BASELINE, key[0]))
    for key in order:
        items = selected[key].records
        # Two chrF columns, because one number cannot answer two questions.
        # 'chrF (all)' keeps a failed run in as a zero: that is the number a
        # project experiences, and a format that breaks must carry the cost.
        # 'chrF (ok)' averages only the runs that produced a usable file: that
        # is translation quality with format survival factored out. Reporting
        # only the first hides why a format lost; reporting only the second
        # rewards a format for failing.
        chrf = [float(r["quality"].get("chrf", 0.0)) for r in items if r.get("quality")]
        chrf_ok = [
            float(r["quality"].get("chrf", 0.0))
            for r in items
            if r.get("quality") and not r.get("failed")
        ]
        glossaries = sum(1 for r in items if (r.get("glossary") or {}).get("emitted"))
        bleu = [float(r["quality"].get("bleu", 0.0)) for r in items if r.get("quality")]
        ter = [float(r["quality"].get("ter", 0.0)) for r in items if r.get("quality")]
        instruction = [
            float(r["instruction"].get("score", 0.0)) for r in items if r.get("instruction")
        ]
        terminology = [
            float(r["terminology"].get("adherence", 0.0)) for r in items if r.get("terminology")
        ]
        jargon = [float(r["jargon"].get("clean_rate", 0.0)) for r in items if r.get("jargon")]
        coverage = [
            float(r["structure"].get("coverage", 0.0)) * 100 for r in items if r.get("structure")
        ]
        valid = [1.0 if r.get("structure", {}).get("valid") else 0.0 for r in items]
        repairs = [float(r.get("repairs", 0) or 0) for r in items]
        read_modes = sorted({str(r.get("read_mode", "tolerant")) for r in items})
        truncated = [1.0 if r.get("truncated") else 0.0 for r in items]
        failed = [1.0 if r.get("failed") else 0.0 for r in items]
        origins = sorted({str(record.get("context_origin", "original")) for record in items})
        interval = bootstrap_mean(chrf) if len(chrf) >= 5 else None
        ci = f" ({interval.low:.1f}-{interval.high:.1f})" if interval else ""
        rows_out.append(
            [
                key[0],
                "/".join(origins),
                "/".join(read_modes),
                str(len(items)),
                _fmt(mean(chrf)) + ci,
                _fmt(mean(chrf_ok)) if chrf_ok else "n/a",
                _fmt(mean(bleu)),
                _fmt(mean(ter)),
                _fmt(mean(instruction)),
                _fmt(mean(terminology)),
                _fmt(mean(jargon)),
                _fmt(mean(coverage)),
                _fmt(100.0 * mean(valid)),
                _fmt(mean(repairs), 2),
                _fmt(100.0 * mean(failed)),
                _fmt(100.0 * mean(truncated)),
                str(glossaries),
            ]
        )
    headers = [
        "format",
        "context source",
        "read mode",
        "runs",
        "chrF++ (all)",
        "chrF++ (ok)",
        "BLEU",
        "TER (lower better)",
        "instruction %",
        "glossary %",
        "de-jargon %",
        "coverage %",
        "valid answer %",
        "repairs/run",
        "failed %",
        "truncated %",
        "glossaries",
    ]
    note = (
        "\n'chrF++ (all)' scores a failed run as zero, which is what a project would "
        "experience; 'chrF++ (ok)' averages only the runs that produced a usable file, "
        "which is translation quality with format survival factored out. Read them "
        "together: the gap between the two columns IS the cost of format fragility.\n"
        "\n'read mode' is how the answer was read back: 'tolerant' applies the documented "
        "relaxations of CLIFF 1.1 Appendix C, 'strict' is the reference-toolchain reading. "
        "'repairs/run' is the mean number of Appendix C repairs a CLIFF answer needed under "
        "the tolerant reading, so the two readings can be compared instead of confused: the "
        "same answers score 'valid answer %' 100 with repairs and 100 without.\n"
        "\n'glossaries' counts answers that also produced a CLIFF glossary through the "
        "terminology workflow. Those answers are longer by design, so their cost shows "
        "up in the latency and output-token tables; the surface metrics do not credit "
        "them, and a comparison that ignores this understates the format.\n"
        "\n'failed %' counts runs whose answer did not parse, did not validate or lost "
        "entries. A parse error is a failure OF THE FORMAT, not an excluded sample: its "
        "quality scores stay in the average as zeros.\n"
        "\nA non-zero 'truncated %' means answers hit the output ceiling: those runs measure "
        "the token budget, not the format, and the run configuration must be fixed before the "
        "row is read as a result.\n"
        "\n'context source' is where the context payload came from: original (written by "
        "hand with the corpus), native (written by the upstream project), derived (computed "
        "deterministically from corpus metadata) or annotated (written by a model and pending "
        "human sign-off). A context-arm gain measured on annotated context is a weaker claim "
        "than one measured on native context.\n"
    )
    return f"### {title}\n\n" + _table(headers, rows_out, align="right") + note


def latency_report(records: list[dict[str, Any]], *, arm: str, title: str) -> str:
    """Dimension 5 or 6: wall-clock cost per format for one arm."""
    buckets = _group(records, "translation")
    selected = {key: value for key, value in buckets.items() if key[1] == arm}
    if not selected:
        return f"### {title}\n\n_no data_\n"
    rows_out: list[list[str]] = []
    baseline_latency = mean(
        [
            float(record["latency_ms"])
            for key, value in selected.items()
            if key[0] == BASELINE
            for record in value.records
        ]
    )
    for key in sorted(selected, key=lambda key: (key[0] != BASELINE, key[0])):
        items = selected[key].records
        latency = [float(r["latency_ms"]) for r in items]
        output = [float(r["tokens"]["output"]) for r in items]
        entries = [float(r["entries"]) for r in items]
        per_entry = [
            float(r["latency_ms"]) / float(r["entries"]) for r in items if float(r["entries"])
        ]
        rows_out.append(
            [
                key[0],
                str(len(items)),
                _fmt(mean(latency), 0),
                _fmt(mean(per_entry), 1),
                _fmt(mean(output), 0),
                _fmt(mean(entries), 1),
                _delta(mean(latency), baseline_latency),
            ]
        )
    headers = [
        "format",
        "runs",
        "latency ms",
        "ms per entry",
        "output tokens",
        "entries",
        "vs CLIFF",
    ]
    note = (
        "\nLatency is dominated by output tokens and by provider load; it is only comparable "
        "inside one run against one endpoint.\n"
    )
    return f"### {title}\n\n" + _table(headers, rows_out, align="right") + note


def robustness_report(records: list[dict[str, Any]]) -> str:
    """Dimension 7: validity and intent success after model edits."""
    rows = [record for record in records if record.get("kind") == "robustness"]
    if not rows:
        return "### D7 - format validity after model edits\n\n_no data_\n"
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in rows:
        buckets[(str(record["format"]), str(record["arm"]))].append(record)
    rows_out: list[list[str]] = []
    for key in sorted(buckets, key=lambda key: (key[0] != BASELINE, key[0], key[1])):
        items = buckets[key]
        applicable = sum(int(r["edits_applicable"]) for r in items)
        validity = mean([float(r["validity_rate"]) for r in items])
        intent = mean([float(r["intent_rate"]) for r in items])
        outcomes = [outcome for r in items for outcome in (r.get("outcomes") or [])]
        applicable_outcomes = [o for o in outcomes if o.get("applicable")]
        repairs = mean([float(o.get("repairs", 0) or 0) for o in applicable_outcomes])
        read_modes = sorted({str(outcome.get("read_mode", "tolerant")) for outcome in outcomes})
        rows_out.append([
            key[0], key[1], "/".join(read_modes) if read_modes else "-",
            str(applicable), _fmt(validity), _fmt(intent), _fmt(repairs, 2),
        ])
    headers = [
        "format", "arm", "read mode", "applicable edits",
        "still valid %", "intent applied %", "repairs/edit",
    ]
    note = (
        "\nAn edit that a format cannot express is excluded from its denominator and counted "
        "in 'applicable edits', so a format is never penalised for lacking a field, only for "
        "breaking when it has one.\n"
        "\n'read mode' is how the edited file was read back: 'tolerant' applies the documented "
        "relaxations of CLIFF 1.1 Appendix C and 'repairs/edit' is the mean number of repairs "
        "that took. Under 'strict' the same edits are rejected instead of repaired, so the two "
        "readings bracket what a project's own toolchain would do.\n"
    )
    heading = "### D7 - format validity after model edits\n\n"
    return heading + _table(headers, rows_out, "right") + note


def fidelity_report(records: list[dict[str, Any]]) -> str:
    """Round-trip context retention per format."""
    rows = [record for record in records if record.get("kind") == "fidelity"]
    if not rows:
        return "### Round-trip context fidelity\n\n_no data_\n"
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in rows:
        buckets[str(record["format"])].append(record)
    rows_out: list[list[str]] = []
    for format_id in sorted(buckets, key=lambda key: (key != BASELINE, key)):
        items = buckets[format_id]
        retention = mean([float(r["retention"]) for r in items]) * 100.0
        present = sum(int(r["facts_present"]) for r in items)
        kept = sum(int(r["facts_kept"]) for r in items)
        lost_fields: dict[str, int] = defaultdict(int)
        for record in items:
            for field_name, count in (record.get("lost_by_field") or {}).items():
                lost_fields[field_name] += int(count)
        ordered = sorted(lost_fields.items(), key=lambda item: -item[1])[:3]
        worst = ", ".join(f"{name} ({count})" for name, count in ordered)
        rows_out.append([format_id, str(present), str(kept), _fmt(retention), worst or "-"])
    headers = ["format", "context facts", "kept", "retention %", "most lost fields"]
    read_modes = sorted({str(r.get("read_mode", "tolerant")) for r in rows})
    repairs = mean([float(r.get("repairs", 0) or 0) for r in rows])
    note = (
        f"\nRead back in '{'/'.join(read_modes)}' mode; repairs per round trip: {repairs:.2f}. "
        "This direction renders canonical CLIFF with cliff-python itself and reads it back, so "
        "a tolerant read of a format that claims to be lossless must find nothing to repair.\n"
    )
    return "### Round-trip context fidelity\n\n" + _table(headers, rows_out, "right") + note


def build_report(
    *,
    title: str,
    config: dict[str, Any],
    token_rows: list[dict[str, Any]] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> str:
    """Assemble the full Markdown report."""
    token_rows = token_rows or []
    records = records or []
    provider = config.get("provider", {})
    header = [
        f"# {title}",
        "",
        f"- Corpus: {config.get('corpus')}",
        f"- Formats: {', '.join(config.get('formats', []))}",
        f"- Arms: {', '.join(config.get('arms', []))}",
        f"- Tokenizer: {config.get('tokenizer')}",
        f"- Model: {provider.get('kind')}:{provider.get('model')} "
        f"(reasoning {provider.get('reasoning')}, temperature {provider.get('temperature')})",
        f"- CLIFF specification injection: production digest, "
          f"{config.get('spec_location', 'split')}",
        f"- Answer read mode: {config.get('read_mode', 'tolerant')}",
        f"- Repeats per cell: {config.get('repeats')}",
        "",
        "Every arm of every format is generated from the same CLIFF corpus documents through "
        "cliff-python, so a difference between two rows is a property of the format, not of the "
        "fixture.",
        "",
    ]
    sections = [
        token_report(token_rows, arm="bare", title="D1 - token cost, plain formats"),
        token_report(token_rows, arm="context", title="D2 - token cost, context-carrying formats"),
        quality_report(records, arm="bare", title="D3 - quality, plain formats"),
        quality_report(records, arm="context", title="D4 - quality, context-carrying formats"),
        latency_report(records, arm="bare", title="D5 - latency, plain formats"),
        latency_report(records, arm="context", title="D6 - latency, context-carrying formats"),
        robustness_report(records),
        fidelity_report(records),
    ]
    return "\n".join(header) + "\n" + "\n".join(sections)
