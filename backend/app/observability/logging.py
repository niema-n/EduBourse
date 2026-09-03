import json
import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def normalize_request_id(raw_request_id: str | None) -> str:
    if raw_request_id is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(raw_request_id))
    except ValueError:
        return str(uuid.uuid4())


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = normalize_request_id(request.headers.get("x-request-id"))
        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        logging.getLogger("app.http").info(
            json.dumps(
                {
                    "request_id": request_id,
                    "route": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
                separators=(",", ":"),
            )
        )
        return response
