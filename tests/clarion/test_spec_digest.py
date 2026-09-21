"""The compressed CLIFF specification: it must be the specification, and only it.

`clarion/prompts/cliff_rules.py` assembles the prompt's `spec` style out of the
specification repository rather than out of prose somebody maintains. Three things
can go wrong with that, and each has a test here:

1. **Drift.** The key tables, the vocabularies and the grammar are read from the
   specification, so they cannot drift *from the document* - but they can drift
   from the implementation that validates the answers. Compared against
   ``cliff_format`` directly.
2. **Silent loss.** A compression pass that drops a normative section looks exactly
   like a compression pass that dropped a rationale section. Every section that
   states a rule must be represented or explicitly excluded with a reason.
3. **Growth.** The whole point is the token cost, so the ceiling is asserted: a
   change that doubles the digest fails here rather than in a paid run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from clarion.metrics.tokens import get_tokenizer
from clarion.paths import SPEC_FILE
from clarion.prompts import cliff_rules

#: The digest is 2 700 tokens today, and the ceiling is a budget rather than a
#: description: it is the point at which this style stops being the cheap one. Four
#: rules were added after the first measurement and each was a *fix* for an observed
#: failure - the escape set (136), the glossary shape and the two-document boundary
#: (180), the single-line marker rule (110) - so the ceiling moved with them,
#: deliberately and in the open. The full specification text is 16 656 tokens and the
#: old hand-written digest was 2 785, which is the comparison that matters.
TOKEN_CEILING = 3_000

RULE_WORDS = re.compile(r"\b(MUST|SHOULD|MAY|REQUIRED)\b")


def test_the_key_tables_are_the_parsers_key_sets() -> None:
    """A key the prompt omits is a key the model has to guess; an extra one is worse."""
    from cliff_format.parser import ENTRY_KEYS, HEADER_KEYS

    header = {key for key, _, _, _ in cliff_rules._table_rows("7")}
    entry = {key for key, _, _, _ in cliff_rules._table_rows("8")}
    assert header == set(HEADER_KEYS), (
        f"prompt header table {sorted(header)} vs parser {sorted(HEADER_KEYS)}"
    )
    assert entry == set(ENTRY_KEYS), (
        f"prompt entry table {sorted(entry)} vs parser {sorted(ENTRY_KEYS)}"
    )


def test_the_group_keys_are_stated_and_status_is_not_one_of_them() -> None:
    """The recorded run's failure: `status` written into a group section."""
    from cliff_format.parser import GROUP_KEYS

    rendered = cliff_rules.field_tables()
    for key in GROUP_KEYS:
        assert key in rendered, f"group key '{key}' is not stated"
    assert "status" not in GROUP_KEYS
    # `status` appears in the entry table, so its scope is stated by position; the
    # group line must not offer it.
    group_line = next(
        line for line in rendered.splitlines() if line.startswith("  context  type")
    )
    assert "status" not in group_line


def test_the_inherited_fields_are_the_ones_section_9_lists() -> None:
    """`type` only was extracted at first, because the flag was found by substring.

    Section 9 says context, type, emotion and max-width inherit; nothing else does.
    """
    inherited = {key for key, _, _, flag in cliff_rules._table_rows("8") if flag == "inherited"}
    assert inherited == {"context", "type", "emotion", "max-width"}
    rendered = cliff_rules.field_tables()
    assert "No other entry field is inherited." in rendered


def test_the_required_fields_match_the_implementation() -> None:
    required = {
        key for key, _, flag, _ in cliff_rules._table_rows("7") if flag == "required"
    }
    assert required == {"namespace", "clan", "source-language", "target-language"}
    entry_required = {
        key for key, _, flag, _ in cliff_rules._table_rows("8") if flag == "required"
    }
    assert entry_required == {"source", "status", "type"}
    # `target` is conditional, and the condition is in the semantic constraints.
    text = cliff_rules.build_normative_rules()
    assert "target is optional and required only for status translated" in text


@pytest.mark.parametrize("label", ["type", "emotion", "status", "variant"])
def test_the_vocabularies_are_the_implementations(label: str) -> None:
    from cliff_format.vocabulary import EMOTION_TAGS, STATUS_TAGS, TYPE_TAGS

    expected = {
        "type": set(TYPE_TAGS),
        "emotion": set(EMOTION_TAGS),
        "status": set(STATUS_TAGS),
        "variant": {"standard", "glossary"},
    }[label]
    text = cliff_rules.build_normative_rules()
    missing = sorted(value for value in expected if value not in text)
    assert missing == [], f"{label}: the digest omits {missing}"


def test_every_normative_section_is_represented_or_excluded_with_a_reason() -> None:
    """The compression pass cannot drop a rule silently.

    Sections that only motivate are marked informative; a section that states a
    rule has to say where the rule went. If the specification grows a section, this
    fails until somebody decides what happens to it.
    """
    text = SPEC_FILE.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        heading = re.match(r"^## (\d+)\.", line)
        appendix = re.match(r"^## Appendix ([A-Z])\.", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
        elif appendix:
            current = appendix.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)

    normative = {
        key for key, body in sections.items() if any(RULE_WORDS.search(line) for line in body)
    }
    uncovered = sorted(normative - set(cliff_rules.SECTION_COVERAGE))
    assert uncovered == [], (
        f"specification section(s) {uncovered} state rules and are not accounted for in "
        "SECTION_COVERAGE; decide whether the digest carries them or why it does not"
    )
    for key, reason in cliff_rules.SECTION_COVERAGE.items():
        assert reason.strip(), f"section {key} has no stated reason"


def test_a_represented_normative_section_really_is_in_the_digest() -> None:
    """The other half: "represented" must mean the text is there."""
    digest = cliff_rules.build_normative_rules()
    # The sections marked as coming from the grammar or the constraints are carried
    # wholesale by those two blocks, so checking the blocks is checking them.
    assert "CLIFF" in digest and "name-char" in digest
    assert "Every key appears at most once per scope" in digest  # section 6.1
    assert "balanced braces" in digest  # section 14
    assert "List-typed fields" in digest and "always written" in digest  # section 6
    assert "resource limits" in digest  # section 19
    assert "variant: glossary" in digest  # section 13
    assert "the specification's own quick example" in digest  # section 3


def test_the_escape_rule_is_stated_as_prose_and_not_only_as_a_production() -> None:
    """The rule the two long-line failures violated, and it was implicit.

    Two answers failed on a missing backslash in a very long value. The `spec` style
    stated the escape set only inside the grammar (`double-escape = "\\" ( DQUOTE /
    "\\" / "n" / "r" / "t" )`), which a model has to notice and apply; hongloumeng
    escaped two of three inner ASCII quotes and sanguo escaped none of two. The
    paragraph is the fix, and it has to name the trap as well: those values mix CJK
    curly quotes (which take no backslash) with ASCII ones (which do).
    """
    digest = cliff_rules.build_normative_rules()
    assert "ESCAPING" in digest
    # The rule is named as a convention the model already has, not spelled out as a
    # list to memorise: that rewording took the three escape failures of the previous
    # cell to zero. Both halves are checked because either alone is not enough - the
    # name gives the prior, the copy sentence stops the model from "tidying up" the
    # backslashes that are already in the file it was given.
    assert "C-style string literal" in digest
    assert "backslashes exactly as written" in digest
    assert "curly quotes" in digest and "no backslash" in digest
    # The escape set is the grammar's, not a wider one a helpful edit might invent.
    for escape in ("\\n", "\\r", "\\t", "\\\\"):
        assert escape in digest


def test_the_two_document_boundary_is_stated_where_the_glossary_is() -> None:
    """The trigger alone produced a Markdown banner and destroyed ten answers.

    Cell A of the glossary ablation (see docs/clarion-prompt-design.md) sent the
    deliverable statement with no shape and no boundary: eleven answers emitted a
    glossary, ten of them introduced by a line like
    `===== OPTIONAL DELIVERABLE: CLIFF GLOSSARY =====`, which the parser reads as an
    invalid field name and which fails the whole answer. A second document is
    recognised by its own version line, so the statement has to say so.
    """
    digest = " ".join(cliff_rules.build_normative_rules().split())
    assert "recognised by its own version line" in digest
    assert "begins with its own CLIFF 1.1 line placed immediately" in digest
    # The shape, so the model does not have to invent the header.
    assert "-terms" in digest and "[terms]" in digest
    assert "13.2.1" in digest and "13.2.2" in digest
    # Stated affirmatively: a sentence that lists what must not be written is a
    # sentence that describes a banner, and a banner is what destroyed ten answers.
    # Scoped to this paragraph: the specification's own constraints carry factual
    # negations ("lists do not merge") that are not fences on how to write.
    boundary = " ".join(digest[digest.find("Two documents are then one answer"):].split())
    for prohibition in ("no heading", "no separator", "do not", "nothing else"):
        assert prohibition not in boundary.lower(), (
            f"the boundary is stated as a prohibition ('{prohibition}'); the failure "
            "mode it is meant to prevent is a separator line, and naming it suggests it"
        )


def test_the_single_line_marker_rule_survives_the_comment_stripping() -> None:
    """`grammar_only()` strips the ABNF comments, and one of them states a rule.

    The ABNF says of `entry-line`: *"single-line marker; no closing tag exists"*. That
    comment is removed with the rest, so the prompt never said it - and three answers
    ended by closing the glossary's section with a line of their own
    (`</terms>`, `</result>`, `</invoke>`), which the tolerant reader then read as an
    entry marker and normalized into an entry the answer does not contain. The rule is
    stated in prose now, affirmatively: what a marker opens runs to the next marker or
    the end of the document.
    """
    digest = " ".join(cliff_rules.build_normative_rules().split())
    assert "SECTIONS AND ENTRIES ARE SINGLE LINES" in digest
    assert "stands alone on its own line" in digest
    assert "runs until the next such line or the end of the document" in digest
    assert "`<` and `>` are ordinary" in digest
    # The stripped comment is why this paragraph exists; the grammar alone must not
    # be carrying the rule, or this test would pass for the wrong reason.
    assert "no closing tag exists" not in digest


def test_the_digest_stays_under_its_token_ceiling() -> None:
    tokenizer = get_tokenizer("o200k_base")
    cost = cliff_rules.normative_rule_tokens(tokenizer)
    assert cost < TOKEN_CEILING, (
        f"the compressed specification is {cost} tokens (ceiling {TOKEN_CEILING}); the "
        "full text is 16 656 and the whole point is the difference"
    )


def test_the_specification_itself_is_not_in_the_digest() -> None:
    """The digest is a compression, not an inclusion: rationale must be gone.

    The ratio is a floor rather than a target. It was 6x when the block was 2 094
    tokens and is 5.9x now: four rules were added, each because an observed failure
    needed it, and the specification grew too. Five is the assertion because it is
    the point below which this stops being a compression at all.
    """
    digest = cliff_rules.build_normative_rules()
    full = SPEC_FILE.read_text(encoding="utf-8")
    assert len(digest) * 5 < len(full), "the digest is not compressed"
    for rationale in (
        "Goals and objectives",
        "Design rationale",
        "Comparison with",
    ):
        assert rationale not in digest, f"rationale survived the compression: {rationale}"


def test_the_extraction_reads_the_specification_not_a_copy() -> None:
    """Guard: a hard-coded table would pass every test above and still go stale."""
    source = (Path(cliff_rules.__file__)).read_text(encoding="utf-8")
    assert "namespace" not in source.replace("``", ""), (
        "the module names keys itself; the tables must be read from the specification"
    )
    assert "read_text(SPEC_FILE)" in source


def test_the_spec_style_carries_the_digest_and_never_the_full_text() -> None:
    """The assembly, not just the module: the full text is 5x the digest.

    The `spec` style exists because the digest is enough; appending the full
    specification as well would cost 16 691 tokens for a second copy of the rules
    the block already states, and the prompt would silently become the most
    expensive of the three.
    """
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts.assembly import build_translation_prompt

    tokenizer = get_tokenizer("o200k_base")
    bundle = build_translation_prompt(
        document_text="CLIFF 1.1\n",
        format_id="cliff",
        tokenizer=tokenizer,
        source_language="en-US",
        target_language="zh-CN",
        arm="bare",
        prompt_style="spec",
    )
    ids = {component.id for component in bundle.budget.components}
    assert "spec.reference" not in ids, "the full specification text reached a spec prompt"
    assert "spec.digest" in ids, "the compressed specification is not in the prompt"
    assert "CLIFF 1.1 - THE SPECIFICATION, COMPRESSED TO ITS RULES" in bundle.system
    assert "--- GRAMMAR ---" in bundle.system
    assert "HEADER FIELDS" in bundle.system and "ENTRY FIELDS" in bundle.system
    assert "variant: glossary" in bundle.system
    assert bundle.total_tokens < 3_600, (
        f"the spec-style prompt is {bundle.total_tokens} tokens; the point of the style "
        "is that the specification costs a few thousand, not twenty"
    )


def test_the_three_styles_are_ordered_by_what_they_carry() -> None:
    """digest > spec > examples, and the two cheap ones differ in kind."""
    from clarion.metrics.tokens import get_tokenizer
    from clarion.prompts.assembly import build_translation_prompt

    tokenizer = get_tokenizer("o200k_base")

    def cost(style: str) -> int:
        return build_translation_prompt(
            document_text="CLIFF 1.1\n",
            format_id="cliff",
            tokenizer=tokenizer,
            source_language="en-US",
            target_language="zh-CN",
            arm="bare",
            prompt_style=style,
        ).total_tokens

    digest, spec, examples = cost("digest"), cost("spec"), cost("examples")
    assert digest > spec > examples, f"digest {digest}, spec {spec}, examples {examples}"
