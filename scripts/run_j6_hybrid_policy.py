"""Run the isolated post-hoc H1 replay over frozen J6-07 data."""

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
    mrr_at_10,
    per_language_recall5,
    recall_at_k,
    verify_sentence_transformer_snapshot,
)
from app.rag.hybrid_policy import (  # noqa: E402
    HYBRID_POLICY_ID,
    RRF_K,
    expected_rank,
    fuse_rankings,
    hit_at,
    hybrid_branches,
    quality_gate,
    rank_query,
)

GOLD_SHA256 = "68da7ebcd739dc42e874bf0052b7a2a6c33a2013ba1cd91979ccea7b6d0355b5"
CHUNKS_SHA256 = "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
ARTIFACT_SHA256 = "b510a4a772175e1567f5fefd18131d6464de05a12d632acf5b3aca4e5f1939ef"
EXP1_REPORT_SHA256 = "3a7c42908f346b5d11dfe9f35c2509dd6a49cca24e6692f5948ce643972880f3"
MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifact(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def policy_rankings(cases, records, chunks, passage_vectors, query_vectors, policy):
    rankings = []
    for case in cases:
        record = records[case.id]
        if policy == "P0":
            branches = [("original", record["original_query"])]
        elif policy == "P1":
            branches = [("french", record["retrieval_query_fr"])]
        elif policy == "H1":
            branches = hybrid_branches(case.language, case.script, record)
        else:
            raise ValueError("unsupported replay policy")
        branch_rankings = [
            rank_query(query_vectors[query], passage_vectors, chunks) for _, query in branches
        ]
        rankings.append(
            branch_rankings[0]
            if len(branch_rankings) == 1
            else fuse_rankings(branch_rankings, chunks)
        )
    return rankings


def metrics(rankings, cases, chunks):
    per_language = per_language_recall5(rankings, cases, chunks)
    return {
        "r_at_1": recall_at_k(rankings, cases, chunks, 1, "source"),
        "r_at_3": recall_at_k(rankings, cases, chunks, 3, "source"),
        "r_at_5": recall_at_k(rankings, cases, chunks, 5, "source"),
        "mrr_at_10": mrr_at_10(rankings, cases, chunks),
        "per_language_recall5": per_language,
        "macro_recall5": sum(per_language.values()) / len(per_language),
        "worst_recall5": min(per_language.values()),
    }


def transitions(reference, candidate, cases, chunks):
    recovered = []
    regressed = []
    for index, case in enumerate(cases):
        old_hit = hit_at(reference[index], case, chunks, 5)
        new_hit = hit_at(candidate[index], case, chunks, 5)
        if not old_hit and new_hit:
            recovered.append(case.id)
        elif old_hit and not new_hit:
            regressed.append(case.id)
    return recovered, regressed


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    gold_path = root / "evaluation/rag/embedding_gold_v1.jsonl"
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    artifact_path = root / "evaluation/rag/query_adapter_v1.jsonl"
    exp1_report_path = root / "backend/data/rag/manifests/query_adapter_experiment_v1.json"
    if (
        sha256(gold_path) != GOLD_SHA256
        or sha256(chunks_path) != CHUNKS_SHA256
        or sha256(artifact_path) != ARTIFACT_SHA256
        or sha256(exp1_report_path) != EXP1_REPORT_SHA256
    ):
        raise ValueError("frozen replay input hash mismatch")
    gold = load_gold(gold_path)
    chunks = load_chunks(chunks_path)
    records = {record["case_id"]: record for record in load_artifact(artifact_path)}
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    if len(filtered) != 353 or len(gold) != 40 or len(records) != 40:
        raise ValueError("frozen replay cardinality mismatch")
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
            for record in records.values()
            for query in (
                record["original_query"],
                record["retrieval_query_fr"],
                record["retrieval_query_ary_arabic"],
            )
            if query
        }
    )
    query_vectors = dict(zip(query_texts, provider.embed_queries(query_texts), strict=True))
    p0_cases = list(gold)
    p0 = policy_rankings(p0_cases, records, filtered, passage_vectors, query_vectors, "P0")
    p1 = policy_rankings(p0_cases, records, filtered, passage_vectors, query_vectors, "P1")
    h1 = policy_rankings(p0_cases, records, filtered, passage_vectors, query_vectors, "H1")
    h1_metrics = metrics(h1, gold, filtered)
    p0_metrics = metrics(p0, gold, filtered)
    p1_metrics = metrics(p1, gold, filtered)
    recovered_p0, regressed_p0 = transitions(p0, h1, gold, filtered)
    recovered_p1, regressed_p1 = transitions(p1, h1, gold, filtered)
    ary_cases = [case for case in gold if case.language == "ary" and case.script == "latin"]
    ary_attribution = []
    for case in ary_cases:
        record = records[case.id]
        original = rank_query(query_vectors[record["original_query"]], passage_vectors, filtered)
        french = rank_query(query_vectors[record["retrieval_query_fr"]], passage_vectors, filtered)
        arabic = rank_query(
            query_vectors[record["retrieval_query_ary_arabic"]], passage_vectors, filtered
        )
        ary_attribution.append(
            {
                "case_id": case.id,
                "original_rank": expected_rank(original, case, filtered),
                "french_rank": expected_rank(french, case, filtered),
                "ary_arabic_rank": expected_rank(arabic, case, filtered),
                "fused_rank": expected_rank(h1[gold.index(case)], case, filtered),
            }
        )
    report = {
        "schema_version": "j6-07b-hybrid-replay-v1",
        "policy_id": HYBRID_POLICY_ID,
        "policy_definition": {
            "fr": "original_only",
            "en": "french_only",
            "ar": "french_only",
            "ary_arabic": "french_only",
            "ary_latin": "original_plus_french_plus_ary_arabic_rrf",
        },
        "policy_origin": "POST_HOC_FROM_J6_07_EXP1",
        "evaluation_type": "SAME_GOLD_REPLAY",
        "independent_validation": False,
        "selection_bias_acknowledged": True,
        "gold_sha256": sha256(gold_path),
        "chunks_sha256": sha256(chunks_path),
        "query_artifact_sha256": sha256(artifact_path),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "rrf_k": RRF_K,
        "overall": h1_metrics,
        "per_language_recall5": h1_metrics["per_language_recall5"],
        "macro_recall5": h1_metrics["macro_recall5"],
        "worst_recall5": h1_metrics["worst_recall5"],
        "p0_metrics": p0_metrics,
        "p1_metrics": p1_metrics,
        "recovered_vs_p0": recovered_p0,
        "regressed_vs_p0": regressed_p0,
        "recovered_vs_p1": recovered_p1,
        "regressed_vs_p1": regressed_p1,
        "ary_latin_branch_attribution": ary_attribution,
        "replay_quality_gate": quality_gate(
            h1_metrics["macro_recall5"], h1_metrics["worst_recall5"]
        ),
        "meaning_preservation_known_issues": ["ary-latin-03", "ary-latin-05", "ary-latin-06"],
        "terminology_normalization_known_issues": ["en-02", "ar-02"],
        "source_leakage_true_count": 0,
        "deployment_ready": False,
        "chroma_ready": False,
        "recommended_next_step": "INDEPENDENT_CONFIRMATORY_EVALUATION",
    }
    output = root / "backend/data/rag/manifests/query_adapter_hybrid_replay_v1.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"report={output}")
    print(f"H1_RECALL5={h1_metrics['r_at_5']:.3f}")
    print(f"H1_MACRO={h1_metrics['macro_recall5']:.3f}")
    print(f"H1_WORST={h1_metrics['worst_recall5']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
