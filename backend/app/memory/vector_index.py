"""Derived, thread-scoped vector index for conversation memory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Protocol

import chromadb

MEMORY_VECTOR_COLLECTION_NAME = "conversation_memory_v1"
DEFAULT_MEMORY_INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "memory" / "chroma"


def thread_ref(thread_id: str) -> str:
    return hashlib.sha256(thread_id.encode("utf-8")).hexdigest()


class MemoryVectorIndex(Protocol):
    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    def query(
        self,
        *,
        embedding: list[float],
        top_k: int,
        where: dict[str, Any],
    ) -> dict[str, Any]: ...

    def delete_thread(self, thread_hash: str) -> None: ...

    def list_thread_ids(self, thread_hash: str) -> list[str]: ...

    def delete_ids(self, ids: list[str]) -> None: ...

    def count_thread(self, thread_hash: str) -> int: ...


class ChromaMemoryVectorIndex:
    """Persistent Chroma collection kept separate from the J6 RAG index."""

    def __init__(
        self,
        path: str | Path = DEFAULT_MEMORY_INDEX_PATH,
        *,
        collection_name: str = MEMORY_VECTOR_COLLECTION_NAME,
    ) -> None:
        self.path = Path(path)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.path))
        self.collection = self.client.get_or_create_collection(
            collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"hnsw:space": "cosine", "index_version": 1},
            embedding_function=None,
        )

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        *,
        embedding: list[float],
        top_k: int,
        where: dict[str, Any],
    ) -> dict[str, Any]:
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["metadatas", "distances"],
        )

    def delete_thread(self, thread_hash: str) -> None:
        self.collection.delete(where={"thread_ref": thread_hash})

    def list_thread_ids(self, thread_hash: str) -> list[str]:
        return self.collection.get(where={"thread_ref": thread_hash}, include=[]).get("ids", [])

    def delete_ids(self, ids: list[str]) -> None:
        if ids:
            self.collection.delete(ids=ids)

    def count_thread(self, thread_hash: str) -> int:
        result = self.collection.get(where={"thread_ref": thread_hash}, include=[])
        return len(result.get("ids", []))
