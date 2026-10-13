import json
from concurrent.futures import ThreadPoolExecutor

from app.api import chat
from app.observability.context import current_context
from app.observability.metrics import get_metrics_snapshot, reset_metrics
from app.schemas.chat import ChatRequest


def test_catastrophic_graph_failure_is_neutral_and_does_not_log_exception(caplog):
    class BrokenGraph:
        def invoke(self, state, config):
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")

    caplog.set_level("INFO", logger="app.observability")
    response = chat.process_text_message(
        ChatRequest(message="What stock should I buy?", thread_id="failure"), BrokenGraph()
    )

    assert response.route == "fallback"
    assert response.status == "error"
    assert response.blocked is False
    assert "recommend" not in response.answer.casefold()
    assert "PRIVATE_PROVIDER_PAYLOAD" not in caplog.text
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.observability"
    ]
    assert any(record["event"] == "request.completed" for record in records)


def test_cached_graph_close_is_idempotent_and_does_not_initialize_graph(monkeypatch):
    class FakeCheckpointer:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    class FakeGraph:
        def __init__(self):
            self.checkpointer = FakeCheckpointer()

    graph = FakeGraph()
    monkeypatch.setattr(chat, "_cached_chat_graph", graph)
    chat.close_cached_chat_graph()
    chat.close_cached_chat_graph()
    assert graph.checkpointer.close_calls == 1
    assert chat._cached_chat_graph is None


def test_concurrent_text_turns_keep_context_and_metrics_isolated(monkeypatch):
    class Graph:
        def invoke(self, state, config):
            return {
                **state,
                "selected_route": "pedagogie",
                "business_answer": "safe",
                "response_key": "pedagogie",
                "status": "completed",
            }

    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: None)
    reset_metrics()
    graph = Graph()
    with ThreadPoolExecutor(max_workers=20) as executor:
        responses = list(executor.map(
            lambda index: chat.process_text_message(
                ChatRequest(message=f"turn {index}", thread_id=f"thread-{index}"), graph
            ),
            range(20),
        ))
    assert all(response.status == "ok" for response in responses)
    assert current_context().request_id is None
    assert get_metrics_snapshot()["counters"]["requests_total"] == 20
