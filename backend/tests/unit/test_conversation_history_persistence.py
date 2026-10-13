from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, func, select

from app.api import chat
from app.database.base import Base
from app.memory.conversation_memory_service import ConversationMemoryService
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.models import ConversationMessageRecord
from app.persistence.thread_store import ConversationThreadStore
from app.schemas.chat import ChatRequest


def make_store(database_url: str) -> tuple[PersistenceDatabase, SqlAlchemyConversationHistoryStore]:
    database = PersistenceDatabase(
        enabled=True,
        database_url=database_url,
        engine_factory=lambda url, **kwargs: create_engine(url, **kwargs),
    )
    Base.metadata.create_all(database.get_engine())
    thread_store = ConversationThreadStore(database)
    return database, SqlAlchemyConversationHistoryStore(database, thread_store)


def insert_messages(database, store, thread_id, messages) -> None:
    store.thread_store.get_or_create(thread_id)
    now = datetime.now(UTC)
    with database.get_session_factory()() as session:
        session.add_all(
            [
                ConversationMessageRecord(
                    thread_id=thread_id,
                    turn_index=turn_index,
                    role=role,
                    content=content,
                    language="fr",
                    script="latin",
                    route="pedagogie",
                    created_at=now,
                )
                for turn_index, role, content in messages
            ]
        )
        session.commit()


def test_history_append_and_order_survive_store_recreation(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'history.db'}"
    database_a, store_a = make_store(database_url)
    store_a.append_turn(
        "history-thread",
        "question one",
        "answer one",
        language="fr",
        script="latin",
        route="pedagogie",
    )
    store_a.append_turn(
        "history-thread",
        "question two",
        "answer two",
        language="en",
        script="latin",
        route="pedagogie",
    )
    database_a.dispose()

    database_b, store_b = make_store(database_url)
    messages = store_b.list_messages("history-thread")

    assert [(item.turn_index, item.role, item.content) for item in messages] == [
        (1, "user", "question one"),
        (1, "assistant", "answer one"),
        (2, "user", "question two"),
        (2, "assistant", "answer two"),
    ]
    assert messages[0].language == "fr"
    assert messages[1].route == "pedagogie"
    database_b.dispose()


def test_history_isolated_by_thread_and_limit_is_oldest_first(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'isolation.db'}")
    store.append_turn("thread-a", "a-user", "a-assistant")
    store.append_turn("thread-b", "b-user", "b-assistant")

    assert [item.content for item in store.list_messages("thread-b")] == [
        "b-user",
        "b-assistant",
    ]
    assert [item.content for item in store.list_messages("thread-a", limit=1)] == ["a-user"]
    database.dispose()


def test_recent_window_selects_distinct_latest_turns_and_keeps_all_messages(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'recent-boundary.db'}")
    insert_messages(
        database,
        store,
        "recent",
        [
            (1, "user", "u-1"),
            (1, "assistant", "a-1"),
            (2, "user", "u-2"),
            (2, "assistant", "a-2"),
            (3, "user", "u-3"),
            (3, "assistant", "a-3"),
            (4, "user", "u-4"),
            (5, "user", "u-5"),
            (6, "user", "u-6"),
        ],
    )

    messages = store.list_recent_messages("recent", max_turns=3)

    assert [(item.turn_index, item.role, item.content) for item in messages] == [
        (4, "user", "u-4"),
        (5, "user", "u-5"),
        (6, "user", "u-6"),
    ]
    database.dispose()


def test_recent_window_does_not_truncate_complete_boundary_turn(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'complete-boundary.db'}")
    insert_messages(
        database,
        store,
        "recent",
        [
            (1, "user", "u-1"),
            (1, "assistant", "a-1"),
            (2, "user", "u-2"),
            (2, "assistant", "a-2"),
            (3, "user", "u-3"),
            (4, "user", "u-4"),
            (4, "assistant", "a-4"),
            (5, "assistant", "a-5"),
        ],
    )

    messages = store.list_recent_messages("recent", max_turns=3)

    assert [(item.turn_index, item.role) for item in messages] == [
        (3, "user"),
        (4, "user"),
        (4, "assistant"),
        (5, "assistant"),
    ]
    database.dispose()


def test_recent_window_preserves_assistant_only_turn(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'assistant-only.db'}")
    insert_messages(database, store, "recent", [(7, "assistant", "a-7")])

    context = ConversationMemoryService(store).get_recent_context("recent", max_turns=1)

    assert context.turn_count == 1
    assert context.turns[0].user is None
    assert context.turns[0].assistant.content == "a-7"
    database.dispose()


def test_recent_window_max_turns_is_latest_distinct_turn_count(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'max-contract.db'}")
    messages = []
    for index in range(1, 11):
        messages.append((index, "user", f"u-{index}"))
        if index % 3 != 0:
            messages.append((index, "assistant", f"a-{index}"))
    insert_messages(database, store, "recent", messages)
    service = ConversationMemoryService(store)

    for max_turns in (1, 3, 6):
        context = service.get_recent_context("recent", max_turns=max_turns)
        assert context.turn_count == max_turns
        assert [turn.turn_index for turn in context.turns] == list(range(11 - max_turns, 11))

    database.dispose()


def test_recent_window_is_one_select_and_thread_scoped(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'bounded.db'}")
    insert_messages(
        database,
        store,
        "thread-a",
        [
            (index, role, f"a-{index}-{role}")
            for index in range(1, 101)
            for role in ("user", "assistant")
        ],
    )
    insert_messages(
        database,
        store,
        "thread-b",
        [(index, "user", f"b-{index}") for index in range(1, 11)],
    )
    statements = []

    def record_selects(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    engine = database.get_engine()
    event.listen(engine, "before_cursor_execute", record_selects)
    try:
        context = ConversationMemoryService(store).get_recent_context("thread-a", max_turns=6)
    finally:
        event.remove(engine, "before_cursor_execute", record_selects)

    assert len(statements) == 1
    assert "LIMIT" in statements[0].upper()
    assert [turn.turn_index for turn in context.turns] == list(range(95, 101))
    assert all(
        turn.user.content.startswith("a-") and turn.assistant.content.startswith("a-")
        for turn in context.turns
    )
    database.dispose()


def test_two_store_writers_preserve_database_order(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'writers.db'}"
    database_a, store_a = make_store(database_url)
    database_b, store_b = make_store(database_url)

    store_a.append_turn("shared", "first", "first answer")
    store_b.append_turn("shared", "second", "second answer")

    messages = store_a.list_messages("shared")
    assert [(item.turn_index, item.role) for item in messages] == [
        (1, "user"),
        (1, "assistant"),
        (2, "user"),
        (2, "assistant"),
    ]
    database_a.dispose()
    database_b.dispose()


def test_turn_pair_is_atomic_when_assistant_insert_fails(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'atomic.db'}")

    def fail_assistant(mapper, connection, target) -> None:
        if target.role == "assistant":
            raise RuntimeError("simulated assistant write failure")

    event.listen(ConversationMessageRecord, "before_insert", fail_assistant)
    try:
        with pytest.raises(RuntimeError, match="simulated assistant"):
            store.append_turn("atomic", "user", "assistant")
    finally:
        event.remove(ConversationMessageRecord, "before_insert", fail_assistant)

    with database.get_session_factory()() as session:
        count = session.scalar(select(func.count()).select_from(ConversationMessageRecord))
    assert count == 0
    database.dispose()


def test_history_failure_is_controlled_without_memory_fallback(tmp_path) -> None:
    database, store = make_store(f"sqlite:///{tmp_path / 'failure.db'}")
    original_factory = database.get_session_factory

    def broken_factory():
        raise RuntimeError("database unavailable")

    database.get_session_factory = broken_factory
    with pytest.raises(RuntimeError, match="database unavailable"):
        store.list_messages("thread")
    database.get_session_factory = original_factory
    database.dispose()


def test_history_store_selection_is_disabled_by_default_and_lazy_when_enabled(monkeypatch) -> None:
    chat.get_conversation_history_store.cache_clear()
    monkeypatch.setattr(chat, "get_settings", lambda: SimpleNamespace(persistence_enabled=False))
    assert chat.get_conversation_history_store() is None

    chat.get_conversation_history_store.cache_clear()
    monkeypatch.setattr(
        chat,
        "get_settings",
        lambda: SimpleNamespace(
            persistence_enabled=True,
            database_url="sqlite:///:memory:",
        ),
    )
    store = chat.get_conversation_history_store()
    assert isinstance(store, SqlAlchemyConversationHistoryStore)
    assert store.database._engine is None
    chat.get_conversation_history_store.cache_clear()


def test_process_text_message_persists_one_user_assistant_pair(monkeypatch) -> None:
    class FakeGraph:
        def invoke(self, state, config):
            return {
                **state,
                "selected_route": "pedagogie",
                "business_answer": "Une réponse éducative.",
                "response_key": "pedagogie",
                "security_status": "clear",
                "status": "completed",
                "error": None,
            }

    class RecordingStore:
        def __init__(self) -> None:
            self.calls = []

        def append_turn(self, *args, **kwargs) -> None:
            self.calls.append((args, kwargs))

    recording = RecordingStore()
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: recording)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: None)
    response = chat.process_text_message(
        ChatRequest(message="C'est quoi une action ?", thread_id="voice-shared"), FakeGraph()
    )

    assert response.status == "ok"
    assert len(recording.calls) == 1
    args, kwargs = recording.calls[0]
    assert args == ("voice-shared", "C'est quoi une action ?", response.answer)
    assert kwargs["route"] == "pedagogie"


def test_finalization_failure_persists_valid_business_turn(monkeypatch) -> None:
    class FakeGraph:
        def invoke(self, state, config):
            return {
                **state,
                "selected_route": "pedagogie",
                "business_answer": "Canonical business answer ALPHA_MEMORY_7319",
                "response_key": "pedagogie",
                "grounded": True,
                "grounded_status": "ok",
                "grounded_citations": [],
                "status": "completed",
                "error": None,
            }

    class RecordingStore:
        def __init__(self) -> None:
            self.calls = []

        def append_turn(self, *args, **kwargs) -> None:
            self.calls.append((args, kwargs))
            return []

    recording = RecordingStore()
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: recording)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: None)
    monkeypatch.setattr(
        chat,
        "multilingual",
        SimpleNamespace(
            analyze=lambda message: SimpleNamespace(
                language="ary",
                script="latin",
                normalized_text=message,
            )
        ),
    )
    monkeypatch.setattr(
        chat,
        "localize_business_answer",
        lambda *args, **kwargs: SimpleNamespace(
            status="failed",
            answer=None,
            provider="test",
            retry_count=0,
            guard_result="not_run",
        ),
    )

    response = chat.process_text_message(
        ChatRequest(message="Mon marqueur est ALPHA_MEMORY_7319", thread_id="memory-failure"),
        FakeGraph(),
    )

    assert response.status == "error"
    assert len(recording.calls) == 1
    args, _ = recording.calls[0]
    assert args[1] == "Mon marqueur est ALPHA_MEMORY_7319"
    assert args[2] == "Canonical business answer ALPHA_MEMORY_7319"


def test_upstream_failure_does_not_persist_error(monkeypatch) -> None:
    class BrokenGraph:
        def invoke(self, state, config):
            raise RuntimeError("upstream failure")

    class RecordingStore:
        def __init__(self) -> None:
            self.calls = []

        def append_turn(self, *args, **kwargs) -> None:
            self.calls.append((args, kwargs))

    recording = RecordingStore()
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: recording)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: None)

    response = chat.process_text_message(
        ChatRequest(message="An upstream failure", thread_id="memory-hard-failure"),
        BrokenGraph(),
    )

    assert response.status == "error"
    assert recording.calls == []


def _run_with_history_result(monkeypatch, result):
    class FakeGraph:
        def invoke(self, state, config):
            return {**state, **result}

    class RecordingStore:
        def __init__(self) -> None:
            self.calls = []

        def append_turn(self, *args, **kwargs) -> None:
            self.calls.append((args, kwargs))

    store = RecordingStore()
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: store)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: None)
    response = chat.process_text_message(
        ChatRequest(message="question", thread_id="provenance-thread"), FakeGraph()
    )
    return response, store.calls[0][1]["knowledge_source"]


def test_history_keeps_current_grounded_rag_provenance(monkeypatch) -> None:
    response, source = _run_with_history_result(
        monkeypatch,
        {
            "selected_route": "pedagogie",
            "business_answer": "Grounded answer",
            "response_key": "pedagogie",
            "grounded": True,
            "grounded_status": "ok",
            "knowledge_source": "rag",
            "status": "completed",
        },
    )
    assert response.route == "pedagogie"
    assert source == "rag"


def test_history_drops_stale_rag_provenance_for_quiz(monkeypatch) -> None:
    response, source = _run_with_history_result(
        monkeypatch,
        {
            "selected_route": "quiz",
            "business_answer": "Quiz answer",
            "response_key": "quiz",
            "grounded": True,
            "knowledge_source": "rag",
            "status": "completed",
        },
    )
    assert response.route == "quiz"
    assert source is None


def test_history_keeps_fresh_quiz_provenance_empty(monkeypatch) -> None:
    response, source = _run_with_history_result(
        monkeypatch,
        {
            "selected_route": "quiz",
            "business_answer": "Quiz answer",
            "response_key": "quiz",
            "status": "completed",
        },
    )
    assert response.route == "quiz"
    assert source is None


def test_history_preserves_financial_expert_provenance(monkeypatch) -> None:
    for source in (
        "llm_general_financial_knowledge",
        "llm_web_grounded_financial_knowledge",
    ):
        _, persisted_source = _run_with_history_result(
            monkeypatch,
            {
                "selected_route": "pedagogie",
                "business_answer": "Expert answer",
                "response_key": "pedagogie",
                "grounded": False,
                "knowledge_source": source,
                "status": "completed",
            },
        )
        assert persisted_source == source
