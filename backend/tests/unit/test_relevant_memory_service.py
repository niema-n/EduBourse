from concurrent.futures import ThreadPoolExecutor
from time import sleep
from types import SimpleNamespace

import numpy as np
import pytest

from app.memory.relevant_memory_service import (
    DEFAULT_MEMORY_SIMILARITY_THRESHOLD,
    MAX_RELEVANT_MEMORIES,
    RelevantConversationMemoryService,
)
from app.memory.vector_index import (
    MEMORY_VECTOR_COLLECTION_NAME,
    ChromaMemoryVectorIndex,
    thread_ref,
)


def record(message_id, thread_id, turn_index, role, content, language="fr", script="latin"):
    return SimpleNamespace(
        id=message_id,
        thread_id=thread_id,
        turn_index=turn_index,
        role=role,
        content=content,
        language=language,
        script=script,
        route="pedagogie",
        knowledge_source=None,
    )


class FakeHistory:
    def __init__(self, records):
        self.records = records
        self.list_by_ids_calls = 0

    def list_messages(self, thread_id, *, limit=None):
        return [item for item in self.records if item.thread_id == thread_id]

    def list_messages_by_ids(self, thread_id, message_ids):
        self.list_by_ids_calls += 1
        requested = set(message_ids)
        return [
            item for item in self.records if item.thread_id == thread_id and item.id in requested
        ]


class FakeEmbedder:
    dimension = 3

    def __init__(self):
        self.text_calls = []
        self.query_calls = []

    def embed_texts(self, texts):
        self.text_calls.append(texts)
        return np.asarray([[float(index), 1.0, 0.0] for index, _ in enumerate(texts, 1)])

    def embed_query(self, text):
        self.query_calls.append(text)
        return np.asarray([1.0, 0.0, 0.0])


class FakeProvider:
    dimension = 3

    def embed_passages(self, texts):
        return np.asarray([[1.0, 0.0, 0.0] for _ in texts])

    def embed_queries(self, texts):
        return np.asarray([[1.0, 0.0, 0.0] for _ in texts])


class FakeIndex:
    def __init__(self, hits=None):
        self.hits = hits or []
        self.upserts = []
        self.deleted = []
        self.queries = []
        self.ids = []

    def upsert(self, **payload):
        self.upserts.append(payload)
        self.ids = sorted(set(self.ids) | set(payload["ids"]))

    def query(self, *, embedding, top_k, where):
        self.queries.append((embedding, top_k, where))
        selected = self.hits[:top_k]
        return {
            "ids": [
                [f"memory:{thread_ref('thread-a')}:{message_id}" for message_id, _ in selected]
            ],
            "distances": [[1.0 - score for _, score in selected]],
            "metadatas": [[{"message_id": message_id} for message_id, _ in selected]],
        }

    def delete_thread(self, thread_hash):
        self.deleted.append(thread_hash)
        self.ids = []

    def list_thread_ids(self, thread_hash):
        return self.ids

    def delete_ids(self, ids):
        self.ids = [item for item in self.ids if item not in ids]

    def count_thread(self, thread_hash):
        return 0


def make_service(records, hits=None):
    return RelevantConversationMemoryService(
        FakeHistory(records),
        vector_index=FakeIndex(hits),
        embedder=FakeEmbedder(),
    )


def test_empty_index_returns_empty_context():
    service = make_service([])
    result = service.search_relevant("thread-a", "old preference")
    assert result.hits == ()
    assert result.hit_count == 0


def test_rebuild_indexes_canonical_messages_in_batches_and_is_idempotent():
    records = [
        record(1, "thread-a", 1, "user", "Je préfère les obligations."),
        record(2, "thread-a", 1, "assistant", "Voici une explication."),
        record(3, "thread-b", 1, "user", "Other thread"),
    ]
    service = make_service(records)

    assert service.rebuild_thread_index("thread-a") == 2
    assert service.rebuild_thread_index("thread-a") == 2
    assert len(service.vector_index.upserts) == 2
    assert service.vector_index.deleted == []
    assert service.vector_index.upserts[0]["metadatas"][0]["thread_ref"] == thread_ref("thread-a")
    assert "thread-a" not in service.vector_index.upserts[0]["ids"][0]


def test_failed_rebuild_preserves_existing_index_and_retry_converges():
    records = [record(1, "thread-a", 1, "user", "old")]
    index = FakeIndex()
    healthy = RelevantConversationMemoryService(
        FakeHistory(records), vector_index=index, embedder=FakeEmbedder()
    )
    healthy.rebuild_thread_index("thread-a")
    old_ids = list(index.ids)

    class BrokenEmbedder(FakeEmbedder):
        def embed_texts(self, texts):
            raise RuntimeError("EMBED_SECRET_INTERNAL_4412")

    broken = RelevantConversationMemoryService(
        FakeHistory([record(2, "thread-a", 2, "user", "new")]),
        vector_index=index,
        embedder=BrokenEmbedder(),
    )
    with pytest.raises(RuntimeError, match="memory index rebuild failed"):
        broken.rebuild_thread_index("thread-a")
    assert index.ids == old_ids

    broken.embedder = FakeEmbedder()
    assert broken.rebuild_thread_index("thread-a") == 1
    assert index.ids == [broken._document_id(thread_ref("thread-a"), 2)]


def test_failed_upsert_preserves_existing_index():
    records = [record(1, "thread-a", 1, "user", "old")]
    index = FakeIndex()
    service = RelevantConversationMemoryService(
        FakeHistory(records), vector_index=index, embedder=FakeEmbedder()
    )
    service.rebuild_thread_index("thread-a")
    old_ids = list(index.ids)

    class BrokenIndex(FakeIndex):
        def __init__(self, existing):
            super().__init__()
            self.ids = list(existing)

        def upsert(self, **payload):
            raise RuntimeError("CHROMA_SECRET_INTERNAL_4411")

    broken_index = BrokenIndex(old_ids)
    broken = RelevantConversationMemoryService(
        FakeHistory([record(2, "thread-a", 2, "user", "new")]),
        vector_index=broken_index,
        embedder=FakeEmbedder(),
    )
    with pytest.raises(RuntimeError, match="memory index rebuild failed"):
        broken.rebuild_thread_index("thread-a")
    assert broken_index.ids == old_ids


def test_successful_rebuild_removes_stale_ids_and_empty_history_clears():
    initial = [
        record(1, "thread-a", 1, "user", "one"),
        record(2, "thread-a", 2, "user", "two"),
        record(3, "thread-a", 3, "user", "three"),
    ]
    index = FakeIndex()
    service = RelevantConversationMemoryService(
        FakeHistory(initial), vector_index=index, embedder=FakeEmbedder()
    )
    service.rebuild_thread_index("thread-a")
    updated = RelevantConversationMemoryService(
        FakeHistory([initial[0], initial[1], record(4, "thread-a", 4, "user", "four")]),
        vector_index=index,
        embedder=FakeEmbedder(),
    )
    updated.rebuild_thread_index("thread-a")
    assert index.ids == [
        updated._document_id(thread_ref("thread-a"), message_id) for message_id in (1, 2, 4)
    ]
    empty = RelevantConversationMemoryService(
        FakeHistory([]), vector_index=index, embedder=FakeEmbedder()
    )
    empty.rebuild_thread_index("thread-a")
    assert index.ids == []


def test_local_bge_uses_frozen_snapshot_and_local_files_only(monkeypatch, tmp_path):
    import app.rag.embedding_benchmark as benchmark
    from app.memory.embeddings import LocalBGEEmbedder

    calls = {}

    def verify(snapshot):
        calls["snapshot"] = snapshot

    class Provider:
        dimension = 1024

        def __init__(self, spec, **kwargs):
            calls["revision"] = kwargs["revision"]
            calls["model_ref"] = kwargs["model_ref"]
            calls["model_kwargs"] = kwargs["model_kwargs"]

        def embed_queries(self, texts):
            return np.asarray([[1.0, 0.0, 0.0]])

    monkeypatch.setattr(benchmark, "verify_sentence_transformer_snapshot", verify)
    monkeypatch.setattr(benchmark, "SentenceTransformerEmbeddingProvider", Provider)
    embedder = LocalBGEEmbedder(model_ref=tmp_path / "snapshot")
    embedder.embed_query("query")

    assert calls["snapshot"] == tmp_path / "snapshot"
    assert calls["model_ref"] == tmp_path / "snapshot"
    assert calls["revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert calls["model_kwargs"] == {"local_files_only": True}


def test_missing_local_bge_snapshot_raises_safe_error(tmp_path):
    from app.memory.embeddings import LocalBGEEmbedder, MemoryEmbeddingUnavailableError

    embedder = LocalBGEEmbedder(model_ref=tmp_path / "missing-snapshot")
    with pytest.raises(MemoryEmbeddingUnavailableError, match="local memory embedding"):
        embedder.embed_query("query")


def test_local_bge_constructs_provider_once_under_concurrency():
    created = []

    def factory():
        sleep(0.01)
        created.append(True)
        return FakeProvider()

    from app.memory.embeddings import LocalBGEEmbedder

    embedder = LocalBGEEmbedder(provider_factory=factory)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(embedder.embed_query, ["query"] * 8))
    assert len(created) == 1


def test_operational_search_failures_return_unavailable_without_secrets():
    secret = "CHROMA_SECRET_INTERNAL_4411"

    class BrokenIndex(FakeIndex):
        def query(self, **kwargs):
            raise RuntimeError(secret)

        def count_thread(self, thread_hash):
            raise RuntimeError(secret)

    service = RelevantConversationMemoryService(
        FakeHistory([]), vector_index=BrokenIndex(), embedder=FakeEmbedder()
    )
    result = service.search_relevant("thread-a", "query")
    assert result.status == "unavailable"
    assert result.failure_stage == "vector_search"
    assert secret not in repr(result)


def test_embedding_and_hydration_failures_are_fail_soft():
    class BrokenEmbedder(FakeEmbedder):
        def embed_query(self, text):
            raise RuntimeError("EMBED_SECRET_INTERNAL_4412")

    service = RelevantConversationMemoryService(
        FakeHistory([]), vector_index=FakeIndex(), embedder=BrokenEmbedder()
    )
    result = service.search_relevant("thread-a", "query")
    assert (result.status, result.failure_stage, result.hits) == (
        "unavailable",
        "embedding",
        (),
    )

    class BrokenHistory(FakeHistory):
        def list_messages_by_ids(self, thread_id, message_ids):
            raise RuntimeError("POSTGRES_SECRET_DSN_4413")

    service = RelevantConversationMemoryService(
        BrokenHistory([record(1, "thread-a", 1, "user", "memory")]),
        vector_index=FakeIndex(hits=[(1, 0.9)]),
        embedder=FakeEmbedder(),
    )
    result = service.search_relevant("thread-a", "query")
    assert (result.status, result.failure_stage, result.hits) == (
        "unavailable",
        "hydration",
        (),
    )


def test_validation_errors_are_not_swallowed():
    service = make_service([])
    with pytest.raises(ValueError):
        service.search_relevant("", "query")
    with pytest.raises(TypeError):
        service.search_relevant("thread-a", "query", top_k="4")
    with pytest.raises(TypeError):
        service.search_relevant("thread-a", "query", before_turn_index=True)
    with pytest.raises(ValueError):
        service.search_relevant("thread-a", "query", min_similarity=2)


def test_old_memory_is_retrieved_and_canonical_content_wins():
    old = record(2, "thread-a", 2, "user", "canonical corrected text")
    service = make_service([old], hits=[(2, 0.91)])
    result = service.search_relevant("thread-a", "what did I prefer?")
    assert result.hits[0].content == "canonical corrected text"
    assert result.hits[0].similarity == 0.91
    assert result.hits[0].role == "user"


def test_before_turn_index_is_applied_at_vector_query():
    records = [
        record(3, "thread-a", 3, "user", "old"),
        record(19, "thread-a", 19, "user", "recent"),
    ]
    service = make_service(records, hits=[(3, 0.9), (19, 0.99)])
    service.search_relevant("thread-a", "query", before_turn_index=15)
    where = service.vector_index.queries[0][2]
    assert {"thread_ref": thread_ref("thread-a")} in where["$and"]
    assert {"turn_index": {"$lt": 15}} in where["$and"]


def test_vector_and_hydration_thread_isolation():
    records = [
        record(1, "thread-a", 1, "user", "A"),
        record(2, "thread-b", 1, "user", "B"),
    ]
    service = make_service(records, hits=[(2, 0.99)])
    result = service.search_relevant("thread-a", "query")
    assert result.hits == ()
    assert service.vector_index.queries[0][2] == {"thread_ref": thread_ref("thread-a")}


def test_stale_vector_hit_is_dropped_without_fabrication():
    service = make_service([], hits=[(999, 0.99)])
    result = service.search_relevant("thread-a", "query")
    assert result.hits == ()


def test_semantic_rank_is_preserved_and_duplicate_messages_are_deduplicated():
    records = [
        record(9, "thread-a", 9, "user", "nine"),
        record(2, "thread-a", 2, "user", "two"),
        record(7, "thread-a", 7, "assistant", "seven"),
    ]
    service = make_service(records, hits=[(9, 0.91), (2, 0.83), (9, 0.80), (7, 0.72)])
    result = service.search_relevant("thread-a", "query")
    assert [hit.message_id for hit in result.hits] == [9, 2, 7]


def test_similarity_threshold_and_top_k_are_bounded():
    records = [record(index, "thread-a", index, "user", str(index)) for index in range(1, 10)]
    service = make_service(records, hits=[(index, 0.9 - index / 100) for index in range(1, 10)])
    result = service.search_relevant("thread-a", "query", top_k=100)
    assert result.hit_count == MAX_RELEVANT_MEMORIES
    assert all(hit.similarity >= DEFAULT_MEMORY_SIMILARITY_THRESHOLD for hit in result.hits)

    service = make_service(records, hits=[(1, 0.9), (2, 0.4)])
    assert [hit.message_id for hit in service.search_relevant("thread-a", "query").hits] == [1]


def test_multilingual_metadata_and_content_are_preserved():
    records = [
        record(1, "thread-a", 1, "user", "Préférence", "fr", "latin"),
        record(2, "thread-a", 2, "assistant", "Stock", "en", "latin"),
        record(3, "thread-a", 3, "user", "سهم", "ar", "arabic"),
        record(4, "thread-a", 4, "user", "شنو", "ary", "latin"),
        record(5, "thread-a", 5, "assistant", "شنو", "ary", "arabic"),
    ]
    service = make_service(records, hits=[(5, 0.95)])
    hit = service.search_relevant("thread-a", "query").hits[0]
    assert (hit.language, hit.script, hit.content) == ("ary", "arabic", "شنو")


def test_blank_query_does_not_embed():
    embedder = FakeEmbedder()
    service = RelevantConversationMemoryService(
        FakeHistory([]), vector_index=FakeIndex(), embedder=embedder
    )
    assert service.search_relevant("thread-a", "  ").hits == ()
    assert embedder.query_calls == []


def test_delete_is_thread_scoped_and_empty_rebuild_is_safe():
    service = make_service([])
    assert service.rebuild_thread_index("thread-a") == 0
    service.delete_thread_index("thread-a")
    assert service.vector_index.deleted == [thread_ref("thread-a")]


def test_chroma_memory_index_restarts_and_keeps_collection_separate(tmp_path):
    path = tmp_path / "memory-chroma"
    first = ChromaMemoryVectorIndex(path)
    first.upsert(
        ids=["memory:thread-hash:1"],
        embeddings=[[1.0, 0.0, 0.0]],
        documents=["canonical memory"],
        metadatas=[{"thread_ref": "thread-hash", "message_id": 1, "turn_index": 1}],
    )
    assert first.count_thread("thread-hash") == 1

    second = ChromaMemoryVectorIndex(path)
    result = second.query(
        embedding=[1.0, 0.0, 0.0],
        top_k=1,
        where={"thread_ref": "thread-hash"},
    )
    assert result["ids"][0] == ["memory:thread-hash:1"]
    assert second.collection.name == MEMORY_VECTOR_COLLECTION_NAME


def test_service_rebuild_search_survives_chroma_restart(tmp_path):
    records = [record(1, "thread-a", 2, "user", "Je préfère les obligations.")]
    embedder = FakeEmbedder()
    first = RelevantConversationMemoryService(
        FakeHistory(records),
        vector_index=ChromaMemoryVectorIndex(tmp_path / "restart"),
        embedder=embedder,
    )
    assert first.rebuild_thread_index("thread-a") == 1

    second = RelevantConversationMemoryService(
        FakeHistory(records),
        vector_index=ChromaMemoryVectorIndex(tmp_path / "restart"),
        embedder=embedder,
    )
    result = second.search_relevant("thread-a", "par quoi commencer")

    assert [hit.message_id for hit in result.hits] == [1]
    assert result.hits[0].content == "Je préfère les obligations."


def test_default_index_and_bge_are_lazy_and_path_is_cwd_independent(tmp_path, monkeypatch):
    from app.memory.embeddings import LocalBGEEmbedder
    from app.memory.relevant_memory_service import DEFAULT_MEMORY_INDEX_PATH

    service = RelevantConversationMemoryService(FakeHistory([]), embedder=FakeEmbedder())
    assert service._vector_index is None
    assert not (tmp_path / "backend" / "data" / "memory" / "chroma").exists()

    created = []
    embedder = LocalBGEEmbedder(provider_factory=lambda: created.append(True) or FakeProvider())
    assert created == []
    embedder.embed_query("query")
    embedder.embed_query("query")
    assert len(created) == 1

    expected = DEFAULT_MEMORY_INDEX_PATH
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_MEMORY_INDEX_PATH == expected
