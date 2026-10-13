"""SQLAlchemy models owned by the optional persistence foundation."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConversationThreadRecord(Base):
    """Minimal durable identity for a conversation thread."""

    __tablename__ = "conversation_threads"

    thread_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearningProfileRecord(Base):
    """Relational envelope for the existing pedagogical profile."""

    __tablename__ = "learning_profiles"

    thread_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"),
        primary_key=True,
    )
    learning_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    level_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quiz_history: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    completed_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    topics_mastered: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    topics_to_review: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    completed_modules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_learning_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    diagnostic_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConversationMessageRecord(Base):
    """User-visible product history for one conversation thread."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint(
            "thread_id", "turn_index", "role", name="uq_conversation_message_turn_role"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    script: Mapped[str | None] = mapped_column(String(16), nullable=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    knowledge_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
