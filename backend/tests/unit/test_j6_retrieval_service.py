import hashlib
import inspect
from pathlib import Path

import numpy as np
import pytest

from app.rag.chroma_index import COLLECTION_NAME
from app.rag.query_adapter import ADAPTER_MODEL, ADAPTER_PROMPT_SHA256, AdapterOutput
from app.rag.retrieval_service import (
    INDEX_MANIFEST_SHA256,
    RetrievalRequest,
    RetrievalService,
    service_manifest,
)

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "backend/data/rag/indexes/bge_m3_v1"
SERVICE_MANIFEST = ROOT / "backend/data/rag/manifests/retrieval_service_v1.json"
SERVICE_MANIFEST_SHA256 = "4467a6ed7c8a1d23ee2d90a39159ac0c404567d42c8d7da10d30dfce9e450f1e"


class FakeEmbeddingProvider:
    dimension = 1024
    revision = "5617a9f61b028005a4858fdac845db406aefb181"

    def __init__(self):
        self.queries = []

    def embed_queries(self, texts):
        self.queries.extend(texts)
        vector = np.zeros((len(texts), self.dimension), dtype=np.float32)
        vector[:, 0] = 1.0
        return vector


class FakeAdapter:
    model = ADAPTER_MODEL

    def __init__(self, output=None, error=None):
        self.output = output or AdapterOutput(
            retrieval_query_fr="question en français",
            retrieval_query_ary_arabic="سؤال بالدارجة",
        )
        self.error = error
        self.payloads = []

    def generate(self, payload):
        self.payloads.append(payload)
        if self.error:
            raise self.error
        if payload["language"] == "ary" and payload["script"] == "latin":
            return self.output
        return AdapterOutput(retrieval_query_fr=self.output.retrieval_query_fr)


@pytest.fixture
def service():
    embedding = FakeEmbeddingProvider()
    adapter = FakeAdapter()
    return RetrievalService(ROOT, embedding_provider=embedding, query_adapter=adapter)


@pytest.mark.parametrize(
    ("language", "script", "expected_branches", "adapter_calls"),
    [
        ("fr", "latin", ["original"], 0),
        ("en", "latin", ["french"], 1),
        ("ar", "arabic", ["original", "french"], 1),
        ("ary", "arabic", ["original", "french"], 1),
        ("ary", "latin", ["original", "french", "ary_arabic"], 1),
    ],
)
def test_h1_branch_matrix_and_result_metadata(
    service, language, script, expected_branches, adapter_calls
):
    request = RetrievalRequest(
        original_query="question originale",
        language=language,
        script=script,
    )
    result = service.retrieve(request)
    assert result.retrieval_status == "ok"
    assert result.branches_used == expected_branches
    assert result.original_query == request.original_query
    assert len(service.query_adapter.payloads) == adapter_calls
    assert result.chunks
    assert all(chunk.text and chunk.source_id and chunk.title for chunk in result.chunks)
    assert all(chunk.rank == index for index, chunk in enumerate(result.chunks, start=1))
    expected_score_type = "rrf" if len(expected_branches) > 1 else "cosine_distance"
    assert all(chunk.score_type == expected_score_type for chunk in result.chunks)


def test_ary_latin_queries_full_corpus_before_rrf(service):
    calls = []
    original_query = service.collection.query

    def recording_query(*args, **kwargs):
        calls.append(kwargs["n_results"])
        return original_query(*args, **kwargs)

    service.collection.query = recording_query
    result = service.retrieve(
        RetrievalRequest(original_query="chno lborsa?", language="ary", script="latin")
    )
    assert result.retrieval_status == "ok"
    assert calls == [353, 353, 353]
    assert all(chunk.score_type == "rrf" for chunk in result.chunks)


def test_provider_failure_fails_closed_without_partial_fusion():
    embedding = FakeEmbeddingProvider()
    adapter = FakeAdapter(error=RuntimeError("provider unavailable"))
    service = RetrievalService(ROOT, embedding_provider=embedding, query_adapter=adapter)
    result = service.retrieve(
        RetrievalRequest(original_query="what is a stock?", language="en", script="latin")
    )
    assert result.retrieval_status == "provider_error"
    assert result.chunks == []
    assert result.branches_used == []
    assert embedding.queries == []


@pytest.mark.parametrize(
    ("language", "script"),
    [("en", "latin"), ("ar", "arabic"), ("ary", "arabic"), ("ary", "latin")],
)
def test_provider_failure_has_distinct_retryable_status(language, script):
    service = RetrievalService(
        ROOT,
        embedding_provider=FakeEmbeddingProvider(),
        query_adapter=FakeAdapter(error=RuntimeError("provider unavailable")),
    )
    result = service.retrieve(
        RetrievalRequest(original_query="question", language=language, script=script)
    )
    assert result.retrieval_status == "provider_error"
    assert result.chunks == []
    assert result.branches_used == []


@pytest.mark.parametrize(
    ("language", "script"),
    [("en", "latin"), ("ary", "latin")],
)
def test_missing_adapter_is_a_non_retryable_configuration_error(language, script):
    service = RetrievalService(ROOT, embedding_provider=FakeEmbeddingProvider())
    result = service.retrieve(
        RetrievalRequest(original_query="question", language=language, script=script)
    )
    assert result.retrieval_status == "configuration_error"
    assert result.chunks == []
    assert result.branches_used == []


def test_wrong_adapter_model_is_a_configuration_error():
    adapter = FakeAdapter()
    adapter.model = "another-model"
    service = RetrievalService(
        ROOT, embedding_provider=FakeEmbeddingProvider(), query_adapter=adapter
    )
    result = service.retrieve(
        RetrievalRequest(original_query="question", language="en", script="latin")
    )
    assert result.retrieval_status == "configuration_error"
    assert result.chunks == []
    assert adapter.payloads == []


def test_ary_latin_invalid_required_branch_is_provider_error_without_partial_fusion():
    adapter = FakeAdapter(
        output=AdapterOutput(retrieval_query_fr="question en français")
    )
    service = RetrievalService(
        ROOT, embedding_provider=FakeEmbeddingProvider(), query_adapter=adapter
    )
    result = service.retrieve(
        RetrievalRequest(original_query="question", language="ary", script="latin")
    )
    assert result.retrieval_status == "provider_error"
    assert result.chunks == []
    assert result.branches_used == []


def test_fr_without_adapter_remains_successful():
    service = RetrievalService(ROOT, embedding_provider=FakeEmbeddingProvider())
    result = service.retrieve(
        RetrievalRequest(original_query="question française", language="fr", script="latin")
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["original"]
    assert result.original_query == "question française"


def test_request_bounds_and_language_contract():
    with pytest.raises(ValueError):
        RetrievalRequest(original_query="x", language="fr", script="arabic")
    with pytest.raises(ValueError):
        RetrievalRequest(original_query="x", language="ar", script="latin")
    with pytest.raises(ValueError):
        RetrievalRequest(original_query="x", language="ary", script="latin", top_k=11)


def test_manifest_and_frozen_contract_guards():
    assert SERVICE_MANIFEST.is_file()
    assert hashlib.sha256(SERVICE_MANIFEST.read_bytes()).hexdigest() == SERVICE_MANIFEST_SHA256
    manifest = service_manifest(ROOT)
    assert manifest["index_manifest_sha256"] == INDEX_MANIFEST_SHA256
    assert manifest["collection_name"] == COLLECTION_NAME
    assert manifest["query_adapter_model"] == ADAPTER_MODEL
    assert manifest["query_adapter_prompt_sha256"] == ADAPTER_PROMPT_SHA256
    assert manifest["embedding_function_none_required"] is True
    assert manifest["retrieval_statuses"] == [
        "ok",
        "provider_error",
        "configuration_error",
    ]
    assert manifest["provider_error_retryable"] is True
    assert manifest["configuration_error_retryable"] is False


def test_service_uses_persistent_client_and_explicit_embedding_none():
    source = inspect.getsource(RetrievalService)
    assert "PersistentClient" in source
    assert "HttpClient" not in source
    assert "embedding_function=None" in source
    assert "query_texts" not in source
    assert "query_embeddings" in source
