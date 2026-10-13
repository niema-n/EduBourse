from types import SimpleNamespace

import pytest

from app.database.base import Base
from app.memory.conversation_memory_service import (
    DEFAULT_RECENT_TURNS,
    MAX_RECENT_TURNS,
    ConversationMemoryService,
)
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.thread_store import ConversationThreadStore


def make_store(url):
    from sqlalchemy import create_engine

    database = PersistenceDatabase(
        enabled=True,
        database_url=url,
        engine_factory=lambda value, **kwargs: create_engine(value, **kwargs),
    )
    Base.metadata.create_all(database.get_engine())
    return database, SqlAlchemyConversationHistoryStore(database, ConversationThreadStore(database))


def test_empty_unknown_thread_returns_empty_context(tmp_path):
    database, store = make_store(f"sqlite:///{tmp_path / 'empty.db'}")
    context = ConversationMemoryService(store).get_recent_context("unknown")
    assert context.turns == ()
    assert context.turn_count == context.message_count == 0
    database.dispose()


def test_recent_context_preserves_order_content_and_metadata(tmp_path):
    database, store = make_store(f"sqlite:///{tmp_path / 'basic.db'}")
    store.append_turn(
        "thread", "Bonjour", "Bonjour", language="fr", script="latin", route="pedagogie"
    )
    store.append_turn(
        "thread",
        "Je veux apprendre les obligations.",
        "Très bien.",
        language="fr",
        script="latin",
        route="pedagogie",
        knowledge_source="rag",
    )
    context = ConversationMemoryService(store).get_recent_context("thread")
    assert [
        (turn.turn_index, turn.user.content, turn.assistant.content) for turn in context.turns
    ] == [(1, "Bonjour", "Bonjour"), (2, "Je veux apprendre les obligations.", "Très bien.")]
    assert context.turns[1].assistant.knowledge_source == "rag"
    database.dispose()


def test_max_turns_returns_latest_groups_ascending(tmp_path):
    database, store = make_store(f"sqlite:///{tmp_path / 'max.db'}")
    for index in range(1, 11):
        store.append_turn("thread", f"user-{index}", f"assistant-{index}")
    context = ConversationMemoryService(store).get_recent_context("thread", max_turns=3)
    assert [turn.turn_index for turn in context.turns] == [8, 9, 10]
    database.dispose()


def test_thread_isolation_and_same_text_boundary(tmp_path):
    database, store = make_store(f"sqlite:///{tmp_path / 'isolation.db'}")
    store.append_turn("a", "same phrase A_SECRET", "answer A")
    store.append_turn("b", "same phrase B_SECRET", "answer B")
    service = ConversationMemoryService(store)
    a = service.get_recent_context("a")
    b = service.get_recent_context("b")
    assert "A_SECRET" in a.turns[0].user.content and "B_SECRET" not in a.turns[0].user.content
    assert "B_SECRET" in b.turns[0].user.content and "A_SECRET" not in b.turns[0].user.content
    database.dispose()


def test_multilingual_content_and_metadata_are_returned_unchanged():
    records = [
        SimpleNamespace(
            turn_index=index,
            role=role,
            content=content,
            language=language,
            script=script,
            route="pedagogie",
            knowledge_source=None,
        )
        for index, (language, script, content) in enumerate(
            [
                ("fr", "latin", "préférence"),
                ("en", "latin", "stock"),
                ("ar", "arabic", "سهم"),
                ("ary", "latin", "chno howa MASI?"),
                ("ary", "arabic", "شنو هو السهم؟"),
            ],
            1,
        )
        for role in ("user", "assistant")
    ]
    context = ConversationMemoryService(_FakeStore(records)).get_recent_context(
        "thread", max_turns=5
    )
    assert context.turns[0].user.content == "préférence"
    assert [(turn.user.language, turn.user.script) for turn in context.turns] == [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ]


def test_partial_turn_does_not_fabricate_missing_side():
    record = SimpleNamespace(
        turn_index=4,
        role="user",
        content="only user",
        language="fr",
        script="latin",
        route="pedagogie",
        knowledge_source=None,
    )
    turn = ConversationMemoryService(_FakeStore([record])).get_recent_context("thread").turns[0]
    assert turn.user.content == "only user"
    assert turn.assistant is None


def test_bounds_and_disabled_contract():
    service = ConversationMemoryService(None)
    assert service.get_recent_context("thread", max_turns=DEFAULT_RECENT_TURNS).turns == ()
    assert service.get_recent_context("thread", max_turns=0).turns == ()
    assert service.get_recent_context("thread", max_turns=-1).turns == ()
    with pytest.raises(ValueError):
        service.get_recent_context("", max_turns=1)
    assert service._bounded_turns(MAX_RECENT_TURNS + 1000) == MAX_RECENT_TURNS


def test_bounded_reader_receives_clamped_window():
    store = _FakeStore([])
    service = ConversationMemoryService(store)
    service.get_recent_context("thread", max_turns=MAX_RECENT_TURNS + 1000)
    assert store.requested == MAX_RECENT_TURNS


def test_memory_read_does_not_redetect_or_log_content(caplog):
    sentinel = "SUPER_PRIVATE_MEMORY_TEXT_817263"
    context = ConversationMemoryService(
        _FakeStore(
            [
                SimpleNamespace(
                    turn_index=1,
                    role="user",
                    content=sentinel,
                    language="fr",
                    script="latin",
                    route=None,
                    knowledge_source=None,
                )
            ]
        )
    ).get_recent_context("thread")
    assert context.turns[0].user.content == sentinel
    assert sentinel not in caplog.text


def test_restart_with_fresh_store_instance(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    database, store = make_store(url)
    store.append_turn("restart", "before", "persisted")
    database.dispose()
    database, fresh_store = make_store(url)
    context = ConversationMemoryService(fresh_store).get_recent_context("restart")
    assert context.turns[0].assistant.content == "persisted"
    database.dispose()


class _FakeStore:
    def __init__(self, records):
        self.records = records
        self.requested = None

    def list_recent_messages(self, thread_id, *, max_turns):
        assert thread_id == "thread"
        self.requested = max_turns
        return self.records
