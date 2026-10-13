"""SQLAlchemy-backed conversation thread store."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.persistence.database import PersistenceDatabase
from app.persistence.models import ConversationThreadRecord


class ConversationThreadStore:
    """Persistence boundary for the existing single thread identifier."""

    def __init__(self, database: PersistenceDatabase) -> None:
        self.database = database

    @staticmethod
    def _validate_thread_id(thread_id: str) -> None:
        if not thread_id.strip():
            raise ValueError("thread_id must not be blank")

    def get(self, thread_id: str) -> ConversationThreadRecord | None:
        self._validate_thread_id(thread_id)
        with self.database.get_session_factory()() as session:
            return session.scalar(
                select(ConversationThreadRecord).where(
                    ConversationThreadRecord.thread_id == thread_id
                )
            )

    def get_or_create(self, thread_id: str) -> ConversationThreadRecord:
        self._validate_thread_id(thread_id)
        session = self.database.get_session_factory()()
        try:
            record = session.scalar(
                select(ConversationThreadRecord).where(
                    ConversationThreadRecord.thread_id == thread_id
                )
            )
            if record is None:
                now = datetime.now(UTC)
                record = ConversationThreadRecord(
                    thread_id=thread_id, created_at=now, updated_at=now
                )
                session.add(record)
                try:
                    session.commit()
                except IntegrityError as exc:
                    session.rollback()
                    if not self._is_thread_id_conflict(exc):
                        raise
                    record = session.scalar(
                        select(ConversationThreadRecord).where(
                            ConversationThreadRecord.thread_id == thread_id
                        )
                    )
                    if record is None:
                        raise
            return record
        finally:
            session.close()

    @staticmethod
    def _is_thread_id_conflict(error: IntegrityError) -> bool:
        original = error.orig
        sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
        message = str(original).lower()
        if sqlstate == "23505":
            constraint_name = getattr(getattr(original, "diag", None), "constraint_name", None)
            return constraint_name in {None, "conversation_threads_pkey"} and "thread_id" in message
        return "thread_id" in message and "unique" in message

    def touch(self, thread_id: str) -> ConversationThreadRecord | None:
        self._validate_thread_id(thread_id)
        with self.database.get_session_factory().begin() as session:
            record = session.scalar(
                select(ConversationThreadRecord).where(
                    ConversationThreadRecord.thread_id == thread_id
                )
            )
            if record is None:
                return None
            now = datetime.now(UTC)
            current_updated_at = record.updated_at
            if current_updated_at.tzinfo is None:
                current_updated_at = current_updated_at.replace(tzinfo=UTC)
            if current_updated_at >= now:
                now = current_updated_at + timedelta(microseconds=1)
            record.updated_at = now
            session.add(record)
            return record
