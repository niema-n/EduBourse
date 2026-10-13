"""Persistent Chroma index builder for the frozen J6 content chunks."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import chromadb

from app.config import get_settings
from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import (
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    classify_index_inputs,
    embedding_text,
    load_chunks,
    load_gold,
    verify_sentence_transformer_snapshot,
)
from app.rag.hybrid_policy import rank_query

COLLECTION_NAME = "j6_bge_m3_content_v1"
INDEX_VERSION = 1
MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
CHUNKS_SHA256 = "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
EXPECTED_DIMENSION = 1024


def resolve_bge_m3_snapshot_path(configured_path: str | Path | None = None) -> Path:
    """Resolve the local BGE-M3 snapshot without enabling network downloads."""
    configured = configured_path
    if configured is None:
        configured = get_settings().bge_m3_model_path.strip()
    if configured:
        snapshot = Path(configured).expanduser()
    else:
        snapshot = (
            Path.home()
            / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
            / MODEL_REVISION
        )
    verify_sentence_transformer_snapshot(snapshot)
    return snapshot


def chunk_metadata(chunk: ChunkRecord, role: str = "content") -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "title": chunk.title,
        "page": chunk.page_start,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "page_numbers": json.dumps(chunk.page_numbers),
        "role": role,
    }
    if chunk.section_heading is not None:
        metadata["heading"] = chunk.section_heading
    if chunk.section_heading_page is not None:
        metadata["heading_page"] = chunk.section_heading_page
    return metadata


def content_chunks(root: Path) -> tuple[list[ChunkRecord], dict[str, str], list[dict[str, Any]]]:
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    chunks = load_chunks(chunks_path)
    roles, duplicate_groups = classify_index_inputs(chunks)
    if len(chunks) != 400:
        raise ValueError("frozen chunk role inputs do not match J6 counts")
    counts = Counter(roles.values())
    if counts != Counter({"content": 353, "navigation": 34, "shared_redundant": 13}):
        raise ValueError(f"unexpected frozen chunk roles: {counts}")
    selected = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    if len({chunk.chunk_id for chunk in selected}) != 353:
        raise ValueError("content chunk IDs are not unique")
    return selected, roles, duplicate_groups


def create_collection(index_path: Path):
    client = chromadb.PersistentClient(path=str(index_path))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception as exc:  # Chroma raises when the collection is absent.
        if "does not exist" not in str(exc).casefold():
            raise
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"hnsw:space": "cosine", "index_version": INDEX_VERSION},
        embedding_function=None,
    )
    return client, collection


def build_collection(root: Path) -> dict[str, Any]:
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    selected, roles, duplicate_groups = content_chunks(root)
    if hashlib.sha256(chunks_path.read_bytes()).hexdigest() != CHUNKS_SHA256:
        raise ValueError("frozen chunks hash mismatch")
    snapshot = resolve_bge_m3_snapshot_path()
    spec = next(spec for spec in MODEL_SPECS if spec.model_name == MODEL_NAME)
    provider = SentenceTransformerEmbeddingProvider(
        spec,
        model_ref=snapshot,
        revision=MODEL_REVISION,
        model_kwargs={"local_files_only": True},
    )
    provider.batch_size = 1
    vectors = provider.embed_passages([embedding_text(chunk) for chunk in selected])
    if vectors.shape != (353, EXPECTED_DIMENSION) or provider.dimension != EXPECTED_DIMENSION:
        raise ValueError(f"unexpected BGE dimension: {vectors.shape}, {provider.dimension}")
    index_path = root / "backend/data/rag/indexes/bge_m3_v1"
    index_path.mkdir(parents=True, exist_ok=True)
    client, collection = create_collection(index_path)
    ids = [chunk.chunk_id for chunk in selected]
    documents = [chunk.text for chunk in selected]
    metadata = [chunk_metadata(chunk) for chunk in selected]
    collection.add(ids=ids, embeddings=vectors.tolist(), documents=documents, metadatas=metadata)
    if collection.count() != 353:
        raise ValueError("Chroma collection cardinality mismatch")
    reopened_client = chromadb.PersistentClient(path=str(index_path))
    reopened = reopened_client.get_collection(COLLECTION_NAME, embedding_function=None)
    if reopened.count() != 353:
        raise ValueError("Chroma persistence reopen cardinality mismatch")
    sample = reopened.get(ids=ids[:2], include=["documents", "metadatas"])
    if sample["ids"] != ids[:2] or sample["documents"] != documents[:2]:
        raise ValueError("Chroma persistence sample mismatch")
    smoke = smoke_compare(root, reopened, provider, selected, vectors)
    source_distribution = Counter(chunk.source_id for chunk in selected)
    manifest = {
        "schema_version": "j6-chroma-index-v1",
        "index_version": INDEX_VERSION,
        "index_path": "backend/data/rag/indexes/bge_m3_v1",
        "collection_name": COLLECTION_NAME,
        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "embedding_dimension": EXPECTED_DIMENSION,
        "distance_metric": "cosine",
        "chunks_sha256": CHUNKS_SHA256,
        "input_chunk_count": len(roles),
        "indexed_role": "content",
        "indexed_chunk_count": len(selected),
        "excluded_navigation_count": sum(role == "navigation" for role in roles.values()),
        "excluded_shared_redundant_count": sum(
            role == "shared_redundant" for role in roles.values()
        ),
        "unique_chunk_id_count": len(ids),
        "source_count": len(source_distribution),
        "source_distribution": dict(sorted(source_distribution.items())),
        "created_from_frozen_chunks": True,
        "retrieval_policy": "H1_LANGUAGE_ROUTED_V1",
        "retrieval_policy_status": "ACCEPTED_WITH_DOCUMENTED_CONFIRMATORY_LIMITATIONS",
        "confirmatory_quality_gate": False,
        "no_more_retrieval_policy_tuning": True,
        "known_limitations": [
            "Ary-Latin unweighted RRF dilution.",
            "The brochure placement source has only three content chunks and creates "
            "cross-language competition for confirmatory group 11.",
        ],
        "production_integration": False,
        "next_step": "J6_06_RETRIEVAL_SERVICE",
        "persistence_reopen_test": True,
        "smoke_query_count": len(smoke),
        "chroma_vs_offline_ranking": (
            "MATCH" if all(item["match"] for item in smoke) else "DIFFERENT"
        ),
        "smoke_queries": smoke,
        "duplicate_groups_excluded": len(duplicate_groups),
    }
    return manifest


def smoke_compare(
    root: Path, collection, provider, selected: list[ChunkRecord], passage_vectors
) -> list[dict[str, Any]]:
    gold = load_gold(root / "evaluation/rag/embedding_gold_v1.jsonl")
    cases = [case for case in gold if case.id in {"fr-01", "en-01", "ary-latin-01"}]
    query_vectors = provider.embed_queries([case.query for case in cases])
    ids = [chunk.chunk_id for chunk in selected]
    results = []
    for case, vector in zip(cases, query_vectors, strict=True):
        offline_indexes = rank_query(vector, passage_vectors, selected)[:5]
        offline_ids = [ids[index] for index in offline_indexes]
        response = collection.query(
            query_embeddings=[vector.tolist()], n_results=5, include=["metadatas"]
        )
        chroma_ids = response["ids"][0]
        results.append(
            {
                "case_id": case.id,
                "match": chroma_ids == offline_ids,
                "offline_top5": offline_ids,
                "chroma_top5": chroma_ids,
            }
        )
    return results
