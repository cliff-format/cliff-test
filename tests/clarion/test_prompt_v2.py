"""The example-driven CLIFF prompt states only facts the implementation enforces.

The redesigned prompt claims to list exactly the legal key names per scope and the
complete closed vocabularies. If any claim drifts from `cliff_format`, the prompt
teaches a model to write files no validator accepts - and, because Appendix C.5
forbids repairing an unknown key, that the tolerant reader will not save either.
So the claims are checked against the implementation rather than reviewed by eye.

The second half of the module asserts the *scope* of what the prompt states: the
shape deviations a tolerant reader repairs (quoted tags, bare list scalars, quoted
entry ids, repeated fields, version-line spelling, identifier normalization) are
deliberately NOT stated, because the probe in `.tools/probe_repairs.py` shows they
cost a repair instead of causing a failure. Stating them would spend prompt tokens
on something the reader already handles, so their absence is a property to
protect, not an omission to fix.
"""

from __future__ import annotations

import pytest
from clarion.prompts import cliff_prompt_v2 as v2

RENDERED = f"{v2.CLIFF_FACTS}\n{v2.CLIFF_TASK_RULES}\n{v2.EXAMPLES}"


def test_key_names_and_scopes_match_the_parser() -> None:
    """Each scope lists exactly the keys the parser accepts there."""
    from cliff_format.parser import ENTRY_KEYS, GROUP_KEYS, HEADER_KEYS

    expected = {
        "header": set(HEADER_KEYS),
        "group": set(GROUP_KEYS),
        "entry": set(ENTRY_KEYS),
    }
    for scope, keys in expected.items():
        listed = set(v2.KEYS_BY_SCOPE[scope]["required"]) | set(v2.KEYS_BY_SCOPE[scope]["optional"])
        assert listed == keys, (
            f"{scope}: prompt lists {sorted(listed)}, parser accepts {sorted(keys)}"
        )


def test_status_is_not_offered_in_group_scope() -> None:
    """The recorded run's D7 failure: `status` written into a group section.

    Appendix C.5 forbids repairing it, so the prompt must not allow it - this is
    the specific rule the redesign exists to add, asserted so a later edit cannot
    quietly drop it.
    """
    assert "status" not in v2.KEYS_BY_SCOPE["group"]["optional"]
    entry_keys = set(v2.KEYS_BY_SCOPE["entry"]["required"]) | set(
        v2.KEYS_BY_SCOPE["entry"]["optional"]
    )
    assert "status" in entry_keys
    assert "status" in v2.KEYS_BY_SCOPE["entry"]["required"]
    # The prompt must say it in prose too, not only in the table, because the
    # failure it prevents is a model placing the key by intuition.
    flat = " ".join(v2.CLIFF_FACTS.split())
    assert "entry only" in flat
    assert "and nothing else" in flat


def test_required_fields_match_the_specification() -> None:
    """7 requires four header fields; 8 requires source, status and an effective type."""
    assert set(v2.KEYS_BY_SCOPE["header"]["required"]) == {
        "namespace",
        "clan",
        "source-language",
        "target-language",
    }
    entry_required = set(v2.KEYS_BY_SCOPE["entry"]["required"])
    assert entry_required == {"source", "status"}
    # `type` is required as well, but it may be inherited, which is stated in prose
    # because it cannot be expressed as a per-scope set.
    assert "inherited" in v2.CLIFF_FACTS
    assert "type" in v2.KEYS_BY_SCOPE["entry"]["optional"]
    assert "type" in v2.KEYS_BY_SCOPE["group"]["optional"]


@pytest.mark.parametrize("label", ["type", "emotion", "status", "variant"])
def test_closed_vocabularies_are_complete_and_exact(label: str) -> None:
    """Each stated vocabulary equals the implementation's set, no more and no less."""
    from cliff_format.vocabulary import EMOTION_TAGS, STATUS_TAGS, TYPE_TAGS

    expected = {
        "type": set(TYPE_TAGS),
        "emotion": set(EMOTION_TAGS),
        "status": set(STATUS_TAGS),
        "variant": {"standard", "glossary"},
    }[label]
    listed = set(v2.VOCABULARIES[label])
    assert listed == expected, (
        f"{label}: prompt has {sorted(listed - expected)} extra and "
        f"{sorted(expected - listed)} missing"
    )


def test_every_stated_tag_reaches_the_rendered_prompt() -> None:
    """A vocabulary stored but never rendered would teach nothing."""
    for label, values in v2.VOCABULARIES.items():
        for value in values:
            assert value in RENDERED, f"{label} value '{value}' is not in the prompt text"


def test_the_prompt_does_not_state_what_a_tolerant_read_repairs() -> None:
    """Shape deviations cost a repair, not a failure, so they cost no tokens.

    `.tools/probe_repairs.py` measures the boundary; this test holds the prompt to
    it. The phrases below are the ones a well-meaning edit would add back.
    """
    forbidden = [
        "never quoted",          # C.2.3 quoted tag
        "always brackets",       # C.2.1 bare scalar in a list-typed field
        "not `status: \"final\"`",  # the same rule, spelled out
        "case-sensitive",        # C.2.5 identifier normalization
        "kebab-case",
        "even for a single item",
    ]
    lowered = RENDERED.lower()
    for phrase in forbidden:
        assert phrase.lower() not in lowered, (
            f"the prompt re-states '{phrase}', which a tolerant read repairs; "
            "that costs tokens for something that no longer fails"
        )


def test_examples_are_valid_cliff_and_need_no_repair() -> None:
    """An example that does not validate would teach the wrong shape."""
    cliff_format = pytest.importorskip("cliff_format", reason="cliff-python is not importable")

    documents = [
        block.split("\n", 1)[1]
        for block in v2.EXAMPLES.split("--- ")[1:]
        if block.startswith(("a complete file", "a terminology glossary"))
    ]
    assert len(documents) == 2, "expected the conforming file and the glossary example"
    for text in documents:
        document = cliff_format.parse(text.strip())
        errors = [
            issue
            for issue in cliff_format.validate_document(document)
            if issue.category not in cliff_format.ADVISORY_CATEGORIES
        ]
        assert not errors, [f"line {i.line}: {i.message}" for i in errors]
        assert not document.corrections, "the examples are the standard; they must be canonical"


def test_examples_demonstrate_the_constructs_the_spec_has() -> None:
    """The examples are the teaching device, so they must cover the constructs.

    Each item below is a CLIFF construct that would otherwise be unstated: if the
    examples stop showing one, the prompt silently stops teaching it.
    """
    constructs = {
        "version line": "CLIFF 1.1",
        "header field": "namespace:",
        "adjacent string continuation": '"\n  "',
        "section": "\n[video]",
        "nested-capable group path": "[notifications]",
        "group metadata": "max-width: 12",
        "entry marker": "<resolution>",
        "required entry field": "source:",
        "target field": "target:",
        "list-typed field": "emotion: [objective]",
        "quoted list-typed field": 'dependency: ["',
        "ICU payload": "{count, plural,",
        "escaped quote": '\\"',
        "glossary variant": "variant: glossary",
    }
    missing = [name for name, needle in constructs.items() if needle not in v2.EXAMPLES]
    assert not missing, f"the examples stopped demonstrating: {missing}"
