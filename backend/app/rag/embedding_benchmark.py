"""Model-independent J6-05A embedding benchmark primitives."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from app.rag.chunking import ChunkRecord

POLICIES = ("ALL_CANONICAL", "CONTENT_FILTERED")
LANGUAGE_LABELS = ("fr", "en", "ar", "ary-latin", "ary-arabic")
PAGE_CHUNK_METRIC_STATUS = "not_evaluated"
E5_LARGE_INSTRUCT_QUERY_INSTRUCTION = (
    "Given a user question about the Moroccan capital market and financial "
    "education, retrieve the most relevant passage from the official French "
    "financial-education corpus."
)


class GoldCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    language: str
    script: str
    topic: str = Field(min_length=1)
    expected_source_ids: list[str] = Field(min_length=1)
    expected_pages: list[int] = Field(default_factory=list)
    acceptable_chunk_ids: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class EmbeddingModelSpec:
    model_name: str
    query_format: str
    passage_format: str
    expected_dimension: int
    requires_prefixes: bool = False
    query_mode: str = "original"
    passage_mode: str = "title_heading_text"
    query_instruction: str | None = None


MODEL_SPECS = (
    EmbeddingModelSpec("BAAI/bge-m3", "original", "title_heading_text", 1024),
    EmbeddingModelSpec(
        "intfloat/multilingual-e5-base", "query: {text}", "passage: {text}", 768, True
    ),
    EmbeddingModelSpec(
        "intfloat/multilingual-e5-large-instruct",
        "Instruct: {instruction}\nQuery: {text}",
        "title_heading_text",
        1024,
        False,
        "instruct",
        "title_heading_text",
        E5_LARGE_INSTRUCT_QUERY_INSTRUCTION,
    ),
)


class EmbeddingProvider(Protocol):
    dimension: int
    revision: str

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...

    def embed_queries(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbeddingProvider:
    """Common SentenceTransformers adapter with model-specific E5 formatting."""

    def __init__(
        self,
        spec: EmbeddingModelSpec,
        *,
        device: str | None = None,
        model_ref: str | Path | None = None,
        revision: str | None = None,
        model_kwargs: dict[str, Any] | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.spec = spec
        model_source = str(model_ref) if model_ref is not None else spec.model_name
        self.model = SentenceTransformer(
            model_source, device=device, model_kwargs=model_kwargs
        )
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        self.device = str(getattr(self.model, "device", device or "cpu"))
        self.batch_size = 8
        self.revision = str(
            revision
            or getattr(self.model, "_commit_hash", None)
            or getattr(getattr(self.model, "config", None), "_commit_hash", None)
            or "unresolved"
        )

    def _encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([format_passage(self.spec, text) for text in texts])

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode([format_query(self.spec, text) for text in texts])


def verify_sentence_transformer_snapshot(snapshot: Path) -> dict[str, Any]:
    """Validate the module structure before passing an official snapshot to ST."""
    modules_path = snapshot / "modules.json"
    if not modules_path.is_file():
        raise ValueError("snapshot is missing modules.json")
    modules = json.loads(modules_path.read_text(encoding="utf-8"))
    referenced = [snapshot / module["path"] for module in modules if module.get("path")]
    missing = [str(path.name) for path in referenced if not path.exists()]
    if missing:
        raise ValueError(f"snapshot is missing module paths: {', '.join(missing)}")
    if (snapshot / "1_Pooling").exists() and not (snapshot / "1_Pooling" / "config.json").is_file():
        raise ValueError("snapshot is missing 1_Pooling/config.json")
    if (snapshot / "2_Normalize").exists() and not (snapshot / "2_Normalize").is_dir():
        raise ValueError("snapshot has an invalid 2_Normalize module")
    tokenizer_assets = ("tokenizer.json", "tokenizer_config.json", "sentencepiece.bpe.model")
    if not any((snapshot / name).is_file() for name in tokenizer_assets):
        raise ValueError("snapshot is missing tokenizer assets")
    weight_assets = ("model.safetensors", "pytorch_model.bin", "pytorch_model.bin.index.json")
    if not any((snapshot / name).is_file() for name in weight_assets):
        raise ValueError("snapshot is missing model weights")
    return {
        "modules": len(modules),
        "module_paths": [str(path.relative_to(snapshot)) for path in referenced],
        "tokenizer_assets": [name for name in tokenizer_assets if (snapshot / name).is_file()],
    }


def format_passage(spec: EmbeddingModelSpec, text: str) -> str:
    if spec.passage_mode == "title_heading_text":
        return ("passage: " if spec.requires_prefixes else "") + text
    raise ValueError(f"unsupported passage mode: {spec.passage_mode}")


def format_query(spec: EmbeddingModelSpec, text: str) -> str:
    if spec.query_mode == "instruct":
        if not spec.query_instruction:
            raise ValueError("instruct query mode requires a query instruction")
        return f"Instruct: {spec.query_instruction}\nQuery: {text}"
    return ("query: " if spec.requires_prefixes else "") + text


def cosine_similarity(query: np.ndarray, documents: np.ndarray) -> np.ndarray:
    query_norm = query / np.maximum(np.linalg.norm(query), 1e-12)
    doc_norm = documents / np.maximum(np.linalg.norm(documents, axis=1, keepdims=True), 1e-12)
    return doc_norm @ query_norm


def _normalized_text(text: str) -> str:
    comparison = unicodedata.normalize("NFC", text).translate(
        str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"})
    )
    return re.sub(r"\s+", " ", comparison.strip().casefold())


def _is_navigation(chunk: ChunkRecord) -> bool:
    text = chunk.text.strip()
    if chunk.char_count >= 100:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    numeric_layout = bool(re.fullmatch(r"(?:page\s*)?\d+(?:\s*[|/-]\s*.*)?", text.casefold()))
    title_layout = len(lines) >= 2 or bool(re.search(r"\|\s*\d+\s*$", text))
    has_complete_sentence = bool(re.search(r"[.!?]$", text)) and len(lines) == 1
    return (numeric_layout or title_layout) and not has_complete_sentence


def _is_shared_redundant(group: list[ChunkRecord]) -> bool:
    joined = " ".join(chunk.text for chunk in group).casefold()
    comparison = _normalized_text(joined)
    signals = (
        "guide de l'investisseur",
        "guides de l'investisseur",
        "comprendre les instruments financiers",
        "ammc",
        "avenue annakhil",
        "www.ammc.ma",
        "contact",
    )
    return any(signal in comparison for signal in signals)


def classify_index_inputs(chunks: list[ChunkRecord]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    roles = {
        chunk.chunk_id: ("navigation" if _is_navigation(chunk) else "content") for chunk in chunks
    }
    groups: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        groups.setdefault(_normalized_text(chunk.text), []).append(chunk)
    duplicate_groups: list[dict[str, Any]] = []
    for normalized, group in sorted(groups.items()):
        if len(group) < 2 or not _is_shared_redundant(group):
            continue
        for chunk in group:
            roles[chunk.chunk_id] = "shared_redundant"
        duplicate_groups.append(
            {
                "text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                "chunk_ids": sorted(chunk.chunk_id for chunk in group),
                "source_ids": sorted({chunk.source_id for chunk in group}),
                "char_count": len(normalized),
                "retrieval_role": "shared_redundant",
                "reason": "exact repeated edge/boilerplate content across sources",
            }
        )
    return roles, duplicate_groups


def load_chunks(path: Path) -> list[ChunkRecord]:
    return [ChunkRecord.model_validate_json(line) for line in path.read_bytes().splitlines()]


def load_gold(path: Path) -> list[GoldCase]:
    return [GoldCase.model_validate_json(line) for line in path.read_bytes().splitlines()]


def embedding_text(chunk: ChunkRecord) -> str:
    return "\n".join(part for part in (chunk.title, chunk.section_heading, chunk.text) if part)


def recall_at_k(
    rankings: list[list[int]], cases: list[GoldCase], chunks: list[ChunkRecord], k: int, kind: str
) -> float:
    hits = 0
    for ranking, case in zip(rankings, cases, strict=True):
        selected = [chunks[index] for index in ranking[:k]]
        if kind == "source":
            hit = any(chunk.source_id in case.expected_source_ids for chunk in selected)
        else:
            hit = any(
                chunk.source_id in case.expected_source_ids
                and (not case.expected_pages or chunk.page_start in case.expected_pages)
                for chunk in selected
            )
        hits += int(hit)
    return hits / len(cases) if cases else 0.0


def mrr_at_10(rankings: list[list[int]], cases: list[GoldCase], chunks: list[ChunkRecord]) -> float:
    reciprocal = []
    for ranking, case in zip(rankings, cases, strict=True):
        for position, index in enumerate(ranking[:10], start=1):
            if chunks[index].source_id in case.expected_source_ids:
                reciprocal.append(1.0 / position)
                break
        else:
            reciprocal.append(0.0)
    return sum(reciprocal) / len(reciprocal) if reciprocal else 0.0


def per_language_recall5(
    rankings: list[list[int]], cases: list[GoldCase], chunks: list[ChunkRecord]
) -> dict[str, float]:
    result = {}
    for language in LANGUAGE_LABELS:
        indexes = [
            index
            for index, case in enumerate(cases)
            if (
                case.language == language
                if language in {"fr", "en", "ar"}
                else f"{case.language}-{case.script}" == language
            )
        ]
        if not indexes:
            result[language] = 0.0
            continue
        result[language] = recall_at_k(
            [rankings[index] for index in indexes],
            [cases[index] for index in indexes],
            chunks,
            5,
            "source",
        )
    return result


def select_model(results: dict[str, dict[str, Any]]) -> str | None:
    eligible = {
        name: value
        for name, value in results.items()
        if value["macro_source_recall5"] >= 0.90 and value["worst_language_recall5"] >= 0.80
    }
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda name: (
            eligible[name]["worst_language_recall5"],
            eligible[name]["macro_source_recall5"],
            eligible[name]["mrr10"],
            eligible[name]["source_recall1"],
            -eligible[name].get("query_encoding_median_ms", float("inf")),
        ),
    )


def benchmark_provider(
    provider: EmbeddingProvider,
    chunks: list[ChunkRecord],
    cases: list[GoldCase],
    roles: dict[str, str],
    policy: str,
) -> dict[str, Any]:
    return benchmark_provider_policies(provider, chunks, cases, roles)[policy]


def benchmark_provider_policies(
    provider: EmbeddingProvider,
    chunks: list[ChunkRecord],
    cases: list[GoldCase],
    roles: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Encode the canonical corpus and queries once, then score both policies."""
    policy_indexes = {
        "ALL_CANONICAL": list(range(len(chunks))),
        "CONTENT_FILTERED": [
            index for index, chunk in enumerate(chunks) if roles[chunk.chunk_id] == "content"
        ],
    }
    passage_inputs = [embedding_text(chunk) for chunk in chunks]
    start = time.perf_counter()
    passage_vectors = provider.embed_passages(passage_inputs)
    document_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    query_vectors = provider.embed_queries([case.query for case in cases])
    query_ms = (time.perf_counter() - start) * 1000
    results: dict[str, dict[str, Any]] = {}
    for policy, indexes in policy_indexes.items():
        selected = [chunks[index] for index in indexes]
        selected_vectors = passage_vectors[indexes]
        rankings = [
            list(np.argsort(-cosine_similarity(vector, selected_vectors)))
            for vector in query_vectors
        ]
        source = {
            f"source_recall{k}": recall_at_k(rankings, cases, selected, k, "source")
            for k in (1, 3, 5)
        }
        language = per_language_recall5(rankings, cases, selected)
        results[policy] = {
            **source,
            "page_chunk_metric_status": PAGE_CHUNK_METRIC_STATUS,
            "mrr10": mrr_at_10(rankings, cases, selected),
            "per_language_recall5": language,
            "macro_source_recall5": statistics.mean(language.values()),
            "worst_language_recall5": min(language.values()),
            "embedding_dimension": provider.dimension,
            "model_revision": provider.revision,
            "device": getattr(provider, "device", "unknown"),
            "batch_size": getattr(provider, "batch_size", None),
            "model_load_ms": None,
            "document_embedding_ms": round(document_ms, 3),
            "query_encoding_ms": round(query_ms, 3),
            "documents_indexed": len(selected),
        }
    return results
