import pickle
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.api.chat import get_chat_graph, process_text_message
from app.api.voice import get_chat_graph as voice_get_chat_graph
from app.api.voice import process_text_message as voice_process_text_message
from app.config import Settings
from app.formation.models import FormationSession
from app.graph.state import GraphState
from app.graph.workflow_context import ConversationWorkflowContext
from app.learning import LearningProfileService
from app.persistence.checkpointer import (
    PersistentPostgresCheckpointer,
    create_graph_checkpointer,
)
from app.persistence.database import PersistenceDatabase
from app.persistence.learning_profile_store import SqlAlchemyLearningProfileStore
from app.persistence.models import Base
from app.persistence.thread_store import ConversationThreadStore
from app.quiz.models import QuizQuestion, QuizSession


class FileBackedTestSaver(MemorySaver):
    """Test-only file persistence using LangGraph's real saver contract."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        if path.exists():
            with path.open("rb") as stream:
                saved = pickle.load(stream)
                self.storage = defaultdict(
                    lambda: defaultdict(dict), saved["storage"]
                )
                self.writes = defaultdict(dict, saved["writes"])
                self.blobs = defaultdict(dict, saved["blobs"])

    def _persist(self) -> None:
        with self.path.open("wb") as stream:
            pickle.dump(
                {
                    "storage": dict(self.storage),
                    "writes": dict(self.writes),
                    "blobs": dict(self.blobs),
                },
                stream,
            )

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        self._persist()
        return result

    def put_writes(self, config, writes, task_id, task_path=""):
        result = super().put_writes(config, writes, task_id, task_path)
        self._persist()
        return result


def workflow_graph(checkpointer):
    builder = StateGraph(GraphState)

    def establish_context(state):
        question = QuizQuestion(
            question_id="q1",
            topic="stocks",
            level="beginner",
            prompt="What is a stock?",
            options={"A": "Ownership", "B": "A loan", "C": "Cash", "D": "A fee"},
            correct_option="A",
            explanation="A stock represents ownership.",
        )
        return {
            "workflow_context": ConversationWorkflowContext(
                active_agent="quiz",
                active_workflow="diagnostic",
                workflow_step="waiting_for_answer",
                status="waiting_user",
                expected_input_kind="choice",
                expected_input_values=["A", "B", "C", "D"],
                turn_count=1,
            ),
            "quiz_session": QuizSession(
                quiz_id="quiz-1",
                profile_key="workflow-restart",
                phase="quiz",
                level="beginner",
                topic="stocks",
                questions=[question],
            ),
            "formation_session": FormationSession(
                formation_id="formation-1",
                level="beginner",
                path_id="path-1",
                status="active",
            ),
        }

    builder.add_node("establish", establish_context)
    builder.add_edge(START, "establish")
    builder.add_edge("establish", END)
    return builder.compile(checkpointer=checkpointer)


def test_disabled_mode_selects_memory_saver_without_database_access() -> None:
    checkpointer = create_graph_checkpointer(Settings(PERSISTENCE_ENABLED=False))

    assert isinstance(checkpointer, MemorySaver)


def test_enabled_mode_selects_lazy_postgres_saver_without_fallback() -> None:
    checkpointer = create_graph_checkpointer(
        Settings(
            PERSISTENCE_ENABLED=True,
            DATABASE_URL="postgresql+psycopg://user:password@localhost/db",
        )
    )

    assert isinstance(checkpointer, PersistentPostgresCheckpointer)
    assert checkpointer._saver is None


def test_enabled_mode_without_url_fails_clearly() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_graph_checkpointer(Settings(PERSISTENCE_ENABLED=True, DATABASE_URL=""))


def test_official_saver_setup_is_lazy_and_uses_canonical_url() -> None:
    calls = []

    class FakeConnection:
        def close(self) -> None:
            pass

    class FakeSaver:
        config_specs = []

        def __init__(self, connection) -> None:
            self.connection = connection
            self.setup_calls = 0

        def setup(self) -> None:
            self.setup_calls += 1

    def connection_factory(url, **kwargs):
        calls.append((url, kwargs))
        return FakeConnection()

    checkpointer = PersistentPostgresCheckpointer(
        "postgresql+psycopg://user:password@localhost/db",
        connection_factory=connection_factory,
        saver_factory=FakeSaver,
    )
    assert calls == []

    saver = checkpointer._ensure_saver()
    assert calls[0][0] == "postgresql://user:password@localhost/db"
    assert calls[0][1]["autocommit"] is True
    assert calls[0][1]["row_factory"] is not None
    assert saver.setup_calls == 1
    checkpointer.close()


def test_concurrent_first_use_constructs_and_sets_up_one_saver() -> None:
    constructions = 0
    setups = 0

    class FakeConnection:
        def close(self):
            pass

    class FakeSaver:
        def __init__(self, connection):
            nonlocal constructions
            constructions += 1
            self.connection = connection

        def setup(self):
            nonlocal setups
            setups += 1

    checkpointer = PersistentPostgresCheckpointer(
        "postgresql://localhost/db", connection_factory=lambda *a, **k: FakeConnection(),
        saver_factory=FakeSaver,
    )
    with ThreadPoolExecutor(max_workers=8) as executor:
        savers = list(executor.map(lambda _: checkpointer._ensure_saver(), range(8)))
    assert len({id(saver) for saver in savers}) == 1
    assert constructions == 1
    assert setups == 1


def test_concurrent_initialization_failure_is_not_cached_as_memory_fallback() -> None:
    constructions = 0

    def failing_connection(*args, **kwargs):
        nonlocal constructions
        constructions += 1
        raise RuntimeError("database unavailable")

    checkpointer = PersistentPostgresCheckpointer(
        "postgresql://localhost/db", connection_factory=failing_connection
    )
    with ThreadPoolExecutor(max_workers=8) as executor:
        errors = list(executor.map(lambda _: _ensure_error(checkpointer), range(8)))
    assert all(error == "RuntimeError" for error in errors)
    assert constructions == 1
    assert checkpointer._saver is None
    assert not isinstance(checkpointer, MemorySaver)


def test_failed_setup_closes_connection_and_caches_no_partial_saver() -> None:
    connections = []

    class FakeConnection:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    class BrokenSaver:
        config_specs = []

        def __init__(self, connection):
            self.connection = connection

        def setup(self):
            raise RuntimeError("setup failed")

    def connection_factory(*args, **kwargs):
        connection = FakeConnection()
        connections.append(connection)
        return connection

    checkpointer = PersistentPostgresCheckpointer(
        "postgresql://localhost/db",
        connection_factory=connection_factory,
        saver_factory=BrokenSaver,
    )
    with pytest.raises(RuntimeError, match="setup failed"):
        checkpointer._ensure_saver()
    assert connections[0].closed == 1
    assert checkpointer._connection is None
    assert checkpointer._saver is None


def _ensure_error(checkpointer):
    try:
        checkpointer._ensure_saver()
    except Exception as exc:
        return type(exc).__name__
    return "no error"


def test_enabled_checkpointer_failure_does_not_fallback_to_memory() -> None:
    def failing_connection(*args, **kwargs):
        raise RuntimeError("database unavailable")

    checkpointer = PersistentPostgresCheckpointer(
        "postgresql://localhost/db", connection_factory=failing_connection
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        checkpointer._ensure_saver()

    assert not isinstance(checkpointer, MemorySaver)


def test_workflow_context_survives_independent_graph_recreation(tmp_path) -> None:
    checkpoint_path = tmp_path / "checkpoints.pkl"
    config = {"configurable": {"thread_id": "workflow-restart"}}
    saver_a = FileBackedTestSaver(checkpoint_path)
    graph_a = workflow_graph(saver_a)
    graph_a.invoke({"thread_id": "workflow-restart"}, config)
    saver_a._persist()

    graph_b = workflow_graph(FileBackedTestSaver(checkpoint_path))
    restored = graph_b.get_state(config).values["workflow_context"]

    assert restored.status == "waiting_user"
    assert restored.active_agent == "quiz"
    assert restored.expected_input_values == ["A", "B", "C", "D"]
    restored_state = graph_b.get_state(config).values
    assert restored_state["quiz_session"].current_question_index == 0
    assert restored_state["formation_session"].status == "active"


def test_profile_and_workflow_persistence_coexist(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'persistence.db'}"
    database = PersistenceDatabase(enabled=True, database_url=database_url)
    Base.metadata.create_all(database.get_engine())
    profile_store = SqlAlchemyLearningProfileStore(
        database, ConversationThreadStore(database)
    )
    LearningProfileService(profile_store).set_level(
        "shared-thread", "intermediate", "diagnostic"
    )
    checkpoint_path = tmp_path / "coexist.pkl"
    saver_a = FileBackedTestSaver(checkpoint_path)
    graph_a = workflow_graph(saver_a)
    config = {"configurable": {"thread_id": "shared-thread"}}
    graph_a.invoke({"thread_id": "shared-thread"}, config)
    saver_a._persist()
    database.dispose()

    database_b = PersistenceDatabase(enabled=True, database_url=database_url)
    profile_store_b = SqlAlchemyLearningProfileStore(
        database_b, ConversationThreadStore(database_b)
    )
    graph_b = workflow_graph(FileBackedTestSaver(checkpoint_path))

    assert profile_store_b.get("shared-thread").learning_level == "intermediate"
    assert graph_b.get_state(config).values["workflow_context"].active_agent == "quiz"
    database_b.dispose()


def test_threads_have_isolated_checkpoints_and_no_mutable_bleed(tmp_path) -> None:
    checkpoint_path = tmp_path / "isolated.pkl"
    saver_a = FileBackedTestSaver(checkpoint_path)
    graph = workflow_graph(saver_a)
    graph.invoke({"thread_id": "thread-a"}, {"configurable": {"thread_id": "thread-a"}})
    saver_a._persist()

    assert graph.get_state({"configurable": {"thread_id": "thread-b"}}).values == {}


def test_voice_uses_the_common_text_graph_path() -> None:
    assert voice_process_text_message is process_text_message
    assert voice_get_chat_graph is get_chat_graph
