"""Immutable data contracts for persisted recent conversation memory."""

from dataclasses import dataclass
from typing import Literal

MemoryRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class MemoryMessage:
    turn_index: int
    role: MemoryRole
    content: str
    language: str | None = None
    script: str | None = None
    route: str | None = None
    knowledge_source: str | None = None


@dataclass(frozen=True)
class ConversationTurn:
    turn_index: int
    user: MemoryMessage | None = None
    assistant: MemoryMessage | None = None


@dataclass(frozen=True)
class RecentConversationContext:
    thread_id: str
    turns: tuple[ConversationTurn, ...]
    message_count: int
    turn_count: int
