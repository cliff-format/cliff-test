"""Prompt assembly, specification digest and the glossary bootstrap tool."""

from __future__ import annotations

from clarion.config import RunConfig
from clarion.formats import Arm, render
from clarion.metrics.tokens import get_tokenizer
from clarion.prompts import build_grammar_plus, build_translation_prompt, emotion_tags, type_tags
from clarion.tools.glossary import (
    attach_dependency,
    build_glossary_document,
    extract_candidates,
    merge_glossary,
)


def test_no_paragraph_of_the_composed_prompt_is_stated_twice(
    corpus_root, sample_document
) -> None:
    """A composed prompt is read by a model, and a repetition reads as emphasis.

    The deliverable statement used to be both prefixed to the terminology block and
    appended to the task rules, so the shipped `deliverable` style sent the same
    paragraph twice in one message. Every style must state it exactly once; the
    style decides *where*, not *how often*.
    """
    from clarion.corpus.store import load_corpus
    from clarion.metrics.terminology import load_policy
    from clarion.prompts import templates

    corpus = load_corpus("fixture", root=corpus_root)
    corpus_file = corpus.files[0]
    tokenizer = get_tokenizer("o200k_base")
    policy = load_policy("zh-CN")
    document_text = render(corpus_file.document, "cliff", arm=Arm.CONTEXT)

    # The style decides where the deliverable is stated, and `appendix` states it
    # nowhere: only the two styles that promote it say it at all.
    expected_counts = {"appendix": 0, "deliverable": 1, "front": 1}
    for style, expected in expected_counts.items():
        user = build_translation_prompt(
            document_text=document_text,
            format_id="cliff",
            tokenizer=tokenizer,
            source_language="en-US",
            target_language="zh-CN",
            arm="context",
            policy_fragment=policy.prompt_fragment(),
            allow_glossary_output=True,
            workflow_style=style,
            prompt_style="examples",
            document=corpus_file.document,
        ).user
        # Only the instruction part. The split has to use the document block's own
        # header: the phrase "FILE TO TRANSLATE" also appears in task rule 1, so
        # splitting on that cut the instructions off after their first sentence and
        # the assertions below were reading almost nothing.
        instructions = user.split(templates.DOCUMENT_HEADER, 1)[0]
        stated = instructions.count(templates.GLOSSARY_DELIVERABLE)
        assert stated == expected, (
            f"workflow_style={style} states the deliverable {stated} times, expected {expected}"
        )
        paragraphs = [p.strip() for p in instructions.split("\n\n") if len(p.strip()) > 40]
        repeated = [p[:60] for p in paragraphs if paragraphs.count(p) > 1]
        assert repeated == [], f"workflow_style={style} repeats: {sorted(set(repeated))}"


def test_spec_digest_lists_the_closed_vocabularies() -> None:
    assert len(type_tags()) == 26
    assert len(emotion_tags()) == 23
    sheet = build_grammar_plus()
    # The digest injects the *current* specification; the 1.0 files stay as the
    # frozen definition but are not what a prompt should teach.
    assert "CLIFF 1.1" in sheet
    assert "accessibility-cue" in sheet
    assert "nostalgic" in sheet
    assert "initial, translated, reviewed, final" in sheet
    # 1.1's relaxed identifier rule reaches the model, not the 1.0 one.
    assert "lowercase kebab-case and" not in sheet
    assert "case-sensitive" in sheet


def test_prompt_components_are_measured_separately(sample_document) -> None:
    tokenizer = get_tokenizer("o200k_base")
    document_text = render(sample_document, "cliff", arm=Arm.CONTEXT, blank=True)
    bundle = build_translation_prompt(
        document_text=document_text,
        format_id="cliff",
        tokenizer=tokenizer,
        source_language="en-US",
        target_language="zh-CN",
        arm="context",
    )
    ids = {component.id for component in bundle.budget.components}
    assert {"system.role", "task.rules", "format.notes", "spec.digest", "document"} <= ids
    assert bundle.budget.tokens_of("spec.digest") > 100
    assert bundle.tokens_without_format_instructions() < bundle.total_tokens
    assert document_text in bundle.user


def test_non_cliff_formats_get_no_specification_block(sample_document) -> None:
    tokenizer = get_tokenizer("o200k_base")
    document_text = render(sample_document, "po", arm=Arm.BARE, blank=True)
    bundle = build_translation_prompt(
        document_text=document_text,
        format_id="po",
        tokenizer=tokenizer,
        source_language="en-US",
        target_language="zh-CN",
        arm="bare",
    )
    assert bundle.budget.tokens_of("spec.digest") == 0
    assert bundle.budget.tokens_of("format.notes") > 0


def test_d1_d2_price_the_prompt_the_translation_arms_actually_send(
    corpus_root, sample_document
) -> None:
    """D1/D2 claim to cost the prompt a translation run sends - so compare with a run.

    Twice now an argument was in the run's prompt and not in the matrix's:
    ``allow_glossary_output``/``workflow_style`` (the terminology block, worth about
    half the CLIFF row), and later ``prompt_style``. The second one is the reason
    this test no longer rebuilds the prompt itself: a hand-written argument list
    reproduces whatever the code omits, so both sides agreed while the run directory
    named a style neither path used. A recording provider makes the run the source
    of truth, and the assertion on the system message makes the configuration the
    other one.
    """
    from clarion.corpus.store import load_corpus
    from clarion.experiments.translate import run_translation_task
    from clarion.metrics.terminology import load_policy
    from clarion.prompts import cliff_prompt_v2 as v2
    from clarion.runner import token_matrix

    config = RunConfig(
        name="token-parity",
        formats=["cliff"],
        arms=["bare", "context"],
        spec_location="split",
        spec_reference=True,
        include_policy=True,
        allow_glossary_output=True,
        workflow_style="deliverable",
        prompt_style="examples",
    )
    corpus = load_corpus("fixture", root=corpus_root)
    tokenizer = get_tokenizer(config.tokenizer)
    policy = load_policy(config.target_language)

    rows = token_matrix(config, corpus, tokenizer=tokenizer, policy=policy)
    assert rows, "the token matrix produced no rows"

    # Compared against the run, not against a second hand-written argument list.
    # The earlier version of this test rebuilt the bundle itself and therefore
    # reproduced whatever the matrix omitted: both sides left out `prompt_style`, so
    # the numbers agreed while the run directory named a style neither path used. A
    # recording provider makes the run the source of truth.
    import clarion.runner as runner_module
    from clarion.providers.base import Completion, CompletionRequest
    from clarion.providers.mock import MockProvider

    class Recording:
        name = "recording"
        model = "mock-1"

        def __init__(self) -> None:
            self.inner = MockProvider(mode="perfect", model="mock-1")
            self.requests: list[CompletionRequest] = []

        def complete(self, request: CompletionRequest) -> Completion:
            self.requests.append(request)
            return self.inner.complete(request)

    provider = Recording()
    original = runner_module.build_provider
    runner_module.build_provider = lambda _config: provider  # type: ignore[assignment]
    try:
        corpus_file = corpus.files[0]
        result = run_translation_task(
            corpus_file,
            format_id="cliff",
            arm=Arm.CONTEXT,
            provider=provider,
            tokenizer=tokenizer,
            config=config,
            policy=policy,
        )
    finally:
        runner_module.build_provider = original  # type: ignore[assignment]

    matrix_row = next(
        row for row in rows if row["format"] == "cliff" and row["arm"] == "context"
    )
    assert matrix_row["prompt_tokens"] == result.prompt_tokens, (
        "the token matrix and the translation run price different prompts "
        f"({matrix_row['prompt_tokens']} vs {result.prompt_tokens})"
    )
    # And the run reflects the configuration rather than a default: the style the
    # config names must be the style in the system message it actually sends.
    system = provider.requests[-1].messages[0].content
    # The marker is the stated-facts block's own title line, taken from the module so
    # a retitled block cannot leave this assertion pointing at a string that no longer
    # exists (it did: the block was retitled to "KEYS AND THEIR SCOPE" and this test
    # kept asserting the old heading, which meant a dead check rather than a failing
    # one). The assertion below it is the load-bearing one.
    assert v2.CLIFF_FACTS.splitlines()[0] in system, (
        "prompt_style='examples' must reach the system message; the configuration "
        "naming a style is not the same as the run using it"
    )
    assert v2.CLIFF_FACTS in system
    assert "spec.reference" not in system

    # The run keeps the prompt it sent as evidence, and that evidence has to be the
    # whole prompt: for CLIFF the system message is where the field table lives, so a
    # file that holds only the user message cannot show what the prompt said.
    assert result.prompt_text.startswith(system), (
        "the stored prompt must begin with the system message"
    )
    assert "FILE TO TRANSLATE" in result.prompt_text, (
        "the stored prompt must also carry the user message with the document"
    )


def test_glossary_candidates_and_merge(sample_document, sample_glossary) -> None:
    candidates = extract_candidates(sample_document, min_count=1)
    assert candidates
    mined = build_glossary_document(sample_document, candidates)
    assert mined.header.variant == "glossary"
    merged, report = merge_glossary(sample_glossary, mined)
    assert report.added or report.kept
    ids = {entry.id for group in merged.groups for entry in group.entries}
    assert "default" in ids


def test_merge_never_overwrites_locked_terms(sample_glossary) -> None:
    import copy

    mined = copy.deepcopy(sample_glossary)
    for group in mined.groups:
        for entry in group.entries:
            if entry.source == "Default":
                entry.target = "缺省"
    merged, report = merge_glossary(sample_glossary, mined)
    kept = {
        entry.source: entry.target for group in merged.groups for entry in group.entries
    }
    assert kept["Default"] == "默认"
    assert report.conflicts


def test_attach_dependency_is_idempotent(sample_document) -> None:
    once = attach_dependency(sample_document, "glossary.zh-CN.cliff")
    twice = attach_dependency(once, "glossary.zh-CN.cliff")
    assert twice.header.dependency.count("glossary.zh-CN.cliff") == 1


#: What a prompt block is allowed to say: what the format's own specification
#: requires of the file, and what we need back (the translated file). Anything
#: else fences how the model works. Reproducing the file it was given and editing
#: it is a good way to arrive at the answer, so a block may not forbid a method,
#: and a block may not impose a house rule the specification does not have.
#:
#: Each entry is the phrase an edit would add back, and the reason it is not
#: allowed. These are stated as literal phrases rather than as a check for
#: imperative mood, because the fences that were actually there are specific.
METHOD_FENCES: dict[str, str] = {
    "never a diff": "the answer shape stated as a prohibition (was SYSTEM_ROLE)",
    "never a commentary": "the same prohibition, second half (was SYSTEM_ROLE)",
    "hard rules": "our framing of the request as a rule list (was TASK_RULES)",
    "leave the source field untouched": "prohibition where a property will do",
    "in its original order and count": (
        "no specification section requires the entry order to be preserved; that "
        "was our bookkeeping stated as a rule"
    ),
    "keep the glossary concise": "a house cap on the optional glossary",
    "only the renderings that matter": "the same cap, second half",
    "stop after the last needed term": "the same cap, third half (13.2.2 states the criterion)",
}


def test_no_prompt_block_fences_the_working_method() -> None:
    """Constraint comes from the specification and the deliverable, not from us.

    Checked on the blocks themselves rather than on one composed prompt, because
    these templates are shared: SYSTEM_ROLE and TASK_RULES reach all ten formats,
    and the glossary blocks reach every CLIFF run that allows a glossary.

    The scan covers **every** block that can reach a model. It used to hold the
    templates and `cliff_prompt_v2` only, which left two holes: the `spec` style's
    block and the digest style's supplement were both unscanned, and the supplement
    was carrying "Keep the glossary concise." - the exact house cap this table
    forbids - in a prompt no test could see.
    """
    from clarion.prompts import cliff_prompt_v2 as v2
    from clarion.prompts import cliff_rules, spec_digest, templates

    blocks = {
        "SYSTEM_ROLE": templates.SYSTEM_ROLE,
        "TASK_RULES": templates.TASK_RULES,
        "OUTPUT_RULES_BILINGUAL": templates.OUTPUT_RULES_BILINGUAL,
        "OUTPUT_RULES_MONOLINGUAL": templates.OUTPUT_RULES_MONOLINGUAL,
        "CONTEXT_HINT": templates.CONTEXT_HINT,
        "GLOSSARY_DELIVERABLE": templates.GLOSSARY_DELIVERABLE,
        "GLOSSARY_WORKFLOW": templates.GLOSSARY_WORKFLOW,
        "CLIFF_EDIT_SAFETY": templates.CLIFF_EDIT_SAFETY,
        "CLIFF_ANSWER_REMINDER": templates.CLIFF_ANSWER_REMINDER,
        "CLIFF_FACTS": v2.CLIFF_FACTS,
        "CLIFF_TASK_RULES": v2.CLIFF_TASK_RULES,
        "EXAMPLES": v2.EXAMPLES,
        "SPEC_BLOCK": cliff_rules.build_normative_rules(),
        "spec_supplement": spec_digest.spec_supplement(),
        **{f"FORMAT_NOTES[{key}]": value for key, value in templates.FORMAT_NOTES.items()},
    }
    assert all(text.strip() for text in blocks.values()), (
        "a block under test is empty, so its share of this check proves nothing"
    )
    for name, text in blocks.items():
        lowered = text.lower()
        for phrase, why in METHOD_FENCES.items():
            assert phrase not in lowered, f"{name} fences the method: '{phrase}' - {why}"

    # And the other half: the deliverable is still stated, because "state what we
    # need and nothing about the method" is the rule, not "state nothing".
    role = " ".join(templates.SYSTEM_ROLE.split()).lower()
    assert "we need the translated file itself, complete" in role
    assert "the translated file" in " ".join(templates.TASK_RULES.split()).lower()
    # The examples style no longer carries a separate edit-safety reminder, so the
    # glossary workflow is the only place a CLIFF run learns what a glossary is.
    workflow = " ".join(templates.GLOSSARY_WORKFLOW.split())
    assert "Specification 13.2.2 is the criterion" in workflow, (
        "the glossary trigger must cite the specification's own criterion, not a "
        "house rule about how often terminology repeats"
    )


def test_the_answer_boundary_is_stated_in_the_shared_rules() -> None:
    """The deliverable's *extent*, stated affirmatively.

    Three of the five remaining failures in the best CLIFF run were the model
    writing its own notes into the answer - a `{"note": ...}` object, `##### Result
    impossible.`, an entry marker followed by a comment on the corpus - and one was
    an answer that stopped mid-string. All four are the same missing fact: nothing
    said that the answer is the file and only the file. The old prompt said it, in
    two places, and both were removed in one pass: "Your answer is the file that
    appears under FILE TO TRANSLATE..." (shared rules) and "never a diff and never a
    commentary" (system role). The second is a prohibition and stays out; the first
    is the deliverable and belongs in, phrased as what the answer is.
    """
    from clarion.prompts import templates

    rules = " ".join(templates.TASK_RULES.split())
    assert "opening with that file's first line and closing with its last" in rules, (
        "the rules no longer state where the answer begins and ends, and the failure "
        "that follows is the model annotating its own output"
    )
    lowered = rules.lower()
    for prohibition in ("never ", "do not", "cannot", "nothing else"):
        assert prohibition not in lowered, (
            f"the boundary is stated as a prohibition ('{prohibition}') again; state "
            "what the answer is"
        )
    # The CLIFF reminder is in the same message, and it is where this rule is hardest
    # to keep affirmative: it exists because the model closes what it opens, so the
    # sentence that describes the failure is always one edit away. It said "nothing in
    # a CLIFF file is closed" and that half was removed - a prompt that names a
    # failure shape hands the model the shape - leaving the statement of what a marker
    # is and how far it runs.
    reminder = " ".join(templates.CLIFF_ANSWER_REMINDER.split())
    for prohibition in ("never ", "do not", "cannot", "nothing else", "not closed", "is closed"):
        assert prohibition not in reminder.lower(), (
            f"CLIFF_ANSWER_REMINDER names the failure shape ('{prohibition}'); state what a "
            "marker is and how far its fields run"
        )
    assert "stand alone" in reminder and "to the end of the file" in reminder, (
        "the reminder no longer states the marker rule it is injected for"
    )
    # And the CLIFF block says the same thing in the format's own terms: the grammar
    # has one start symbol, and it is what an answer is.
    from clarion.prompts import cliff_rules

    spec = " ".join(cliff_rules.build_normative_rules().split())
    assert "one `cliff-file`, from its version line to its last field" in spec


def test_the_two_rule_lists_in_one_message_have_different_headings() -> None:
    """One message, two numbered lists, and the headings have to tell them apart.

    The shared rules and the CLIFF-specific rules are concatenated into the same
    user message. Both were titled "WHAT WE NEED" for one revision, which reads as
    one list restarted at 1 in the middle rather than as a refinement of it. The
    paragraph-duplication test above cannot see this: it compares paragraphs longer
    than 40 characters and both headings are two words.
    """
    from clarion.prompts import cliff_prompt_v2 as v2
    from clarion.prompts import templates

    shared = templates.TASK_RULES.splitlines()[2].strip()
    cliff = v2.CLIFF_TASK_RULES.splitlines()[0].strip()
    assert shared and cliff
    assert shared != cliff, f"both rule lists are titled '{shared}' in one message"
