from types import SimpleNamespace

from app.config import Settings
from app.graph.agents import fallback_agent
from app.graph.final_response_composer import (
    MultilingualFinalResponseComposer,
    _validate_final_answer_result,
)
from app.graph.state import create_turn_input


def test_reachable_fallback_text_is_utf8_clean():
    answer = fallback_agent(create_turn_input("?"))["business_answer"]

    assert "Ã" not in answer
    assert "Â" not in answer
    assert "\ufffd" not in answer
    assert "éducation financière" in answer


def test_arabic_bond_terminology_rejects_stock_substitution():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "السهم هو ورقة مالية تمثل ملكية.",
        "ar",
        "arabic",
        {"status": "completed"},
    )

    assert result.accepted is False
    assert "financial_concept_drift" in result.reasons


def test_arabic_bond_terminology_accepts_sanad():
    result = _validate_final_answer_result(
        "Une obligation est un titre de dette.",
        "السند هو ورقة مالية تمثل دينا على الجهة المصدرة.",
        "ar",
        "arabic",
        {"status": "completed"},
    )

    assert result.accepted is True


def test_arabic_composer_retries_instrument_drift():
    class Responses:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                output_text=(
                    "السهم هو ورقة مالية تمثل ملكية."
                    if len(self.calls) == 1
                    else "السند هو ورقة مالية تمثل دينا على الجهة المصدرة."
                ),
                status="completed",
                incomplete_details=None,
            )

    responses = Responses()
    client = SimpleNamespace(responses=responses)
    settings = Settings(
        app_env="test",
        azure_openai_endpoint="https://resource.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_deployment="test-deployment",
        azure_final_response_max_output_tokens=4096,
    )
    composer = MultilingualFinalResponseComposer(settings, client)

    answer = composer.compose("Une obligation est un titre de dette.", "ar", "arabic")

    assert answer.startswith("السند")
    assert len(responses.calls) == 2
    assert "financial_concept_drift" in composer.validation_attempts[0]["reasons"]
