"""Concurrency-safe execution context for request observability."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ObservabilityContext:
    request_id: str | None = None
    trace_id: str | None = None
    modality: str | None = None


_context: ContextVar[ObservabilityContext | None] = ContextVar(
    "observability_context", default=None
)


def current_context() -> ObservabilityContext:
    return _context.get() or ObservabilityContext()


def new_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def bind_context(
    *, request_id: str | None = None, trace_id: str | None = None, modality: str | None = None
) -> Iterator[ObservabilityContext]:
    previous = _context.get()
    bound = ObservabilityContext(
        request_id=request_id if request_id is not None else previous.request_id,
        trace_id=trace_id if trace_id is not None else previous.trace_id,
        modality=modality if modality is not None else previous.modality,
    )
    token = _context.set(bound)
    try:
        yield bound
    finally:
        _context.reset(token)


@contextmanager
def ensure_turn_context(modality: str) -> Iterator[ObservabilityContext]:
    previous = current_context()
    with bind_context(
        request_id=previous.request_id or new_id(),
        trace_id=previous.trace_id or new_id(),
        modality=previous.modality or modality,
    ) as bound:
        yield bound
