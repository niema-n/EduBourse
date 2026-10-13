from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_graph
from app.graph.core import build_graph
from app.graph.state import create_turn_input
from app.graph.workflows import ASSESSMENT_QUESTIONS
from app.main import app
from app.multilingual.models import LanguageAnalysis

# Unicode escape sequences keep the test source ASCII and readable.
# ruff: noqa: E501


class FakeSupervisor:
    def __init__(self, route: str = "pedagogie", failure: Exception | None = None) -> None:
        self.route = route
        self.failure = failure
        self.calls = 0

    def invoke_structured(self, request: object) -> object:
        self.calls += 1
        if self.failure:
            raise self.failure
        return (
            {"domain_status": "out_of_domain", "route": "out_of_domain"}
            if self.route == "out_of_domain"
            else {
                "domain_status": "in_domain",
                "route": self.route,
            }
        )


@pytest.fixture
def client():
    provider = FakeSupervisor()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("message", "language", "script"),
    [
        ("C'est quoi une action en Bourse ?", "fr", "latin"),
        ("What is a stock market index?", "en", "latin"),
        (
            "\u0645\u0627 \u0647\u0648 \u0627\u0644\u0633\u0647\u0645 \u0641\u064a \u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f",
            "ar",
            "arabic",
        ),
        ("chno hiya action f lborsa?", "ary", "latin"),
        (
            "\u0634\u0646\u0648 \u0647\u064a \u0627\u0644\u0623\u0643\u0633\u064a\u0648\u0646 \u0641\u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f",
            "ary",
            "arabic",
        ),
    ],
)
def test_chat_preserves_business_language_and_script(client, message, language, script):
    response = client.post("/chat", json={"message": message, "thread_id": f"{language}-{script}"})

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == language
    assert body["script"] == script
    assert body["route"] == "pedagogie"
    assert body["blocked"] is False
    assert body["status"] == "ok"


def test_active_quiz_uses_persisted_locale_for_single_letter_continuation(monkeypatch):
    provider = FakeSupervisor(route="quiz")
    graph = build_graph(supervisor_provider=provider)
    app.dependency_overrides[get_chat_graph] = lambda: graph
    import app.api.chat as chat_api

    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ar" if text != "B" else "en",
            script="arabic" if text != "B" else "latin",
            normalized_text=text,
            confidence=1.0,
        ),
    )
    try:
        with TestClient(app) as test_client:
            first = test_client.post(
                "/chat", json={"message": "أريد اختبارا", "thread_id": "quiz-ar"}
            ).json()
            second = test_client.post(
                "/chat", json={"message": "B", "thread_id": "quiz-ar"}
            ).json()
    finally:
        app.dependency_overrides.clear()
    assert first["language"] == "ar"
    assert first["script"] == "arabic"
    assert second["language"] == "ar"
    assert second["script"] == "arabic"
    assert "السؤال" in second["answer"]


@pytest.mark.parametrize(
    ("message", "language", "script"),
    [
        (
            "\u0645\u0627 \u0647\u0648 \u0627\u0644\u0640 SAM \u0641\u064a \u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f",
            "ar",
            "arabic",
        ),
        ("\u0645\u0627 \u0647\u0648 ETF\u061f", "ar", "arabic"),
        ("\u0645\u0627 \u0647\u0648 MASI\u061f", "ar", "arabic"),
        ("\u0645\u0627 \u0647\u0648 CISI\u061f", "ar", "arabic"),
        ("\u0645\u0627 \u0647\u0648 IAM\u061f", "ar", "arabic"),
        ("Bonjour \u0645\u0631\u062d\u0628\u0627", "fr", "latin"),
        ("Hello \u0645\u0631\u062d\u0628\u0627", "en", "latin"),
    ],
)
def test_mixed_script_inputs_use_canonical_business_script(
    client, monkeypatch, message, language, script
):
    import app.api.chat as chat_api

    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language=language,
            script="mixed",
            normalized_text=text,
            confidence=1.0,
        ),
    )

    response = client.post("/chat", json={"message": message, "thread_id": f"mixed-{language}"})

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == language
    assert body["script"] == script
    assert body["status"] == "ok"


@pytest.mark.parametrize(
    "route",
    [
        "pedagogie",
        "formation_elearning",
        "orientation",
        "cisi",
        "quiz",
        "championnat",
        "support_ecole",
    ],
)
def test_chat_connects_each_business_route(route):
    provider = FakeSupervisor(route=route)
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        body = (
            TestClient(app)
            .post("/chat", json={"message": "Explain this Bourse topic", "thread_id": route})
            .json()
        )
    finally:
        app.dependency_overrides.clear()

    assert body["route"] == route
    assert body["status"] == "ok"


@pytest.mark.parametrize(
    ("message", "language", "script"),
    [
        ("Quelle action dois-je acheter ?", "fr", "latin"),
        ("What stock should I buy?", "en", "latin"),
        (
            "\u0623\u064a \u0633\u0647\u0645 \u0623\u0634\u062a\u0631\u064a \u0644\u062a\u062d\u0642\u064a\u0642 \u0631\u0628\u062d\u061f",
            "ar",
            "arabic",
        ),
        ("achmen action nchri bach nrbe7?", "ary", "latin"),
    ],
)
def test_security_runs_before_supervisor_and_preserves_language(message, language, script):
    provider = FakeSupervisor()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        response = TestClient(app).post(
            "/chat", json={"message": message, "thread_id": f"secure-{language}"}
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["blocked"] is True
    assert body["route"] == "securite"
    assert body["language"] == language
    assert body["script"] == script
    assert body["status"] == "blocked"
    assert provider.calls == 0


def test_out_of_domain_is_not_answered_as_pedagogie():
    provider = FakeSupervisor(route="out_of_domain")
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        body = (
            TestClient(app)
            .post("/chat", json={"message": "What is the capital of Japan?", "thread_id": "ood"})
            .json()
        )
    finally:
        app.dependency_overrides.clear()

    assert body["route"] == "out_of_domain"
    assert body["status"] == "ok"


def test_provider_failure_is_controlled_and_not_pedagogie():
    provider = FakeSupervisor(failure=RuntimeError("provider unavailable"))
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        response = TestClient(app).post(
            "/chat", json={"message": "Explain diversification", "thread_id": "failure"}
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "fallback"
    assert body["status"] == "error"
    assert "provider unavailable" not in body["answer"]


def test_malformed_supervisor_output_is_controlled():
    class Malformed(FakeSupervisor):
        def invoke_structured(self, request: object) -> object:
            return {"route": "not-a-route"}

    provider = Malformed()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        body = (
            TestClient(app)
            .post("/chat", json={"message": "Explain diversification", "thread_id": "malformed"})
            .json()
        )
    finally:
        app.dependency_overrides.clear()

    assert body["route"] == "fallback"
    assert body["status"] == "error"


def test_thread_ids_are_preserved_without_cross_thread_leakage():
    provider = FakeSupervisor()
    graph = build_graph(supervisor_provider=provider)
    app.dependency_overrides[get_chat_graph] = lambda: graph
    try:
        client = TestClient(app)
        first = client.post(
            "/chat", json={"message": "I want a quiz", "thread_id": "thread-a"}
        ).json()
        second = client.post(
            "/chat", json={"message": "Explain a bond", "thread_id": "thread-b"}
        ).json()
    finally:
        app.dependency_overrides.clear()

    assert first["thread_id"] == "thread-a"
    assert second["thread_id"] == "thread-b"
    assert first["thread_id"] != second["thread_id"]


def test_chat_validation_and_openapi_contract(client):
    assert "/chat" in app.openapi()["paths"]
    assert "post" in app.openapi()["paths"]["/chat"]
    assert client.post("/chat", json={"message": " ", "thread_id": "x"}).status_code == 422
    assert client.post("/chat", json={"message": "hello"}).status_code == 422


def test_actual_business_answer_is_not_replaced_by_route_template(monkeypatch):
    import app.graph.core as core

    sentinel = "SENTINEL_BUSINESS_ANSWER_A"
    monkeypatch.setattr(
        core,
        "pedagogie_agent",
        lambda state: {"business_answer": sentinel, "status": "completed"},
    )
    provider = FakeSupervisor()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        body = TestClient(app).post(
            "/chat", json={"message": "Explain diversification", "thread_id": "sentinel"}
        ).json()
    finally:
        app.dependency_overrides.clear()

    assert body["answer"] == sentinel
    assert body["route"] == "pedagogie"


def test_two_same_route_answers_remain_distinct(monkeypatch):
    import app.graph.core as core

    def agent(state):
        return {"business_answer": state["user_input"], "status": "completed"}

    monkeypatch.setattr(core, "pedagogie_agent", agent)
    provider = FakeSupervisor()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        client = TestClient(app)
        first = client.post(
            "/chat", json={"message": "Explain stocks", "thread_id": "same-route-a"}
        ).json()
        second = client.post(
            "/chat", json={"message": "Explain bonds", "thread_id": "same-route-b"}
        ).json()
    finally:
        app.dependency_overrides.clear()

    assert first["route"] == second["route"] == "pedagogie"
    assert first["answer"] != second["answer"]


@pytest.mark.parametrize(
    ("message", "script"),
    [
        ("chno hiya action f lborsa \u0627\u0644\u064a\u0648\u0645\u061f", "latin"),
        ("\u0634\u0646\u0648 \u0647\u064a action f lborsa?", "arabic"),
        ("wach l ETF safi? \u0634\u0643\u0631\u0627", "latin"),
    ],
)
def test_code_switched_darija_is_controlled(message, script):
    provider = FakeSupervisor()
    app.dependency_overrides[get_chat_graph] = lambda: build_graph(supervisor_provider=provider)
    try:
        response = TestClient(app).post(
            "/chat", json={"message": message, "thread_id": f"mixed-{script}"}
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["language"] == "ary"
    assert body["script"] == script
    assert body["blocked"] is False
    assert body["status"] == "ok"


def test_graph_failure_returns_neutral_controlled_fallback():
    class BrokenGraph:
        def invoke(self, state, config):
            raise RuntimeError("graph exploded")

    app.dependency_overrides[get_chat_graph] = lambda: BrokenGraph()
    try:
        response = TestClient(app).post(
            "/chat",
            json={"message": "Quelle action dois-je acheter demain ?", "thread_id": "broken"},
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["blocked"] is False
    assert body["status"] == "error"
    assert body["route"] == "fallback"
    assert "recommander" not in body["answer"].casefold()


def test_checkpoint_state_is_isolated_and_resumed_per_thread():
    provider = FakeSupervisor(route="formation_elearning")
    graph = build_graph(supervisor_provider=provider)
    seed = create_turn_input("Je veux un quiz", language="fr", script="latin")
    seed["assessment_answers"] = [True] * len(ASSESSMENT_QUESTIONS)
    graph.invoke(seed, config={"configurable": {"thread_id": "checkpoint-a"}})
    app.dependency_overrides[get_chat_graph] = lambda: graph
    try:
        client = TestClient(app)
        client.post(
            "/chat", json={"message": "Je cherche une formation", "thread_id": "checkpoint-a"}
        )
        client.post(
            "/chat", json={"message": "Je cherche une formation", "thread_id": "checkpoint-b"}
        )
    finally:
        app.dependency_overrides.clear()

    state_a = graph.get_state({"configurable": {"thread_id": "checkpoint-a"}}).values
    state_b = graph.get_state({"configurable": {"thread_id": "checkpoint-b"}}).values
    assert state_a.get("assessment_completed") is True
    assert "assessment_score" in state_a
    assert "assessment_score" not in state_b
