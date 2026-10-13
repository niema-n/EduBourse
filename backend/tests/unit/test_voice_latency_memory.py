import asyncio
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from app.api import chat
from app.database.base import Base
from app.memory.conversation_memory_service import ConversationMemoryService
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.thread_store import ConversationThreadStore
from app.schemas.chat import ChatRequest


class Graph:
    def invoke(self, state, config):
        return {
            **state, "selected_route": "pedagogie", "business_answer": "Une action.",
            "response_key": "pedagogie", "security_status": "clear",
            "status": "completed", "error": None,
        }


@pytest.mark.parametrize("index_fails", [False, True])
def test_committed_history_available_before_and_after_deferred_index(
    tmp_path, monkeypatch, index_fails,
):
    database = PersistenceDatabase(
        enabled=True, database_url=f"sqlite:///{tmp_path / 'history.db'}",
    )
    Base.metadata.create_all(database.get_engine())
    store = SqlAlchemyConversationHistoryStore(database, ConversationThreadStore(database))
    calls = []

    def index(thread_id, ids):
        # Work uses committed rows, never detached SQLAlchemy sessions.
        assert len(store.list_messages_by_ids(thread_id, ids)) == 2
        calls.append(ids)
        if index_fails:
            raise RuntimeError("semantic index unavailable")

    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: store)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: SimpleNamespace(
        index_canonical_messages=index,
    ))
    tasks = BackgroundTasks()
    response = chat.process_text_message(
        ChatRequest(message="C'est quoi une action ?", thread_id="continuity"),
        Graph(), post_response_tasks=tasks,
    )
    assert response.status == "ok"
    assert calls == []
    recent = ConversationMemoryService(store).get_recent_context("continuity")
    assert recent.turn_count == 1
    assert recent.turns[0].assistant.content == response.answer
    # A next turn can read and commit immediately, before semantic enrichment.
    store.append_turn("continuity", "Et une obligation ?", "Un titre de dette.")
    asyncio.run(tasks())
    assert len(calls) == 1
    recent = ConversationMemoryService(store).get_recent_context("continuity")
    assert recent.turn_count == 2
    assert recent.turns[-1].user.content == "Et une obligation ?"
    database.dispose()


def test_failed_canonical_commit_is_not_deferred(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: SimpleNamespace(
        append_turn=fail,
    ))
    tasks = BackgroundTasks()
    with pytest.raises(RuntimeError, match="commit failed"):
        chat.process_text_message(
            ChatRequest(message="Une action ?", thread_id="failure"),
            Graph(), post_response_tasks=tasks,
        )
    assert tasks.tasks == []
