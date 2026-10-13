import inspect
import json

from app.api import chat
from scripts.measure_j8_performance import run_baseline


def test_baseline_runs_real_pipeline_and_all_fake_backed_scenarios():
    previous_history_store = chat.get_conversation_history_store
    report = run_baseline()
    assert chat.get_conversation_history_store is previous_history_store
    assert report["baseline_type"] == "offline_fake_backed_real_pipeline"
    assert report["measured"] is True
    assert report["network_used"] is False
    assert report["scenario_count"] == 8
    assert report["warmup_iterations"] == 1
    assert report["measured_iterations"] == 5
    scenarios = {item["scenario"]: item for item in report["scenarios"]}
    assert set(scenarios) == {
        "simple_pedagogie", "rag_sufficient", "financial_expert_general",
        "financial_expert_web", "quiz", "formation", "security_blocked", "voice",
    }
    assert scenarios["rag_sufficient"]["fake_call_counts"] == {"rag": 5}
    assert scenarios["financial_expert_general"]["fake_call_counts"] == {
        "rag": 5, "financial_expert": 5
    }
    assert scenarios["financial_expert_web"]["fake_call_counts"] == {
        "rag": 5, "financial_expert": 5
    }
    assert scenarios["voice"]["fake_call_counts"] == {"stt": 5, "tts": 5}
    assert "rag" not in scenarios["simple_pedagogie"]["stages"]
    assert "financial_expert" not in scenarios["rag_sufficient"]["stages"]
    assert all(item["request"]["count"] == 5 for item in scenarios.values())


def test_baseline_has_no_manual_stage_duration_emission_or_private_report_data():
    module = __import__("scripts.measure_j8_performance", fromlist=["run_baseline"])
    source = inspect.getsource(module)
    assert "emit(\"request.completed\", duration_ms" not in source
    assert "duration_ms=5.0" not in source
    report = run_baseline()
    encoded = json.dumps(report)
    assert "request_id" not in encoded
    assert "trace_id" not in encoded
    assert "thread_id" not in encoded
    assert "C:\\Users" not in encoded
