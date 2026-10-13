"""Offline English/Arabic retrieval diagnosis for the frozen J6 corpus."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import GoldCase, cosine_similarity

TARGET_LANGUAGES = ("en", "ar")
COUNTERPART_VARIANTS = (
    "FR_COUNTERPART",
    "EN_COUNTERPART",
    "AR_COUNTERPART",
    "ARY_LATIN_COUNTERPART",
    "ARY_ARABIC_COUNTERPART",
)
RANK_VARIANTS = ("ORIGINAL", *COUNTERPART_VARIANTS)
BASELINE_RECALL5 = {"fr": 1.0, "en": 0.75, "ar": 0.75, "ary-latin": 0.625, "ary-arabic": 0.875}


def pair_target_cases(cases: list[GoldCase]) -> list[dict[str, GoldCase | None]]:
    """Pair EN/AR cases with unique compatible frozen records by metadata."""
    paired = []
    for original in cases:
        if original.language not in TARGET_LANGUAGES:
            continue
        item: dict[str, GoldCase | None] = {"ORIGINAL": original}
        for language, variant, script in (
            ("fr", "FR_COUNTERPART", "latin"),
            ("en", "EN_COUNTERPART", "latin"),
            ("ar", "AR_COUNTERPART", "arabic"),
            ("ary", "ARY_LATIN_COUNTERPART", "latin"),
            ("ary", "ARY_ARABIC_COUNTERPART", "arabic"),
        ):
            candidates = [
                case
                for case in cases
                if case.language == language
                and case.script == script
                and case.topic == original.topic
                and case.expected_source_ids == original.expected_source_ids
                and case.id != original.id
            ]
            item[variant] = candidates[0] if len(candidates) == 1 else None
        paired.append(item)
    return paired


def expected_source_rank(
    ranking: list[int], case: GoldCase, chunks: list[ChunkRecord]
) -> int | None:
    for rank, index in enumerate(ranking, start=1):
        if chunks[index].source_id in case.expected_source_ids:
            return rank
    return None


def rank_query(
    query_vector: np.ndarray,
    passage_vectors: np.ndarray,
    chunks: list[ChunkRecord],
    case: GoldCase,
) -> dict[str, Any]:
    scores = cosine_similarity(query_vector, passage_vectors)
    ranking = sorted(
        range(len(scores)), key=lambda index: (-float(scores[index]), chunks[index].chunk_id)
    )
    top = ranking[:5]
    return {
        "available": True,
        "expected_source_ids": case.expected_source_ids,
        "expected_source_rank": expected_source_rank(ranking, case, chunks),
        "hit_at_1": bool(top and chunks[top[0]].source_id in case.expected_source_ids),
        "hit_at_3": any(chunks[index].source_id in case.expected_source_ids for index in top[:3]),
        "hit_at_5": any(chunks[index].source_id in case.expected_source_ids for index in top),
        "top_5_source_ids": [chunks[index].source_id for index in top],
    }


def unavailable_result() -> dict[str, Any]:
    return {"available": False, "expected_source_rank": None}


def recall5(results: list[dict[str, Any]]) -> float:
    available = [result for result in results if result["available"]]
    return (
        sum(result.get("hit_at_5", False) for result in available) / len(available)
        if available
        else 0.0
    )


def hit_count(results: list[dict[str, Any]]) -> int:
    return sum(bool(result.get("available") and result.get("hit_at_5")) for result in results)


def classify_failure(result: dict[str, Any]) -> str:
    original = result["variants"]["ORIGINAL"]
    if original.get("hit_at_5"):
        return "NOT_A_FAILURE"
    french = result["variants"].get("FR_COUNTERPART", unavailable_result())
    ary_arabic = result["variants"].get("ARY_ARABIC_COUNTERPART", unavailable_result())
    other_hits = any(
        variant.get("available") and variant.get("hit_at_5")
        for name, variant in result["variants"].items()
        if name != "ORIGINAL"
    )
    if french.get("available") and french.get("hit_at_5"):
        return "FRENCH_REPRESENTATION_RECOVERY"
    if result["original_language"] == "ar" and ary_arabic.get("hit_at_5"):
        return "ARABIC_VARIANT_RECOVERY"
    if other_hits:
        return "MULTILINGUAL_REPRESENTATION_GAP"
    return "CORPUS_GAP_SUSPECTED"


def diagnostic_projection(
    language: str, results: list[dict[str, Any]], baseline: dict[str, float] | None = None
) -> dict[str, Any]:
    baseline = baseline or BASELINE_RECALL5
    recoverable = sum(
        bool(
            result["variants"]["ORIGINAL"].get("hit_at_5")
            or any(
                variant.get("available") and variant.get("hit_at_5")
                for name, variant in result["variants"].items()
                if name != "ORIGINAL"
            )
        )
        for result in results
    )
    projected = recoverable / len(results) if results else 0.0
    values = dict(baseline)
    values[language] = projected
    return {
        "language": language,
        "recoverable_recall5": projected,
        "diagnostic_only": True,
        "projected_macro_recall5": sum(values.values()) / len(values),
        "projected_worst_recall5": min(values.values()),
    }


def reason_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                result["failure_reason"]
                for result in results
                if result["failure_reason"] != "NOT_A_FAILURE"
            ).items()
        )
    )
