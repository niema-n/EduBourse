"""Real HTTP/graph/grounding/composer path with deterministic provider boundaries."""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_graph
from app.config import Settings
from app.graph.core import build_graph
from app.graph.final_response_composer import MultilingualFinalResponseComposer
from app.main import app
from app.multilingual.models import LanguageAnalysis
from app.rag.comparison import comparison_concepts, coverage, has_source_mechanics
from app.rag.grounded_generation import GENERATION_MODEL, GroundedGenerationService
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

CASES = [
    (
        "fr",
        "latin",
        "Quelle est la différence entre une action et une obligation ?",
        "Une action est un titre de propriété du capital. Une obligation est un titre de créance.",
    ),
    (
        "en",
        "latin",
        "What is the difference between a stock and a bond?",
        "A stock is an ownership share in a company. A bond is a debt instrument.",
    ),
    (
        "ar",
        "arabic",
        "ما الفرق بين السهم والسند؟",
        "السهم أداة ملكية في الشركة. السند أداة دين على الجهة المصدرة.",
    ),
    (
        "ary",
        "arabic",
        "شنو الفرق بين السهم والسند؟",
        "السهم كيمثل حصة فملكية الشركة ديالك. أما السند فهو دين على الجهة اللي صدراتو.",
    ),
]


def chunk(key, text):
    return RetrievedChunk(
        chunk_id=key,
        source_id="approved-corpus",
        title="Guide officiel",
        page=8,
        page_start=8,
        page_end=8,
        text=text,
        rank=1,
        retrieval_score=0.1,
        score_type="cosine_distance",
    )


class Retrieval:
    def __init__(self):
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        text = (
            "Une action est un titre de propriété du capital."
            if len(self.requests) == 1
            else "Une obligation est un titre de créance."
        )
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original"],
            retrieval_status="ok",
            chunks=[chunk("stock" if len(self.requests) == 1 else "bond", text)],
        )


@pytest.mark.parametrize("language,script,question,answer", CASES)
def test_normal_endpoint_preserves_both_grounded_concepts(
    monkeypatch, language, script, question, answer
):
    exercise_endpoint(monkeypatch, language, script, question, answer)


def test_legacy_darija_localization_cannot_publish_an_incomplete_grounded_answer(monkeypatch):
    exercise_endpoint(monkeypatch, *CASES[3], incomplete_fallback=True)


def exercise_endpoint(monkeypatch, language, script, question, answer, incomplete_fallback=False):
    import app.api.chat as chat_api
    import app.graph.core as core

    # Replace remote provider results, never the security/output guard nodes or graph.
    monkeypatch.setattr(core, "security_decision", lambda text: (False, 1.0, {}, "test"))
    monkeypatch.setattr(chat_api, "get_memory_runtime", lambda: None)
    monkeypatch.setattr(chat_api, "get_conversation_history_store", lambda: None)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ary-arabic" if language == "ary" else language,
            script=script,
            normalized_text=text,
            confidence=1.0,
        ),
    )
    retrieval = Retrieval()
    business_answer = CASES[2][3] if language == "ary" else answer
    calls = []

    def generate(system, prompt):
        calls.append((system, prompt))
        assert "chunk_id: stock" in prompt and "chunk_id: bond" in prompt
        return {
            "answer": business_answer,
            "used_evidence_ids": ["S1", "S2"],
            "insufficient_evidence": False,
        }

    grounding = GroundedGenerationService(
        retrieval,
        provider=SimpleNamespace(model=GENERATION_MODEL, generate=generate),
    )
    supervisor = SimpleNamespace(
        invoke_structured=lambda request: {
            "domain_status": "in_domain",
            "route": "pedagogie",
        }
    )
    graph = build_graph(supervisor_provider=supervisor, grounded_service=grounding)
    azure_calls = []

    def compose(**kwargs):
        azure_calls.append(kwargs)
        assert json.loads(kwargs["input"])["business_answer"] == business_answer
        if incomplete_fallback:
            raise RuntimeError("Provider unavailable")
        return SimpleNamespace(output_text=answer, status="completed")

    composer = MultilingualFinalResponseComposer(
        settings=Settings(
            azure_openai_endpoint="https://example.openai.azure.com/",
            azure_openai_api_key="test",
            azure_openai_deployment="gpt-4.1",
        ),
        client=SimpleNamespace(responses=SimpleNamespace(create=compose)),
    )
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)
    if incomplete_fallback:
        monkeypatch.setattr(chat_api, "get_response_localizer", lambda: None)
        monkeypatch.setattr(
            chat_api,
            "localize_business_answer",
            lambda *args: SimpleNamespace(
                answer="السهم كيمثل حصة فملكية الشركة ديالك.",
                status="ok",
                provider="test",
                retry_count=0,
                guard_result="accepted",
            ),
        )
    app.dependency_overrides[get_chat_graph] = lambda: graph
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat", json={"message": question, "thread_id": f"comparison-{language}"}
            )
    finally:
        app.dependency_overrides.pop(get_chat_graph, None)
    assert response.status_code == 200
    body = response.json()
    if incomplete_fallback:
        assert body["route"] == "pedagogie" and body["status"] == "error"
        assert body["grounded"] is False and body["citations"] == []
        assert "مقارنة موثوقة" in body["answer"]
        return
    assert body["route"] == "pedagogie" and body["status"] == "ok"
    assert body["grounded"] is True and not body["blocked"]
    assert body["language"] == language and body["script"] == script
    assert {c["chunk_id"] for c in body["citations"]} == {"stock", "bond"}
    assert all(c["source_id"] == "approved-corpus" for c in body["citations"])
    # Enrichment stays bounded: the base search plus at most one per compared concept.
    assert 2 <= len(retrieval.requests) <= 1 + len(comparison_concepts(question))
    assert len(calls) == 1 and len(azure_calls) == 1
    assert body["answer"] == answer  # No added unsupported remuneration/risk facts.
    assert not has_source_mechanics(body["answer"])
    assert all("definition" in coverage(body["answer"], c) for c in comparison_concepts(question))
    assert composer.validation_attempts[-1]["accepted"]
