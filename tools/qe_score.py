"""Score stored CLARION answers with MetricX-23-QE (reference-free, Apache-2.0).

Usage:
    python tools/qe_score.py <results-run-dir> [--limit N] [--batch N]

Writes <run-dir>/qe_scores.jsonl (one line per scored segment) and
<run-dir>/qe_summary.json (per format/arm aggregate). No reference
translation is used anywhere: this is the WMT-QE style measurement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # clif-test/
CLIF_SRC = ROOT.parent / "clif-python" / "src"
QEDEPS1 = ROOT.parent / ".qe-deps"
QEDEPS2 = ROOT.parent / ".qe-deps2"
QEDEPS = QEDEPS2

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CLIF_SRC))
sys.path.insert(0, str(QEDEPS1))
sys.path.insert(0, str(QEDEPS2))

import torch  # noqa: E402
from transformers import AutoModelForSeq2SeqLM, T5Tokenizer  # noqa: E402

from clarion.formats.parse import parse_back  # noqa: E402

MODEL_DIR = QEDEPS / "metricx23qe"
LABEL_ID = 250089     # <extra_id_10>
MAX_LEN = int(__import__("os").environ.get("QE_MAX_LEN", "512"))


def corpus_sources(core: Path) -> dict[str, dict[str, str]]:
    out = {}
    for p in sorted(core.rglob("*.clif")):
        if "glossary" in p.stem:
            continue
        import clif_format
        doc = clif_format.parse(p.read_text(encoding="utf-8"))
        sources = {}
        for g in doc.groups:
            for e in g.entries:
                sources[e.id] = e.source or ""
        out[p.stem.split(".")[0]] = sources
    return out


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: python tools/qe_score.py <results-run-dir> [--limit N] [--batch N]")
    run_dir = Path(args[0])
    limit = None
    batch = 16
    out_name = "qe_scores.jsonl"
    resume = False
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        if a == "--batch" and i + 1 < len(args):
            batch = int(args[i + 1])
        if a == "--out" and i + 1 < len(args):
            out_name = args[i + 1]
        if a == "--resume":
            resume = True

    core = ROOT / "datasets" / "clarion-core"
    done_keys = set()
    if resume:
        rp = run_dir / out_name
        if rp.exists():
            for line in rp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    done_keys.add(f"{rec['file']}|{rec['format']}|{rec['arm']}|{rec['repeat']}|{rec['entry']}")
        print(f"resume: {len(done_keys)} segments already scored", flush=True)
    print("indexing corpus...")
    sources = corpus_sources(core)

    records = [
        json.loads(line)
        for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    translations = [r for r in records if r.get("kind") == "translation"]

    print("loading MetricX-23-QE ...")
    tokenizer = T5Tokenizer.from_pretrained(str(MODEL_DIR), use_fast=False)
    torch.set_num_threads(max(1, min(16, torch.get_num_threads())))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(MODEL_DIR))
    model.eval()

    pairs = []      # dicts with meta + source + hypothesis
    for r in translations:
        ap = r.get("answer_file")
        if not ap:
            continue
        p = run_dir / ap
        if not p.exists():
            continue
        src_map = sources.get(r["file"])
        if not src_map:
            continue
        text = p.read_text(encoding="utf-8")
        outcome = parse_back(text, r["format"])
        if outcome.document is None:
            continue
        for g in outcome.document.groups:
            for e in g.entries:
                if not e.target:
                    continue
                src = src_map.get(e.id, "")
                if not src:
                    continue
                key = f"{r['file']}|{r['format']}|{r['arm']}|{r['repeat']}|{e.id}"
                if resume and key in done_keys:
                    continue
                pairs.append({
                    "file": r["file"],
                    "format": r["format"],
                    "arm": r["arm"],
                    "repeat": r["repeat"],
                    "entry": e.id,
                    "source": src,
                    "hypothesis": e.target,
                })
        if limit and len(pairs) >= limit:
            break
    print(f"segments to score: {len(pairs)}")

    out = open(run_dir / out_name, "a" if resume else "w", encoding="utf-8")
    mem_lines = []
    with torch.no_grad():
        for start in range(0, len(pairs), batch):
            chunk = pairs[start:start + batch]
            texts = ["candidate: " + c["hypothesis"] + " source: " + c["source"] for c in chunk]
            enc = tokenizer(texts, max_length=MAX_LEN, truncation=True, padding=False)
            seqs = [list(ids[:-1]) if len(ids) > 1 else list(ids) for ids in enc["input_ids"]]
            input_ids = torch.nn.utils.rnn.pad_sequence([torch.tensor(s, dtype=torch.long) for s in seqs], batch_first=True, padding_value=0)
            att = (input_ids != 0).long()
            decoder_ids = torch.full((input_ids.size(0), 1), 0, dtype=torch.long)
            outputs = model(input_ids=input_ids, attention_mask=att, decoder_input_ids=decoder_ids)
            preds = torch.clamp(outputs.logits[:, 0, LABEL_ID], 0.0, 25.0).tolist()
            for c, pr in zip(chunk, preds):
                rec = dict(c)
                rec["qe"] = pr
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                mem_lines.append(rec)
            if (start // batch) % 5 == 0:
                print(f"  scored {start + len(chunk)}/{len(pairs)}", flush=True)

    out.close()
    print(f"wrote {out_name} ({len(mem_lines)} scored of {len(pairs)} collected)", flush=True)

    lines = mem_lines
    summary = {}
    for key in sorted({(l["format"], l["arm"]) for l in lines}):
        vals = [l["qe"] for l in lines if (l["format"], l["arm"]) == key]
        summary[f"{key[0]}::{key[1]}"] = {"n": len(vals), "mean_qe": sum(vals) / len(vals)}
    json.dump(summary, open(run_dir / "qe_summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote qe_summary.json")


if __name__ == "__main__":
    main()
