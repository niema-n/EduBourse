"""Bounded retrieval of previously persisted conversation turns."""

from __future__ import annotations

from typing import Protocol

from app.memory.models import ConversationTurn, MemoryMessage, RecentConversationContext

DEFAULT_RECENT_TURNS = 6
MAX_RECENT_TURNS = 20


class ConversationHistoryReader(Protocol):
    def list_recent_messages(self, thread_id: str, *, max_turns: int): ...


class ConversationMemoryService:
    """Read-only recent memory over the canonical conversation history store."""

    def __init__(self, history_store: ConversationHistoryReader | None) -> None:
        self.history_store = history_store

    @staticmethod
    def _bounded_turns(max_turns: int) -> int:
        if isinstance(max_turns, bool) or not isinstance(max_turns, int):
            raise TypeError("max_turns must be an integer")
        if max_turns <= 0:
            return 0
        return min(max_turns, MAX_RECENT_TURNS)

    def get_recent_context(
        self, thread_id: str, *, max_turns: int = DEFAULT_RECENT_TURNS
    ) -> RecentConversationContext:
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        bounded_turns = self._bounded_turns(max_turns)
        if bounded_turns == 0 or self.history_store is None:
            return RecentConversationContext(thread_id, (), 0, 0)

        records = self.history_store.list_recent_messages(thread_id, max_turns=bounded_turns)
        grouped: dict[int, dict[str, MemoryMessage]] = {}
        for record in records:
            role = record.role
            if role not in {"user", "assistant"}:
                continue
            grouped.setdefault(record.turn_index, {})[role] = MemoryMessage(
                turn_index=record.turn_index,
                role=role,
                content=record.content,
                language=record.language,
                script=record.script,
                route=record.route,
                knowledge_source=record.knowledge_source,
            )
        turns = tuple(
            ConversationTurn(
                turn_index=turn_index,
                user=messages.get("user"),
                assistant=messages.get("assistant"),
            )
            for turn_index, messages in sorted(grouped.items())
        )
        return RecentConversationContext(
            thread_id=thread_id,
            turns=turns,
            message_count=sum(
                int(message is not None)
                for turn in turns
                for message in (turn.user, turn.assistant)
            ),
            turn_count=len(turns),
        )
