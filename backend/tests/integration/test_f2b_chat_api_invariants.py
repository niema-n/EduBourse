"""F2B regression at the canonical POST /api/v1/chat boundary.

These assert the wire contract the F2 frontend consumes, not just graph state.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_graph
from app.graph.core import build_graph
from app.main import app
from app.rag.grounded_generation import GroundedGenerationResult

# Unicode escape sequences keep the test source ASCII and readable.
# ruff: noqa: E501

CITATION = {
    "evidence_id": "S1",
    "chunk_id": "ammc-demo-p001-c001-abcdef01",
    "source_id": "ammc-demo",
    "title": "Document de demonstration",
    "page": 1,
    "page_start": 1,
    "page_end": 1,
    "heading": None,
}


class ScriptedSupervisor:
    def __init__(self, routes):
        self.routes = list(routes)
        self.calls = 0

    def invoke_structured(self, request):
        del request
        route = self.routes[min(self.calls, len(self.routes) - 1)]
        self.calls += 1
        if route == "out_of_domain":
            return {"domain_status": "out_of_domain", "route": "out_of_domain"}
        return {"domain_status": "in_domain", "route": route}


class GroundedStub:
    def generate(self, request):
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Une action represente une part du capital d'une societe.",
            citations=[CITATION],
            used_evidence_ids=["S1"],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


def _client(routes):
    graph = build_graph(
        supervisor_provider=ScriptedSupervisor(routes),
        grounded_service=GroundedStub(),
    )
    app.dependency_overrides[get_chat_graph] = lambda: graph
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _post(client, message, thread_id):
    response = client.post("/api/v1/chat", json={"message": message, "thread_id": thread_id})
    assert response.status_code == 200
    return response.json()


def test_grounded_answer_still_reports_its_real_citations():
    client = _client(["pedagogie"])
    body = _post(client, "C'est quoi une action ?", "f2b-api-grounded")
    assert body["route"] == "pedagogie"
    assert body["status"] == "ok"
    assert body["grounded"] is True
    assert len(body["citations"]) > 0


def test_true_fallback_reports_no_grounding_and_no_citations():
    client = _client(["fallback"])
    body = _post(client, "hmm ?", "f2b-api-fallback")
    assert body["route"] == "fallback"
    assert body["citations"] == []
    assert body["grounded"] in (False, None)


def test_fallback_after_a_grounded_turn_does_not_reuse_its_citations():
    """The reported defect: turn 2 returned grounded=true with turn 1's citations."""
    client = _client(["pedagogie", "fallback"])
    thread_id = "f2b-api-stale"

    first = _post(client, "C'est quoi une action ?", thread_id)
    second = _post(client, "hmm ?", thread_id)

    assert first["grounded"] is True and len(first["citations"]) > 0
    assert second["route"] == "fallback"
    assert second["citations"] == []
    assert second["grounded"] in (False, None)
    assert first["thread_id"] == second["thread_id"] == thread_id


def test_response_contract_fields_are_unchanged():
    client = _client(["pedagogie"])
    body = _post(client, "C'est quoi une action ?", "f2b-api-contract")
    assert set(body) == {
        "answer",
        "language",
        "script",
        "route",
        "blocked",
        "thread_id",
        "status",
        "grounded",
        "citations",
        "knowledge_source",
        "web_sources",
        "internal_pedagogical_source",
    }
