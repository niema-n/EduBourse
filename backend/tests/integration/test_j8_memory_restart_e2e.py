import pickle
from collections import defaultdict
from pathlib import Path
from threading import RLock

from langgraph.checkpoint.memory import MemorySaver

from app.api import chat
from app.api.voice import process_text_message as voice_process_text_message
from app.graph.core import build_graph
from app.learning import LearningProfileService
from app.memory.models import RecentConversationContext
from app.memory.relevant_models import RelevantMemoryContext
from app.memory.shared_context import AgentMemoryContext, ConversationMemoryContext
from app.persistence.database import PersistenceDatabase
from app.persistence.learning_profile_store import SqlAlchemyLearningProfileStore
from app.persistence.models import Base
from app.persistence.thread_store import ConversationThreadStore
from app.schemas.chat import ChatRequest


class FileBackedSaver(MemorySaver):
    """Small test-only durable saver using LangGraph's real saver contract."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._snapshot_lock = RLock()
        self.path = path
        if path.exists():
            with self._snapshot_lock, path.open("rb") as stream:
                saved = pickle.load(stream)
                self.storage = defaultdict(lambda: defaultdict(dict), saved["storage"])
                self.writes = defaultdict(dict, saved["writes"])
                self.blobs = defaultdict(dict, saved["blobs"])

    def _persist(self) -> None:
        with self._snapshot_lock, self.path.open("wb") as stream:
            pickle.dump(
                {
                    "storage": dict(self.storage),
                    "writes": dict(self.writes),
                    "blobs": dict(self.blobs),
                },
                stream,
            )

    def put(self, config, checkpoint, metadata, new_versions):
        with self._snapshot_lock:
            result = super().put(config, checkpoint, metadata, new_versions)
            self._persist()
            return result

    def put_writes(self, config, writes, task_id, task_path=""):
        with self._snapshot_lock:
            result = super().put_writes(config, writes, task_id, task_path)
            self._persist()
            return result


class QuizRestartSupervisor:
    def invoke_structured(self, request):
        text = request.user_message.casefold()
        route = "quiz" if "quiz" in text or "continue le" in text else "pedagogie"
        return {"domain_status": "in_domain", "route": route}


class IsolatedMemoryRuntime:
    """Deterministic test runtime; never opens the production BGE/Chroma index."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.context = ConversationMemoryContext(
            RecentConversationContext("memory-e2e-thread", (), 0, 0),
            RelevantMemoryContext("memory-e2e-thread", (), 0, 0),
            "ok",
        )

    def resolve(self, thread_id, query):
        return self.context

    def rehydrate(self, thread_id, message_ids, status):
        return self.context

    def agent_context(self, state):
        return AgentMemoryContext('{"type":"untrusted_conversation_memory"}', ())

    def index_canonical_messages(self, thread_id, message_ids):
        return len(message_ids)


def make_persistent_services(database_url: str):
    database = PersistenceDatabase(enabled=True, database_url=database_url)
    Base.metadata.create_all(database.get_engine())
    thread_store = ConversationThreadStore(database)
    profile_store = SqlAlchemyLearningProfileStore(database, thread_store)
    return database, LearningProfileService(profile_store), chat.SqlAlchemyConversationHistoryStore(
        database, thread_store
    )


def test_text_restart_pause_resume_profile_and_history_e2e(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'memory.db'}"
    checkpoint_path = tmp_path / "checkpoints.pkl"
    memory_runtime = IsolatedMemoryRuntime(tmp_path / "memory-chroma")
    thread_id = "memory-e2e-thread"

    database_a, profile_a, history_a = make_persistent_services(database_url)
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: history_a)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: memory_runtime)
    graph_a = build_graph(
        checkpointer=FileBackedSaver(checkpoint_path),
        supervisor_provider=QuizRestartSupervisor(),
        learning_profile_service=profile_a,
        memory_runtime=memory_runtime,
    )

    started = chat.process_text_message(
        ChatRequest(message="Start a diagnostic quiz.", thread_id=thread_id), graph_a
    )
    assert started.route == "quiz"
    quiz_id = graph_a.get_state({"configurable": {"thread_id": thread_id}}).values[
        "quiz_session"
    ].quiz_id

    paused = chat.process_text_message(
        ChatRequest(message="What is a stock?", thread_id=thread_id), graph_a
    )
    assert paused.route == "pedagogie"
    assert graph_a.get_state({"configurable": {"thread_id": thread_id}}).values[
        "quiz_session"
    ].phase == "paused"
    database_a.dispose()

    database_b, profile_b, history_b = make_persistent_services(database_url)
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: history_b)
    graph_b = build_graph(
        checkpointer=FileBackedSaver(checkpoint_path),
        supervisor_provider=QuizRestartSupervisor(),
        learning_profile_service=profile_b,
        memory_runtime=memory_runtime,
    )
    config = {"configurable": {"thread_id": thread_id}}

    bare_choice = chat.process_text_message(
        ChatRequest(message="B", thread_id=thread_id), graph_b
    )
    assert bare_choice.route == "pedagogie"
    assert graph_b.get_state(config).values["quiz_session"].phase == "paused"

    resumed = chat.process_text_message(
        ChatRequest(message="continue le quiz", thread_id=thread_id), graph_b
    )
    restored_session = graph_b.get_state(config).values["quiz_session"]
    assert resumed.route == "quiz"
    assert restored_session.quiz_id == quiz_id
    assert restored_session.phase == "diagnostic"
    assert profile_b.get_profile(thread_id).learning_level is None

    voice_turn = voice_process_text_message(
        ChatRequest(message="A", thread_id=thread_id), graph_b
    )
    assert voice_turn.route == "quiz"

    messages = history_b.list_messages(thread_id)
    assert len(messages) == 10
    assert [item.role for item in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[0].content == "Start a diagnostic quiz."
    assert messages[-1].content == voice_turn.answer
    assert history_b.list_messages("memory-other-thread") == []
    assert graph_b.get_state({"configurable": {"thread_id": "memory-other-thread"}}).values == {}
    database_b.dispose()
