from fastapi import APIRouter

from app.config import get_settings
from app.database.postgres import check_postgres
from app.providers.chroma import check_chroma
from app.schemas.health import ComponentHealth, HealthResponse, LiveResponse, VectorStoreHealth

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveResponse)
def live() -> LiveResponse:
    settings = get_settings()
    return LiveResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    postgres_status = check_postgres()
    chroma_status = check_chroma()
    unavailable_count = sum(
        status == "unavailable" for status in (postgres_status.status, chroma_status.status)
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
        chroma=VectorStoreHealth(
            status=chroma_status.status,
            collection=settings.chroma_collection,
            collection_status=chroma_status.collection_status,
            document_count=chroma_status.document_count,
        ),
    )
