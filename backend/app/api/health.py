from fastapi import APIRouter

from app.config import get_settings
from app.database.postgres import check_postgres
from app.providers.chroma import check_chroma
from app.rag.runtime import check_retrieval_index
from app.schemas.health import (
    ChromaServerHealth,
    ComponentHealth,
    HealthResponse,
    LiveResponse,
    RagIndexHealth,
)

router = APIRouter(tags=["System"])


@router.get(
    "/health/live",
    response_model=LiveResponse,
    summary="Check application liveness",
    operation_id="live_health",
)
def live() -> LiveResponse:
    settings = get_settings()
    return LiveResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check application dependencies",
    operation_id="health_check",
)
def health() -> HealthResponse:
    settings = get_settings()
    postgres_status = check_postgres()
    rag_index_status = check_retrieval_index()
    chroma_status = check_chroma()
    unavailable_count = sum(
        status == "unavailable" for status in (postgres_status.status, rag_index_status.status)
    )
    if unavailable_count == 0:
        overall = "ok"
    elif unavailable_count == 2:
        overall = "unavailable"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        postgres=ComponentHealth(status=postgres_status.status),
        rag_index=RagIndexHealth(
            status=rag_index_status.status,
            collection=rag_index_status.collection,
            document_count=rag_index_status.document_count,
        ),
        chroma_server=ChromaServerHealth(
            status=chroma_status.status,
            collection=settings.chroma_collection,
            collection_status=chroma_status.collection_status,
            document_count=chroma_status.document_count,
        ),
    )


legacy_router = APIRouter(tags=["System"])
legacy_router.add_api_route(
    "/health/live",
    live,
    methods=["GET"],
    response_model=LiveResponse,
    summary="Check application liveness (legacy)",
    operation_id="live_health_legacy",
    deprecated=True,
)
legacy_router.add_api_route(
    "/health",
    health,
    methods=["GET"],
    response_model=HealthResponse,
    summary="Check application dependencies (legacy)",
    operation_id="health_check_legacy",
    deprecated=True,
)
