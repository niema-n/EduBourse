from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_graph
from app.graph.core import build_graph
from app.graph.final_response_composer import FinalResponseCompositionError
from app.main import app
from app.multilingual.models import LanguageAnalysis
from app.quiz.models import QuizQuestion, QuizSession
from app.rag.grounded_generation import GroundedGenerationResult


class FakeSupervisor:
    def __init__(self, route: str = "pedagogie") -> None:
        self.route = route
        self.calls = 0

    def invoke_structured(self, request: object) -> object:
        del request
        self.calls += 1
        if self.route == "out_of_domain":
            return {"domain_status": "out_of_domain", "route": "out_of_domain"}
        return {"domain_status": "in_domain", "route": self.route}


class FakeComposer:
    def __init__(self, answer: str = "AZURE_FINAL") -> None:
        self.answer = answer
        self.calls: list[dict[str, object]] = []
        self.validation_attempts: list[dict[str, object]] = []

    def compose(self, business_answer, language, script, **kwargs):
        self.calls.append(
            {
                "business_answer": business_answer,
                "language": language,
                "script": script,
                **kwargs,
            }
        )
        self.validation_attempts.append({"accepted": True, "reasons": []})
        return self.answer


class FailingComposer(FakeComposer):
    def compose(self, business_answer, language, script, **kwargs):
        self.calls.append(
            {
                "business_answer": business_answer,
                "language": language,
                "script": script,
                **kwargs,
            }
        )
        self.validation_attempts.extend([{}, {}])
        raise FinalResponseCompositionError("Azure unavailable")


class GroundedStub:
    def generate(self, request):
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Une action represente une part du capital.",
            citations=[
                {
                    "evidence_id": "S1",
                    "chunk_id": "chunk-s1",
                    "source_id": "source-s1",
                    "title": "Source officielle",
                    "page": 1,
                    "page_start": 1,
                    "page_end": 1,
                    "heading": None,
                }
            ],
            used_evidence_ids=["S1"],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


class StructuredQuizGraph:
    def __init__(self, answer: str, session: QuizSession, route: str = "quiz") -> None:
        self.answer = answer
        self.session = session
        self.route = route

    def invoke(self, state, config):
        del config
        return {
            **state,
            "selected_route": self.route,
            "business_answer": self.answer,
            "quiz_session": self.session,
            "status": "completed",
            "response_key": "quiz",
        }


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def _install_graph(route="pedagogie", grounded_service=None):
    graph = build_graph(
        supervisor_provider=FakeSupervisor(route), grounded_service=grounded_service
    )
    app.dependency_overrides[get_chat_graph] = lambda: graph


@pytest.mark.parametrize(
    ("language", "script"),
    [("fr", "latin"), ("en", "latin"), ("ar", "arabic"), ("ary", "latin"), ("ary", "arabic")],
)
def test_azure_final_answer_is_returned_for_every_supported_locale(monkeypatch, language, script):
    import app.api.chat as chat_api

    composer = FakeComposer(answer=f"FINAL_{language}_{script}")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language=f"ary-{script}" if language == "ary" else language,
            script=script,
            normalized_text=text,
            confidence=1.0,
        ),
    )
    _install_graph()

    body = TestClient(app).post(
        "/chat", json={"message": "Explain this financial concept", "thread_id": language}
    ).json()

    assert body["answer"] == f"FINAL_{language}_{script}"
    assert composer.calls[0]["language"] == language
    assert composer.calls[0]["script"] == script
    assert body["status"] == "ok"


def test_azure_success_does_not_call_a_second_localizer(monkeypatch):
    import app.api.chat as chat_api

    composer = FakeComposer("Une obligation est un titre de dette.")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api, "localize_answer", lambda *args, **kwargs: pytest.fail("legacy localizer called")
    )
    monkeypatch.setattr(
        chat_api,
        "localize_business_answer",
        lambda *args, **kwargs: pytest.fail("Darija localizer called after Azure"),
    )
    _install_graph()

    body = TestClient(app).post(
        "/chat", json={"message": "What is a bond?", "thread_id": "no-double-localization"}
    ).json()

    assert body["answer"] == "Une obligation est un titre de dette."


def test_azure_failure_uses_controlled_legacy_fallback(monkeypatch):
    import app.api.chat as chat_api

    composer = FailingComposer()
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(chat_api, "localize_answer", lambda *args, **kwargs: "Legacy safe answer")
    _install_graph()

    response = TestClient(app).post(
        "/chat", json={"message": "Explain a bond", "thread_id": "azure-fallback"}
    )
    body = response.json()

    assert response.status_code == 200
    assert body["answer"] == "Legacy safe answer"
    assert body["status"] == "ok"


def test_grounded_and_citations_are_unchanged_when_azure_composes(monkeypatch):
    import app.api.chat as chat_api

    composer = FakeComposer("Final grounded answer")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    _install_graph(grounded_service=GroundedStub())

    body = TestClient(app).post(
        "/api/v1/chat", json={"message": "C'est quoi une action ?", "thread_id": "grounded-azure"}
    ).json()

    assert body["answer"] == "Final grounded answer"
    assert body["grounded"] is True
    assert body["citations"] == [
        {
            "evidence_id": "S1",
            "chunk_id": "chunk-s1",
            "source_id": "source-s1",
            "title": "Source officielle",
            "page": 1,
            "page_start": 1,
            "page_end": 1,
            "heading": None,
        }
    ]


def test_ary_latin_azure_failure_preserves_grounded_business_answer(monkeypatch):
    import app.api.chat as chat_api

    composer = FailingComposer()
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ary-latin",
            script="latin",
            normalized_text=text,
            confidence=1.0,
        ),
    )

    _install_graph(grounded_service=GroundedStub())

    body = TestClient(app).post(
        "/api/v1/chat", json={"message": "chno hiya action?", "thread_id": "ary-groq"}
    ).json()

    assert body["answer"] == "Une action represente une part du capital."
    assert body["status"] == "ok"
    assert body["grounded"] is True
    assert body["citations"][0]["source_id"] == "source-s1"


def test_ary_latin_double_azure_failure_preserves_grounded_business_answer(
    monkeypatch,
):
    import app.api.chat as chat_api

    composer = FailingComposer()
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ary-latin",
            script="latin",
            normalized_text=text,
            confidence=1.0,
        ),
    )
    _install_graph(grounded_service=GroundedStub())

    body = TestClient(app).post(
        "/api/v1/chat", json={"message": "chno hiya obligation?", "thread_id": "ary-safe"}
    ).json()

    assert composer.validation_attempts == [{}, {}]
    assert body["answer"] == "Une action represente une part du capital."
    assert body["status"] == "ok"
    assert body["grounded"] is True
    assert body["citations"][0]["source_id"] == "source-s1"
    assert "buy" not in body["answer"].lower()


def test_ary_latin_failure_without_business_answer_keeps_safe_controlled_message(monkeypatch):
    import app.api.chat as chat_api

    class EmptyBusinessGraph:
        def invoke(self, state, config):
            del config
            return {
                **state,
                "selected_route": "pedagogie",
                "business_answer": "",
                "status": "completed",
            }

    composer = FailingComposer()
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ary-latin",
            script="latin",
            normalized_text=text,
            confidence=1.0,
        ),
    )
    app.dependency_overrides[get_chat_graph] = lambda: EmptyBusinessGraph()

    body = TestClient(app).post(
        "/api/v1/chat", json={"message": "chno hiya obligation?", "thread_id": "ary-empty"}
    ).json()

    assert body["answer"]
    assert body["answer"] != ""
    assert body["grounded"] is None
    assert body["citations"] == []


def test_security_refusal_remains_blocked_through_azure(monkeypatch):
    import app.api.chat as chat_api

    composer = FakeComposer("Je ne peux pas recommander un titre pour vous.")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    _install_graph()

    body = TestClient(app).post(
        "/chat", json={"message": "What stock should I buy?", "thread_id": "security-azure"}
    ).json()

    assert body["route"] == "securite"
    assert body["blocked"] is True
    assert body["status"] == "blocked"
    assert body["answer"] == "Je ne peux pas recommander un titre pour vous."


def test_out_of_domain_can_be_composed_without_changing_route(monkeypatch):
    import app.api.chat as chat_api

    composer = FakeComposer("I specialize in financial education.")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    _install_graph(route="out_of_domain")

    body = TestClient(app).post(
        "/chat", json={"message": "What is the capital of Japan?", "thread_id": "ood-azure"}
    ).json()

    assert body["route"] == "out_of_domain"
    assert body["answer"] == "I specialize in financial education."


def _quiz_fixture() -> tuple[str, QuizSession]:
    question = QuizQuestion(
        question_id="quiz-1",
        topic="actions",
        level="beginner",
        prompt="Which instrument represents ownership?",
        options={"A": "A bond", "B": "A stock", "C": "A fee", "D": "An index"},
        correct_option="B",
        explanation="A stock represents ownership in a company.",
    )
    answer = (
        "Question 1/1\nWhich instrument represents ownership?\n"
        "A. A bond\nB. A stock\nC. A fee\nD. An index"
    )
    session = QuizSession(
        quiz_id="quiz-fixture",
        profile_key="quiz-thread",
        phase="quiz",
        level="beginner",
        topic="financial_education",
        questions=[question],
    )
    return answer, session


def test_structured_quiz_bypasses_composer_and_preserves_choices(monkeypatch):
    import app.api.chat as chat_api

    answer, session = _quiz_fixture()
    composer = FakeComposer("A. A stock\nB. A bond")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="fr", script="latin", normalized_text=text, confidence=1.0
        ),
    )
    app.dependency_overrides[get_chat_graph] = lambda: StructuredQuizGraph(answer, session)

    body = TestClient(app).post(
        "/chat", json={"message": "Start the quiz", "thread_id": "quiz-thread"}
    ).json()

    assert composer.calls == []
    assert body["answer"] == answer
    assert "A. A bond\nB. A stock\nC. A fee\nD. An index" in body["answer"]


@pytest.mark.parametrize("route", ["formation_elearning", "orientation"])
def test_indirect_structured_quiz_bypasses_composer_and_preserves_exact_payload(
    monkeypatch, route
):
    import app.api.chat as chat_api

    answer, session = _quiz_fixture()
    composer = FakeComposer("AZURE_REWRITTEN_QUIZ")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    app.dependency_overrides[get_chat_graph] = lambda: StructuredQuizGraph(
        answer, session, route=route
    )

    body = TestClient(app).post(
        "/chat", json={"message": "Start the quiz", "thread_id": f"quiz-{route}"}
    ).json()

    assert composer.calls == []
    assert body["route"] == route
    assert body["answer"] == answer


@pytest.mark.parametrize("route", ["formation_elearning", "orientation"])
def test_non_quiz_formation_and_orientation_still_use_composer(monkeypatch, route):
    import app.api.chat as chat_api

    class NonQuizGraph:
        def invoke(self, state, config):
            del config
            return {
                **state,
                "selected_route": route,
                "business_answer": f"{route} business answer",
                "response_key": route,
                "status": "completed",
            }

    composer = FakeComposer("AZURE_FINAL")
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    app.dependency_overrides[get_chat_graph] = lambda: NonQuizGraph()

    body = TestClient(app).post(
        "/chat", json={"message": "Continue", "thread_id": f"nonquiz-{route}"}
    ).json()

    assert len(composer.calls) == 1
    assert body["answer"] == "AZURE_FINAL"
