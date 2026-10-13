import pytest

from app.graph import agents, localization
from app.graph.state import create_turn_input

MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\ufffd")


def test_french_pedagogie_runtime_response_uses_valid_utf8_text() -> None:
    answer = agents.pedagogie_agent(
        {"user_input": "C'est quoi une action en bourse ?"}
    )["business_answer"]

    assert "march\u00e9" in answer
    assert "vis\u00e9e \u00e9ducative" in answer
    assert not any(marker in answer for marker in MOJIBAKE_MARKERS)


def test_arabic_and_darija_localized_runtime_responses_are_not_mojibake() -> None:
    source = agents.pedagogie_agent({"user_input": "x"})["business_answer"]
    arabic = localization.localize_answer(
        source, "ar", "arabic", route="pedagogie", response_key="pedagogie"
    )
    darija = localization.localize_answer(
        source, "ary", "arabic", route="pedagogie", response_key="pedagogie"
    )

    assert "\u0627\u0644\u0623\u0633\u0647\u0645" in arabic
    assert "\u0646\u0642\u062f\u0631" in darija
    assert not any(marker in arabic for marker in MOJIBAKE_MARKERS)
    assert not any(marker in darija for marker in MOJIBAKE_MARKERS)


def test_known_pedagogie_response_localizes_by_shared_response_key() -> None:
    source = agents.pedagogie_agent({"user_input": "x"})["business_answer"]

    french = localization.localize_answer(
        source, "fr", "latin", route="pedagogie", response_key="pedagogie"
    )
    english = localization.localize_answer(
        source, "en", "latin", route="pedagogie", response_key="pedagogie"
    )

    assert "march\u00e9" in french
    assert english == "I can explain stocks, bonds, indexes, and risk for educational purposes."
    assert english != source


def test_unknown_injected_business_content_is_preserved() -> None:
    injected = "Provider-authored educational detail"
    variants = [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ]

    for language, script in variants:
        answer = localization.localize_answer(injected, language, script, route="pedagogie")
        assert answer == injected


def test_new_turn_resets_response_key() -> None:
    state = create_turn_input(
        "next turn", language="en", script="latin", thread_id="same-thread"
    )

    assert state["response_key"] == ""


def test_same_route_dynamic_answer_is_not_localized_from_stale_key() -> None:
    first_turn = create_turn_input("first", language="en", script="latin")
    first_turn.update({"selected_route": "championnat", "response_key": "championnat"})
    second_turn = create_turn_input("second", language="en", script="latin")
    dynamic_answer = "Personalized catalog recommendation for this learner"
    second_turn.update({"selected_route": "championnat", "business_answer": dynamic_answer})

    assert first_turn["response_key"] == "championnat"
    assert second_turn["response_key"] == ""
    assert (
        localization.localize_answer(
            second_turn["business_answer"],
            "en",
            "latin",
            route=second_turn["selected_route"],
            response_key=second_turn["response_key"],
        )
        == dynamic_answer
    )


def test_formation_static_response_localizes_by_shared_response_key() -> None:
    source = (
        "Une courte \u00e9valuation est n\u00e9cessaire avant de proposer un parcours; "
        "le catalogue officiel n'est pas encore connect\u00e9."
    )

    french = localization.localize_answer(
        source,
        "fr",
        "latin",
        route="formation_elearning",
        response_key="formation_elearning",
    )
    english = localization.localize_answer(
        source,
        "en",
        "latin",
        route="formation_elearning",
        response_key="formation_elearning",
    )

    assert french == source
    assert english == "I can present available learning paths for educational purposes."
    assert "\u00e9valuation" not in english


def test_dynamic_formation_content_is_preserved_in_all_variants() -> None:
    dynamic_answer = "Learner-specific recommendation from the training catalog"
    variants = [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ]

    for language, script in variants:
        answer = localization.localize_answer(
            dynamic_answer,
            language,
            script,
            route="formation_elearning",
            response_key="",
        )
        assert answer == dynamic_answer


@pytest.mark.parametrize(
    ("language", "script"),
    [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ],
)
def test_known_pedagogie_response_passes_localized_script_validation(
    language: str, script: str
) -> None:
    source = agents.pedagogie_agent({"user_input": "x"})["business_answer"]
    answer = localization.localize_answer(
        source, language, script, route="pedagogie", response_key="pedagogie"
    )

    assert localization.validate_localized_script(answer, language, script)
