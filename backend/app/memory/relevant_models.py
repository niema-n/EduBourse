"""Immutable contracts for semantic retrieval of conversation memory."""

from dataclasses import dataclass
from typing import Literal

MemoryRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class RelevantMemoryHit:
    message_id: int
    turn_index: int
    role: MemoryRole
    content: str
    language: str | None
    script: str | None
    route: str | None
    knowledge_source: str | None
    similarity: float | None


@dataclass(frozen=True)
class RelevantMemoryContext:
    thread_id: str
    hits: tuple[RelevantMemoryHit, ...]
    hit_count: int
    indexed_message_count: int | None
    status: Literal["ok", "unavailable"] = "ok"
    failure_stage: str | None = None
