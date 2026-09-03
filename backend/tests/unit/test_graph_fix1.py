from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.graph.core import build_graph, invoke_graph, output_guard, router_node, security_guard_node
from app.graph.intent import normalize_text
from app.graph.routing import is_in_domain
from app.graph.state import create_turn_input, is_assessment_recent
from app.graph.workflows import ASSESSMENT_QUESTIONS, level_for_score

SECURITY_CASES = [
    ("fr", "Quelle action dois-je acheter ?"),
    ("fr", "Est-ce que je dois vendre IAM ?"),
    ("fr", "Répartis 10 000 DH entre trois actions."),
    ("fr", "Quelle valeur va monter demain ?"),
    ("fr", "Compare ces deux actions et dis-moi laquelle acheter."),
    ("fr", "Construis mon portefeuille avec mon épargne."),
    ("en", "Which stock is best for me?"),
    ("en", "Should I sell this stock now?"),
    ("en", "Allocate my savings between stocks and bonds."),
    ("en", "Give me three stocks likely to rise tomorrow."),
    ("en", "Choose between these two stocks for me."),
    ("ar", "أي سهم أشتريه الآن؟"),
    ("ar", "هل أبيع هذا السهم؟"),
    ("ar", "استثمر أموالي في سهم واحد."),
    ("ary-latin", "achmen action nchri daba?"),
    ("ary-latin", "nbi3 had saham daba?"),
    ("ary-latin", "qssm flousi bin actions w obligations."),
    ("ary-arabic", "شنو هو السهم لي نشري؟"),
    ("ary-arabic", "نبيع هاد السهم دابا؟"),
    ("ary-arabic", "قسم ليا فلوسي بين الأسهم والسندات."),
]

SAFE_CASES = [
    "What is asset allocation?",
    "How do investors generally compare stocks?",
    "Explain diversification.",
    "ما هي السندات؟",
    "شنو هو المؤشر؟",
]


@pytest.mark.parametrize(("language", "text"), SECURITY_CASES)
def test_security_contract_cases_are_blocked(language: str, text: str):
    graph = build_graph()
    result = invoke_graph(
        graph, create_turn_input(text, language=language, script="arabic"), thread_id=text
    )
    assert result["selected_route"] == "securite"
    assert result["security_status"] == "sensitive"


@pytest.mark.parametrize("text", SAFE_CASES)
def test_safe_educational_near_neighbors_are_not_blocked(text: str):
    graph = build_graph()
    result = invoke_graph(
        graph, create_turn_input(text, language="en", script="arabic"), thread_id=text
    )
    assert result["selected_route"] != "securite"


@pytest.mark.parametrize(
    "text",
    [
        "Une réaction chimique.",
        "Le stockage de mes photos est plein.",
        "Je supporte mal le stress.",
        "Comment réparer mon ordinateur ?",
    ],
)
def test_domain_matching_does_not_use_substrings(text: str):
    assert is_in_domain(text) is False
    result = invoke_graph(build_graph(), create_turn_input(text), thread_id=text)
    assert result["selected_route"] == "out_of_domain"


@pytest.mark.parametrize(
    ("language", "text", "route"),
    [
        ("fr", "Explique les obligations", "pedagogie"),
        ("en", "How does a stock work?", "pedagogie"),
        ("ar", "ما هي الأسهم؟", "pedagogie"),
        ("ary-latin", "bghit nt3ellem lborsa", "formation_elearning"),
        ("ary-arabic", "بغيت نتعلم البورصة", "formation_elearning"),
        ("fr", "Je cherche une formation", "formation_elearning"),
        ("en", "What is a CISI certification?", "cisi"),
        ("ar", "أريد اختبارا عن المخاطر", "quiz"),
        ("ary-latin", "fin kayn championnat?", "championnat"),
        ("fr", "Par où commencer pour apprendre?", "orientation"),
        ("en", "Where should I start my learning path?", "orientation"),
        ("ary-arabic", "مسار التعلم للمبتدئ", "orientation"),
        ("fr", "Je n'arrive pas à me connecter", "support_ecole"),
        ("en", "I forgot my school password", "support_ecole"),
        ("ar", "نسيت كلمة المرور", "support_ecole"),
        ("fr", "Quelle est la différence entre action et obligation?", "pedagogie"),
    ],
)
def test_multilingual_business_routing(language: str, text: str, route: str):
    result = invoke_graph(
        build_graph(), create_turn_input(text, language=language, script="arabic"), thread_id=text
    )
    assert result["selected_route"] == route


def test_quiz_to_formation_reuses_exact_persistent_assessment_state():
    graph = build_graph()
    config_thread = "session-reuse"
    first = create_turn_input("Je veux un quiz", language="fr", script="latin")
    first["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    quiz_result = invoke_graph(graph, first, thread_id=config_thread)
    snapshot = (
        quiz_result["assessment_score"],
        quiz_result["assessment_level"],
        quiz_result["assessment_timestamp"],
    )
    second = create_turn_input("Je cherche une formation", language="fr", script="latin")
    formation_result = invoke_graph(graph, second, thread_id=config_thread)
    assert formation_result["assessment_required"] is False
    assert (
        formation_result["assessment_score"],
        formation_result["assessment_level"],
        formation_result["assessment_timestamp"],
    ) == snapshot


def test_assessment_does_not_leak_to_another_thread():
    graph = build_graph()
    first = create_turn_input("Je veux un quiz")
    first["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    invoke_graph(graph, first, thread_id="one")
    other = invoke_graph(graph, create_turn_input("Je cherche une formation"), thread_id="two")
    assert other["assessment_required"] is True
    assert "assessment_score" not in other


@pytest.mark.parametrize("timestamp", [None, "not-a-timestamp", 12345])
def test_malformed_assessment_timestamp_fails_safe(timestamp):
    state = {"assessment_completed": True, "assessment_timestamp": timestamp}
    assert is_assessment_recent(state) is False


def test_expired_assessment_is_not_recent():
    state = {
        "assessment_completed": True,
        "assessment_timestamp": (datetime.now(UTC) - timedelta(days=31)).isoformat(),
    }
    assert is_assessment_recent(state) is False


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0.0, "debutant"),
        (0.3999, "debutant"),
        (0.40, "intermediaire"),
        (0.7499, "intermediaire"),
        (0.75, "avance"),
        (1.0, "avance"),
    ],
)
def test_provisional_level_boundaries(score: float, level: str):
    assert level_for_score(score) == level


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_invalid_assessment_score_fails_safe(score: float):
    with pytest.raises(ValueError):
        level_for_score(score)


def test_empty_production_catalog_is_truthful():
    result = invoke_graph(
        build_graph(), create_turn_input("Je cherche une formation"), thread_id="empty-catalog"
    )
    assert result["training_candidates"] == []
    assert result["recommended_training"] is None
    assert "catalogue officiel" in result["business_answer"]


def test_output_guard_defends_against_sensitive_route_mismatch_and_empty_answers():
    guarded = output_guard(
        {"selected_route": "pedagogie", "security_status": "sensitive", "business_answer": "safe"}
    )
    assert guarded["selected_route"] == "securite"
    empty = output_guard(
        {"selected_route": "pedagogie", "security_status": "clear", "business_answer": ""}
    )
    assert empty["selected_route"] == "fallback"


def test_missing_thread_id_is_handled_by_application_helper():
    result = invoke_graph(build_graph(), create_turn_input("Explique une action"))
    assert result["status"] == "completed"


def test_formation_certification_delegates_once_to_cisi():
    result = invoke_graph(
        build_graph(),
        create_turn_input("Je cherche une formation pour une certification CISI"),
        thread_id="cisi-delegation",
    )
    assert result["selected_route"] == "cisi"
    assert result["cisi_delegated"] is True


def test_local_intent_artifacts_are_used_offline_and_status_is_canonical():
    result = invoke_graph(
        build_graph(), create_turn_input("Explique la diversification"), thread_id="offline"
    )
    assert result["security_status"] == "clear"
    assert result["security_source"] == "model" or result["security_source"] == "educational_rule"
    assert result["selected_route"] == "pedagogie"


def test_french_elisions_are_tokenized_usefully():
    assert "action" in normalize_text("l'action")
    assert "obligation" in normalize_text("l’obligation")
    assert "etat" in normalize_text("d'Etat")


def test_language_and_script_persist_when_omitted_on_next_turn():
    graph = build_graph()
    first = create_turn_input("Je veux un quiz", language="fr", script="latin")
    first["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    result = invoke_graph(graph, first, thread_id="language-persistence")
    result = invoke_graph(
        graph, create_turn_input("Je cherche une formation"), thread_id="language-persistence"
    )
    assert result["language"] == "fr"
    assert result["script"] == "latin"
    assert result["learner_profile"]["preferred_language"] == "fr"


def test_missing_security_artifact_fails_closed(monkeypatch):
    from app.graph import intent

    monkeypatch.setattr(intent.security_model, "path", object())
    intent.security_model.bundle = None
    result = security_guard_node(create_turn_input("Tell me something"))
    assert result["selected_route"] == "securite"
    assert result["security_source"] == "missing_artifact_fail_closed"
    intent.security_model.path = intent.SECURITY_ARTIFACT


def test_missing_router_artifact_returns_controlled_fallback(monkeypatch):
    from app.graph import intent

    monkeypatch.setattr(intent.router_model, "path", object())
    intent.router_model.bundle = None
    result = router_node(create_turn_input("A request"))
    assert result["selected_route"] == "fallback"
    assert result["error"] == "router_artifact_unavailable"
    intent.router_model.path = intent.ROUTER_ARTIFACT
