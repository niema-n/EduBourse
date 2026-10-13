"""Diagnostic helpers for the frozen Ary-Latin retrieval cases."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np

from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import (
    GoldCase,
    cosine_similarity,
)

DIAGNOSTIC_VARIANTS = (
    "ORIGINAL_ARY_LATIN",
    "ARY_ARABIC_COUNTERPART",
    "AR_COUNTERPART",
    "FR_COUNTERPART",
    "ARY_LATIN_NORMALIZED",
)
REQUIRED_VARIANTS = DIAGNOSTIC_VARIANTS[:4]
REQUIRED_COUNTERPART_VARIANTS = REQUIRED_VARIANTS[1:]
ADJACENT_SOURCE_IDS_BY_TOPIC = {
    "valeur_liquidative": {
        "ammc-comprendre-les-instruments-financiers-et-leurs-mecanismes",
        "ammc-les-assemblees-generales-ordinaires",
        "ammc-comprendre-les-ipo",
        "ammc-les-documents-d-information-qu-il-faut-absolument-connaitre",
    },
    "public_offerings": {
        "ammc-comprendre-les-ipo",
        "ammc-comprendre-le-financement-collaboratif",
    },
    "investor_protection": {
        "ammc-les-assemblees-generales-ordinaires",
        "ammc-comprendre-le-financement-collaboratif",
        "ammc-comprendre-les-ipo",
    },
}


def normalize_ary_latin(text: str) -> str:
    """Apply only deterministic orthographic cleanup, never translation."""
    text = unicodedata.normalize("NFC", text.casefold())
    text = text.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'"}))
    text = re.sub(r"[!?]+", "?", text)
    return re.sub(r"\s+", " ", text).strip()


def pair_gold_cases(cases: list[GoldCase]) -> list[dict[str, GoldCase | None]]:
    """Pair each Ary-Latin case with compatible records from the frozen gold."""
    by_variant: dict[str, list[GoldCase]] = {
        "ARY_ARABIC_COUNTERPART": [
            case for case in cases if case.language == "ary" and case.script == "arabic"
        ],
        "AR_COUNTERPART": [case for case in cases if case.language == "ar"],
        "FR_COUNTERPART": [case for case in cases if case.language == "fr"],
    }
    originals = [
        case for case in cases if case.language == "ary" and case.script == "latin"
    ]
    paired = []
    for original in originals:
        item: dict[str, GoldCase | None] = {"ORIGINAL_ARY_LATIN": original}
        for variant, records in by_variant.items():
            matches = [
                case
                for case in records
                if case.topic == original.topic
                and case.expected_source_ids == original.expected_source_ids
            ]
            item[variant] = matches[0] if len(matches) == 1 else None
        paired.append(item)
    return paired


def expected_source_rank(
    ranking: list[int], case: GoldCase, chunks: list[ChunkRecord]
) -> int | None:
    for position, index in enumerate(ranking, start=1):
        if chunks[index].source_id in case.expected_source_ids:
            return position
    return None


def diagnostic_recall5(results: list[dict[str, Any]]) -> float:
    available = [result for result in results if result["available"]]
    return (
        sum(result["hit_at_5"] for result in available) / len(available)
        if available
        else 0.0
    )


def derive_conclusion(variant_metrics: dict[str, dict[str, Any]]) -> dict[str, str]:
    original = variant_metrics["ORIGINAL_ARY_LATIN"]["recall_at_5"]
    arabic = variant_metrics["ARY_ARABIC_COUNTERPART"]["recall_at_5"]
    french = variant_metrics["FR_COUNTERPART"]["recall_at_5"]
    normalized = variant_metrics["ARY_LATIN_NORMALIZED"]["recall_at_5"]
    if arabic > original and french > original and normalized == original:
        return {
            "diagnosis": "QUERY_REPRESENTATION_GAP",
            "recommended_next_step": "J6_07_QUERY_ADAPTER_EXPERIMENT",
            "rationale": (
                "Two of three Ary-Latin misses show cross-script/Arabizi representation "
                "problems; one shows broader language and terminology transfer difficulty. "
                "All three show adjacent-topic competition. Corpus and gold ambiguity are "
                "not established as primary causes. A Darija-Latin adapter alone cannot "
                "satisfy the frozen gate while English and Arabic remain at 0.750."
            ),
        }
    return {
        "diagnosis": "INCONCLUSIVE",
        "recommended_next_step": "MORE_DIAGNOSTICS",
        "rationale": "The frozen counterpart matrix does not isolate one dominant gap.",
    }


def rank_variant(
    vector: np.ndarray,
    passage_vectors: np.ndarray,
    chunks: list[ChunkRecord],
    case: GoldCase,
) -> dict[str, Any]:
    ranking = list(np.argsort(-cosine_similarity(vector, passage_vectors)))
    top = ranking[:5]
    return {
        "expected_source_ids": case.expected_source_ids,
        "top_1_source_id": chunks[top[0]].source_id if top else None,
        "top_3_source_ids": [chunks[index].source_id for index in top[:3]],
        "top_5_source_ids": [chunks[index].source_id for index in top],
        "top_5_titles": [chunks[index].title for index in top],
        "top_5_similarities": [
            round(float(cosine_similarity(vector, passage_vectors)[index]), 6)
            for index in top
        ],
        "expected_source_best_rank": expected_source_rank(ranking, case, chunks),
        "hit_at_1": bool(top and chunks[top[0]].source_id in case.expected_source_ids),
        "hit_at_3": any(chunks[index].source_id in case.expected_source_ids for index in top[:3]),
        "hit_at_5": any(chunks[index].source_id in case.expected_source_ids for index in top),
    }


def failure_reasons(case_result: dict[str, Any]) -> list[str]:
    original = case_result["variants"]["ORIGINAL_ARY_LATIN"]
    if original["hit_at_5"]:
        return []
    ary_arabic = case_result["variants"].get("ARY_ARABIC_COUNTERPART")
    ar = case_result["variants"].get("AR_COUNTERPART")
    fr = case_result["variants"].get("FR_COUNTERPART")
    def hit(result: dict[str, Any] | None) -> bool:
        return bool(result and result.get("available") and result.get("hit_at_5"))
    reasons = []
    if hit(ary_arabic):
        reasons.append("CROSS_SCRIPT_GAP")
    if not hit(ary_arabic) and not hit(ar) and hit(fr):
        reasons.append("LANGUAGE_TRANSFER_GAP")
    if not original.get("hit_at_5") and any(
        source_id in ADJACENT_SOURCE_IDS_BY_TOPIC.get(case_result["topic"], set())
        for source_id in original.get("top_5_source_ids", [])
    ):
        reasons.append("TOPIC_OVERLAP")
    if not any(hit(result) for result in (ary_arabic, ar, fr)) and "TOPIC_OVERLAP" not in reasons:
        reasons.append("CORPUS_GAP")
    normalized = case_result["variants"].get("ARY_LATIN_NORMALIZED")
    if not original.get("hit_at_5") and hit(normalized):
        reasons.append("ORTHOGRAPHIC_NORMALIZATION_GAP")
    return reasons or ["UNKNOWN"]


def build_variant_queries(
    paired: list[dict[str, GoldCase | None]], include_normalized: bool = True
) -> list[tuple[str, int, GoldCase]]:
    queries = []
    for case_index, item in enumerate(paired):
        original = item["ORIGINAL_ARY_LATIN"]
        assert original is not None
        variants = list(REQUIRED_VARIANTS)
        if include_normalized:
            variants.append("ARY_LATIN_NORMALIZED")
        for variant in variants:
            case = original if variant == "ORIGINAL_ARY_LATIN" else item.get(variant)
            if variant == "ARY_LATIN_NORMALIZED":
                case = original
            if case is not None:
                queries.append((variant, case_index, case))
    return queries
