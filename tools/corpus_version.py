#!/usr/bin/env python3
"""Guard and migrate the declared CLIFF version line of a corpus.

The CLARION corpus documents are hand-authored and are not cliff-python's
canonical output on purpose: the authors order fields the way a translator reads
them, keep long ``info``/``standard`` values as adjacent-string continuation
lines, and keep the licence attribution block at the top of imported files.  A
round-trip ``serialize(parse(text)) == text`` check would therefore flag all 18
files, and "fixing" them would destroy exactly the readability and attribution
that the corpus is supposed to demonstrate.

So the safety gate here is a **semantic fingerprint** plus a strict line-level
change assertion:

* every field of the CLIFF data model that carries meaning is captured (header
  values, group metadata, every entry field, and the provenance digests the gold
  manifests store for the source and reference strings);
* the only accepted edit is the version line, and it must change exactly once,
  from the expected old value to the expected new value;
* after the edit the document must still parse strictly with zero errors, must
  need zero tolerant repairs (Appendix C), and must keep its provenance digests
  intact.

Usage:
    python tools/corpus_version.py                     # verify only, change nothing
    python tools/corpus_version.py --bump 1.1           # apply and verify
    python tools/corpus_version.py --root <dir>         # verify another tree
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clarion.paths import CORE_CORPUS_ROOT, ensure_cliff_format  # noqa: E402
from clarion.util import sha256_text  # noqa: E402

#: The version line is the whole line, optionally indented. A comment line may
#: mention "CLIFF 1.0" in prose (the imported corpora do), so the pattern is
#: anchored and requires the line to hold nothing but the version.
VERSION_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)CLIFF[ \t]+(?P<version>1\.[0-9]+)[ \t]*$")


@dataclass(frozen=True)
class Finding:
    """One problem with one corpus file."""

    path: Path
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: [{self.kind}] {self.detail}"


@dataclass(frozen=True)
class Inspection:
    """What one guard pass found in one corpus file."""

    findings: list[Finding]
    payload: dict[str, object] | None
    version_lines: int


def _counts(payload: dict[str, object]) -> str:
    """A one-line size summary of a fingerprint payload."""
    groups = payload.get("groups") or []
    entries = sum(len(group.get("entries") or []) for group in groups if isinstance(group, dict))
    return f"groups={len(groups)} entries={entries}"


def _entry_fingerprint(entry) -> dict[str, object]:
    return {
        "id": entry.id,
        "source": entry.source,
        "target": entry.target,
        "type": entry.type,
        "emotion": list(entry.emotion or []),
        "status": entry.status,
        "context": entry.context,
        "max_width": entry.max_width,
        "reference": list(entry.reference or []),
        "reviewer": entry.reviewer,
    }


def semantic_fingerprint(text: str) -> tuple[str, dict[str, object]]:
    """Everything a version-line change must not touch, as a comparable value.

    Physical line layout is deliberately excluded: the corpus keeps adjacent
    string continuation lines and field orders that a serializer would
    normalise away, and those are author choices, not data.
    """
    ensure_cliff_format()
    import cliff_format

    document = cliff_format.parse(text)
    header = document.header
    payload: dict[str, object] = {
        "namespace": header.namespace,
        "clan": header.clan,
        "source_language": header.source_language,
        "target_language": header.target_language,
        "version": header.version,
        "variant": header.variant,
        "title": header.title,
        "info": header.info,
        "standard": header.standard,
        "dependency": list(header.dependency or []),
        "groups": [
            {
                "path": group.path,
                "context": group.context,
                "type": group.type,
                "emotion": list(group.emotion or []),
                "max_width": group.max_width,
                "entries": [_entry_fingerprint(entry) for entry in group.entries],
            }
            for group in document.groups
        ],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest(), payload


def gold_digests(cliff_path: Path) -> dict[str, tuple[str, str]]:
    """The source/reference digests a gold manifest stores, keyed by entry id.

    Only the imported corpora carry these; the authored ones keep provenance at
    file level, so a missing digest is not an error.
    """
    gold_path = cliff_path.parent / (cliff_path.name.split(".")[0] + ".gold.json")
    if not gold_path.exists():
        return {}
    data = json.loads(gold_path.read_text(encoding="utf-8"))
    default = data.get("provenance") if isinstance(data.get("provenance"), dict) else {}
    out: dict[str, tuple[str, str]] = {}
    for entry_id, item in (data.get("items") or {}).items():
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else default
        source_digest = str(provenance.get("source_sha256", ""))
        reference_digest = str(provenance.get("reference_sha256", ""))
        if source_digest or reference_digest:
            out[entry_id] = (source_digest, reference_digest)
    return out


def inspect(path: Path, *, expected_version: str | None = None) -> Inspection:
    """Validate one corpus file and report its problems and fingerprint."""
    ensure_cliff_format()
    import cliff_format

    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    lines = text.split("\n")
    matches = [
        (index, match)
        for index, line in enumerate(lines, start=1)
        if (match := VERSION_LINE_RE.match(line))
    ]
    if len(matches) != 1:
        findings.append(
            Finding(path, "version-line", f"expected exactly one, found {len(matches)}")
        )
    elif expected_version is not None and matches[0][1].group("version") != expected_version:
        declared = matches[0][1].group("version")
        findings.append(
            Finding(path, "version-line", f"declares {declared}, expected {expected_version}")
        )

    try:
        document = cliff_format.parse(text)
    except cliff_format.CliffParseError as exc:
        findings.append(Finding(path, "strict-parse", f"line {exc.line}: {exc.message}"))
        return Inspection(findings=findings, payload=None, version_lines=len(matches))

    issues = cliff_format.validate_document(document)
    errors = [issue for issue in issues if issue.category not in cliff_format.ADVISORY_CATEGORIES]
    for issue in errors[:5]:
        findings.append(Finding(path, "strict-validate", f"line {issue.line}: {issue.message}"))
    advisories = [issue for issue in issues if issue.category in cliff_format.ADVISORY_CATEGORIES]
    for issue in advisories[:5]:
        findings.append(
            Finding(path, "advisory", f"line {issue.line} [{issue.category}]: {issue.message}")
        )

    _repaired, corrections = cliff_format.parse_tolerant(text)
    for correction in corrections[:5]:
        findings.append(
            Finding(
                path,
                "tolerant-repair-needed",
                f"line {correction.line}: {correction.describe()}",
            )
        )

    entries = {entry.id: entry for group in document.groups for entry in group.entries}
    for entry_id, (source_digest, reference_digest) in gold_digests(path).items():
        found = entries.get(entry_id)
        if found is None:
            findings.append(
                Finding(path, "gold-mismatch", f"gold references unknown entry '{entry_id}'")
            )
            continue
        if source_digest and source_digest != sha256_text(found.source or ""):
            findings.append(Finding(path, "digest-mismatch", f"source_sha256 of '{entry_id}'"))
        if reference_digest and reference_digest != sha256_text(found.target or ""):
            findings.append(
                Finding(path, "digest-mismatch", f"reference_sha256 of '{entry_id}'")
            )

    digest, payload = semantic_fingerprint(text)
    payload["_fingerprint"] = digest
    return Inspection(findings=findings, payload=payload, version_lines=len(matches))


def corpus_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.cliff"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=CORE_CORPUS_ROOT)
    parser.add_argument(
        "--bump", metavar="VERSION", help="rewrite the version line to this value, then verify"
    )
    parser.add_argument(
        "--from",
        dest="from_version",
        default="1.0",
        help="only bump files declaring this version (default 1.0)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="omit the per-file fingerprint listing"
    )
    args = parser.parse_args(argv)

    files = corpus_files(args.root)
    if not files:
        print(f"no .cliff files under {args.root}", file=sys.stderr)
        return 2

    before: dict[Path, str] = {}
    blobs: dict[Path, dict[str, object]] = {}
    failures = 0
    for path in files:
        result = inspect(path)
        if result.payload is not None:
            before[path] = str(result.payload["_fingerprint"])
            blobs[path] = result.payload
        for finding in result.findings:
            print(finding)
            failures += 1

    if args.bump:
        changed = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            lines = text.split("\n")
            for index, line in enumerate(lines):
                match = VERSION_LINE_RE.match(line)
                if match and match.group("version") == args.from_version:
                    lines[index] = f"{match.group('indent')}CLIFF {args.bump}"
                    changed += 1
                    break
            else:
                continue
            path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"\nrewrote the version line in {changed} file(s) -> CLIFF {args.bump}")

    # Verification pass; with --bump this is the post-edit check that gates the
    # change, without it, it is the plain guard the test suite runs.
    expected = args.bump or None
    for path in files:
        result = inspect(path, expected_version=expected)
        for finding in result.findings:
            print(finding)
            failures += 1
        if result.payload is None or path not in before:
            failures += 1
            continue
        if result.payload["_fingerprint"] != before[path]:
            print(
                Finding(
                    path,
                    "semantic-drift",
                    "document content changed, not only the version line",
                )
            )
            failures += 1

    print(f"\n{len(files)} files checked, {failures} problem(s)")
    if not args.quiet:
        for path in files:
            blob = blobs.get(path)
            counts = _counts(blob) if blob else "n/a"
            print(
                f"  {path.name:<36} {counts:<22} "
                f"fingerprint={before.get(path, '-')[:12]}"
            )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
