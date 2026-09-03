"""Publishing imported corpora without breaking their licences.

CLARION is published on GitHub under MIT, but imported corpus text is not ours
to relicense. Three mechanisms keep that straight:

1. **Tier routing.** A recipe's tier decides where its output is written.
   Permissive output goes into the corpus tree; ShareAlike and MPL output goes
   into its own directory with its own LICENSE, because our segmentation is a
   derivative work; anything that may not be redistributed is written to a
   gitignored cache and never committed.
2. **In-file attribution.** Every generated CLIF file starts with comment lines
   naming the upstream project, its licence and the exact revision. CLIF
   comments are inert developer notes, so this cannot leak into a prompt or a
   translation, and a file that travels alone still carries its own licence.
3. **Machine-checkable compliance.** 'clarion corpus license-check' verifies
   that every committed corpus file has a provenance block, a licence, an
   attribution file next to it, and that nothing whose licence forbids
   redistribution ended up inside the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..paths import DATASETS_ROOT
from ..util import load_json, utc_now, write_text

CORE_ROOT = DATASETS_ROOT / "clarion-core"
SHAREALIKE_ROOT = DATASETS_ROOT / "cc-by-sa"
WEAK_COPYLEFT_ROOT = DATASETS_ROOT / "mpl-2.0"
FETCH_CACHE_ROOT = DATASETS_ROOT.parent / ".clarion-cache" / "fetch"
ATTRIBUTION_NAME = "ATTRIBUTION.md"

# SPDX identifiers whose text may sit next to MIT code with attribution only.
PERMISSIVE_SPDX = {"MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "CC0-1.0", "CC-BY-4.0", "CC-BY-3.0"}
# File-level copyleft: publishable, but the files keep their own licence.
WEAK_COPYLEFT_SPDX = {"MPL-2.0"}
# Adaptation-level copyleft: our segmentation inherits ShareAlike.
SHAREALIKE_SPDX = {"CC-BY-SA-4.0", "CC-BY-SA-3.0"}


def tier_root(tier: str, spdx: str) -> Path:
    """Directory a recipe's output belongs in, given its licence tier."""
    if tier == "vendor":
        return WEAK_COPYLEFT_ROOT if spdx in WEAK_COPYLEFT_SPDX else CORE_ROOT
    if tier == "sharealike":
        return SHAREALIKE_ROOT
    return FETCH_CACHE_ROOT


def spdx_header(
    *,
    title: str,
    url: str,
    license_name: str,
    spdx: str,
    revision: str = "",
    retrieved: str = "",
    context_origin: str = "derived",
) -> str:
    """CLIF comment block that travels with a generated corpus file."""
    lines = [
        "# CLARION imported corpus file.",
        f"# Upstream: {title}",
    ]
    if url:
        lines.append(f"# Source: {url}")
    if revision:
        lines.append(f"# Revision: {revision}")
    lines.append(f"# Licence: {license_name}")
    lines.append(f"# SPDX-License-Identifier: {spdx}")
    lines.append(f"# Retrieved: {retrieved or utc_now()}")
    lines.append(f"# Translator context in this file is {context_origin}.")
    lines.append(
        "# These comment lines are attribution metadata, not translator context; "
        "a translator may delete them without losing anything."
    )
    return "\n".join(lines) + "\n"


def attribution_markdown(entries: list[dict[str, str]]) -> str:
    """ATTRIBUTION.md content for one imported directory."""
    lines = [
        "# Attribution",
        "",
        "The CLARION harness is MIT licensed. The corpus files in this directory",
        "are derived from the upstream projects below and remain under their own",
        "licences. Each file repeats its licence in its own header comments, and",
        "the machine-readable record is in the matching gold manifest.",
        "",
        "| File | Upstream | Licence | Revision | Retrieved |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            f"| {entry.get('file', '')} | [{entry.get('title', '')}]({entry.get('url', '')}) "
            f"| {entry.get('license', '')} | {entry.get('revision', '') or '-'} "
            f"| {entry.get('retrieved', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_attribution(directory: Path, entries: list[dict[str, str]]) -> Path:
    """Write or refresh the attribution file of an imported directory."""
    path = directory / ATTRIBUTION_NAME
    existing: list[dict[str, str]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("| ") and not line.startswith("| File") and "---" not in line:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if cells and cells[0] and cells[0] not in {item.get("file") for item in entries}:
                    existing.append(
                        {
                            "file": cells[0],
                            "title": cells[1].split("]")[0].lstrip("["),
                            "url": cells[1].split("(")[-1].rstrip(")") if "(" in cells[1] else "",
                            "license": cells[2] if len(cells) > 2 else "",
                            "revision": cells[3] if len(cells) > 3 else "",
                            "retrieved": cells[4] if len(cells) > 4 else "",
                        }
                    )
    write_text(path, attribution_markdown([*existing, *entries]))
    return path


def write_license_file(
    directory: Path, *, title: str, url: str, license_name: str, spdx: str
) -> Path:
    """LICENSE file for a segregated ShareAlike or MPL directory."""
    path = directory / "LICENSE"
    write_text(
        path,
        f"The corpus files in this directory are derived from {title} ({url}) and are\n"
        f"distributed under {license_name} (SPDX: {spdx}), NOT under the MIT licence of\n"
        "the CLARION harness. Segmenting and reformatting the upstream text is an\n"
        "adaptation, so the derived files keep the upstream terms.\n",
    )
    return path


@dataclass
class ComplianceProblem:
    """One licence-compliance defect found in the dataset tree."""

    path: str
    problem: str

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly record."""
        return {"path": self.path, "problem": self.problem}


def _gold_for(clif_path: Path) -> Path:
    return clif_path.parent / (clif_path.name.split(".")[0] + ".gold.json")


def license_check(root: Path | None = None) -> list[ComplianceProblem]:
    """Verify that everything committed under datasets/ may be committed."""
    base = root or DATASETS_ROOT
    problems: list[ComplianceProblem] = []
    if not base.exists():
        return problems

    for clif_path in sorted(base.rglob("*.clif")):
        relative = clif_path.relative_to(base.parent)
        gold_path = _gold_for(clif_path)
        if not gold_path.exists():
            problems.append(ComplianceProblem(str(relative), "no gold manifest with provenance"))
            continue
        data = load_json(gold_path)
        provenance = data.get("provenance") or {}
        license_name = str(provenance.get("license", "")).strip()
        spdx = str(provenance.get("spdx", "")).strip()
        if not license_name:
            problems.append(ComplianceProblem(str(relative), "provenance has no licence"))
        if not provenance.get("redistributable", False):
            problems.append(
                ComplianceProblem(
                    str(relative),
                    "marked not redistributable but committed under datasets/",
                )
            )
        if spdx in SHAREALIKE_SPDX and SHAREALIKE_ROOT not in clif_path.parents:
            problems.append(
                ComplianceProblem(
                    str(relative),
                    f"ShareAlike licence {spdx} outside datasets/cc-by-sa/",
                )
            )
        if spdx in WEAK_COPYLEFT_SPDX and WEAK_COPYLEFT_ROOT not in clif_path.parents:
            problems.append(
                ComplianceProblem(
                    str(relative),
                    f"file-level copyleft licence {spdx} outside datasets/mpl-2.0/",
                )
            )
        if str(provenance.get("origin", "")) != "original":
            attribution = clif_path.parent / ATTRIBUTION_NAME
            if not attribution.exists():
                problems.append(
                    ComplianceProblem(str(relative), f"imported file without {ATTRIBUTION_NAME}")
                )
            header = clif_path.read_text(encoding="utf-8")[:600]
            if "SPDX-License-Identifier" not in header:
                problems.append(
                    ComplianceProblem(str(relative), "imported file without an SPDX header comment")
                )
    return problems
