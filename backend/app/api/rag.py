"""Read-only RAG inspection API for the frontend RAG & Sources page.

Only GET metadata and a retrieval preview. No ingestion, mutation, generation,
collection selection or path input: the backend owns every configuration value.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.graph.language_adapter import normalize_business_language
from app.multilingual.service import MultilingualService
from app.rag.preview_translation import get_preview_translator, translate_previews
from app.rag.retrieval_service import RetrievalRequest
from app.rag.runtime import get_retrieval_service, repository_root, retrieval_state
from app.schemas.rag import (
    RagOverviewResponse,
    RagSearchHit,
    RagSearchRequest,
    RagSearchResponse,
    RagSource,
    RagSourcesResponse,
)

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger(__name__)
multilingual = MultilingualService()

EXCERPT_CHARS = 700
UNAVAILABLE_DETAIL = "Le corpus ne peut pas être interrogé pour le moment."


@lru_cache(maxsize=1)
def _manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    base = repository_root() / "backend/data/rag/manifests"
    index = json.loads((base / "chroma_index_v1.json").read_text(encoding="utf-8"))
    corpus = json.loads((base / "corpus_v1.json").read_text(encoding="utf-8"))
    return index, corpus


def load_manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        return _manifests()
    except Exception as exc:
        logger.error("rag manifest load failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc


def _indexed_sources(index: dict[str, Any], corpus: dict[str, Any]) -> list[RagSource]:
    distribution: dict[str, int] = index.get("source_distribution", {})
    sources = [
        RagSource(
            source_id=document["source_id"],
            title=document["title"],
            authority=document["authority"],
            categories=list(document.get("category", [])),
            language=document["language"],
            source_type=document["source_type"],
            chunk_count=int(distribution.get(document["source_id"], 0)),
        )
        for document in corpus["documents"]
        if document.get("status") == "active"
    ]
    return sorted(sources, key=lambda item: (-item.chunk_count, item.title))


@router.get(
    "/overview",
    response_model=RagOverviewResponse,
    summary="Read the approved RAG index metadata",
    operation_id="rag_overview",
)
def rag_overview(
    manifests: Annotated[tuple[dict[str, Any], dict[str, Any]], Depends(load_manifests)],
) -> RagOverviewResponse:
    index, corpus = manifests
    documents = corpus["documents"]
    state = retrieval_state()
    live_count: int | None = None
    if state == "available":
        service = get_retrieval_service()
        try:
            live_count = int(service.collection.count()) if service is not None else None
        except Exception as exc:
            logger.error("rag collection count failed error_type=%s", type(exc).__name__)
            state = "unavailable"
    return RagOverviewResponse(
        collection_name=index["collection_name"],
        embedding_model=index["embedding_model"],
        embedding_dimension=int(index["embedding_dimension"]),
        distance_metric=index["distance_metric"],
        index_version=int(index["index_version"]),
        indexed_chunk_count=int(index["indexed_chunk_count"]),
        live_chunk_count=live_count,
        source_count=len({document["source_id"] for document in documents}),
        corpus_languages=sorted({document["language"] for document in documents}),
        authorities=sorted({document["authority"] for document in documents}),
        index_status=state,
    )


@router.get(
    "/sources",
    response_model=RagSourcesResponse,
    summary="List the approved corpus sources",
    operation_id="rag_sources",
)
def rag_sources(
    manifests: Annotated[tuple[dict[str, Any], dict[str, Any]], Depends(load_manifests)],
) -> RagSourcesResponse:
    index, corpus = manifests
    sources = _indexed_sources(index, corpus)
    return RagSourcesResponse(
        total_sources=len(sources),
        total_chunks=sum(source.chunk_count for source in sources),
        sources=sources,
    )


def require_retrieval_service() -> Any:
    service = get_retrieval_service()
    if service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL)
    return service


@router.post(
    "/search",
    response_model=RagSearchResponse,
    summary="Preview semantic retrieval over the approved corpus (no generation)",
    operation_id="rag_search",
    responses={503: {"description": "Retrieval temporarily unavailable"}},
)
def rag_search(
    payload: RagSearchRequest,
    service: Annotated[Any, Depends(require_retrieval_service)],
    manifests: Annotated[tuple[dict[str, Any], dict[str, Any]], Depends(load_manifests)],
    translator: Annotated[Any, Depends(get_preview_translator)],
) -> RagSearchResponse:
    query = payload.query.strip()
    analysis = multilingual.analyze(query)
    language, script = normalize_business_language(
        analysis.language, None if analysis.language.startswith("ary-") else analysis.script
    )
    try:
        result = service.retrieve(
            RetrievalRequest(
                original_query=query, language=language, script=script, top_k=payload.top_k
            )
        )
    except Exception as exc:
        logger.error("rag search failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc
    if result.retrieval_status != "ok":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL)

    _, corpus = manifests
    documents = {document["source_id"]: document for document in corpus["documents"]}
    hits = []
    for chunk in result.chunks:
        document = documents.get(chunk.source_id, {})
        text = " ".join(chunk.text.split())
        hits.append(
            RagSearchHit(
                rank=chunk.rank,
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                title=chunk.title,
                authority=document.get("authority"),
                categories=list(document.get("category", [])),
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                heading=chunk.heading,
                excerpt=text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rstrip() + "…",
                source_language=document.get("language"),
                score=round(float(chunk.retrieval_score), 6),
                score_type=chunk.score_type,
            )
        )
    # Display-only previews in the user's language. The excerpts above are final:
    # translations are attached beside them and never replace or feed evidence.
    previews = translate_previews(translator, [hit.excerpt for hit in hits], language, script)
    hits = [
        hit.model_copy(
            update={
                "translation_status": preview.status,
                "translated_excerpt": preview.text,
                "translated_language": language if preview.status == "translated" else None,
                "translated_script": script if preview.status == "translated" else None,
            }
        )
        for hit, preview in zip(hits, previews, strict=True)
    ]
    return RagSearchResponse(
        query=query,
        language=language,
        script=script,
        retrieval_query=result.adapted_query_fr,
        branches=list(result.branches_used),
        top_k=payload.top_k,
        results=hits,
    )
