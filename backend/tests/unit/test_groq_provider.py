import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app.graph.response_localizer import GroqResponseLocalizationProvider
from app.graph.supervisor import SupervisorRequest
from app.llm.groq_provider import GroqProvider


def test_groq_request_uses_bounded_deterministic_structured_options(monkeypatch) -> None:
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(
                            content='{"domain_status":"in_domain","route":"pedagogie",'
                            '"decision_basis":"general_financial_education"}'
                        )
                    )
                ]
            )

    class FakeGroq:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 60.0
            assert kwargs["max_retries"] == 2
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    provider = GroqProvider("test-key", "test-model")
    provider.invoke_structured(
        SupervisorRequest(user_message="What is a bond?", business_language="en", script="latin")
    )
    assert calls[0]["reasoning_effort"] == "none"
    assert calls[0]["max_completion_tokens"] == 100
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_checkpoint_is_written_after_each_result(tmp_path) -> None:
    script = Path(__file__).parents[3] / "scripts" / "evaluate_j3_llm_supervisor.py"
    spec = spec_from_file_location("j3_evaluator", script)
    assert spec and spec.loader
    evaluator = module_from_spec(spec)
    sys.modules["j3_evaluator"] = evaluator
    spec.loader.exec_module(evaluator)

    path = tmp_path / "run1.jsonl"
    evaluator.append_jsonl(path, {"validation_id": "row-1", "parse_success": True})
    assert evaluator.load_jsonl(path)["row-1"]["parse_success"] is True


def test_response_localizer_groq_json_mode_is_explicit(monkeypatch) -> None:
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content='{"answer":"Saham howa joz."}'),
                        finish_reason="stop",
                    )
                ]
            )

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    provider = GroqResponseLocalizationProvider("test-key", "test-model")
    provider._complete("system", {"answer": "source"})
    assert calls[0]["response_format"] == {"type": "json_object"}

    provider._complete("system", {"answer": "source"}, json_mode=False)
    assert "response_format" not in calls[1]
