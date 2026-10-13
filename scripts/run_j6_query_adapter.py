"""Generate frozen J6-07 query variants and evaluate isolated BGE retrieval."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.embedding_benchmark import (
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    classify_index_inputs,
    embedding_text,
    load_chunks,
    load_gold,
)
from app.rag.query_adapter import (
    ADAPTER_MODEL,
    ADAPTER_PROMPT_SHA256,
    ADAPTER_SYSTEM_PROMPT,
    POLICY_DEFINITIONS,
    GroqQueryAdapterProvider,
    evaluate_policy,
    experiment_gate,
    generate_artifact_records,
    quality_gate_from_metrics,
    query_quality_flags,
    resolve_embedding_model_spec,
    sanitized_provider_error,
    validate_content_filtered_count,
    validate_embedding_model_revision,
    validate_query_artifact,
)

GOLD_SHA256 = "68da7ebcd739dc42e874bf0052b7a2a6c33a2013ba1cd91979ccea7b6d0355b5"
CHUNKS_SHA256 = "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_BGE_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifact(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def expected_source_rank(ranking, filtered, expected_source_ids):
    return next(
        (
            rank
            for rank, item in enumerate(ranking, 1)
            if filtered[item].source_id in expected_source_ids
        ),
        None,
    )


def generate_artifact(gold, path: Path, provider) -> list[dict]:
    records = generate_artifact_records(gold, provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    return records


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env", override=False)
    gold_path = root / "evaluation/rag/embedding_gold_v1.jsonl"
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    artifact_path = root / "evaluation/rag/query_adapter_v1.jsonl"
    report_path = root / "backend/data/rag/manifests/query_adapter_experiment_v1.json"
    gold = load_gold(gold_path)
    chunks = load_chunks(chunks_path)
    if sha256(gold_path) != GOLD_SHA256 or sha256(chunks_path) != CHUNKS_SHA256:
        raise ValueError("frozen gold or chunks hash mismatch")
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    try:
        validate_content_filtered_count(len(filtered))
    except ValueError:
        print(f"CONTENT_FILTER_COUNT_MISMATCH = {len(filtered)}")
        return 3

    if artifact_path.exists():
        records = load_artifact(artifact_path)
        validate_query_artifact(records, gold)
    else:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            print("ADAPTER_GENERATION_COMPLETED = NO\nRETRIEVAL_EVALUATION_COMPLETED = NO")
            return 2
        try:
            records = generate_artifact(
                gold,
                artifact_path,
                GroqQueryAdapterProvider(api_key=api_key, model=ADAPTER_MODEL),
            )
        except Exception as exc:  # noqa: BLE001
            print("ADAPTER_GENERATION_COMPLETED = NO")
            print("RETRIEVAL_EVALUATION_COMPLETED = NO")
            print(f"PROVIDER_ERROR_TYPE = {type(exc).__name__}")
            print(f"PROVIDER_ERROR_MESSAGE = {sanitized_provider_error(exc)}")
            return 2

    record_map = {record["case_id"]: record for record in records}
    quality_flags = {
        record["case_id"]: query_quality_flags(
            next(case for case in gold if case.id == record["case_id"]), record
        )
        for record in records
    }
    snapshot_root = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
    snapshot = snapshot_root / MODEL_REVISION
    model_spec = resolve_embedding_model_spec(MODEL_SPECS, MODEL_NAME)
    validate_embedding_model_revision(snapshot.name, EXPECTED_BGE_REVISION)
    provider = SentenceTransformerEmbeddingProvider(
        model_spec, model_ref=snapshot, revision=MODEL_REVISION
    )
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
    query_vectors_array = provider.embed_queries(query_texts)
    query_vectors = dict(zip(query_texts, query_vectors_array, strict=True))
    policies = (
        "P0_ORIGINAL_ONLY",
        "P1_FRENCH_ONLY",
        "P2_ORIGINAL_PLUS_FRENCH_RRF",
        "P3_ORIGINAL_PLUS_ADAPTIVE_RRF",
    )
    evaluations = {}
    rankings_by_policy = {}
    for policy in policies:
        metrics, rankings = evaluate_policy(
            policy, gold, record_map, filtered, passage_vectors, query_vectors
        )
        evaluations[policy] = metrics
        rankings_by_policy[policy] = rankings
    p0 = rankings_by_policy[policies[0]]
    p3 = rankings_by_policy[policies[-1]]
    changed = []
    for index, case in enumerate(gold):
        def hit(ranking, expected_source_ids=case.expected_source_ids):
            return any(
                filtered[item].source_id in expected_source_ids for item in ranking[:5]
            )

        if hit(p0[index]) != hit(p3[index]):
            changed.append(
                {
                    "case_id": case.id,
                    "language": case.language,
                    "script": case.script,
                    "p0_expected_source_rank": expected_source_rank(
                        p0[index], filtered, case.expected_source_ids
                    ),
                    "p3_expected_source_rank": expected_source_rank(
                        p3[index], filtered, case.expected_source_ids
                    ),
                    "change": "RECOVERED" if hit(p3[index]) else "REGRESSED",
                }
            )
    p0_lang = evaluations[policies[0]]["per_language_recall5"]
    p3_lang = evaluations[policies[-1]]["per_language_recall5"]
    report = {
        "schema_version": "j6-query-adapter-experiment-v1",
        "gold_sha256": sha256(gold_path),
        "chunks_sha256": sha256(chunks_path),
        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "adapter_provider": "groq",
        "adapter_model": ADAPTER_MODEL,
        "adapter_prompt_sha256": ADAPTER_PROMPT_SHA256,
        "adapter_prompt": ADAPTER_SYSTEM_PROMPT,
        "generation_settings": {
            "temperature": 0,
            "max_completion_tokens": 160,
            "response_format": "json_object",
        },
        "rrf_k": 60,
        "query_artifact_sha256": sha256(artifact_path),
        "query_records": len(records),
        "policy_definitions": POLICY_DEFINITIONS,
        "metrics": evaluations,
        "p3_deltas_vs_p0": {
            language: p3_lang[language] - p0_lang[language] for language in p0_lang
        },
        "recovered_query_count": sum(item["change"] == "RECOVERED" for item in changed),
        "regressed_query_count": sum(item["change"] == "REGRESSED" for item in changed),
        "per_case_changed_rank": changed,
        "query_quality_flags": quality_flags,
        "query_quality_flag_count": sum(bool(flags) for flags in quality_flags.values()),
        "language_regression": any(p3_lang[language] < p0_lang[language] for language in p0_lang),
        "quality_gate": quality_gate_from_metrics(
            p3_lang,
            evaluations[policies[-1]]["macro_source_recall5"],
            evaluations[policies[-1]]["worst_language_recall5"],
        ),
        "embedding_model_selection": "NO_WINNER",
        "embedding_model_manifest": "NOT_CREATED",
    }
    report["query_adapter_experiment_gate"] = experiment_gate(report["quality_gate"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"report={report_path}")
    print(f"query_artifact={artifact_path}")
    print(f"QUERY_ADAPTER_EXPERIMENT_GATE = {report['query_adapter_experiment_gate']}")
    print("READY_FOR_CLAUDE_J6_07_AUDIT = YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
