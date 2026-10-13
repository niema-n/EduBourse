"""Read-only public RAG API. Uses a fake retrieval service: BGE-M3 is never loaded."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.rag import require_retrieval_service
from app.main import app
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

FORBIDDEN_KEYS = {"index_path", "file_path", "document_hash", "embedding", "embeddings", "vector"}


def _walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


class FakeRetrieval:
    def __init__(self, status="ok"):
        self.requests = []
        self.status = status

    def retrieve(self, request):
        self.requests.append(request)
        chunk = RetrievedChunk(
            chunk_id="ammc-les-opcvm-p003-c001-abcdef01",
            source_id="ammc-les-opcvm",
            title="Les OPCVM",
            page=3,
            page_start=3,
            page_end=4,
            heading=None,
            text="Un OPCVM est un organisme de placement collectif.   " * 40,
            rank=1,
            retrieval_score=0.1234567,
            score_type="cosine_distance",
        )
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original"],
            adapted_query_fr=None,
            chunks=[chunk] if self.status == "ok" else [],
            retrieval_status=self.status,
        )


@pytest.fixture
def fake():
    return FakeRetrieval()


@pytest.fixture
def client(fake):
    app.dependency_overrides[require_retrieval_service] = lambda: fake
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_overview_returns_real_manifest_metadata_without_paths(client):
    response = client.get("/api/v1/rag/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["collection_name"] == "j6_bge_m3_content_v1"
    assert body["embedding_model"] == "BAAI/bge-m3"
    assert body["embedding_dimension"] == 1024
    assert body["indexed_chunk_count"] == 353
    assert body["source_count"] == 13
    assert body["index_status"] in {"available", "not_loaded", "unavailable"}
    assert not FORBIDDEN_KEYS & set(_walk_keys(body))


def test_sources_are_safe_and_account_for_every_indexed_chunk(client):
    response = client.get("/api/v1/rag/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["total_sources"] == len(body["sources"]) == 13
    assert body["total_chunks"] == 353
    assert all(source["chunk_count"] > 0 for source in body["sources"])
    assert not FORBIDDEN_KEYS & set(_walk_keys(body))
    assert "url" not in json.dumps(body)


def test_search_returns_retrieval_only_with_bounded_excerpt(client, fake):
    response = client.post(
        "/api/v1/rag/search", json={"query": "Comment fonctionne un OPCVM ?", "top_k": 3}
    )
    assert response.status_code == 200
    body = response.json()
    assert fake.requests[0].top_k == 3
    assert body["language"] == "fr"
    hit = body["results"][0]
    assert hit["title"] == "Les OPCVM"
    assert hit["authority"] == "ammc"
    assert hit["page_start"] == 3 and hit["page_end"] == 4
    assert len(hit["excerpt"]) <= 701
    assert "  " not in hit["excerpt"]
    assert "answer" not in body
    assert not FORBIDDEN_KEYS & set(_walk_keys(body))


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "x" * 1001},
        {"query": "action", "top_k": 0},
        {"query": "action", "top_k": 11},
        {"query": "action", "collection_name": "other"},
        {"query": "action", "model_name": "other"},
    ],
)
def test_search_rejects_invalid_or_configuration_input(client, fake, payload):
    response = client.post("/api/v1/rag/search", json=payload)
    assert response.status_code == 422
    assert fake.requests == []


def test_search_failure_is_generic_and_leaks_nothing():
    failing = FakeRetrieval(status="provider_error")
    app.dependency_overrides[require_retrieval_service] = lambda: failing
    try:
        response = TestClient(app).post("/api/v1/rag/search", json={"query": "What is an ETF?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"detail": "Le corpus ne peut pas être interrogé pour le moment."}


def test_unavailable_service_returns_503():
    def unavailable():
        from fastapi import HTTPException

        raise HTTPException(503, "Le corpus ne peut pas être interrogé pour le moment.")

    app.dependency_overrides[require_retrieval_service] = unavailable
    try:
        response = TestClient(app).post("/api/v1/rag/search", json={"query": "action"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/rag/overview"),
        ("put", "/api/v1/rag/sources"),
        ("delete", "/api/v1/rag/sources"),
        ("get", "/api/v1/rag/search"),
        ("patch", "/api/v1/rag/search"),
    ],
)
def test_no_mutation_methods(client, method, path):
    assert getattr(client, method)(path).status_code == 405
