"""Assistant history API, chat provenance exposure and the shared memory embedder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api import chat as chat_api
from app.api import conversations as conversations_api
from app.api.chat import get_conversation_history_store, process_text_message
from app.database.base import Base
from app.financial_expert.freshness import requires_current_information
from app.financial_expert.provider import FinancialExpertGeneration
from app.financial_expert.service import FinancialExpertService
from app.graph.core import build_graph
from app.main import app
from app.memory.embeddings import MemoryEmbeddingUnavailableError
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.models import ConversationMessageRecord
from app.persistence.thread_store import ConversationThreadStore
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest

THREAD_A = "assistant-0b7e3c1e-1111-4c5d-9a8b-000000000001"
THREAD_B = "assistant-0b7e3c1e-2222-4c5d-9a8b-000000000002"


def make_store(tmp_path) -> SqlAlchemyConversationHistoryStore:
    database = PersistenceDatabase(
        enabled=True,
        database_url=f"sqlite:///{tmp_path / 'history.db'}",
        engine_factory=lambda url, **kwargs: create_engine(url, **kwargs),
    )
    Base.metadata.create_all(database.get_engine())
    return SqlAlchemyConversationHistoryStore(database, ConversationThreadStore(database))


@pytest.fixture
def client_with_store(tmp_path):
    store = make_store(tmp_path)
    app.dependency_overrides[get_conversation_history_store] = lambda: store
    try:
        yield TestClient(app), store
    finally:
        app.dependency_overrides.pop(get_conversation_history_store, None)


def shift_thread_time(store, thread_id: str, minutes: int) -> None:
    with store.database.get_session_factory().begin() as session:
        for record in session.query(ConversationMessageRecord).filter_by(thread_id=thread_id):
            record.created_at = datetime(2026, 9, 14, 10, tzinfo=UTC) + timedelta(minutes=minutes)


# ---------------------------------------------------------------- history API


def test_empty_history_lists_no_conversation(client_with_store):
    client, _ = client_with_store
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_lists_only_assistant_threads_newest_first_with_deterministic_titles(client_with_store):
    client, store = client_with_store
    store.append_turn(
        THREAD_A, "le masi a augmente combien le vendredi 11/09", "Réponse A", route="pedagogie"
    )
    store.append_turn(THREAD_B, "C'est quoi une action ?", "Réponse B", route="pedagogie")
    store.append_turn(THREAD_B, "Et quels sont ses avantages ?", "Réponse B2", route="pedagogie")
    store.append_turn("voice-thread-not-listed", "Bonjour", "Salut", route="pedagogie")
    store.append_turn("integration-0000-not-listed", "Bonjour", "Salut", route="pedagogie")
    shift_thread_time(store, THREAD_A, 1)
    shift_thread_time(store, THREAD_B, 5)

    body = client.get("/api/v1/conversations").json()["conversations"]

    assert [item["thread_id"] for item in body] == [THREAD_B, THREAD_A]
    assert body[0]["title"] == "C'est quoi une action ?"
    assert body[0]["message_count"] == 4
    assert body[1]["title"] == "Le masi a augmente combien le vendredi 11/09"
    assert set(body[0]) == {"thread_id", "title", "updated_at", "message_count"}


def test_list_limit_is_bounded(client_with_store):
    client, _ = client_with_store
    assert client.get("/api/v1/conversations?limit=0").status_code == 422
    assert client.get("/api/v1/conversations?limit=101").status_code == 422


def test_detail_restores_chronological_user_visible_turns(client_with_store):
    client, store = client_with_store
    store.append_turn(
        THREAD_A,
        "C'est quoi une action ?",
        "Une action est un titre de propriété.",
        language="fr",
        script="latin",
        route="pedagogie",
        knowledge_source="rag",
    )
    store.append_turn(THREAD_A, "Et quels sont ses avantages ?", "Dividendes.", route="pedagogie")

    body = client.get(f"/api/v1/conversations/{THREAD_A}").json()

    assert body["thread_id"] == THREAD_A
    assert body["truncated"] is False
    assert [(m["role"], m["content"]) for m in body["messages"]] == [
        ("user", "C'est quoi une action ?"),
        ("assistant", "Une action est un titre de propriété."),
        ("user", "Et quels sont ses avantages ?"),
        ("assistant", "Dividendes."),
    ]
    assert body["messages"][1]["knowledge_source"] == "rag"
    assert set(body["messages"][0]) == {
        "turn_index",
        "role",
        "content",
        "language",
        "script",
        "route",
        "knowledge_source",
        "created_at",
    }


def test_detail_is_bounded(client_with_store, monkeypatch):
    client, store = client_with_store
    monkeypatch.setattr(conversations_api, "MAX_MESSAGES", 2)
    store.append_turn(THREAD_A, "q1", "a1")
    store.append_turn(THREAD_A, "q2", "a2")

    body = client.get(f"/api/v1/conversations/{THREAD_A}").json()

    assert body["truncated"] is True
    assert [m["content"] for m in body["messages"]] == ["q1", "a1"]


@pytest.mark.parametrize(
    "thread_id",
    ["voice-0b7e3c1e-1111", "integration-0b7e3c1e-1111", "assistant-bad!id", "assistant-x"],
)
def test_detail_rejects_non_assistant_or_malformed_thread_ids(client_with_store, thread_id):
    client, _ = client_with_store
    assert client.get(f"/api/v1/conversations/{thread_id}").status_code == 422


def test_unknown_conversation_is_404(client_with_store):
    client, _ = client_with_store
    assert client.get(f"/api/v1/conversations/{THREAD_A}").status_code == 404


def test_history_is_503_when_persistence_is_disabled():
    app.dependency_overrides[get_conversation_history_store] = lambda: None
    try:
        client = TestClient(app)
        assert client.get("/api/v1/conversations").status_code == 503
        assert client.get(f"/api/v1/conversations/{THREAD_A}").status_code == 503
    finally:
        app.dependency_overrides.pop(get_conversation_history_store, None)


def test_title_is_deterministic_and_truncated_on_a_word():
    title = conversations_api.conversation_title(
        "  quelle   est la différence entre une obligation et une action "
        "cotée à la bourse de casablanca ?"
    )
    assert title.startswith("Quelle est la différence")
    assert title.endswith("…")
    assert len(title) <= conversations_api.TITLE_MAX_CHARS + 1
    assert conversations_api.conversation_title("") == "Conversation"


def test_delete_history_preserves_other_conversations(client_with_store):
    client, store = client_with_store
    store.append_turn(THREAD_A, "Question A", "Answer A")
    store.append_turn(THREAD_B, "Question B", "Answer B")
    response = client.delete(f"/api/v1/conversations/{THREAD_A}")
    assert response.status_code == 204
    assert not response.content
    assert client.get(f"/api/v1/conversations/{THREAD_A}").status_code == 404
    assert client.get(f"/api/v1/conversations/{THREAD_B}").status_code == 200
    remaining = client.get("/api/v1/conversations").json()["conversations"]
    assert [item["thread_id"] for item in remaining] == [THREAD_B]
    assert store.list_messages(THREAD_A) == []
    assert client.delete(f"/api/v1/conversations/{THREAD_A}").status_code == 204


def test_delete_rejects_non_assistant_threads(client_with_store):
    client, store = client_with_store
    store.append_turn("voice-12345678", "Question", "Answer")
    assert client.delete("/api/v1/conversations/voice-12345678").status_code == 422
    assert len(store.list_messages("voice-12345678")) == 2


def test_delete_unavailable_database():
    app.dependency_overrides[get_conversation_history_store] = lambda: None
    try:
        assert TestClient(app).delete(f"/api/v1/conversations/{THREAD_A}").status_code == 503
    finally:
        app.dependency_overrides.pop(get_conversation_history_store, None)


def test_history_pagination(client_with_store):
    client, store = client_with_store
    store.append_turn(THREAD_A, "Question A", "Answer A")
    store.append_turn(THREAD_B, "Question B", "Answer B")
    shift_thread_time(store, THREAD_A, 1)
    shift_thread_time(store, THREAD_B, 2)
    first = client.get("/api/v1/conversations?limit=1").json()["conversations"]
    second = client.get("/api/v1/conversations?limit=1&offset=1").json()["conversations"]
    assert first[0]["thread_id"] == THREAD_B
    assert second[0]["thread_id"] == THREAD_A
    assert client.get("/api/v1/conversations?offset=-1").status_code == 422


def test_history_routes_support_read_and_delete():
    methods = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/conversations")
        for method in operations
    }
    assert methods == {
        ("/api/v1/conversations", "GET"),
        ("/api/v1/conversations/{thread_id}", "GET"),
        ("/api/v1/conversations/{thread_id}", "DELETE"),
    }


# ---------------------------------------------------------------- provenance


class FakeExpertProvider:
    provider_name = "fake-gemini"
    model = "gemini-2.5-flash"

    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, question, system_prompt, *, use_web_grounding=False):
        self.calls.append(use_web_grounding)
        return self.response


class Grounded:
    def __init__(self, insufficient: bool):
        self.insufficient = insufficient
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Sources insuffisantes." if self.insufficient else "Réponse du corpus.",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="insufficient_evidence" if self.insufficient else "ok",
            grounded=not self.insufficient,
            insufficient_evidence=self.insufficient,
            provider_retryable=False,
        )


def graph_for(route: str, grounded: Grounded, expert_provider: FakeExpertProvider):
    return build_graph(
        supervisor_provider=SimpleNamespace(
            invoke_structured=lambda request: {
                "domain_status": "out_of_domain" if route == "out_of_domain" else "in_domain",
                "route": route,
            }
        ),
        grounded_service=grounded,
        financial_expert_service=FinancialExpertService(
            expert_provider, web_grounding_enabled=True
        ),
        financial_expert_fallback_enabled=True,
    )


@pytest.fixture(autouse=True)
def french_localizer(monkeypatch):
    # French answers need no localization; keep the test offline.
    monkeypatch.setattr(
        chat_api,
        "localize_business_answer",
        lambda answer, language, script, localizer: SimpleNamespace(
            status="ok",
            answer=answer,
            provider="test",
            retry_count=0,
            guard_result="accepted",
        ),
    )


def test_web_grounded_answer_exposes_provenance_and_bounded_https_sources():
    sources = tuple(
        {
            "domain": "casablanca-bourse.com",
            "title": f"source {i}",
            "uri": f"https://example.test/{i}",
        }
        for i in range(14)
    )
    provider = FakeExpertProvider(
        FinancialExpertGeneration(
            text="Réponse confirmée par une source web.",
            web_grounded=True,
            web_sources=(
                {"domain": "ammc.ma", "title": "insecure", "uri": "http://example.test/x"},
                *sources,
            ),
        )
    )
    response = process_text_message(
        ChatRequest(message="Le MASI a augmenté de combien le vendredi 11/09 ?", thread_id="t-web"),
        graph_for("pedagogie", Grounded(insufficient=True), provider),
    )

    assert provider.calls == [True]
    assert response.knowledge_source == "llm_web_grounded_financial_knowledge"
    assert response.grounded is False
    assert response.citations == []
    assert len(response.web_sources) == 10
    assert response.web_sources[0].title == "insecure" and response.web_sources[0].uri is None
    assert all(s.uri is None or s.uri.startswith("https://") for s in response.web_sources)


def test_rag_answer_reports_rag_provenance_without_web_research():
    provider = FakeExpertProvider(FinancialExpertGeneration(text="must not run"))
    response = process_text_message(
        ChatRequest(message="C'est quoi une action ?", thread_id="t-rag"),
        graph_for("pedagogie", Grounded(insufficient=False), provider),
    )
    assert provider.calls == []
    assert response.knowledge_source == "rag"
    assert response.web_sources == []


def test_out_of_domain_never_reaches_external_research():
    grounded = Grounded(insufficient=True)
    provider = FakeExpertProvider(FinancialExpertGeneration(text="must not run", web_grounded=True))
    response = process_text_message(
        ChatRequest(message="Donne-moi une recette de pizza", thread_id="t-ood"),
        graph_for("out_of_domain", grounded, provider),
    )
    assert response.route == "out_of_domain"
    assert provider.calls == [] and grounded.calls == 0
    assert response.knowledge_source is None and response.web_sources == []


def test_personalized_advice_is_blocked_before_external_research():
    grounded = Grounded(insufficient=True)
    provider = FakeExpertProvider(FinancialExpertGeneration(text="must not run", web_grounded=True))
    response = process_text_message(
        ChatRequest(message="Quelle action dois-je acheter ?", thread_id="t-sec"),
        graph_for("pedagogie", grounded, provider),
    )
    assert response.route == "securite" and response.blocked is True
    assert provider.calls == [] and grounded.calls == 0
    assert response.knowledge_source is None and response.web_sources == []


@pytest.mark.parametrize(
    "question",
    [
        "le masi a augmente combien le vendredi 11/09",
        "le MASI a augmenté combien le vendredi 11/09 ?",
        "Le MASI a baissé hier ?",
        "How much did the MASI index rise yesterday?",
        "ch7al tla3 masi lbar7?",
        "كم ارتفع مؤشر مازي البارح؟",
    ],
)
def test_dated_index_moves_are_current_information(question):
    assert requires_current_information(question, "fr", "latin") is True


@pytest.mark.parametrize(
    "question",
    [
        "Qu'est-ce que le MASI ?",
        "Comment est calculé le MASI ?",
        "C'est quoi un indice boursier ?",
        "What is a stock market index?",
        "Donne-moi une recette de pizza",
        "Et quels sont ses avantages ?",
    ],
)
def test_educational_index_questions_stay_general(question):
    assert requires_current_information(question, "fr", "latin") is False


def test_financial_expert_model_is_configurable(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setenv("GEMINI_FINANCIAL_EXPERT_MODEL", "gemini-3.5-flash")
    get_settings.cache_clear()
    try:
        assert FinancialExpertService.from_environment().provider.model == "gemini-3.5-flash"
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- shared BGE


def test_memory_runtime_reuses_the_rag_embedding_instance(monkeypatch):
    sentinel = SimpleNamespace(dimension=1024)
    monkeypatch.setattr(chat_api, "get_conversation_history_store", lambda: object())
    monkeypatch.setattr(
        chat_api, "get_retrieval_service", lambda: SimpleNamespace(embedding_provider=sentinel)
    )
    chat_api.get_memory_runtime.cache_clear()
    try:
        runtime = chat_api.get_memory_runtime()
        assert runtime.embedder._get_provider() is sentinel
    finally:
        chat_api.get_memory_runtime.cache_clear()


def test_memory_embedder_never_loads_a_second_model_when_rag_is_unavailable(monkeypatch):
    monkeypatch.setattr(chat_api, "get_retrieval_service", lambda: None)
    with pytest.raises(MemoryEmbeddingUnavailableError):
        chat_api.shared_retrieval_embedding_provider()
