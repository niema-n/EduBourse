import json
from concurrent.futures import ThreadPoolExecutor

from app.observability import metrics
from app.observability.logging import emit


def test_known_request_sequence_and_low_cardinality_dimensions():
    metrics.reset_metrics()
    for _ in range(3):
        emit("request.completed", modality="text", response_status="ok", route="pedagogie",
             language="fr", script="latin", knowledge_source="none")
    for _ in range(2):
        emit("request.completed", modality="voice", response_status="blocked", route="securite",
             language="ar", script="arabic", knowledge_source=None)

    snapshot = metrics.get_metrics_snapshot()
    counters = snapshot["counters"]
    assert counters["requests_total"] == 5
    assert counters["requests_total.by_modality"] == {"text": 3, "voice": 2}
    assert counters["requests_total.by_status"] == {"ok": 3, "blocked": 2}
    assert counters["requests_total.by_route"] == {"pedagogie": 3, "securite": 2}


def test_stage_histograms_are_accurate_and_bounded():
    metrics.reset_metrics()
    for duration in (5, 20, 300, 1200):
        emit("graph.completed", duration_ms=duration)
    histogram = metrics.get_metrics_snapshot()["latency"]["graph"]
    assert histogram["count"] == 4
    assert histogram["average_ms"] == 381.25
    assert histogram["min_ms"] == 5.0
    assert histogram["max_ms"] == 1200.0
    assert histogram["bucket_counts"]["5"] == 1
    assert histogram["bucket_counts"]["25"] == 2
    assert histogram["bucket_counts"]["1000"] == 3
    assert histogram["bucket_counts"]["+Inf"] == 4


def test_missing_stages_do_not_get_fabricated():
    metrics.reset_metrics()
    emit("request.completed", route="quiz", response_status="ok", modality="text")
    snapshot = metrics.get_metrics_snapshot()
    assert "rag" not in snapshot["latency"]
    assert snapshot["counters"].get("rag_calls_total", 0) == 0


def test_provenance_is_current_turn_and_finite():
    metrics.reset_metrics()
    emit("request.completed", route="pedagogie", response_status="ok", modality="text",
         knowledge_source="rag")
    emit("request.completed", route="pedagogie", response_status="ok", modality="text",
         knowledge_source="llm_general_financial_knowledge")
    emit("request.completed", route="pedagogie", response_status="ok", modality="text",
         knowledge_source="llm_web_grounded_financial_knowledge")
    emit("request.completed", route="pedagogie", response_status="ok", modality="text",
         knowledge_source="old_checkpoint_secret")
    provenance = metrics.get_metrics_snapshot()["counters"]["requests_total.by_provenance"]
    assert provenance == {
        "rag": 1,
        "llm_general_financial_knowledge": 1,
        "llm_web_grounded_financial_knowledge": 1,
        "unknown": 1,
    }


def test_all_event_families_are_aggregated_without_content():
    metrics.reset_metrics()
    emit("security.completed", security_status="clear", risk_level="none", duration_ms=1)
    emit("agent.completed", route="pedagogie", duration_ms=2)
    emit("rag.completed", grounded=True, insufficient_evidence=False, duration_ms=3)
    emit("financial_expert.completed", mode="general", duration_ms=4)
    emit("financial_expert.completed", mode="web_grounded", duration_ms=5)
    emit("persistence.history.failed", error_type="RuntimeError", duration_ms=6)
    emit("voice.stt.failed", error_type="SecretException", duration_ms=7)
    emit("voice.tts.completed", language="fr", script="latin", duration_ms=8)
    snapshot = metrics.get_metrics_snapshot()
    counters = snapshot["counters"]
    assert counters["security_decisions_total"] == 1
    assert counters["security_decisions_total.by_status"] == {"clear": 1}
    assert counters["agent_calls_total"] == 1
    assert counters["agent_calls_total.by_route"] == {"pedagogie": 1}
    assert counters["rag_calls_total"] == 1
    assert counters["rag_grounded_total"] == 1
    assert counters["financial_expert_general_total"] == 1
    assert counters["financial_expert_web_grounded_total"] == 1
    assert counters["history_persistence_failures_total"] == 1
    assert counters["voice_stt_calls_total"] == 1
    assert counters["voice_tts_calls_total"] == 1
    assert "SecretException" not in json.dumps(snapshot)


def test_concurrent_increments_are_exact():
    metrics.reset_metrics()

    def worker():
        for _ in range(100):
            emit("request.completed", modality="text", response_status="ok", route="quiz")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: worker(), range(8)))
    assert metrics.get_metrics_snapshot()["counters"]["requests_total"] == 800


def test_metric_observer_failure_does_not_break_emit(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("SENTINEL_METRIC_FAILURE")

    monkeypatch.setattr(metrics.REGISTRY, "observe_event", fail)
    emit("request.completed", route="pedagogie", response_status="ok")


def test_snapshot_is_json_serializable_and_has_no_private_fields():
    metrics.reset_metrics()
    emit("request.completed", route="pedagogie", response_status="ok",
         request_id="REQUEST_SECRET", trace_id="TRACE_SECRET", thread_ref="THREAD_SECRET",
         user_text="USER_SECRET", answer_text="ANSWER_SECRET", duration_ms=1)
    encoded = json.dumps(metrics.get_metrics_snapshot())
    assert "SECRET" not in encoded
