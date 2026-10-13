"""Run the offline EN/AR retrieval diagnostic against frozen BGE-M3."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.embedding_benchmark import (  # noqa: E402
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    classify_index_inputs,
    embedding_text,
    load_chunks,
    load_gold,
    verify_sentence_transformer_snapshot,
)
from app.rag.en_ar_diagnostic import (  # noqa: E402
    BASELINE_RECALL5,
    COUNTERPART_VARIANTS,
    RANK_VARIANTS,
    classify_failure,
    diagnostic_projection,
    hit_count,
    pair_target_cases,
    rank_query,
    reason_counts,
    recall5,
    unavailable_result,
)

MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
GOLD_SHA256 = "68da7ebcd739dc42e874bf0052b7a2a6c33a2013ba1cd91979ccea7b6d0355b5"
CHUNKS_SHA256 = "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
MANIFEST_SHA256 = "2ec834e160851a59d52b9d200470aa714ec850a39f672e480b2c8207880f3b0a"
PAGES_SHA256 = "69312419a872f02eb74e1547dc4a80c8d322be6796580d54a17b1ee2b7252968"
CHUNKING_AUDIT_SHA256 = "1fc6290d01e5c54ab49ad02d8393a71786fb6873473f8e8320c9fb05158c688c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_snapshot() -> Path:
    snapshot_root = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
    snapshot = snapshot_root / MODEL_REVISION
    verify_sentence_transformer_snapshot(snapshot)
    return snapshot


def reciprocal_metrics(results: list[dict], query_vectors: dict[str, object]) -> dict[str, float]:
    del query_vectors
    ranks = [result["variants"]["ORIGINAL"].get("expected_source_rank") for result in results]
    available = [rank for rank in ranks if rank is not None]
    return {
        "recall_at_1": sum(rank == 1 for rank in available) / len(results),
        "recall_at_3": sum(rank is not None and rank <= 3 for rank in available) / len(results),
        "recall_at_5": sum(rank is not None and rank <= 5 for rank in available) / len(results),
        "mrr_at_10": sum(1 / rank for rank in available if rank <= 10) / len(results),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    gold_path = root / "evaluation/rag/embedding_gold_v1.jsonl"
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    if sha256(gold_path) != GOLD_SHA256 or sha256(chunks_path) != CHUNKS_SHA256:
        print("BASELINE_REPRODUCTION = FAIL")
        return 2
    chunks = load_chunks(chunks_path)
    gold = load_gold(gold_path)
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    if len(filtered) != 353:
        print("BASELINE_REPRODUCTION = FAIL")
        return 2
    paired = pair_target_cases(gold)
    if len(paired) != 16:
        raise ValueError(f"expected 16 EN/AR cases, found {len(paired)}")
    spec = next(spec for spec in MODEL_SPECS if spec.model_name == MODEL_NAME)
    snapshot = find_snapshot()
    provider = SentenceTransformerEmbeddingProvider(
        spec, model_ref=snapshot, revision=MODEL_REVISION
    )
    passage_vectors = provider.embed_passages([embedding_text(chunk) for chunk in filtered])
    query_map: dict[str, tuple[int, str]] = {}
    for case_index, item in enumerate(paired):
        for variant in ("ORIGINAL", *COUNTERPART_VARIANTS):
            case = item.get(variant)
            if case is not None:
                query_map.setdefault(case.query, (case_index, variant))
    query_texts = list(query_map)
    query_vectors = dict(zip(query_texts, provider.embed_queries(query_texts), strict=True))
    results = []
    for item in paired:
        original = item["ORIGINAL"]
        assert original is not None
        variants = {}
        for variant in ("ORIGINAL", *COUNTERPART_VARIANTS):
            case = item.get(variant)
            variants[variant] = (
                rank_query(query_vectors[case.query], passage_vectors, filtered, case)
                if case is not None
                else unavailable_result()
            )
        result = {
            "case_id": original.id,
            "original_language": original.language,
            "original_script": original.script,
            "original_query": original.query,
            "expected_source_ids": original.expected_source_ids,
            "variants": variants,
        }
        result["failure_reason"] = classify_failure(result)
        results.append(result)
    baseline_metrics = {
        language: reciprocal_metrics(
            [result for result in results if result["original_language"] == language], query_vectors
        )
        for language in ("en", "ar")
    }
    counterpart_metrics = {}
    for language in ("en", "ar"):
        language_results = [result for result in results if result["original_language"] == language]
        counterpart_metrics[language] = {}
        for variant in COUNTERPART_VARIANTS:
            variant_results = [result["variants"][variant] for result in language_results]
            counterpart_metrics[language][variant] = {
                "available_cases": sum(item["available"] for item in variant_results),
                "hit_at_5_count": hit_count(variant_results),
                "recall_at_5_available": recall5(variant_results),
            }
    rank_matrix = [
        {
            "case_id": result["case_id"],
            "original_language": result["original_language"],
            **{
                f"{variant.lower()}_rank": result["variants"][variant]["expected_source_rank"]
                for variant in RANK_VARIANTS
            },
        }
        for result in results
    ]
    failures = [
        {
            "case_id": result["case_id"],
            "original_query": result["original_query"],
            "expected_source_ids": result["expected_source_ids"],
            "original_expected_source_rank": result["variants"]["ORIGINAL"]["expected_source_rank"],
            "counterpart_ranks": {
                variant: result["variants"][variant]["expected_source_rank"]
                for variant in COUNTERPART_VARIANTS
            },
            "top_5_source_ids": result["variants"]["ORIGINAL"]["top_5_source_ids"],
            "reason": result["failure_reason"],
        }
        for result in results
        if not result["variants"]["ORIGINAL"].get("hit_at_5")
    ]
    projections = {
        language: diagnostic_projection(
            language, [result for result in results if result["original_language"] == language]
        )
        for language in ("en", "ar")
    }
    report = {
        "schema_version": "j6-en-ar-diagnostic-v1",
        "gold_sha256": sha256(gold_path),
        "chunks_sha256": sha256(chunks_path),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "input_policy": "CONTENT_FILTERED",
        "content_filtered_count": len(filtered),
        "baseline_metrics": baseline_metrics,
        "frozen_baseline_recall5": BASELINE_RECALL5,
        "counterpart_metrics": counterpart_metrics,
        "cases": results,
        "rank_matrix": rank_matrix,
        "per_failure_analysis": failures,
        "diagnostic_reason_counts": reason_counts(results),
        "gold_ambiguity_status": "not_evaluated",
        "topic_competition": "NOT_EVALUATED",
        "french_counterpart_recovery": {
            language: counterpart_metrics[language]["FR_COUNTERPART"] for language in ("en", "ar")
        },
        "diagnostic_projections": projections,
        "global_diagnosis": (
            "QUERY_REPRESENTATION_GAP_SUPPORTED"
            if any(
                result["reason"] == "FRENCH_REPRESENTATION_RECOVERY"
                for result in failures
            )
            else "INSUFFICIENT_EVIDENCE"
        ),
        "recommended_next_step": "RESUME_J6_07_WHEN_GROQ_AVAILABLE",
        "model_selection": "NO_WINNER",
    }
    output = root / "backend/data/rag/manifests/en_ar_diagnostic_v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"report={output}")
    en_count = sum(r["original_language"] == "en" for r in results)
    ar_count = sum(r["original_language"] == "ar" for r in results)
    print(f"CONTENT_FILTERED={len(filtered)} EN={en_count} AR={ar_count}")
    for language, metrics in baseline_metrics.items():
        print(f"{language} ORIGINAL Recall@5={metrics['recall_at_5']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
