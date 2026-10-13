"""Semantic retrieval of derived long-term conversation memory."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from app.memory.embeddings import LocalBGEEmbedder, MemoryEmbedder
from app.memory.relevant_models import RelevantMemoryContext, RelevantMemoryHit
from app.memory.vector_index import (
    DEFAULT_MEMORY_INDEX_PATH,
    ChromaMemoryVectorIndex,
    MemoryVectorIndex,
    thread_ref,
)

DEFAULT_RELEVANT_MEMORIES = 4
MAX_RELEVANT_MEMORIES = 8
DEFAULT_MEMORY_SIMILARITY_THRESHOLD = 0.55
MEMORY_REBUILD_BATCH_SIZE = 32


class MemoryIndexBuildError(RuntimeError):
    """Safe error for an explicit derived-index rebuild failure."""


class MemoryHistoryStore(Protocol):
    def list_messages(self, thread_id: str, *, limit: int | None = None): ...

    def list_messages_by_ids(self, thread_id: str, message_ids: Sequence[int]): ...


class RelevantConversationMemoryService:
    """Maintain and search a rebuildable index over one conversation thread."""

    def __init__(
        self,
        history_store: MemoryHistoryStore,
        *,
        vector_index: MemoryVectorIndex | None = None,
        embedder: MemoryEmbedder | None = None,
        index_path=DEFAULT_MEMORY_INDEX_PATH,
        similarity_threshold: float = DEFAULT_MEMORY_SIMILARITY_THRESHOLD,
        rebuild_batch_size: int = MEMORY_REBUILD_BATCH_SIZE,
    ) -> None:
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between zero and one")
        if rebuild_batch_size <= 0:
            raise ValueError("rebuild_batch_size must be greater than zero")
        self.history_store = history_store
        self._vector_index = vector_index
        self.index_path = index_path
        self.embedder = embedder or LocalBGEEmbedder()
        self.similarity_threshold = similarity_threshold
        self.rebuild_batch_size = rebuild_batch_size

    @property
    def vector_index(self) -> MemoryVectorIndex:
        if self._vector_index is None:
            self._vector_index = ChromaMemoryVectorIndex(self.index_path)
        return self._vector_index

    def rebuild_thread_index(self, thread_id: str) -> int:
        self._validate_thread_id(thread_id)
        messages = [
            message
            for message in self.history_store.list_messages(thread_id)
            if message.role in {"user", "assistant"} and message.content
        ]
        thread_hash = thread_ref(thread_id)
        try:
            index = self.vector_index
            existing_ids = set(index.list_thread_ids(thread_hash))
            desired_ids = {self._document_id(thread_hash, message.id) for message in messages}
            for start in range(0, len(messages), self.rebuild_batch_size):
                batch = messages[start : start + self.rebuild_batch_size]
                vectors = self.embedder.embed_texts([message.content for message in batch])
                index.upsert(
                    ids=[self._document_id(thread_hash, message.id) for message in batch],
                    embeddings=vectors.tolist(),
                    documents=[message.content for message in batch],
                    metadatas=[self._metadata(thread_hash, message) for message in batch],
                )
            index.delete_ids(sorted(existing_ids - desired_ids))
        except Exception as exc:
            raise MemoryIndexBuildError("memory index rebuild failed") from exc
        return len(messages)

    def index_canonical_messages(self, thread_id: str, message_ids: Sequence[int]) -> int:
        self._validate_thread_id(thread_id)
        if not message_ids:
            return 0
        try:
            messages = [
                message
                for message in self.history_store.list_messages_by_ids(
                    thread_id, list(dict.fromkeys(message_ids))
                )
                if message.role in {"user", "assistant"} and message.content
            ]
            thread_hash = thread_ref(thread_id)
            for start in range(0, len(messages), self.rebuild_batch_size):
                batch = messages[start : start + self.rebuild_batch_size]
                vectors = self.embedder.embed_texts([message.content for message in batch])
                self.vector_index.upsert(
                    ids=[self._document_id(thread_hash, message.id) for message in batch],
                    embeddings=vectors.tolist(),
                    documents=[message.content for message in batch],
                    metadatas=[self._metadata(thread_hash, message) for message in batch],
                )
            return len(messages)
        except Exception as exc:
            raise MemoryIndexBuildError("memory message indexing failed") from exc

    def delete_thread_index(self, thread_id: str) -> None:
        self._validate_thread_id(thread_id)
        self.vector_index.delete_thread(thread_ref(thread_id))

    def search_relevant(
        self,
        thread_id: str,
        query: str,
        *,
        top_k: int = DEFAULT_RELEVANT_MEMORIES,
        before_turn_index: int | None = None,
        min_similarity: float | None = None,
    ) -> RelevantMemoryContext:
        self._validate_thread_id(thread_id)
        if not isinstance(query, str) or not query.strip():
            return self._empty_context(thread_id)
        bounded_top_k = self._bounded_top_k(top_k)
        if bounded_top_k == 0:
            return self._empty_context(thread_id)
        threshold = self.similarity_threshold if min_similarity is None else min_similarity
        if not 0 <= threshold <= 1:
            raise ValueError("min_similarity must be between zero and one")
        where: dict[str, Any] = {"thread_ref": thread_ref(thread_id)}
        if before_turn_index is not None:
            if not isinstance(before_turn_index, int) or isinstance(before_turn_index, bool):
                raise TypeError("before_turn_index must be an integer")
            where = {
                "$and": [
                    {"thread_ref": thread_ref(thread_id)},
                    {"turn_index": {"$lt": before_turn_index}},
                ]
            }
        try:
            query_vector = self.embedder.embed_query(query)
        except Exception:
            return self._unavailable_context(thread_id, "embedding")
        try:
            result = self.vector_index.query(
                embedding=query_vector.tolist(), top_k=bounded_top_k, where=where
            )
        except Exception:
            return self._unavailable_context(thread_id, "vector_search")
        candidates = self._candidates(result, threshold)
        if not candidates:
            return self._empty_context(thread_id, self._indexed_count(thread_id))
        try:
            records = self.history_store.list_messages_by_ids(
                thread_id, [message_id for message_id, _ in candidates]
            )
        except Exception:
            return self._unavailable_context(thread_id, "hydration")
        by_id = {record.id: record for record in records}
        hits = []
        seen: set[int] = set()
        for message_id, similarity in candidates:
            record = by_id.get(message_id)
            if record is None or record.id in seen:
                continue
            seen.add(record.id)
            hits.append(
                RelevantMemoryHit(
                    message_id=record.id,
                    turn_index=record.turn_index,
                    role=record.role,
                    content=record.content,
                    language=record.language,
                    script=record.script,
                    route=record.route,
                    knowledge_source=record.knowledge_source,
                    similarity=similarity,
                )
            )
        return RelevantMemoryContext(
            thread_id=thread_id,
            hits=tuple(hits),
            hit_count=len(hits),
            indexed_message_count=self._indexed_count(thread_id),
        )

    def hydrate_message_ids(
        self, thread_id: str, message_ids: Sequence[int]
    ) -> RelevantMemoryContext:
        """Reload previously selected canonical messages without searching."""
        self._validate_thread_id(thread_id)
        if not message_ids:
            return self._empty_context(thread_id)
        try:
            records = self.history_store.list_messages_by_ids(
                thread_id, list(dict.fromkeys(message_ids))
            )
        except Exception:
            return self._unavailable_context(thread_id, "hydration")
        by_id = {record.id: record for record in records}
        hits = tuple(
            RelevantMemoryHit(
                message_id=message_id,
                turn_index=record.turn_index,
                role=record.role,
                content=record.content,
                language=record.language,
                script=record.script,
                route=record.route,
                knowledge_source=record.knowledge_source,
                similarity=None,
            )
            for message_id in message_ids
            for record in (by_id.get(message_id),)
            if record is not None
            if record.role in {"user", "assistant"} and record.content
        )
        return RelevantMemoryContext(
            thread_id, hits, len(hits), self._indexed_count(thread_id)
        )

    @staticmethod
    def _document_id(thread_hash: str, message_id: int) -> str:
        return f"memory:{thread_hash}:{message_id}"

    @staticmethod
    def _metadata(thread_hash: str, message: Any) -> dict[str, Any]:
        return {
            "thread_ref": thread_hash,
            "message_id": message.id,
            "turn_index": message.turn_index,
            "role": message.role,
            "language": message.language or "",
            "script": message.script or "",
        }

    @staticmethod
    def _bounded_top_k(top_k: int) -> int:
        if isinstance(top_k, bool) or not isinstance(top_k, int):
            raise TypeError("top_k must be an integer")
        if top_k <= 0:
            return 0
        return min(top_k, MAX_RELEVANT_MEMORIES)

    @staticmethod
    def _validate_thread_id(thread_id: str) -> None:
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("thread_id must not be blank")

    @staticmethod
    def _empty_context(thread_id: str, indexed_count: int | None = None):
        return RelevantMemoryContext(thread_id, (), 0, indexed_count)

    @staticmethod
    def _unavailable_context(thread_id: str, failure_stage: str):
        return RelevantMemoryContext(
            thread_id,
            (),
            0,
            None,
            status="unavailable",
            failure_stage=failure_stage,
        )

    def _indexed_count(self, thread_id: str) -> int | None:
        try:
            return self.vector_index.count_thread(thread_ref(thread_id))
        except Exception:
            return None

    @staticmethod
    def _candidates(result: dict[str, Any], threshold: float) -> list[tuple[int, float]]:
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        candidates = []
        for distance, metadata in zip(distances, metadatas, strict=False):
            if not metadata or not isinstance(metadata.get("message_id"), int):
                continue
            message_id = metadata["message_id"]
            similarity = max(-1.0, min(1.0, 1.0 - float(distance)))
            if similarity >= threshold:
                candidates.append((int(message_id), similarity))
        return candidates
