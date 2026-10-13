import hashlib
import json
from pathlib import Path

import chromadb

from app.rag.embedding_benchmark import classify_index_inputs, load_chunks

ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = ROOT / "backend/data/rag/indexes/bge_m3_v1"
MANIFEST = ROOT / "backend/data/rag/manifests/chroma_index_v1.json"
CHUNKS = ROOT / "backend/data/rag/processed/chunks_v1.jsonl"
QUERY_ARTIFACT = ROOT / "evaluation/rag/query_adapter_confirmatory_v1.jsonl"
CONFIRMATORY_REPORT = ROOT / "backend/data/rag/manifests/query_adapter_confirmatory_result_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_chroma_manifest_is_final_and_pinned():
    manifest = _manifest()
    assert manifest["index_version"] == 1
    assert manifest["collection_name"] == "j6_bge_m3_content_v1"
    assert manifest["embedding_model"] == "BAAI/bge-m3"
    assert manifest["embedding_revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert manifest["embedding_dimension"] == 1024
    assert manifest["distance_metric"] == "cosine"
    assert manifest["chunks_sha256"] == (
        "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
    )
    assert manifest["retrieval_policy"] == "H1_LANGUAGE_ROUTED_V1"
    assert manifest["confirmatory_quality_gate"] is False
    assert manifest["no_more_retrieval_policy_tuning"] is True
    assert manifest["production_integration"] is False


def test_chroma_contains_exact_frozen_content_ids_and_metadata():
    chunks = load_chunks(CHUNKS)
    roles, _ = classify_index_inputs(chunks)
    expected = {chunk.chunk_id for chunk in chunks if roles[chunk.chunk_id] == "content"}
    client = chromadb.PersistentClient(path=str(INDEX_PATH))
    collection = client.get_collection("j6_bge_m3_content_v1", embedding_function=None)
    assert collection.count() == 353
    values = collection.get(include=["documents", "metadatas"])
    assert set(values["ids"]) == expected
    assert len(values["ids"]) == len(set(values["ids"])) == 353
    assert all(document for document in values["documents"])
    assert all(metadata["role"] == "content" for metadata in values["metadatas"])
    assert all(metadata["chunk_id"] in expected for metadata in values["metadatas"])
    assert all("source_id" in metadata and "page" in metadata for metadata in values["metadatas"])


def test_chroma_excludes_navigation_and_shared_redundant_roles():
    chunks = load_chunks(CHUNKS)
    roles, _ = classify_index_inputs(chunks)
    client = chromadb.PersistentClient(path=str(INDEX_PATH))
    collection = client.get_collection("j6_bge_m3_content_v1", embedding_function=None)
    values = collection.get(include=["metadatas"])
    indexed = {metadata["chunk_id"] for metadata in values["metadatas"]}
    assert not indexed & {chunk_id for chunk_id, role in roles.items() if role != "content"}


def test_chroma_manifest_counts_and_persistence():
    manifest = _manifest()
    assert manifest["input_chunk_count"] == 400
    assert manifest["indexed_chunk_count"] == 353
    assert manifest["unique_chunk_id_count"] == 353
    assert manifest["excluded_navigation_count"] == 34
    assert manifest["excluded_shared_redundant_count"] == 13
    reopened = chromadb.PersistentClient(path=str(INDEX_PATH)).get_collection(
        "j6_bge_m3_content_v1", embedding_function=None
    )
    assert reopened.count() == 353


def test_chroma_freezes_confirmatory_artifact_and_report_hashes():
    assert _sha256(QUERY_ARTIFACT) == (
        "b133e0bb14a4e0303ace70d217296e8d9fa4c560a387c228234c680f526a4230"
    )
    assert _sha256(CONFIRMATORY_REPORT) == (
        "796f962921f91f429e5cf3eeba37be7dbbd2a091cb366f05930f99fc4257b6cf"
    )


def test_chroma_builder_owns_embeddings_and_is_not_production_integrated():
    source = (ROOT / "backend/app/rag/chroma_index.py").read_text(encoding="utf-8").lower()
    assert "embedding_function=none" in source
    assert "groq" not in source
    assert "app.api" not in source
    assert "langgraph" not in source
