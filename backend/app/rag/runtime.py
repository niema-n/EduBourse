"""Process-wide access to the single RetrievalService instance.

RetrievalService loads BGE-M3 when it is constructed, which costs gigabytes of
RAM. The chat graph and the read-only RAG API therefore share one lazily built
instance instead of each creating their own.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

from app.observability.logging import emit
from app.rag.chroma_index import COLLECTION_NAME
from app.rag.query_adapter import GroqQueryAdapterProvider
from app.rag.retrieval_service import RetrievalService, inspect_persisted_index

logger = logging.getLogger(__name__)

RetrievalState = Literal["not_loaded", "available", "unavailable"]
RagIndexStatus = Literal["available", "unavailable"]


@dataclass(frozen=True)
class RagIndexCheck:
    """Read-only health of the on-disk J6 index used by RetrievalService."""

    status: RagIndexStatus
    collection: str = COLLECTION_NAME
    document_count: int = 0

_lock = Lock()
_service: RetrievalService | None = None
_state: RetrievalState = "not_loaded"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_retrieval_service() -> RetrievalService | None:
    """Build the shared service once; None when it cannot be configured."""
    global _service, _state
    if _state != "not_loaded":
        return _service
    with _lock:
        if _state != "not_loaded":
            return _service
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            _state = "unavailable"
            return None
        try:
            started = time.perf_counter()
            _service = RetrievalService(
                repository_root(),
                query_adapter=GroqQueryAdapterProvider(api_key=api_key),
            )
            _state = "available"
            # Emitted once per process: proves BGE-M3/Chroma are loaded a single time.
            emit(
                "rag.retrieval_service.created",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                stage="rag_init",
            )
        except Exception as exc:
            logger.error(
                "retrieval service initialization failed error_type=%s", type(exc).__name__
            )
            _service = None
            _state = "unavailable"
    return _service


def reset_after_failed_warmup() -> None:
    """Allow one later lazy load after a failed background warm-up."""
    global _service, _state
    with _lock:
        if _state == "unavailable" and _service is None:
            _state = "not_loaded"


def retrieval_state() -> RetrievalState:
    """Report the shared service state without forcing the model to load."""
    return _state


def check_retrieval_index() -> RagIndexCheck:
    """Check the actual J6 index without loading BGE-M3 or creating data.

    Reuse the process-wide collection when it is already loaded. Before that,
    ``inspect_persisted_index`` opens the exact same fixed PersistentClient
    location and calls only ``get_collection`` and ``count``.
    """
    if _state == "available" and _service is not None:
        try:
            return RagIndexCheck(
                status="available",
                document_count=int(_service.collection.count()),
            )
        except Exception:
            return RagIndexCheck(status="unavailable")
    try:
        return RagIndexCheck(
            status="available",
            document_count=inspect_persisted_index(repository_root()),
        )
    except Exception:
        return RagIndexCheck(status="unavailable")
