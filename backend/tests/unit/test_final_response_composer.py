import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.graph.final_response_composer import (
    GROQ_ARY_LATIN_FALLBACK_INSTRUCTIONS,
    FinalResponseCompositionError,
    MultilingualFinalResponseComposer,
    _negation_markers,
    _retry_prompt,
    _validate_final_answer_result,
    compose_ary_latin_fallback,
    darija_latin_quality_issue,
    normalize_azure_base_url,
)


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def settings() -> Settings:
    return Settings(
        app_env="test",
        azure_openai_endpoint="https://resource.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_deployment="deployment-from-settings",
        azure_final_response_max_output_tokens=4096,
    )


def response(text, status="completed", reason=None):
    return SimpleNamespace(
        output_text=text,
        status=status,
        incomplete_details=SimpleNamespace(reason=reason) if reason else None,
    )


def test_normalize_endpoint_does_not_duplicate_v1_path():
    assert normalize_azure_base_url("https://resource.openai.azure.com") == (
        "https://resource.openai.azure.com/openai/v1/"
    )
    assert normalize_azure_base_url("https://resource.openai.azure.com/openai/v1/") == (
        "https://resource.openai.azure.com/openai/v1/"
    )


@pytest.mark.parametrize(
    ("language", "script", "answer"),
    [
        ("fr", "latin", "La réponse explique une action à 12 euros."),
        ("en", "latin", "The answer explains a stock at 12 euros."),
        ("ar", "arabic", "هذه إجابة تعليمية عن سهم بقيمة 12 يورو."),
    ],
)
def test_composes_non_darija_languages_with_configured_deployment(language, script, answer):
    client = FakeClient([response(answer)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Business answer with 12 euros.", language, script) == answer
    call = client.responses.calls[0]
    assert call["model"] == "deployment-from-settings"
    assert call["max_output_tokens"] == 4096
    payload = json.loads(call["input"])
    assert set(payload) == {"business_answer", "language", "script"}


def test_darija_latin_is_guarded_and_json_output_is_unwrapped():
    answer = "Saham howa wara9a maliya b 12 euro li kat3ni part mn ras lmal dyal charika."
    client = FakeClient([response(f'```json\n{{"answer": {json.dumps(answer)}}}\n```')])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Une action represente 12 euros.", "ary", "latin") == answer


def test_darija_arabic_is_guarded_in_arabic_script():
    answer = "السهم ورقة مالية كتمثل جزء من راس المال ديال الشركة بقيمة 12 يورو."
    client = FakeClient([response(answer)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Une action represente 12 euros.", "ary", "arabic") == answer


@pytest.mark.parametrize(
    "candidate",
    ["l-3a2id dyal l-istitmar", "l2arba7", "l5atar", "l6aman", "l8..."],
)
def test_darija_latin_rejects_phonetic_forbidden_digits(candidate):
    assert darija_latin_quality_issue(candidate) == "phonetic_forbidden_digit"


@pytest.mark.parametrize(
    "candidate",
    ["rendement 4.5%", "f 2026", "10 actions", "OPCVM", "ETF", "ISO 27001"],
)
def test_darija_latin_keeps_business_numbers_and_identifiers(candidate):
    assert darija_latin_quality_issue(candidate) is None


def test_darija_latin_rejects_arabic_unicode_even_when_negation_is_valid():
    candidate = "L'obligation hiya dette. Le rendement \u0645\u0627\u0634\u064a garanti."
    assert darija_latin_quality_issue(candidate) == "arabic_script_in_latin"
    assert "\u0645\u0627\u0634\u064a" in _negation_markers(candidate)


def test_darija_latin_retry_for_arabic_script_preserves_darija_instruction():
    prompt = _retry_prompt("arabic_script_in_latin")

    assert "Moroccan Darija" in prompt
    assert "Latin script" in prompt
    assert "Arabic-script characters" in prompt
    assert "Do not switch the answer to French" in prompt


def test_darija_latin_arabic_script_reason_is_specific_and_rejects_mixed_text():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "hada b l3\u0643\u0633 dyal l'action",
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is False
    assert result.reasons[0] == "arabic_script_in_latin"


def test_real_wrong_language_still_uses_wrong_language_reason():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "This is a bond and its main characteristics are listed here.",
        "fr",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is False
    assert "wrong_language" in result.reasons


def test_darija_latin_valid_answer_still_passes_after_arabic_script_reason_split():
    result = _validate_final_answer_result(
        "Une action represente une part du capital.",
        "Saham kaymattel joz men ras lmal dyal charika.",
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is True


@pytest.mark.parametrize(
    "candidate",
    [
        "L'obligation hiya titre de dette.",
        "Saham kaymattel joz men ras lmal dyal charika.",
    ],
)
def test_ary_latin_semantic_gate_accepts_short_natural_code_switching(candidate):
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        candidate,
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is True


def test_ary_latin_semantic_gate_accepts_structured_financial_code_switching():
    candidate = (
        "L'obligation hiya titre de créance kaykhalli l'investisseur ywlli créancier dyal "
        "l'emetteur.\n\n"
        "- La valeur faciale : hiya lmontant li kayt7seb 3lih remboursement.\n"
        "- Le prix d'émission : howa taman li kattsdar bih l'obligation.\n"
        "- Le taux : y9der ykoun fixe ola variable.\n"
        "- Le rendement : kay3ti fikra 3la ch7al kayrbe7 l'investisseur."
    )
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        candidate,
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is True


@pytest.mark.parametrize(
    "candidate",
    [
        "Une obligation est un titre de dette qui permet à l'investisseur de devenir "
        "créancier de l'emetteur.",
        "Une obligation est un titre de dette, w hiya importante.",
    ],
)
def test_ary_latin_semantic_gate_rejects_french_syntax_with_decorative_darija(candidate):
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        candidate,
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is False
    assert "wrong_language" in result.reasons


def test_ary_latin_semantic_gate_accepts_financial_label_with_darija_explanation():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "- Le prix d'émission : kaymattel taman li kattsdar bih l'obligation.",
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is True


def test_ary_latin_rejects_long_french_final_rewrite_with_one_darija_marker():
    candidate = (
        "IPO kat3ni une introduction en bourse. Cette opération permet à une "
        "entreprise de lever des capitaux et de financer son développement. "
        "Elle améliore aussi sa visibilité auprès des investisseurs."
    )
    result = _validate_final_answer_result(
        "Une introduction en bourse permet à une entreprise de lever des capitaux.",
        candidate,
        "ary",
        "latin",
        {"status": "completed"},
    )
    assert result.accepted is False
    assert "wrong_language" in result.reasons


def test_ary_latin_semantic_gate_rejects_financial_label_with_french_explanation():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "- Le prix d'émission : il représente le prix auquel l'obligation est émise.",
        "ary",
        "latin",
        {"status": "completed"},
    )

    assert result.accepted is False
    assert "wrong_language" in result.reasons


def test_darija_arabic_is_unaffected_by_latin_script_reason_split():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "السند كيمثل دين",
        "ary",
        "arabic",
        {"status": "completed"},
    )

    assert result.accepted is True


def test_darija_arabic_negations_are_detected_without_latin_script_permission():
    assert "\u0645\u0627\u0634\u064a" in _negation_markers(
        "\u0627\u0644\u0631\u0628\u062d \u0645\u0627\u0634\u064a \u0645\u0636\u0645\u0648\u0646"
    )
    assert "\u0645\u0634\u064a" in _negation_markers(
        "\u0627\u0644\u0631\u0628\u062d \u0645\u0634\u064a \u0645\u0636\u0645\u0648\u0646"
    )
    assert "ma" in _negation_markers("rendement ma\u0634\u064a garanti")


def test_ary_latin_negation_preservation_is_separate_from_script_validation():
    result = _validate_final_answer_result(
        "Le rendement n'est pas garanti.",
        "L'obligation hiya dette. Le rendement machi garanti.",
        "ary",
        "latin",
        {"status": "completed"},
    )
    assert result.accepted is True
    assert "critical_negation_loss" not in result.reasons
    assert "wrong_language" not in result.reasons


def test_darija_latin_allows_moderate_arabizi_and_business_values():
    candidate = (
        "L'action kat3tik 7issa dyal capital. Rendement 4.5% f 2026, "
        "OPCVM w ETF kayn 9bel ay qarar."
    )
    assert darija_latin_quality_issue(candidate) is None


def test_darija_latin_rejects_romanized_msa_financial_style():
    assert darija_latin_quality_issue("mostatmir mosdir issdar sanad mouachir") == (
        "romanized_msa_style"
    )


def test_darija_latin_allows_one_technical_word_in_a_natural_answer():
    assert darija_latin_quality_issue(
        "L'obligation hiya sanad dyal dette, w l'investisseur kayfhem chourout dyalha."
    ) is None


def test_darija_latin_rejects_compact_arabizi_without_rejecting_business_numbers():
    assert darija_latin_quality_issue("kat3tik wa7d 7in b7al") == "excessive_arabizi"
    assert darija_latin_quality_issue("mymostatmirrrrr3 words words words words words") == (
        "unreadable_compaction"
    )


def test_darija_latin_prompt_prefers_french_financial_terms_and_readability():
    client = FakeClient(
        [response("Saham howa wara9a maliya b 12 euro li kat3ni part mn ras lmal dyal charika.")]
    )
    composer = MultilingualFinalResponseComposer(settings(), client)

    composer.compose("Une action represente 12 euros.", "ary", "latin")
    instructions = client.responses.calls[0]["instructions"]
    assert "not romanized Modern Standard Arabic" in instructions
    assert "French financial terminology" in instructions
    assert "Do not use phonetic 2, 5, 6 or 8" in instructions


def test_professional_prompt_has_hierarchical_quality_contract():
    client = FakeClient([response("The answer explains a stock at 12 euros.")])
    composer = MultilingualFinalResponseComposer(settings(), client)

    composer.compose("Business answer with 12 euros.", "en", "latin")
    instructions = client.responses.calls[0]["instructions"]
    for section in (
        "ROLE",
        "OBJECTIVE",
        "SOURCE OF TRUTH",
        "RESPONSE STYLE",
        "STRUCTURE",
        "LANGUAGE",
        "LANGUAGE-SPECIFIC RULES",
        "FINANCIAL SAFETY",
        "CONTENT PRESERVATION",
        "OUTPUT CONTRACT",
    ):
        assert section in instructions
    assert "Rewrite for clarity and professionalism. Do not add facts." in instructions
    assert "only factual source of truth" in instructions
    assert "personalized advice" in instructions
    assert "no citations invented by you" in instructions


def test_darija_latin_quality_retry_uses_original_input_and_diagnostic():
    valid = "L'obligation hiya titre dyal dette. L'investisseur kay9red flous l'emetteur."
    client = FakeClient([response("l2arba7"), response(valid)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Une obligation est un titre de dette.", "ary", "latin") == valid
    assert len(client.responses.calls) == 2
    first_payload = json.loads(client.responses.calls[0]["input"])
    retry_payload = json.loads(client.responses.calls[1]["input"])
    assert retry_payload["business_answer"] == first_payload["business_answer"]
    assert retry_payload["rejected_answer"] == "l2arba7"
    assert retry_payload["validation_reasons"] == ["phonetic_forbidden_digit"]
    assert "phonetic_forbidden_digit" in client.responses.calls[1]["instructions"]


def test_wrong_language_retry_repairs_rejected_draft_with_original_source():
    rejected = "L'obligation est un titre de créance qui donne des intérêts à l'investisseur."
    valid = (
        "L'obligation hiya titre de créance. L'investisseur kaywlli créancier dyal "
        "l'emetteur, w kayakhod les coupons 7sab les conditions dyalha."
    )
    source = "Une obligation est un titre de créance et l'investisseur reçoit des intérêts."
    client = FakeClient([response(rejected), response(valid)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose(source, "ary", "latin") == valid
    retry_payload = json.loads(client.responses.calls[1]["input"])
    retry_instructions = client.responses.calls[1]["instructions"]
    assert retry_payload["business_answer"] == source
    assert retry_payload["rejected_answer"] == rejected
    assert "wrong_language" in retry_payload["validation_reasons"]
    assert "Darija syntax, verbs, pronouns and connectors" in retry_instructions
    assert "Repair the rejected_answer draft" in retry_instructions
    assert "authoritative source of facts" in retry_instructions


def test_arabic_script_retry_repairs_rejected_draft():
    rejected = "hada b l3\u0643\u0633 dyal l'action"
    valid = "hada b l3aks dyal l'action"
    client = FakeClient([response(rejected), response(valid)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Une action represente une part du capital.", "ary", "latin") == valid
    retry_payload = json.loads(client.responses.calls[1]["input"])
    retry_instructions = client.responses.calls[1]["instructions"]
    assert retry_payload["rejected_answer"] == rejected
    assert "arabic_script_in_latin" in retry_payload["validation_reasons"]
    assert "Latin script only" in retry_instructions
    assert "remove every Arabic-script character" in retry_instructions


def test_multiple_retry_reasons_combine_darija_and_script_repairs():
    rejected = "L'obligation \u0645\u0627\u0634\u064a garantie pour l'investisseur."
    valid = "L'obligation hiya dette, w rendement machi garanti 7sab chourout dyalha."
    client = FakeClient([response(rejected), response(valid)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Le rendement n'est pas garanti.", "ary", "latin") == valid
    retry_payload = json.loads(client.responses.calls[1]["input"])
    retry_instructions = client.responses.calls[1]["instructions"]
    assert "arabic_script_in_latin" in retry_payload["validation_reasons"]
    assert "wrong_language" in retry_payload["validation_reasons"]
    assert "Latin script only" in retry_instructions
    assert "Darija syntax, verbs, pronouns and connectors" in retry_instructions


def test_structured_answer_preserves_list_numbers_percentage_and_acronym():
    source = (
        "1. A stock can be worth 12 euros.\n"
        "2. A 4.5% return is not guaranteed.\n"
        "3. An OPCVM follows its documented rules.\n"
        "4. The investor must compare the risks.\n"
        "5. Diversification does not remove every loss."
    )
    answer = (
        "1. A stock can be worth 12 euros.\n"
        "2. A 4.5% return is not guaranteed.\n"
        "3. An OPCVM follows its documented rules.\n"
        "4. The investor must compare the risks.\n"
        "5. Diversification does not remove every loss."
    )
    client = FakeClient([response(answer)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose(source, "en", "latin") == answer


def test_empty_output_fails_closed_after_one_retry():
    client = FakeClient([response(""), response("")])
    composer = MultilingualFinalResponseComposer(settings(), client)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose("Business answer.", "en", "latin")
    assert len(client.responses.calls) == 2


def test_truncation_retries_once_from_original_answer():
    answer = "The complete answer explains a stock and preserves 12 euros."
    client = FakeClient(
        [
            response("The answer explains", status="incomplete", reason="max_output_tokens"),
            response(answer),
        ]
    )
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Business answer preserves 12 euros.", "en", "latin") == answer
    assert len(client.responses.calls) == 2


def test_guard_failure_after_one_retry_fails_closed():
    client = FakeClient([response('{"answer":"bad"}'), response('{"answer":"bad"}')])
    composer = MultilingualFinalResponseComposer(settings(), client)

    with pytest.raises(FinalResponseCompositionError):
        composer.compose("Business answer with 12 euros.", "en", "latin")
    assert len(client.responses.calls) == 2


def test_provider_error_retries_once_and_does_not_expose_secrets():
    answer = "The answer explains a stock at 12 euros."
    client = FakeClient([TimeoutError("private provider detail"), response(answer)])
    composer = MultilingualFinalResponseComposer(settings(), client)

    assert composer.compose("Business answer with 12 euros.", "en", "latin") == answer
    assert len(client.responses.calls) == 2


def test_validation_observability_is_structured_and_opt_in():
    client = FakeClient([response("l2arba7"), response("L'obligation hiya dette dyal 12 euros.")])
    composer = MultilingualFinalResponseComposer(settings(), client, debug_validation=True)

    assert composer.compose("Une obligation est une dette de 12 euros.", "ary", "latin")
    first, second = composer.validation_attempts
    assert first["accepted"] is False
    assert "phonetic_forbidden_digit" in first["reasons"]
    assert first["diagnostics"]["phonetic_tokens"] == ["l2arba7"]
    assert first["output"] == "l2arba7"
    assert second["accepted"] is True


def test_validation_observability_does_not_store_output_by_default():
    answer = "The complete answer explains a stock at 12 euros."
    composer = MultilingualFinalResponseComposer(settings(), FakeClient([response(answer)]))

    assert composer.compose("Business answer preserves 12 euros.", "en", "latin") == answer
    assert "output" not in composer.validation_attempts[0]
    assert composer.validation_attempts[0]["diagnostics"]["business_numbers"] == ["12"]


def test_short_financial_code_switching_is_not_rejected_as_wrong_language():
    answer = (
        "Une obligation hiya titre de dette. L'investisseur kay sellef des fonds "
        "l'emetteur, w remboursement kayb9a 7sab les conditions prevues."
    )
    composer = MultilingualFinalResponseComposer(settings(), FakeClient([response(answer)]))

    assert composer.compose("Une obligation est un titre de dette.", "ary", "latin") == answer
    assert composer.validation_attempts[0]["accepted"] is True


@pytest.mark.parametrize(
    ("language", "script", "candidate"),
    [
        ("fr", "latin", "This is a stock at 12 euros."),
        ("en", "latin", "C'est une action a 12 euros."),
        ("ar", "arabic", "Une obligation vaut 12 euros."),
    ],
)
def test_non_matching_language_is_rejected(language, script, candidate):
    result = _validate_final_answer_result(
        "A business answer with 12 euros.", candidate, language, script, {"status": "completed"}
    )
    assert "wrong_language" in result.reasons


@pytest.mark.parametrize(
    ("language", "script", "candidate"),
    [
        ("fr", "latin", "Une action represente 12 euros."),
        ("en", "latin", "A stock represents 12 euros."),
        (
            "ar",
            "arabic",
            "\u0627\u0644\u0633\u0646\u062f \u0623\u062f\u0627\u0629 \u062f\u064a\u0646 "
            "\u0628\u0642\u064a\u0645\u0629 "
            "12.",
        ),
    ],
)
def test_matching_language_is_accepted(language, script, candidate):
    result = _validate_final_answer_result(
        "A business answer with 12 euros.", candidate, language, script, {"status": "completed"}
    )
    assert result.accepted is True


def test_linguistic_short_answer_must_match_requested_language():
    result = _validate_final_answer_result(
        "A short answer.", "Oui.", "en", "latin", {"status": "completed"}
    )
    assert result.accepted is False
    assert "wrong_language" in result.reasons


def test_short_darija_arabic_and_negation_are_accepted():
    result = _validate_final_answer_result(
        "Une reponse courte.",
        "\u0645\u0627\u0634\u064a \u0645\u0636\u0645\u0648\u0646",
        "ary",
        "arabic",
        {"status": "completed"},
    )
    assert result.accepted is True


def test_modern_standard_arabic_is_not_accepted_as_short_darija_arabic():
    result = _validate_final_answer_result(
        "Une reponse.",
        (
            "\u064a\u0645\u062b\u0644 \u0627\u0644\u0633\u0647\u0645 \u062c\u0632\u0621\u0627 "
            "\u0645\u0646 "
            "\u0631\u0623\u0633 \u0645\u0627\u0644 \u0627\u0644\u0634\u0631\u0643\u0629"
        ),
        "ary",
        "arabic",
        {"status": "completed"},
    )
    assert "wrong_language" in result.reasons


def test_personalized_advice_drift_is_rejected_but_source_advice_is_preserved():
    drift = _validate_final_answer_result(
        "The return may vary and is not guaranteed.",
        "The return may vary. You should buy this stock.",
        "en",
        "latin",
        {"status": "completed"},
    )
    preserved = _validate_final_answer_result(
        "You should buy this stock only in a personal advice workflow.",
        "You should buy this stock only in a personal advice workflow.",
        "en",
        "latin",
        {"status": "completed"},
    )
    assert "personalized_advice_drift" in drift.reasons
    assert "personalized_advice_drift" not in preserved.reasons


@pytest.mark.parametrize(
    ("source", "candidate", "language", "script"),
    [
        (
            "Le rendement depend des conditions de marche.",
            "Le rendement garantit un profit dans toutes les conditions de marche.",
            "fr",
            "latin",
        ),
        (
            "Returns may vary depending on market conditions.",
            "Returns are guaranteed in all cases.",
            "en",
            "latin",
        ),
        (
            (
                "\u064a\u0639\u062a\u0645\u062f \u0627\u0644\u0639\u0627\u0626\u062f "
                "\u0639\u0644\u0649 "
                "\u0638\u0631\u0648\u0641 \u0627\u0644\u0633\u0648\u0642."
            ),
            (
                "\u0627\u0644\u0639\u0627\u0626\u062f \u0645\u0636\u0645ون \u0641\u064a "
                "\u062c\u0645\u064a\u0639 \u0627\u0644\u062d\u0627\u0644\u0627\u062a."
            ),
            "ar",
            "arabic",
        ),
    ],
)
def test_certainty_drift_is_rejected(source, candidate, language, script):
    result = _validate_final_answer_result(
        source, candidate, language, script, {"status": "completed"}
    )
    assert "certainty_drift" in result.reasons


@pytest.mark.parametrize(
    ("source", "candidate", "language", "script"),
    [
        ("Le rendement est garanti.", "Le rendement est garanti.", "fr", "latin"),
        (
            "The return is not guaranteed.",
            "The return is not guaranteed.",
            "en",
            "latin",
        ),
        (
            (
                "\u064a\u0639\u062a\u0645\u062f \u0627\u0644\u0639\u0627\u0626\u062f \u0639\u0644ى "
                "\u0627\u0644\u0633\u0648\u0642."
            ),
            (
                "\u064a\u0639\u062a\u0645\u062f \u0627\u0644\u0639\u0627\u0626\u062f \u0639\u0644ى "
                "\u0627\u0644\u0633\u0648\u0642."
            ),
            "ar",
            "arabic",
        ),
    ],
)
def test_certainty_preservation_is_accepted(source, candidate, language, script):
    result = _validate_final_answer_result(
        source, candidate, language, script, {"status": "completed"}
    )
    assert "certainty_drift" not in result.reasons
    assert result.accepted is True


@pytest.mark.parametrize(
    ("language", "script", "candidate"),
    [
        ("fr", "latin", "AMMC."),
        ("en", "latin", "OPCVM."),
        ("fr", "latin", "ISO 27001."),
        ("en", "latin", "4.5%."),
        ("ar", "arabic", "2026."),
        ("fr", "latin", "3/3."),
        ("en", "latin", "5 actions."),
    ],
)
def test_short_financial_notation_is_language_neutral(language, script, candidate):
    result = _validate_final_answer_result(
        "A short business answer.", candidate, language, script, {"status": "completed"}
    )
    assert "wrong_language" not in result.reasons
    assert result.accepted is True


@pytest.mark.parametrize(
    ("source", "candidate", "expected"),
    [
        (
            "\u0627\u0644\u0639\u0627\u0626\u062f \u062f\u064a\u0627لو \u0645اشي \u0645ضمون.",
            "\u0648\u0627\u0644\u0639\u0627\u0626\u062f \u062f\u064aالو \u0645اشي \u0645ضمون.",
            True,
        ),
        (
            "\u0627\u0644\u0639\u0627ئ\u062f \u062f\u064aالو \u0645اشي \u0645ضمون.",
            "\u0627\u0644\u0639\u0627\u0626د \u062f\u064aالو \u0645ضمون.",
            False,
        ),
    ],
)
def test_darija_arabic_negated_guarantee_is_preserved(source, candidate, expected):
    result = _validate_final_answer_result(
        source, candidate, "ary", "arabic", {"status": "completed"}
    )
    assert result.accepted is expected
    if not expected:
        assert "certainty_drift" in result.reasons


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        ("Le rendement peut varier.", "Le rendement est garanti."),
        ("Le rendement pourrait varier.", "Le rendement est certain."),
        ("Le rendement est possible.", "Le rendement est certain."),
        ("Returns may vary.", "Returns are guaranteed."),
        ("A return is possible.", "The return is certain."),
        ("Le rendement est machi garanti.", "Le rendement est garanti."),
    ],
)
def test_certainty_modalities_are_hardened(source, candidate):
    language = "en" if source.startswith(("Returns", "A return")) else "fr"
    result = _validate_final_answer_result(
        source, candidate, language, "latin", {"status": "completed"}
    )
    assert "certainty_drift" in result.reasons


def test_certainty_drift_is_not_cancelled_by_unrelated_modal_sentence():
    result = _validate_final_answer_result(
        "Le rendement dépend du marché.",
        "Le rendement est garanti. Vous pouvez consulter le prospectus selon vos besoins.",
        "fr",
        "latin",
        {"status": "completed"},
    )
    assert "certainty_drift" in result.reasons


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        (
            "Le rendement dépend des conditions prévues.",
            "Le rendement varie conformément aux conditions prévues.",
        ),
        (
            "Le rendement est garanti selon les conditions du produit.",
            "Selon les conditions du produit, le rendement est garanti.",
        ),
        ("Le rendement dépend du marché.", "Le rendement peut varier selon le marché."),
    ],
)
def test_legitimate_conditional_reformulation_is_accepted(source, candidate):
    result = _validate_final_answer_result(
        source, candidate, "fr", "latin", {"status": "completed"}
    )
    assert "certainty_drift" not in result.reasons
    assert result.accepted is True


@pytest.mark.parametrize(
    "candidate",
    [
        "Il faut acheter cette action.",
        "Je vous recommande d'acheter cette action.",
        "Investissez dans cette société.",
        "Vendez cette action.",
    ],
)
def test_french_directive_advice_drift_is_rejected(candidate):
    result = _validate_final_answer_result(
        "Cette action peut monter ou baisser.",
        candidate,
        "fr",
        "latin",
        {"status": "completed"},
    )
    assert "personalized_advice_drift" in result.reasons


@pytest.mark.parametrize(
    "candidate",
    [
        "Les investisseurs peuvent acheter ce type d'obligation.",
        "Cette catégorie concerne les personnes qui investissent dans ce produit.",
        "Investir comporte des risques.",
        "Investors can buy this type of bond.",
    ],
)
def test_educational_descriptions_are_not_advice_drift(candidate):
    language = "en" if candidate.startswith("Investors") else "fr"
    result = _validate_final_answer_result(
        "Cette information décrit un produit financier.",
        candidate,
        language,
        "latin",
        {"status": "completed"},
    )
    assert "personalized_advice_drift" not in result.reasons


def test_existing_advice_is_not_reported_as_drift():
    result = _validate_final_answer_result(
        "Vous devriez consulter un professionnel.",
        "Vous devriez consulter un professionnel.",
        "fr",
        "latin",
        {"status": "completed"},
    )
    assert "personalized_advice_drift" not in result.reasons


@pytest.mark.parametrize(
    ("language", "script", "candidate"),
    [
        ("fr", "latin", "Hello."),
        ("ar", "arabic", "Hello."),
        ("ary", "arabic", "Non."),
        ("ary", "latin", "\u0646\u0639\u0645."),
    ],
)
def test_linguistic_short_words_never_bypass_language_or_script(language, script, candidate):
    result = _validate_final_answer_result(
        "A short business answer.", candidate, language, script, {"status": "completed"}
    )
    assert result.accepted is False
    assert "wrong_language" in result.reasons or "wrong_script" in result.reasons


@pytest.mark.parametrize(
    "candidate",
    ["ISO27001.", "ISO 27001.", "q2.", "Q2.", "v2.", "V2.", "t1.", "T1."],
)
def test_structural_financial_identifiers_are_neutral(candidate):
    result = _validate_final_answer_result(
        "A short business answer.", candidate, "fr", "latin", {"status": "completed"}
    )
    assert result.accepted is True


def test_phonetic_darija_digit_is_not_treated_as_business_number():
    result = _validate_final_answer_result(
        "Saham kaymattel joz2 men ras lmal dyal charika.",
        "Saham kaymattel joz men ras lmal dyal charika.",
        "ary",
        "latin",
        {"status": "completed"},
    )
    assert result.accepted is True
    assert result.diagnostics["business_numbers"] == []


def test_deployment_is_required_and_validated_before_client_use():
    with pytest.raises(ValueError, match="AZURE_OPENAI_DEPLOYMENT is required"):
        MultilingualFinalResponseComposer(
            settings().model_copy(update={"azure_openai_deployment": ""}), FakeClient([])
        )
    with pytest.raises(ValueError, match="invalid format"):
        MultilingualFinalResponseComposer(
            settings().model_copy(update={"azure_openai_deployment": "bad/name"}), FakeClient([])
        )


@pytest.mark.parametrize("candidate", ["q2 2026", "v2", "t1", "ISO 27001", "4.5%", "OPCVM"])
def test_legitimate_identifiers_are_not_phonetic_arabizi(candidate):
    assert darija_latin_quality_issue(candidate) is None


def test_iso_identifier_allows_cosmetic_spacing_change():
    result = _validate_final_answer_result(
        "The identifier ISO 27001 is listed.",
        "The identifier ISO27001 is listed.",
        "en",
        "latin",
        {"status": "completed"},
    )
    assert result.accepted is True


def test_long_source_can_be_concise_when_complete_and_terminated():
    source = " ".join(["The source explains a financial concept in detail."] * 20)
    result = _validate_final_answer_result(
        source,
        "The complete answer explains the financial concept.",
        "en",
        "latin",
        {"status": "completed"},
    )
    assert result.accepted is True


def test_ary_latin_groq_prompt_prioritizes_darija_and_semantic_fidelity():
    prompt = " ".join(GROQ_ARY_LATIN_FALLBACK_INSTRUCTIONS.split())
    required_fragments = (
        "Your output must NOT be a French answer",
        "natural Moroccan Darija written in Latin script",
        "Every explanatory sentence must use Moroccan Darija grammar",
        "The business_answer is authoritative",
        "preserving the exact meaning",
        "Prefer a French financial term over an inaccurate Darija paraphrase",
        "Do not invent facts",
        "zero Arabic Unicode characters",
    )
    for fragment in required_fragments:
        assert fragment in prompt


def test_ary_latin_groq_fallback_is_single_guarded_attempt(monkeypatch):
    answer = "Saham howa joz mn ras lmal dyal charika, walakin rbe7 machi garanti."
    calls = []

    class FakeGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def _complete(self, system_prompt, payload, **kwargs):
            calls.append((system_prompt, payload))
            assert kwargs == {"json_mode": False}
            return {"answer": answer, "_metadata": {"finish_reason": "stop"}}

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setattr(
        "app.graph.final_response_composer.GroqResponseLocalizationProvider", FakeGroq
    )

    assert (
        compose_ary_latin_fallback(
            "Une action represente une part du capital, mais le rendement n'est pas garanti.",
            route="pedagogie",
            status="completed",
        )
        == answer
    )
    assert len(calls) == 1
    assert calls[0][1] == {
        "business_answer": (
            "Une action represente une part du capital, mais le rendement n'est pas garanti."
        ),
        "language": "ary",
        "script": "latin",
        "route": "pedagogie",
        "status": "completed",
    }
    assert "citations" not in calls[0][1]
    assert "chunks" not in calls[0][1]


def test_ary_latin_groq_fallback_rejects_arabic_script(monkeypatch):
    class FakeGroq:
        def __init__(self, **kwargs):
            del kwargs

        def _complete(self, system_prompt, payload, **kwargs):
            del system_prompt, payload, kwargs
            return {"answer": "Saham هو joz2 mn ras lmal.", "_metadata": {}}

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setattr(
        "app.graph.final_response_composer.GroqResponseLocalizationProvider", FakeGroq
    )

    with pytest.raises(FinalResponseCompositionError, match="arabic_script_in_latin"):
        compose_ary_latin_fallback("Saham howa joz2 mn ras lmal.")


def test_ary_latin_groq_fallback_preserves_long_list_structure(monkeypatch):
    source = (
        "Les points sont: 1) capital 2) rendement 3) risque 4) liquidite, "
        "et le rendement machi garanti."
    )
    answer = (
        "Les points homa: 1) capital 2) rendement 3) risque 4) liquidite, "
        "w rendement machi garanti."
    )

    class FakeGroq:
        def __init__(self, **kwargs):
            del kwargs

        def _complete(self, system_prompt, payload, **kwargs):
            del system_prompt, payload, kwargs
            return {"answer": answer, "_metadata": {"finish_reason": "stop"}}

    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setattr(
        "app.graph.final_response_composer.GroqResponseLocalizationProvider", FakeGroq
    )

    assert compose_ary_latin_fallback(source) == answer
