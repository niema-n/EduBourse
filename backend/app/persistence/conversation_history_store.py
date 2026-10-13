"""Storage-only persistence for user-visible conversation turns."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.persistence.database import PersistenceDatabase, PersistenceUnavailableError
from app.persistence.models import ConversationMessageRecord, ConversationThreadRecord
from app.persistence.thread_store import ConversationThreadStore


class SqlAlchemyConversationHistoryStore:
    """Append and read atomic user/assistant turn pairs."""

    def __init__(
        self, database: PersistenceDatabase, thread_store: ConversationThreadStore
    ) -> None:
        self.database = database
        self.thread_store = thread_store

    def append_turn(
        self,
        thread_id: str,
        user_message: str,
        assistant_message: str,
        *,
        language: str | None = None,
        script: str | None = None,
        route: str | None = None,
        knowledge_source: str | None = None,
    ) -> list[ConversationMessageRecord]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        if not user_message or not assistant_message:
            raise ValueError("conversation messages must not be blank")
        try:
            self.thread_store.get_or_create(thread_id)
            session = self.database.get_session_factory()()
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history setup failed") from exc
        try:
            parent = session.scalar(
                select(ConversationThreadRecord)
                .where(ConversationThreadRecord.thread_id == thread_id)
                .with_for_update()
            )
            if parent is None:
                raise PersistenceUnavailableError("conversation thread is unavailable")
            last_turn = session.scalar(
                select(func.max(ConversationMessageRecord.turn_index)).where(
                    ConversationMessageRecord.thread_id == thread_id
                )
            )
            turn_index = (last_turn or 0) + 1
            now = datetime.now(UTC)
            records = [
                ConversationMessageRecord(
                    thread_id=thread_id,
                    turn_index=turn_index,
                    role="user",
                    content=user_message,
                    language=language,
                    script=script,
                    route=route,
                    created_at=now,
                ),
                ConversationMessageRecord(
                    thread_id=thread_id,
                    turn_index=turn_index,
                    role="assistant",
                    content=assistant_message,
                    language=language,
                    script=script,
                    route=route,
                    knowledge_source=knowledge_source,
                    created_at=now,
                ),
            ]
            session.add_all(records)
            session.commit()
            return records
        except SQLAlchemyError as exc:
            session.rollback()
            raise PersistenceUnavailableError("conversation history write failed") from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_messages(
        self, thread_id: str, *, limit: int | None = None
    ) -> list[ConversationMessageRecord]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")
        try:
            session = self.database.get_session_factory()()
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        try:
            statement = (
                select(ConversationMessageRecord)
                .where(ConversationMessageRecord.thread_id == thread_id)
                .order_by(ConversationMessageRecord.turn_index, ConversationMessageRecord.id)
            )
            if limit is not None:
                statement = statement.limit(limit)
            return list(session.scalars(statement))
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        finally:
            session.close()

    def list_messages_by_ids(
        self, thread_id: str, message_ids: Sequence[int]
    ) -> list[ConversationMessageRecord]:
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        if not message_ids:
            return []
        try:
            session = self.database.get_session_factory()()
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        try:
            statement = select(ConversationMessageRecord).where(
                ConversationMessageRecord.thread_id == thread_id,
                ConversationMessageRecord.id.in_(list(message_ids)),
            )
            return list(session.scalars(statement))
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        finally:
            session.close()

    def list_recent_messages(
        self, thread_id: str, *, max_turns: int
    ) -> list[ConversationMessageRecord]:
        """Fetch all messages belonging to the latest distinct turns."""
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")
        if max_turns <= 0:
            raise ValueError("max_turns must be greater than zero")
        try:
            session = self.database.get_session_factory()()
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        try:
            recent_turn_indexes = (
                select(ConversationMessageRecord.turn_index)
                .where(ConversationMessageRecord.thread_id == thread_id)
                .distinct()
                .order_by(ConversationMessageRecord.turn_index.desc())
                .limit(max_turns)
                .subquery()
            )
            statement = (
                select(ConversationMessageRecord)
                .where(
                    ConversationMessageRecord.thread_id == thread_id,
                    ConversationMessageRecord.turn_index.in_(
                        select(recent_turn_indexes.c.turn_index)
                    ),
                )
                .order_by(
                    ConversationMessageRecord.turn_index,
                    ConversationMessageRecord.id,
                )
            )
            records = list(session.scalars(statement))
            return records
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("conversation history read failed") from exc
        finally:
            session.close()
