import hashlib
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.context import bind_context, current_context, new_id
from app.observability.metrics import observe_event


def normalize_request_id(raw_request_id: str | None) -> str:
    if raw_request_id:
        try:
            return str(uuid.UUID(raw_request_id))
        except ValueError:
            pass
    return new_id()


def thread_ref(thread_id: str | None) -> str | None:
    if not thread_id:
        return None
    return hashlib.sha256(thread_id.encode("utf-8")).hexdigest()[:16]


def emit(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    context = current_context()
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": logging.getLevelName(level),
        "event": event,
    }
    for key, value in {
        "request_id": context.request_id,
        "trace_id": context.trace_id,
        "modality": context.modality,
        **fields,
    }.items():
        if value is not None:
            payload[key] = value
    observe_event(event, payload)
    logging.getLogger("app.observability").log(
        level, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


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
        trace_id = new_id()
        with bind_context(request_id=request_id, trace_id=trace_id, modality="text"):
            try:
                response = await call_next(request)
            except Exception:
                raise
            response.headers["x-request-id"] = request_id
            response.headers["x-content-type-options"] = "nosniff"
            return response
