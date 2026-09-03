from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.observability.logging import RequestIdMiddleware, configure_logging
from app.schemas.chat import APIError


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Academic/PFA implementation of a multilingual multi-agent financial education "
            "assistant for the Ecole de la Bourse and Bourse de Casablanca context. "
            "It supports French, English, Arabic and Moroccan Darija for educational use, "
            "without personalized investment recommendations."
        ),
        contact={"name": "EduBourse PFA Project"},
        openapi_tags=[
            {
                "name": "Assistant",
                "description": (
                    "Text-to-text interaction with the multilingual EduBourse assistant."
                ),
            },
            {
                "name": "System",
                "description": "Application liveness and dependency health endpoints.",
            },
        ],
    )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        del exc
        request_id = request.headers.get("x-request-id")
        return JSONResponse(
            status_code=500,
            content=APIError(
                error="internal_error",
                message="An unexpected internal error occurred.",
                status=500,
                request_id=request_id,
            ).model_dump(),
        )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
