"""Conversation history for the Assistant page.

Reuses the existing PostgreSQL persistence (conversation_threads and
conversation_messages written by the canonical chat pipeline). It creates no
store, no table and no memory of its own, and exposes only user-visible turns:
no prompts, no provider payloads, no logs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.chat import get_conversation_history_store
from app.persistence.models import ConversationMessageRecord, ConversationThreadRecord

router = APIRouter(prefix="/conversations", tags=["Conversations"])
logger = logging.getLogger(__name__)

# Only threads created by the Assistant page (frontend createThreadId) are listed.
ASSISTANT_THREAD_PREFIX = "assistant-"
THREAD_ID_PATTERN = r"^assistant-[A-Za-z0-9-]{8,80}$"
MAX_CONVERSATIONS = 100
DEFAULT_CONVERSATIONS = 50
MAX_MESSAGES = 200
TITLE_MAX_CHARS = 60
UNAVAILABLE_DETAIL = "conversation_history_unavailable"


class ConversationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    title: str
    updated_at: datetime
    message_count: int


class ConversationList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[ConversationSummary]


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_index: int
    role: Literal["user", "assistant"]
    content: str
    language: str | None
    script: str | None
    route: str | None
    knowledge_source: str | None
    created_at: datetime


class ConversationDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    title: str
    messages: list[ConversationMessage]
    truncated: bool


def conversation_title(first_user_message: str | None) -> str:
    """Deterministic title from the first user message: no provider call."""
    text = " ".join((first_user_message or "").split())
    if not text:
        return "Conversation"
    text = text[0].upper() + text[1:]
    if len(text) <= TITLE_MAX_CHARS:
        return text
    cut = text[:TITLE_MAX_CHARS]
    space = cut.rfind(" ")
    if space >= TITLE_MAX_CHARS // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-") + "…"


def _session_factory(store: Any) -> Any:
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL)
    try:
        return store.database.get_session_factory()
    except Exception as exc:
        logger.error("conversation history setup failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc


def _first_user_message_subquery():
    first = (
        select(ConversationMessageRecord.content)
        .where(
            ConversationMessageRecord.thread_id == ConversationThreadRecord.thread_id,
            ConversationMessageRecord.role == "user",
        )
        .order_by(ConversationMessageRecord.turn_index, ConversationMessageRecord.id)
        .limit(1)
        .correlate(ConversationThreadRecord)
        .scalar_subquery()
    )
    return first


@router.get(
    "",
    response_model=ConversationList,
    summary="List recent Assistant conversations",
    operation_id="list_conversations",
)
def list_conversations(
    store: Annotated[Any, Depends(get_conversation_history_store)],
    limit: Annotated[int, Query(ge=1, le=MAX_CONVERSATIONS)] = DEFAULT_CONVERSATIONS,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationList:
    factory = _session_factory(store)
    last_message_at = func.max(ConversationMessageRecord.created_at)
    # One bounded aggregate query: no per-thread follow-up reads.
    statement = (
        select(
            ConversationThreadRecord.thread_id,
            func.count(ConversationMessageRecord.id),
            last_message_at,
            _first_user_message_subquery(),
        )
        .join(
            ConversationMessageRecord,
            ConversationMessageRecord.thread_id == ConversationThreadRecord.thread_id,
        )
        .where(ConversationThreadRecord.thread_id.startswith(ASSISTANT_THREAD_PREFIX))
        .group_by(ConversationThreadRecord.thread_id)
        .order_by(last_message_at.desc(), ConversationThreadRecord.thread_id)
        .offset(offset)
        .limit(limit)
    )
    try:
        with factory() as session:
            rows = session.execute(statement).all()
    except SQLAlchemyError as exc:
        logger.error("conversation list failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc
    return ConversationList(
        conversations=[
            ConversationSummary(
                thread_id=thread_id,
                title=conversation_title(first_message),
                updated_at=updated_at,
                message_count=int(count),
            )
            for thread_id, count, updated_at, first_message in rows
        ]
    )


@router.delete(
    "/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the user-visible history of an Assistant conversation",
    operation_id="delete_conversation_history",
)
def delete_conversation_history(
    thread_id: Annotated[str, Path(pattern=THREAD_ID_PATTERN, max_length=200)],
    store: Annotated[Any, Depends(get_conversation_history_store)],
) -> Response:
    factory = _session_factory(store)
    try:
        with factory.begin() as session:
            # Keep internal learning/checkpoint state separate from visible history.
            # Repeated deletion is safe and never affects another conversation.
            session.execute(
                delete(ConversationMessageRecord).where(
                    ConversationMessageRecord.thread_id == thread_id
                )
            )
    except SQLAlchemyError as exc:
        logger.error("conversation deletion failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{thread_id}",
    response_model=ConversationDetail,
    summary="Read one Assistant conversation",
    operation_id="get_conversation",
    responses={404: {"description": "Unknown conversation"}},
)
def get_conversation(
    thread_id: Annotated[str, Path(pattern=THREAD_ID_PATTERN, max_length=200)],
    store: Annotated[Any, Depends(get_conversation_history_store)],
) -> ConversationDetail:
    factory = _session_factory(store)
    statement = (
        select(ConversationMessageRecord)
        .where(ConversationMessageRecord.thread_id == thread_id)
        .order_by(ConversationMessageRecord.turn_index, ConversationMessageRecord.id)
        .limit(MAX_MESSAGES + 1)
    )
    try:
        with factory() as session:
            records = list(session.scalars(statement))
    except SQLAlchemyError as exc:
        logger.error("conversation read failed error_type=%s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from exc
    if not records:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation_not_found")
    truncated = len(records) > MAX_MESSAGES
    records = records[:MAX_MESSAGES]
    first_user = next((record.content for record in records if record.role == "user"), None)
    return ConversationDetail(
        thread_id=thread_id,
        title=conversation_title(first_user),
        truncated=truncated,
        messages=[
            ConversationMessage(
                turn_index=record.turn_index,
                role=record.role,
                content=record.content,
                language=record.language,
                script=record.script,
                route=record.route,
                knowledge_source=record.knowledge_source,
                created_at=record.created_at,
            )
            for record in records
            if record.role in {"user", "assistant"}
        ],
    )
