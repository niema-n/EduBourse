import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.api import chat
from app.graph import core
from app.graph.agents import pedagogie_agent
from app.observability.context import bind_context, current_context
from app.observability.logging import RequestIdMiddleware, normalize_request_id, thread_ref
from app.schemas.chat import ChatRequest


class FakeGraph:
    def __init__(self, result=None):
        self.result = result or {
            "selected_route": "pedagogie",
            "business_answer": "A safe answer.",
            "response_key": "pedagogie",
            "status": "completed",
        }

    def invoke(self, state, config):
        return {**state, **self.result}


def structured_records(caplog):
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.observability"
    ]


def test_structured_text_events_are_json_correlated_and_safe(monkeypatch, caplog):
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: None)
    caplog.set_level("INFO", logger="app.observability")

    response = chat.process_text_message(
        ChatRequest(message="SUPER_PRIVATE_USER_MESSAGE_92817", thread_id="private-thread"),
        FakeGraph({
            "selected_route": "pedagogie",
            "business_answer": "SUPER_PRIVATE_ASSISTANT_48192",
            "response_key": "pedagogie",
            "status": "completed",
        }),
    )

    records = structured_records(caplog)
    assert response.status == "ok"
    assert {record["event"] for record in records} >= {
        "request.started",
        "request.completed",
        "graph.completed",
    }
    request_records = [record for record in records if record["event"] != "request.started"]
    assert len({record["request_id"] for record in request_records}) == 1
    assert len({record["trace_id"] for record in request_records}) == 1
    completed = next(record for record in records if record["event"] == "request.completed")
    assert completed["route"] == "pedagogie"
    assert completed["response_status"] == "ok"
    assert isinstance(completed["duration_ms"], float)
    assert "SUPER_PRIVATE" not in caplog.text


def test_request_ids_are_unique_and_safe():
    valid = "12345678-1234-5678-1234-567812345678"
    assert normalize_request_id(valid) == valid
    assert normalize_request_id("bad\nrequest") != "bad\nrequest"
    assert normalize_request_id("x" * 129) != "x" * 129
    assert normalize_request_id(None)
    assert thread_ref("private-thread") != "private-thread"


def test_contextvars_isolate_concurrent_turns():
    barrier = Barrier(2)

    def read_context(request_id, trace_id, modality):
        with bind_context(request_id=request_id, trace_id=trace_id, modality=modality):
            barrier.wait()
            value = current_context()
            return value.request_id, value.trace_id, value.modality

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda values: read_context(*values),
                (("request-A", "trace-A", "text"), ("request-B", "trace-B", "voice")),
            )
        )
    assert results == [("request-A", "trace-A", "text"), ("request-B", "trace-B", "voice")]
    assert current_context().request_id is None


def test_http_request_id_header_preserves_valid_and_replaces_invalid():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    def root():
        return {"ok": True}

    client = TestClient(app)
    valid = "12345678-1234-5678-1234-567812345678"
    assert client.get("/", headers={"X-Request-ID": valid}).headers["x-request-id"] == valid
    generated = client.get("/", headers={"X-Request-ID": "not-valid"}).headers["x-request-id"]
    assert generated != "not-valid"


def test_voice_business_context_is_preserved_by_common_pipeline(monkeypatch, caplog):
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: None)
    caplog.set_level("INFO", logger="app.observability")

    with bind_context(request_id="voice-request", trace_id="voice-trace", modality="voice"):
        chat.process_text_message(
            ChatRequest(message="voice-safe", thread_id="voice-thread"), FakeGraph()
        )

    records = structured_records(caplog)
    assert records
    assert {record["request_id"] for record in records} == {"voice-request"}
    assert {record["trace_id"] for record in records} == {"voice-trace"}
    assert {record["modality"] for record in records} == {"voice"}


def test_history_failure_logs_safe_error_and_propagates(monkeypatch, caplog):
    class FailingStore:
        def append_turn(self, *args, **kwargs):
            raise RuntimeError("SUPER_SECRET_API_KEY_123456")

    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: FailingStore())
    caplog.set_level("INFO", logger="app.observability")

    with pytest.raises(RuntimeError, match="SUPER_SECRET_API_KEY_123456"):
        chat.process_text_message(ChatRequest(message="safe", thread_id="failure"), FakeGraph())

    records = structured_records(caplog)
    failed = next(record for record in records if record["event"] == "persistence.history.failed")
    assert failed["error_type"] == "RuntimeError"
    assert "SUPER_SECRET_API_KEY_123456" not in caplog.text
    assert any(record["event"] == "request.failed" for record in records)


def test_observed_node_times_the_wrapped_operation(caplog):
    caplog.set_level("INFO", logger="app.observability")

    def slow_node(state):
        time.sleep(0.01)
        return {**state, "selected_route": "pedagogie", "status": "completed"}

    result = core.observed_node(slow_node, "agent", "pedagogie")({})
    assert result["selected_route"] == "pedagogie"
    record = next(
        item for item in structured_records(caplog) if item["event"] == "agent.completed"
    )
    assert record["duration_ms"] >= 8
    assert record["route"] == "pedagogie"


def test_routing_duration_wraps_only_the_routing_node(caplog):
    caplog.set_level("INFO", logger="app.observability")

    def slow_router(state):
        time.sleep(0.01)
        return {**state, "selected_route": "pedagogie", "route_confidence": 0.9}

    core.observed_node(slow_router, "routing", "router")({})
    record = next(
        item for item in structured_records(caplog) if item["event"] == "routing.completed"
    )
    assert record["duration_ms"] >= 8
    assert record["route"] == "pedagogie"


def test_rag_and_financial_expert_events_time_real_calls(caplog):
    caplog.set_level("INFO", logger="app.observability")

    class GroundedService:
        def generate(self, request):
            time.sleep(0.01)
            return SimpleNamespace(
                generation_status="ok",
                answer="Grounded answer",
                citations=[],
                insufficient_evidence=False,
            )

    pedagogie_agent({"user_input": "question"}, GroundedService())
    rag_record = next(
        item for item in structured_records(caplog) if item["event"] == "rag.completed"
    )
    assert rag_record["duration_ms"] >= 8

    class InsufficientGroundedService:
        def generate(self, request):
            return SimpleNamespace(
                generation_status="insufficient_evidence",
                answer=None,
                citations=[],
                insufficient_evidence=True,
            )

    class ExpertService:
        def answer(self, request):
            time.sleep(0.01)
            return SimpleNamespace(
                answer="Expert answer",
                knowledge_source="llm_general_financial_knowledge",
                web_grounded=False,
                web_sources=[],
                web_search_entry_point=None,
            )

    pedagogie_agent(
        {"user_input": "question", "language": "fr", "script": "latin"},
        InsufficientGroundedService(),
        ExpertService(),
        True,
    )
    expert_record = next(
        item
        for item in structured_records(caplog)
        if item["event"] == "financial_expert.completed"
    )
    assert expert_record["duration_ms"] >= 8


def test_security_runs_once_as_the_graph_node(monkeypatch, caplog):
    calls = 0

    def security_node(state):
        nonlocal calls
        calls += 1
        return {"security_status": "clear", "risk_level": "none"}

    class Supervisor:
        def invoke_structured(self, request):
            return {"domain_status": "in_domain", "route": "pedagogie"}

    monkeypatch.setattr(core, "security_guard_node", security_node)
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: None)
    caplog.set_level("INFO", logger="app.observability")
    graph = core.build_graph(
        checkpointer=MemorySaver(), supervisor_provider=Supervisor(), grounded_service=None
    )
    response = chat.process_text_message(
        ChatRequest(message="What is a stock?", thread_id="security-once"), graph
    )

    records = structured_records(caplog)
    assert response.route == "pedagogie"
    assert calls == 1
    assert sum(item["event"] == "security.completed" for item in records) == 1
    assert sum(item["event"] == "routing.completed" for item in records) == 1
    assert sum(item["event"] == "agent.completed" for item in records) == 1
