from fastapi import APIRouter

from app.api.chat import legacy_router as legacy_chat_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.health import legacy_router as legacy_health_router
from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.rag import router as rag_router
from app.api.rag_admin import router as rag_admin_router
from app.api.voice import router as voice_router
from app.config import get_settings

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(chat_router, prefix="/api/v1")
api_router.include_router(voice_router, prefix="/api/v1")
api_router.include_router(rag_admin_router, prefix="/api/v1")
api_router.include_router(rag_router, prefix="/api/v1")
api_router.include_router(integrations_router, prefix="/api/v1")
api_router.include_router(conversations_router, prefix="/api/v1")
api_router.include_router(legacy_health_router)
api_router.include_router(legacy_chat_router)


@api_router.get("/", tags=["System"], summary="Get API metadata", operation_id="api_root")
def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "docs": "/docs",
        "redoc": "/redoc",
    }
