"""Deterministic post-hoc H1 hybrid replay primitives."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import GoldCase, cosine_similarity

HYBRID_POLICY_ID = "H1_LANGUAGE_ROUTED_V1"
RRF_K = 60


def _deduplicated(branches: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop later branches whose query text repeats an earlier one.

    Two identical queries would only score the same ranking twice under RRF, so
    the first occurrence is kept and the duplicate removed.
    """
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, query in branches:
        key = " ".join(query.split()).casefold() if isinstance(query, str) else repr(query)
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, query))
    return unique


def hybrid_branches(language: str, script: str, record: dict[str, Any]) -> list[tuple[str, str]]:
    """Select H1 branches from language/script only."""
    original = record["original_query"]
    french = record["retrieval_query_fr"]
    arabic = record["retrieval_query_ary_arabic"]
    if language == "fr":
        return [("original", original)]
    if language == "en":
        return [("french", french)]
    # Arabic-script questions keep the adapted French branch and also search with
    # the user's own wording: BGE-M3 is cross-lingual, so the original query still
    # matches the French corpus when the adapter picks a neighbouring concept.
    if language == "ar" or (language == "ary" and script == "arabic"):
        return _deduplicated([("original", original), ("french", french)])
    if language == "ary" and script == "latin":
        # Frozen three-branch behaviour, kept exactly as validated.
        return [("original", original), ("french", french), ("ary_arabic", arabic)]
    raise ValueError("unsupported language/script")


def rrf_scores(rankings: list[list[int]], rrf_k: int = RRF_K) -> dict[int, float]:
    scores = {index: 0.0 for ranking in rankings for index in ranking}
    for ranking in rankings:
        for rank, index in enumerate(ranking, start=1):
            scores[index] += 1.0 / (rrf_k + rank)
    return scores


def fuse_rankings(
    rankings: list[list[int]], chunks: list[ChunkRecord], rrf_k: int = RRF_K
) -> list[int]:
    scores = rrf_scores(rankings, rrf_k)
    return sorted(scores, key=lambda index: (-scores[index], chunks[index].chunk_id))


def rank_query(
    query: np.ndarray, passages: np.ndarray, chunks: list[ChunkRecord]
) -> list[int]:
    scores = cosine_similarity(query, passages)
    return sorted(
        range(len(scores)), key=lambda index: (-float(scores[index]), chunks[index].chunk_id)
    )


def expected_rank(ranking: list[int], case: GoldCase, chunks: list[ChunkRecord]) -> int | None:
    for rank, index in enumerate(ranking, start=1):
        if chunks[index].source_id in case.expected_source_ids:
            return rank
    return None


def hit_at(ranking: list[int], case: GoldCase, chunks: list[ChunkRecord], k: int) -> bool:
    return any(chunks[index].source_id in case.expected_source_ids for index in ranking[:k])


def quality_gate(macro: float, worst: float) -> bool:
    return bool(macro >= 0.90 and worst >= 0.80)
