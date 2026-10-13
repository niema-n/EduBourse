"""Local embedding adapters for the derived conversation-memory index."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Protocol

import numpy as np


class MemoryEmbedder(Protocol):
    dimension: int

    def embed_texts(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class MemoryEmbeddingUnavailableError(RuntimeError):
    """Raised when the frozen local memory model cannot be loaded."""


class LocalBGEEmbedder:
    """Use the frozen local BGE-M3 adapter, initialized on first embedding."""

    def __init__(
        self,
        *,
        device: str | None = None,
        model_ref: str | Path | None = None,
        provider_factory=None,
    ):
        self.device = device
        self.model_ref = Path(model_ref) if model_ref is not None else None
        self._provider_factory = provider_factory or self._create_provider
        self._provider = None
        self._lock = Lock()
        self.dimension = 1024

    def _create_provider(self):
        from app.rag.chroma_index import MODEL_NAME, MODEL_REVISION
        from app.rag.embedding_benchmark import (
            MODEL_SPECS,
            SentenceTransformerEmbeddingProvider,
            verify_sentence_transformer_snapshot,
        )

        snapshot = self.model_ref or (
            Path.home()
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--BAAI--bge-m3"
            / "snapshots"
            / MODEL_REVISION
        )
        try:
            verify_sentence_transformer_snapshot(snapshot)
            spec = next(spec for spec in MODEL_SPECS if spec.model_name == MODEL_NAME)
            return SentenceTransformerEmbeddingProvider(
                spec,
                device=self.device,
                model_ref=snapshot,
                revision=MODEL_REVISION,
                model_kwargs={"local_files_only": True},
            )
        except Exception as exc:
            raise MemoryEmbeddingUnavailableError(
                "local memory embedding model unavailable"
            ) from exc

    def _get_provider(self):
        if self._provider is None:
            with self._lock:
                if self._provider is None:
                    self._provider = self._provider_factory()
                    self.dimension = self._provider.dimension
        return self._provider

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return self._get_provider().embed_passages(texts)

    def embed_query(self, text: str) -> np.ndarray:
        return self._get_provider().embed_queries([text])[0]
