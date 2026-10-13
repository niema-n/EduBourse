"""Generate and evaluate the frozen J6-07C confirmatory H1 run."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.embedding_benchmark import (  # noqa: E402
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    classify_index_inputs,
    embedding_text,
    load_chunks,
    load_gold,
    mrr_at_10,
    per_language_recall5,
    recall_at_k,
    verify_sentence_transformer_snapshot,
)
from app.rag.hybrid_policy import (  # noqa: E402
    HYBRID_POLICY_ID,
    expected_rank,
    fuse_rankings,
    hit_at,
    hybrid_branches,
    quality_gate,
    rank_query,
)
from app.rag.query_adapter import (  # noqa: E402
    ADAPTER_MODEL,
    ADAPTER_PROMPT_SHA256,
    GroqQueryAdapterProvider,
    generate_artifact_records,
    query_quality_flags,
    sanitized_provider_error,
    validate_query_artifact,
)

CONFIRMATORY_GOLD_SHA256 = (
    "09984f65ceab47d5b0aafdaec051cedf45219c183d765985bd95b2652b839289"
)
CONFIRMATORY_MANIFEST_SHA256 = (
    "aa83584e1bf9daa89dafa946c29fb100688645f4b25c4d3b6e28cab15a3787d8"
)
CHUNKS_SHA256 = "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
REPORT_PATH = "backend/data/rag/manifests/query_adapter_confirmatory_result_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifact(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def generate_confirmatory_artifact(gold, artifact_path: Path, api_key: str) -> list[dict]:
    if artifact_path.exists():
        raise RuntimeError("confirmatory query artifact already exists")
    provider = GroqQueryAdapterProvider(api_key=api_key, model=ADAPTER_MODEL)
    records = generate_artifact_records(gold, provider)
    validated = validate_query_artifact(records, gold)
    if len(validated) != 60:
        raise ValueError("confirmatory artifact must contain exactly 60 records")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in validated
        ),
        encoding="utf-8",
    )
    return validated


def evaluate_h1(gold, records, filtered, passage_vectors, query_vectors):
    rankings = []
    branch_rankings_by_case = {}
    for case in gold:
        branches = hybrid_branches(case.language, case.script, records[case.id])
        branch_rankings = [
            rank_query(query_vectors[query], passage_vectors, filtered) for _, query in branches
        ]
        rankings.append(
            branch_rankings[0]
            if len(branch_rankings) == 1
            else fuse_rankings(branch_rankings, filtered)
        )
        branch_rankings_by_case[case.id] = dict(
            zip((name for name, _ in branches), branch_rankings, strict=True)
        )
    language_metrics = per_language_recall5(rankings, gold, filtered)
    metrics = {
        "r_at_1": recall_at_k(rankings, gold, filtered, 1, "source"),
        "r_at_3": recall_at_k(rankings, gold, filtered, 3, "source"),
        "r_at_5": recall_at_k(rankings, gold, filtered, 5, "source"),
        "mrr_at_10": mrr_at_10(rankings, gold, filtered),
        "per_language_recall5": language_metrics,
        "macro_recall5": sum(language_metrics.values()) / len(language_metrics),
        "worst_recall5": min(language_metrics.values()),
    }
    return metrics, rankings, branch_rankings_by_case


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env", override=False)
    gold_path = root / "evaluation/rag/embedding_gold_confirmatory_v1.jsonl"
    manifest_path = root / "backend/data/rag/manifests/confirmatory_gold_v1.json"
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    artifact_path = root / "evaluation/rag/query_adapter_confirmatory_v1.jsonl"
    report_path = root / REPORT_PATH
    if sha256(gold_path) != CONFIRMATORY_GOLD_SHA256:
        raise ValueError("confirmatory gold hash mismatch")
    if sha256(manifest_path) != CONFIRMATORY_MANIFEST_SHA256:
        raise ValueError("confirmatory manifest hash mismatch")
    if sha256(chunks_path) != CHUNKS_SHA256:
        raise ValueError("frozen chunks hash mismatch")
    gold = load_gold(gold_path)
    chunks = load_chunks(chunks_path)
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    if len(gold) != 60 or len(filtered) != 353:
        raise ValueError("confirmatory cardinality mismatch")
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("STATUS = STOPPED_PROVIDER_FAILURE")
        print("PROVIDER_ERROR_TYPE = MissingAPIKey")
        print("CAUSE = GROQ_API_KEY is not configured")
        return 2
    try:
        records = generate_confirmatory_artifact(gold, artifact_path, api_key)
    except Exception as exc:  # noqa: BLE001
        print("STATUS = STOPPED_PROVIDER_FAILURE")
        print(f"PROVIDER_ERROR_TYPE = {type(exc).__name__}")
        print(f"CAUSE = {sanitized_provider_error(exc)}")
        print("ADAPTER_GENERATION_COMPLETED = NO")
        print("H1_EVALUATION_COMPLETED = NO")
        print("QUERY_ARTIFACT = NOT_CREATED")
        return 2

    record_map = {record["case_id"]: record for record in records}
    query_flags = {
        case.id: query_quality_flags(case, record_map[case.id]) for case in gold
    }
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
        / MODEL_REVISION
    )
    verify_sentence_transformer_snapshot(snapshot)
    spec = next(spec for spec in MODEL_SPECS if spec.model_name == MODEL_NAME)
    provider = SentenceTransformerEmbeddingProvider(
        spec, model_ref=snapshot, revision=MODEL_REVISION
    )
    provider.batch_size = 1
    passage_vectors = provider.embed_passages([embedding_text(chunk) for chunk in filtered])
    query_texts = sorted(
        {
            query
            for record in records
            for query in (
                record["original_query"],
                record["retrieval_query_fr"],
                record["retrieval_query_ary_arabic"],
            )
            if query
        }
    )
    query_vectors = dict(zip(query_texts, provider.embed_queries(query_texts), strict=True))
    metrics, rankings, branch_rankings = evaluate_h1(
        gold, record_map, filtered, passage_vectors, query_vectors
    )
    failed = [
        case
        for case, ranking in zip(gold, rankings, strict=True)
        if not hit_at(ranking, case, filtered, 5)
    ]
    failed_ids = [case.id for case in failed]
    failed_by_language = {}
    for case in failed:
        label = case.language if case.language != "ary" else f"ary-{case.script}"
        failed_by_language.setdefault(label, []).append(case.id)
    for values in failed_by_language.values():
        values.sort()
    forensics = []
    for case in failed:
        item = {
            "case_id": case.id,
            "language": case.language,
            "script": case.script,
            "expected_source_ids": case.expected_source_ids,
            "expected_source_rank": expected_rank(rankings[gold.index(case)], case, filtered),
        }
        if case.language == "ary" and case.script == "latin":
            branches = branch_rankings[case.id]
            item.update(
                {
                    "original_branch_rank": expected_rank(branches["original"], case, filtered),
                    "french_branch_rank": expected_rank(branches["french"], case, filtered),
                    "ary_arabic_branch_rank": expected_rank(branches["ary_arabic"], case, filtered),
                    "fused_rank": item["expected_source_rank"],
                }
            )
        forensics.append(item)
    report = {
        "schema_version": "j6-07c-confirmatory-result-v1",
        "confirmatory_gold_path": "evaluation/rag/embedding_gold_confirmatory_v1.jsonl",
        "confirmatory_gold_sha256": sha256(gold_path),
        "confirmatory_query_artifact_path": "evaluation/rag/query_adapter_confirmatory_v1.jsonl",
        "confirmatory_query_artifact_sha256": sha256(artifact_path),
        "chunks_sha256": sha256(chunks_path),
        "policy_id": HYBRID_POLICY_ID,
        "policy_origin": "POST_HOC_FROM_J6_07_EXP1",
        "evaluation_type": "INDEPENDENT_CONFIRMATORY_EVALUATION",
        "independent_validation": True,
        "confirmatory_gold_frozen_before_evaluation": True,
        "policy_frozen_before_evaluation": True,
        "query_adapter_frozen_before_evaluation": True,
        "selection_bias_from_development_set_acknowledged": True,
        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "adapter_provider": "groq",
        "adapter_model": ADAPTER_MODEL,
        "adapter_prompt_sha256": ADAPTER_PROMPT_SHA256,
        "pacing_interval_seconds": 2.5,
        "record_counts": {
            "confirmatory_records": len(records),
            "french_queries": sum(record["retrieval_query_fr"] is not None for record in records),
            "ary_latin_arabic_queries": sum(
                record["retrieval_query_ary_arabic"] is not None for record in records
            ),
            "null_ary_arabic_branches": sum(
                record["retrieval_query_ary_arabic"] is None for record in records
            ),
            "content_filtered_chunks": len(filtered),
        },
        "metrics": metrics,
        "query_quality_flags": query_flags,
        "query_quality_flag_count": sum(bool(flags) for flags in query_flags.values()),
        "failed_case_ids": failed_ids,
        "failed_cases_by_language": failed_by_language,
        "failed_case_forensics": forensics,
        "quality_gate": quality_gate(metrics["macro_recall5"], metrics["worst_recall5"]),
        "retrieval_policy_decision": (
            "ACCEPT_H1_LANGUAGE_ROUTED_V1"
            if quality_gate(metrics["macro_recall5"], metrics["worst_recall5"])
            else "ACCEPT_H1_WITH_DOCUMENTED_CONFIRMATORY_LIMITATIONS"
        ),
        "embedding_decision": (
            "ACCEPT_BGE_M3_FOR_J6"
            if quality_gate(metrics["macro_recall5"], metrics["worst_recall5"])
            else "ACCEPT_BGE_M3_WITH_DOCUMENTED_CONFIRMATORY_LIMITATIONS"
        ),
        "known_limitations": [
            "Retrieval validation only; Chroma, grounded generation, and citations "
            "are not implemented.",
            "Query-quality flags are diagnostic and do not trigger case deletion or regeneration.",
        ],
        "deployment_ready": False,
        "no_more_retrieval_policy_tuning": True,
        "next_step": "J6_05B_CHROMA",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("ADAPTER_GENERATION_COMPLETED = YES")
    print("H1_EVALUATION_COMPLETED = YES")
    print(f"QUERY_ARTIFACT_SHA256 = {sha256(artifact_path)}")
    print(f"R@5 = {metrics['r_at_5']:.6f}")
    print(f"MACRO_RECALL5 = {metrics['macro_recall5']:.6f}")
    print(f"WORST_RECALL5 = {metrics['worst_recall5']:.6f}")
    print(f"REPORT_PATH = {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
