from types import SimpleNamespace
from unittest.mock import Mock

import chromadb
import pytest

from app.api import chat as chat_api
from app.formation.content import modules_for
from app.graph.core import build_graph
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.multilingual.models import LanguageAnalysis
from app.schemas.chat import ChatRequest


@pytest.fixture
def runtime(monkeypatch):
    service = LearningProfileService(InMemoryLearningProfileStore())
    supervisor = SimpleNamespace(route="formation_elearning")
    supervisor.invoke_structured = lambda request: {
        "domain_status": "in_domain",
        "route": supervisor.route,
    }
    no_rag = Mock(side_effect=AssertionError("Formation must not call RAG/Chroma"))
    monkeypatch.setattr(chat_api, "get_retrieval_service", no_rag)
    monkeypatch.setattr(chromadb, "HttpClient", no_rag)
    monkeypatch.setattr(chromadb, "PersistentClient", no_rag)
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: None)
    monkeypatch.setattr(chat_api, "get_conversation_history_store", lambda: None)
    monkeypatch.setattr(
        chat_api,
        "localize_business_answer",
        lambda answer, *args: SimpleNamespace(
            answer=answer,
            status="already_localized",
            provider=None,
            retry_count=0,
            guard_result="accepted",
        ),
    )
    graph = build_graph(
        supervisor_provider=supervisor,
        learning_profile_service=service,
        grounded_service=SimpleNamespace(generate=no_rag),
    )
    yield graph, service, supervisor
    no_rag.assert_not_called()


@pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
@pytest.mark.parametrize(
    "language,script",
    [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ],
)
def test_internal_provenance_matches_shown_module_without_rag(
    runtime, monkeypatch, level, language, script
):
    graph, service, _ = runtime
    service.set_level("source", level, "manual")
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
    for index, message in enumerate(("formation", "next")):
        response = chat_api.process_text_message(
            ChatRequest(message=message, thread_id="source"),
            graph,
        )
        source = response.internal_pedagogical_source
        module = modules_for(level)[index]
        title = module["content"][f"{language}/{script}"]["title"]
        assert response.route == "formation_elearning"
        assert response.grounded is None
        assert response.citations == []
        assert response.knowledge_source is None
        assert response.web_sources == []
        assert source.module_title == title
        assert title in response.answer
        assert source.description in response.answer
        assert source.path_id == f"{level}_financial_learning"
        assert source.module_id == module["module_id"]
        assert source.module_number == index + 1
        assert source.module_count == len(modules_for(level))
        assert source.level == level
        assert "EduBourse" in source.label
        assert (
            response.model_dump(mode="json")["internal_pedagogical_source"]["module_title"] == title
        )


@pytest.mark.parametrize("message", ["pause", "cancel formation", "Teste mon niveau"])
def test_non_module_turn_does_not_reuse_previous_source(runtime, message):
    graph, service, _ = runtime
    service.set_level("source", "beginner", "manual")
    first = chat_api.process_text_message(
        ChatRequest(message="formation", thread_id="source"), graph
    )
    assert first.internal_pedagogical_source is not None
    second = chat_api.process_text_message(ChatRequest(message=message, thread_id="source"), graph)
    assert second.internal_pedagogical_source is None
    assert second.citations == []


def test_clarification_has_no_module_source(runtime):
    graph, _, _ = runtime
    response = chat_api.process_text_message(
        ChatRequest(message="Je veux suivre une formation", thread_id="unknown"),
        graph,
    )
    assert response.internal_pedagogical_source is None


@pytest.mark.parametrize("route", ["orientation", "quiz", "cisi", "support_ecole"])
def test_other_routes_do_not_expose_previous_formation_source(runtime, route):
    graph, service, supervisor = runtime
    service.set_level("source", "beginner", "manual")
    chat_api.process_text_message(ChatRequest(message="formation", thread_id="source"), graph)
    supervisor.route = route
    response = chat_api.process_text_message(
        ChatRequest(message="Guide-moi", thread_id="source"),
        graph,
    )
    assert response.route == route
    assert response.internal_pedagogical_source is None
