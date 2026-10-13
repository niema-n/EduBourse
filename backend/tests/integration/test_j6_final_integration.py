import hashlib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.chat import get_chat_graph
from app.graph.core import build_graph
from app.main import app
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroundedGenerationResult,
)
from app.rag.retrieval_service import RetrievalService

ROOT = Path(__file__).resolve().parents[3]
FINAL_MANIFEST = ROOT / "backend/data/rag/manifests/j6_final_v1.json"
FINAL_MANIFEST_SHA256 = "2fc033932884f10ac0181d20a078a1ff2d1aa3a71383b5e30aecea52f416afe3"


class Supervisor:
    def __init__(self, route="pedagogie"):
        self.route = route
        self.calls = 0

    def invoke_structured(self, request):
        self.calls += 1
        if self.route == "out_of_domain":
            return {"domain_status": "out_of_domain", "route": "out_of_domain"}
        return {"domain_status": "in_domain", "route": self.route}


class GroundedFake:
    def __init__(self, *, answer="Grounded answer.", status="ok", grounded=True):
        self.answer = answer
        self.status = status
        self.grounded = grounded
        self.calls = []

    def generate(self, request):
        self.calls.append(request)
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=self.answer if self.status in {"ok", "insufficient_evidence"} else None,
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status=self.status,
            grounded=self.grounded,
            insufficient_evidence=self.status == "insufficient_evidence",
            provider_retryable=self.status
            in {"retrieval_provider_error", "generation_provider_error"},
        )


def _client(route="pedagogie", grounded=None):
    supervisor = Supervisor(route)
    graph = build_graph(supervisor_provider=supervisor, grounded_service=grounded)
    app.dependency_overrides[get_chat_graph] = lambda: graph
    return TestClient(app), supervisor


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("message", "language", "script", "answer"),
    [
        ("Explique une action", "fr", "latin", "Réponse fondée en français."),
        ("What is a stock?", "en", "latin", "Grounded answer in English."),
        ("ما هو السهم؟", "ar", "arabic", "إجابة مبنية على المصادر."),
        ("chno howa saham?", "ary", "latin", "Jawab mabni 3la lmṣadir."),
        ("شنو هو السهم؟", "ary", "arabic", "الجواب مبني على المصادر."),
    ],
)
def test_five_language_api_e2e(message, language, script, answer):
    grounded = GroundedFake(answer=answer)
    client, _ = _client(grounded=grounded)
    response = client.post("/chat", json={"message": message, "thread_id": language})
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "pedagogie"
    assert body["language"] == language
    assert body["script"] == script
    assert body["answer"] == answer
    assert body["grounded"] is True
    assert grounded.calls[0].original_query == message


def test_citations_are_propagated_without_fabricated_urls():
    grounded = GroundedFake(answer="Grounded answer.")
    grounded.generate = lambda request: GroundedGenerationResult(
        original_query=request.original_query,
        language=request.language,
        script=request.script,
        answer="Grounded answer.",
        citations=[
            {
                "evidence_id": "S1",
                "chunk_id": "c1",
                "source_id": "official",
                "title": "Guide",
                "page": 2,
                "page_start": 2,
                "page_end": 2,
                "heading": "Stocks",
            }
        ],
        used_evidence_ids=["S1"],
        retrieval_status="ok",
        generation_status="ok",
        grounded=True,
        insufficient_evidence=False,
        provider_retryable=False,
    )
    client, _ = _client(grounded=grounded)
    body = client.post("/chat", json={"message": "What is a stock?", "thread_id": "cite"}).json()
    assert body["citations"][0]["source_id"] == "official"
    assert "url" not in body["citations"][0]


@pytest.mark.parametrize("route", ["out_of_domain", "quiz"])
def test_non_grounded_routes_do_not_call_grounded_service(route):
    grounded = GroundedFake()
    client, _ = _client(route=route, grounded=grounded)
    body = client.post("/chat", json={"message": "Explain this", "thread_id": route}).json()
    assert body["route"] == route
    assert grounded.calls == []


def test_security_bypasses_grounding():
    grounded = GroundedFake()
    client, supervisor = _client(grounded=grounded)
    body = client.post(
        "/chat",
        json={"message": "Which stock should I buy tomorrow?", "thread_id": "security"},
    ).json()
    assert body["blocked"] is True
    assert grounded.calls == []
    assert supervisor.calls == 0


@pytest.mark.parametrize(
    "status",
    [
        "retrieval_provider_error",
        "retrieval_configuration_error",
        "generation_provider_error",
        "generation_configuration_error",
        "grounding_error",
    ],
)
def test_grounding_failures_are_controlled_and_not_ungrounded(status):
    grounded = GroundedFake(status=status, grounded=False)
    client, _ = _client(grounded=grounded)
    body = client.post("/chat", json={"message": "What is a stock?", "thread_id": status}).json()
    assert body["status"] == "error"
    assert body["grounded"] is False
    assert body["answer"]
    assert "stack" not in body["answer"].lower()


def test_insufficient_evidence_is_safe_and_not_an_ungrounded_answer():
    grounded = GroundedFake(
        answer="The sources are insufficient.", status="insufficient_evidence", grounded=False
    )
    client, _ = _client(grounded=grounded)
    body = client.post("/chat", json={"message": "What is a stock?", "thread_id": "thin"}).json()
    assert body["status"] == "ok"
    assert body["grounded"] is False
    assert body["answer"] == "The sources are insufficient."


def test_real_local_retrieval_is_used_with_fake_generation():
    class Embedding:
        dimension = 1024
        revision = "5617a9f61b028005a4858fdac845db406aefb181"

        def embed_queries(self, texts):
            vectors = np.zeros((len(texts), 1024), dtype=np.float32)
            vectors[:, 0] = 1
            return vectors

    class Adapter:
        model = "qwen/qwen3.8-27b"  # must match the live ADAPTER_MODEL constant

        def generate(self, payload):
            from app.rag.query_adapter import AdapterOutput

            return AdapterOutput(retrieval_query_fr=payload["original_query"])

    retrieval = RetrievalService(ROOT, embedding_provider=Embedding(), query_adapter=Adapter())
    from app.rag.grounded_generation import GroundedGenerationService, GroundedProviderOutput

    class Provider:
        model = GENERATION_MODEL

        def generate(self, system_prompt, user_prompt):
            return GroundedProviderOutput(
                answer="A stock represents a share in a company.",
                used_evidence_ids=["S1"],
                insufficient_evidence=False,
            )

    grounded = GroundedGenerationService(retrieval, provider=Provider())
    client, _ = _client(grounded=grounded)
    body = client.post("/chat", json={"message": "What is a stock?", "thread_id": "real"}).json()
    assert body["grounded"] is True
    assert body["citations"][0]["source_id"]


def test_final_manifest_pins_all_frozen_j6_components():
    assert hashlib.sha256(FINAL_MANIFEST.read_bytes()).hexdigest() == FINAL_MANIFEST_SHA256
    manifest = __import__("json").loads(FINAL_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["retrieval_service_manifest_sha256"] == (
        "4467a6ed7c8a1d23ee2d90a39159ac0c404567d42c8d7da10d30dfce9e450f1e"
    )
    assert manifest["grounded_generation_manifest_sha256"] == (
        "4a98e96df45ad177e311d3a99cbf250b6cdd3cf18e1bb39262921053650c9d7a"
    )
    assert manifest["retrieval_science_frozen"] is True
    assert manifest["production_integration"] is True
