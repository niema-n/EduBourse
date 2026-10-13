"""Run the offline Ary-Latin retrieval diagnosis against frozen BGE-M3."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.ary_latin_diagnostic import (
    DIAGNOSTIC_VARIANTS,
    build_variant_queries,
    derive_conclusion,
    diagnostic_recall5,
    failure_reasons,
    normalize_ary_latin,
    pair_gold_cases,
    rank_variant,
)
from app.rag.embedding_benchmark import (
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    classify_index_inputs,
    embedding_text,
    format_query,
    load_chunks,
    load_gold,
    verify_sentence_transformer_snapshot,
)

MODEL_NAME = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_snapshot() -> Path:
    downloaded = Path(
        snapshot_download(
            MODEL_NAME,
            revision=MODEL_REVISION,
            local_files_only=True,
            allow_patterns=[
                "config*.json",
                "modules.json",
                "tokenizer*",
                "sentencepiece*",
                "model.safetensors*",
                "pytorch_model.bin*",
                "1_Pooling/*",
                "2_Normalize/*",
            ],
        )
    )
    candidates = [downloaded, *downloaded.parent.iterdir()]
    for candidate in candidates:
        if candidate.is_dir():
            try:
                verify_sentence_transformer_snapshot(candidate)
            except ValueError:
                continue
            return candidate
    raise ValueError("no complete local BGE-M3 snapshot found")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    gold_path = root / "evaluation/rag/embedding_gold_v1.jsonl"
    chunks = load_chunks(chunks_path)
    gold = load_gold(gold_path)
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    paired = pair_gold_cases(gold)
    if len(paired) != 8:
        raise ValueError(f"expected 8 Ary-Latin cases, found {len(paired)}")

    snapshot = find_snapshot()
    spec = MODEL_SPECS[0]
    if spec.model_name != MODEL_NAME:
        raise ValueError("BGE-M3 is not the first frozen model spec")
    provider = SentenceTransformerEmbeddingProvider(
        spec, model_ref=snapshot, revision=MODEL_REVISION
    )
    passage_vectors = provider.embed_passages([embedding_text(chunk) for chunk in filtered])
    query_items = build_variant_queries(paired)
    query_texts = []
    for variant, case_index, case in query_items:
        query = normalize_ary_latin(case.query) if variant == "ARY_LATIN_NORMALIZED" else case.query
        query_texts.append(format_query(spec, query))
    query_vectors = provider.model.encode(
        query_texts,
        batch_size=provider.batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    case_results = [
        {
            "id": item["ORIGINAL_ARY_LATIN"].id,
            "topic": item["ORIGINAL_ARY_LATIN"].topic,
            "original_query": item["ORIGINAL_ARY_LATIN"].query,
            "expected_source_ids": item["ORIGINAL_ARY_LATIN"].expected_source_ids,
            "variants": {},
        }
        for item in paired
    ]
    for cursor, (variant, case_index, case) in enumerate(query_items):
        result = rank_variant(query_vectors[cursor], passage_vectors, filtered, case)
        result["available"] = True
        case_results[case_index]["variants"][variant] = result
    for case_index, item in enumerate(paired):
        for variant in DIAGNOSTIC_VARIANTS:
            if variant not in case_results[case_index]["variants"]:
                case_results[case_index]["variants"][variant] = {"available": False}
        case_results[case_index]["failure_reasons"] = failure_reasons(case_results[case_index])

    variant_metrics = {
        variant: {
            "available_cases": sum(
                result["variants"][variant]["available"] for result in case_results
            ),
            "recall_at_5": diagnostic_recall5(
                [result["variants"][variant] for result in case_results]
            ),
        }
        for variant in DIAGNOSTIC_VARIANTS
    }
    failure_counts = Counter(
        reason for result in case_results for reason in result["failure_reasons"]
    )
    report = {
        "schema_version": "j6-ary-latin-diagnostic-v1",
        "gold_sha256": sha256(gold_path),
        "chunks_sha256": sha256(chunks_path),
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "input_policy": "CONTENT_FILTERED",
        "content_filtered_count": len(filtered),
        "cases": case_results,
        "variant_metrics": variant_metrics,
        "failure_reason_counts": dict(sorted(failure_counts.items())),
        "gold_ambiguity_status": "not_evaluated",
        "gold_ambiguity_findings": None,
        "normalization_note": (
            "The tested lightweight normalization produced no Recall@5 improvement "
            "on this gold set; it changed only one of eight queries, so the evidence "
            "is limited."
        ),
        "fr_counterpart_note": (
            "FR_COUNTERPART Recall@5=1.000 is based on 6 available cases; "
            "public_offerings and investor_protection have no frozen French counterpart."
        ),
        "diagnostic_projection": {
            "current_bge_content_filtered": {
                "fr": 1.0,
                "en": 0.75,
                "ar": 0.75,
                "ary-latin": 0.625,
                "ary-arabic": 0.875,
            },
            "ary_latin_to_0_875": {"macro_recall5": 0.85, "worst_recall5": 0.75},
            "ary_latin_to_1_000": {"macro_recall5": 0.875, "worst_recall5": 0.75},
        },
        "next_work": {
            "primary_experiment": "J6_07_QUERY_ADAPTER_EXPERIMENT",
            "parallel_diagnostic_track": "EN_AR_RETRIEVAL_DIAGNOSTIC",
        },
        "model_selection": "NO_WINNER",
        "narrative": (
            "Two of three Ary-Latin misses are recovered by Ary-Arabic; the third "
            "remains a miss in Ary-Arabic and Arabic but is recovered by French. "
            "The issue is broader than pure script transliteration."
        ),
        "conclusion": derive_conclusion(variant_metrics),
    }
    output = root / "backend/data/rag/manifests/ary_latin_diagnostic_v1.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report={output}")
    print(f"BGE passages={len(filtered)} queries={len(query_items)}")
    for variant, metrics in variant_metrics.items():
        print(f"{variant} Recall@5={metrics['recall_at_5']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
