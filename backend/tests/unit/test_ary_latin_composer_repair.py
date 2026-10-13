"""ary/latin gets one extra repair attempt for recoverable rendering defects.

Every other locale keeps two attempts, the guards are unchanged, and the safe
business_answer degradation stays the last resort.
"""

import pytest

from app.graph.final_response_composer import (
    ARY_LATIN_MAX_ATTEMPTS,
    DEFAULT_MAX_ATTEMPTS,
    FinalResponseCompositionError,
    MultilingualFinalResponseComposer,
    rejected_validation_reasons,
)

SOURCE = (
    "Le dividende est la rémunération versée aux actionnaires. "
    "Le montant est fixé par l'assemblée générale."
)
VALID_ARY_LATIN = (
    "Dividende howa rémunération kattsref l actionnaires. "
    "Montant kat7eddedo assemblée générale dyal actionnaires."
)
ARABIC_RESIDUE = (
    "Dividende howa rémunération kattsref l actionnaires مقابل investissement dyalhom. "
    "Montant kat7eddedo assemblée générale dyal actionnaires."
)
FRENCH_DRAFT = (
    "Le dividende est la rémunération versée aux actionnaires. "
    "Son montant est fixé par l'assemblée générale des actionnaires."
)


class ScriptedClient:
    """Azure stub returning one scripted output per attempt."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.instructions: list[str] = []
        self.payloads: list[str] = []
        self.responses = self

    def create(self, *, model, instructions, input, max_output_tokens):
        del model, max_output_tokens
        self.instructions.append(instructions)
        self.payloads.append(input)
        value = self.outputs.pop(0)
        if isinstance(value, Exception):
            raise value
        return type("Response", (), {"output_text": value, "status": "completed"})()


def _composer(outputs, settings):
    return MultilingualFinalResponseComposer(
        settings=settings, client=ScriptedClient(outputs), debug_validation=True
    )


@pytest.fixture
def settings():
    from app.config import Settings

    return Settings(
        _env_file=None,
        AZURE_OPENAI_API_KEY="k",
        AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com",
        AZURE_OPENAI_DEPLOYMENT="gpt-5.6-sol",
    )


def test_valid_ary_latin_is_accepted_on_the_first_attempt(settings):
    composer = _composer([VALID_ARY_LATIN], settings)

    answer = composer.compose(SOURCE, "ary", "latin")

    assert answer == VALID_ARY_LATIN
    assert len(composer.validation_attempts) == 1
    assert composer.validation_attempts[0]["accepted"] is True


def test_arabic_residue_triggers_the_repair_and_yields_latin_only(settings):
    composer = _composer([ARABIC_RESIDUE, VALID_ARY_LATIN], settings)

    answer = composer.compose(SOURCE, "ary", "latin")

    assert answer == VALID_ARY_LATIN
    assert not any("؀" <= character <= "ۿ" for character in answer)
    assert composer.validation_attempts[0]["reasons"] == ["arabic_script_in_latin"]
    # The repair prompt must name the defect and keep the draft as the base.
    repair_prompt = composer._client.instructions[1]
    assert "Arabic-script" in repair_prompt and "Repair the rejected_answer" in repair_prompt
    assert "rejected_answer" in composer._client.payloads[1]


def test_third_attempt_is_allowed_for_ary_latin_when_residue_persists(settings):
    composer = _composer([ARABIC_RESIDUE, ARABIC_RESIDUE, VALID_ARY_LATIN], settings)

    answer = composer.compose(SOURCE, "ary", "latin")

    assert answer == VALID_ARY_LATIN
    assert len(composer.validation_attempts) == ARY_LATIN_MAX_ATTEMPTS == 3
    assert [attempt["accepted"] for attempt in composer.validation_attempts] == [
        False,
        False,
        True,
    ]


def test_repaired_answer_preserves_business_meaning_and_guards(settings):
    composer = _composer([ARABIC_RESIDUE, VALID_ARY_LATIN], settings)

    answer = composer.compose(SOURCE, "ary", "latin")

    assert "Dividende" in answer and "assemblée générale" in answer
    assert composer.validation_attempts[-1]["reasons"] == []


def test_french_draft_is_repairable_and_uses_the_third_attempt(settings):
    """A French draft is a language defect: the extra ary/latin repair applies."""
    composer = _composer([FRENCH_DRAFT, FRENCH_DRAFT, VALID_ARY_LATIN], settings)

    answer = composer.compose(SOURCE, "ary", "latin")

    assert answer == VALID_ARY_LATIN
    assert len(composer.validation_attempts) == ARY_LATIN_MAX_ATTEMPTS
    assert composer.validation_attempts[0]["reasons"] == ["wrong_language"]


def test_still_invalid_after_three_attempts_degrades_safely(settings):
    """The caller keeps its business_answer fallback when repair cannot succeed."""
    composer = _composer([FRENCH_DRAFT, FRENCH_DRAFT, FRENCH_DRAFT], settings)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose(SOURCE, "ary", "latin")

    assert len(composer.validation_attempts) == ARY_LATIN_MAX_ATTEMPTS
    assert all(not attempt["accepted"] for attempt in composer.validation_attempts)


def test_content_loss_is_never_granted_an_extra_attempt(settings):
    """Dropping a business number is a content failure, not a rendering defect."""
    source = "Le taux est de 4.5% et la maturité de 2026."
    lossy = "Taux howa 4.5% w maturité dyalo machi mahdouda."
    composer = _composer([lossy, lossy, VALID_ARY_LATIN], settings)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose(source, "ary", "latin")

    assert len(composer.validation_attempts) == DEFAULT_MAX_ATTEMPTS
    assert "number_preservation_failure" in composer.validation_attempts[0]["reasons"]


def test_provider_errors_are_not_retried_beyond_the_default(settings):
    composer = _composer([RuntimeError("azure down"), RuntimeError("azure down")], settings)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose(SOURCE, "ary", "latin")

    assert len(composer.validation_attempts) == DEFAULT_MAX_ATTEMPTS
    assert composer.validation_attempts[-1]["reasons"] == ["provider_error"]


@pytest.mark.parametrize(
    ("language", "script", "bad_draft"),
    [
        ("fr", "latin", "جواب قصير جدا هنا بالعربية"),
        ("en", "latin", "جواب قصير جدا هنا بالعربية"),
        ("ar", "arabic", FRENCH_DRAFT),
        ("ary", "arabic", FRENCH_DRAFT),
    ],
)
def test_other_locales_keep_exactly_two_attempts(settings, language, script, bad_draft):
    composer = _composer([bad_draft, bad_draft, VALID_ARY_LATIN], settings)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose(SOURCE, language, script)

    assert len(composer.validation_attempts) == DEFAULT_MAX_ATTEMPTS == 2


def test_rejected_validation_reasons_is_ordered_deduplicated_and_tolerant():
    attempts = [
        {"accepted": False, "reasons": ["arabic_script_in_latin", "wrong_language"]},
        {"accepted": False, "reasons": ["arabic_script_in_latin"]},
        {"accepted": True, "reasons": []},
    ]

    assert rejected_validation_reasons(attempts) == ["arabic_script_in_latin", "wrong_language"]
    assert rejected_validation_reasons([]) == []
    assert rejected_validation_reasons(None) == []
    assert rejected_validation_reasons([{}, "not-a-dict", {"accepted": False}]) == []
