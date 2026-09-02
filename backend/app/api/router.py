from fastapi import APIRouter

from app.api.health import router as health_router
from app.config import get_settings

api_router = APIRouter()
api_router.include_router(health_router)


@api_router.get("/")
def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }
