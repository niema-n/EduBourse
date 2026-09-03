from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.graph.catalog import FixtureTrainingCatalog
from app.graph.core import SUPPORTED_ROUTES, build_graph
from app.graph.state import create_initial_state, is_assessment_recent
from app.graph.workflows import ASSESSMENT_QUESTIONS, score_assessment


def invoke(text: str, **kwargs):
    graph = build_graph(**kwargs)
    return graph.invoke(create_initial_state(text), config={"configurable": {"thread_id": "test"}})


def test_graph_compiles_and_preserves_j2_metadata():
    state = create_initial_state("Bonjour", language="fr", script="latin", thread_id="t-1")
    result = build_graph().invoke(state, config={"configurable": {"thread_id": "t-1"}})
    assert result["language"] == "fr"
    assert result["script"] == "latin"
    assert result["status"] == "completed"


@pytest.mark.parametrize(
    ("text", "route"),
    [
        ("Explique-moi les obligations", "pedagogie"),
        ("Je cherche une formation", "formation_elearning"),
        ("What is CISI?", "cisi"),
        ("Je veux un quiz sur les indices", "quiz"),
        ("Informations sur le Championnat de la Bourse", "championnat"),
        ("Quelle orientation pour apprendre la Bourse ?", "orientation"),
        ("J'ai besoin d'aide pour mon mot de passe", "support_ecole"),
        ("Comment réparer mon ordinateur ?", "out_of_domain"),
        ("Une demande incompréhensible", "out_of_domain"),
    ],
)
def test_canonical_routes(text: str, route: str):
    result = invoke(text)
    assert result["selected_route"] == route
    assert result["business_answer"]


@pytest.mark.parametrize(
    "text",
    [
        "Quelle action dois-je acheter ?",
        "Est-ce que je dois vendre IAM ?",
        "Investis mes 10 000 DH dans une action.",
        "Quelle valeur va monter demain ?",
        "What should I buy for my portfolio?",
    ],
)
def test_sensitive_requests_reach_security_before_business(text: str):
    result = invoke(text)
    assert result["selected_route"] == "securite"
    assert result["security_status"] == "blocked"
    assert "choisir" in result["business_answer"]


def test_unknown_route_falls_back_when_router_is_given_an_unexpected_value():
    from app.graph.core import route_to_agent

    assert route_to_agent({"selected_route": "unknown"}) == "fallback"
    result = invoke("Bourse")
    assert result["selected_route"] in SUPPORTED_ROUTES


def test_formation_without_assessment_requests_one():
    result = invoke("Je cherche une formation")
    assert result["selected_route"] == "formation_elearning"
    assert result["assessment_required"] is True
    assert result["assessment_completed"] is False


def test_assessment_scoring_and_levels():
    assert score_assessment([False] * len(ASSESSMENT_QUESTIONS))[1] == "debutant"
    assert score_assessment([True, True, True, False, True, False])[1] == "intermediaire"
    assert score_assessment([True] * len(ASSESSMENT_QUESTIONS))[1] == "avance"


def test_recent_assessment_is_reused_and_training_is_matched():
    catalog = FixtureTrainingCatalog(
        [
            {
                "id": "fixture-1",
                "title": "Fixture",
                "level": "avance",
                "topics": ["risques"],
                "goals": ["financial_education"],
                "source": "test fixture",
            }
        ]
    )
    state = create_initial_state("Je cherche une formation", language="fr", script="latin")
    state.update(
        {
            "assessment_completed": True,
            "assessment_timestamp": datetime.now(UTC).isoformat(),
            "assessment_level": "avance",
            "assessment_weak_topics": ["risques"],
            "assessment_topics": ["actions"],
        }
    )
    result = build_graph(training_catalog=catalog).invoke(
        state, config={"configurable": {"thread_id": "reuse"}}
    )
    assert result["assessment_required"] is False
    assert result["recommended_training"]["id"] == "fixture-1"
    assert is_assessment_recent(result)


def test_old_assessment_is_not_recent():
    state = create_initial_state("formation")
    state.update(
        {
            "assessment_completed": True,
            "assessment_timestamp": (datetime.now(UTC) - timedelta(days=31)).isoformat(),
        }
    )
    assert is_assessment_recent(state) is False


def test_quiz_writes_shared_assessment_state_then_formation_reuses_it():
    graph = build_graph()
    config = {"configurable": {"thread_id": "shared"}}
    quiz_state = create_initial_state("Je veux un quiz", language="fr", script="latin")
    quiz_state["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    quiz_result = graph.invoke(quiz_state, config=config)
    assert quiz_result["assessment_completed"] is True
    formation_result = graph.invoke(create_initial_state("Je cherche une formation"), config=config)
    assert formation_result["assessment_required"] is False
    assert formation_result["assessment_level"] == "avance"


def test_formation_certification_delegates_to_cisi_without_loop():
    result = invoke("Je cherche une formation pour une certification professionnelle")
    assert result["selected_route"] == "cisi"
    assert result["business_answer"]


def test_agent_failure_is_converted_to_controlled_error():
    class BrokenCatalog:
        def search(self, profile):
            raise RuntimeError("should not escape")

    state = create_initial_state("Je cherche une formation")
    state["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    result = build_graph(training_catalog=BrokenCatalog()).invoke(
        state,
        config={"configurable": {"thread_id": "broken"}},
    )
    assert result["status"] == "error"
    assert result["error"] == "agent_failure_handled"
    assert "erreur contrôlée" in result["business_answer"]
