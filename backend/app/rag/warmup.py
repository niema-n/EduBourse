"""Background BGE-M3 warm-up for the shared RetrievalService.

Loading BGE-M3 and running its first embedding cost about 70 s on the demo
machine. This moves that cost from the first user question to backend startup
without blocking FastAPI: a single daemon thread builds the process-wide
service through ``get_retrieval_service`` (which already serialises creation
behind its lock, so a concurrent user request waits for the same instance and
never creates a second one) and primes the local retrieval cache for common
demo questions. It performs no write, no LLM/provider call, and touches no
conversation or history.
"""

from __future__ import annotations

import logging
import os
import threading
import time

from app.observability.logging import emit
from app.rag import runtime

logger = logging.getLogger(__name__)

WARMUP_QUERIES = (
    "c est quoi une action ?",
    "qu'est-ce qu'une action ?",
    "c est quoi une obligation ?",
    "qu'est-ce qu'une obligation ?",
)

_lock = threading.Lock()
_thread: threading.Thread | None = None
_run_count = 0


def run_warmup() -> bool:
    """Load the shared service and prime common local retrieval queries."""
    global _run_count
    _run_count += 1
    started = time.perf_counter()
    try:
        service = runtime.get_retrieval_service()
        if service is None:
            if os.getenv("GROQ_API_KEY", "").strip():
                # A failed warm-up must not freeze RAG as unavailable: let the next
                # user request retry the normal lazy load.
                runtime.reset_after_failed_warmup()
            emit(
                "rag.warmup.failed",
                level=logging.WARNING,
                reason="retrieval_service_unavailable",
                stage="rag_warmup",
            )
            return False
        for query in WARMUP_QUERIES:
            service._query(query, 5)
    except Exception as exc:
        logger.warning("rag warm-up failed error_type=%s", type(exc).__name__)
        emit(
            "rag.warmup.failed",
            level=logging.WARNING,
            error_type=type(exc).__name__,
            stage="rag_warmup",
        )
        return False
    emit(
        "rag.warmup.completed",
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        stage="rag_warmup",
    )
    return True


def start_background_warmup() -> bool:
    """Start the warm-up once per process; later calls are no-ops."""
    global _thread
    with _lock:
        if _thread is not None:
            return False
        _thread = threading.Thread(target=run_warmup, name="rag-bge-warmup", daemon=True)
        _thread.start()
    emit("rag.warmup.started", stage="rag_warmup")
    return True
