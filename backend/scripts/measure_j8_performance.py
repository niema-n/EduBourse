"""Offline fake-provider performance baseline for the real local pipeline."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import chat  # noqa: E402
from app.api.chat import process_text_message  # noqa: E402
from app.financial_expert.models import FinancialExpertResult  # noqa: E402
from app.graph.core import build_graph  # noqa: E402
from app.learning.profile_service import LearningProfileService  # noqa: E402
from app.learning.store import InMemoryLearningProfileStore  # noqa: E402
from app.rag.grounded_generation import GroundedGenerationResult  # noqa: E402
from app.schemas.chat import ChatRequest  # noqa: E402
from app.voice.models import AudioInput, SpeechSynthesisResult, TranscriptionResult  # noqa: E402
from app.voice.service import VoiceService  # noqa: E402

ITERATIONS = 5
WARMUP_ITERATIONS = 1
LIMITATION_TEXT = (
    "This baseline measures local application/orchestration overhead with fake providers. "
    "It does not represent production latency of Gemini, Groq, Google Search or PostgreSQL."
)


class FakeSupervisor:
    def invoke_structured(self, request: object) -> object:
        message = getattr(request, "user_message", "").casefold()
        if "quiz" in message:
            route = "quiz"
        elif "formation" in message or "training" in message:
            route = "formation_elearning"
        else:
            route = "pedagogie"
        return {"domain_status": "in_domain", "route": route}


class FakeGroundedService:
    def __init__(self, *, sufficient: bool) -> None:
        self.sufficient = sufficient
        self.calls = 0

    def generate(self, request: object) -> GroundedGenerationResult:
        self.calls += 1
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Local fake grounded answer." if self.sufficient else None,
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="ok" if self.sufficient else "insufficient_evidence",
            grounded=self.sufficient,
            insufficient_evidence=not self.sufficient,
            provider_retryable=False,
        )


class FakeFinancialExpertService:
    def __init__(self, *, web_grounded: bool) -> None:
        self.web_grounded = web_grounded
        self.calls = 0

    def answer(self, request: object) -> FinancialExpertResult:
        self.calls += 1
        source = (
            "llm_web_grounded_financial_knowledge"
            if self.web_grounded
            else "llm_general_financial_knowledge"
        )
        return FinancialExpertResult(
            answer="Local fake financial-expert answer.", language=request.language,
            script=request.script, provider="offline-fake", knowledge_source=source,
            web_grounded=self.web_grounded, web_sources=[], web_search_entry_point=None,
        )


class FakeSTT:
    provider_name = "offline-fake-stt"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        self.calls += 1
        return TranscriptionResult(text=self.text, provider=self.provider_name, model="fake")


class FakeTTS:
    provider_name = "offline-fake-tts"

    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, text: str, *, language: str, script: str) -> SpeechSynthesisResult:
        self.calls += 1
        return SpeechSynthesisResult(
            audio=b"offline-fake-audio", mime_type="audio/wav", provider=self.provider_name
        )


def _graph(*, grounded=None, expert=None, expert_enabled=False, checkpointer=None):
    return build_graph(
        checkpointer=checkpointer, supervisor_provider=FakeSupervisor(),
        grounded_service=grounded, financial_expert_service=expert,
        financial_expert_fallback_enabled=expert_enabled,
        learning_profile_service=LearningProfileService(InMemoryLearningProfileStore()),
    )


def _run_text(graph: Any, message: str, thread_id: str) -> None:
    process_text_message(ChatRequest(message=message, thread_id=thread_id), graph)


def _stage_rows(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in snapshot["latency"].items() if value["count"]}


def _scenario_report(name: str, action, *, call_counts=None) -> dict[str, Any]:
    from app.observability.metrics import get_metrics_snapshot, reset_metrics

    action("warmup")
    warmup_counts = call_counts() if call_counts else None
    reset_metrics()
    for index in range(ITERATIONS):
        action(f"measured-{index}")
    current = get_metrics_snapshot()
    stages = _stage_rows(current)
    candidates = {key: value for key, value in stages.items() if key not in {"request", "graph"}}
    slowest = max(candidates, key=lambda key: candidates[key]["average_ms"]) if candidates else None
    result = {
        "scenario": name,
        "warmup_iterations": WARMUP_ITERATIONS,
        "measured_iterations": ITERATIONS,
        "request": stages.get("request"),
        "stages": stages,
        "slowest_stage": slowest,
        "slowest_stage_interpretation": "local_fake_backed_measurement_only",
    }
    if call_counts:
        result["fake_call_counts"] = {
            key: value - warmup_counts.get(key, 0)
            for key, value in call_counts().items()
        }
    return result


def _run_baseline() -> dict[str, Any]:
    reports = []

    simple_graph = _graph()
    reports.append(_scenario_report(
        "simple_pedagogie",
        lambda suffix: _run_text(simple_graph, "Explain a stock", f"simple-{suffix}"),
    ))

    sufficient = FakeGroundedService(sufficient=True)
    rag_graph = _graph(grounded=sufficient)
    reports.append(_scenario_report(
        "rag_sufficient",
        lambda suffix: _run_text(rag_graph, "Explain a stock", f"rag-{suffix}"),
        call_counts=lambda: {"rag": sufficient.calls},
    ))

    insufficient_general = FakeGroundedService(sufficient=False)
    general_expert = FakeFinancialExpertService(web_grounded=False)
    general_graph = _graph(
        grounded=insufficient_general, expert=general_expert, expert_enabled=True
    )
    reports.append(_scenario_report(
        "financial_expert_general",
        lambda suffix: _run_text(general_graph, "Explain a stock", f"general-{suffix}"),
        call_counts=lambda: {
            "rag": insufficient_general.calls,
            "financial_expert": general_expert.calls,
        },
    ))

    insufficient_web = FakeGroundedService(sufficient=False)
    web_expert = FakeFinancialExpertService(web_grounded=True)
    web_graph = _graph(grounded=insufficient_web, expert=web_expert, expert_enabled=True)
    reports.append(_scenario_report(
        "financial_expert_web",
        lambda suffix: _run_text(web_graph, "Explain a stock", f"web-{suffix}"),
        call_counts=lambda: {"rag": insufficient_web.calls, "financial_expert": web_expert.calls},
    ))

    from langgraph.checkpoint.memory import MemorySaver

    quiz_graph = _graph(checkpointer=MemorySaver())
    _run_text(quiz_graph, "I want a quiz", "quiz-seed")
    reports.append(_scenario_report(
        "quiz", lambda suffix: _run_text(quiz_graph, "A", "quiz-seed"),
    ))

    formation_graph = _graph(checkpointer=MemorySaver())
    _run_text(formation_graph, "I want a formation", "formation-seed")
    reports.append(_scenario_report(
        "formation", lambda suffix: _run_text(formation_graph, "next", "formation-seed"),
    ))

    security_graph = _graph()
    reports.append(_scenario_report(
        "security_blocked",
        lambda suffix: _run_text(
            security_graph,
            "Which stock should I buy tomorrow to make money quickly?",
            f"security-{suffix}",
        ),
    ))

    stt = FakeSTT("Explain a stock")
    tts = FakeTTS()
    voice_graph = _graph()
    voice = VoiceService(stt, tts, lambda payload: process_text_message(payload, voice_graph))

    def voice_action(suffix: str) -> None:
        del suffix
        voice.process(
            AudioInput(data=b"pcm", mime_type="audio/wav"),
            session_id="voice-session", thread_id="voice-thread",
        )

    reports.append(_scenario_report(
        "voice", voice_action, call_counts=lambda: {"stt": stt.calls, "tts": tts.calls}
    ))

    return {
        "baseline_type": "offline_fake_backed_real_pipeline",
        "measured": True,
        "network_used": False,
        "real_postgres_used": False,
        "real_gemini_used": False,
        "real_groq_used": False,
        "real_google_search_used": False,
        "python_version": platform.python_version(),
        "system": platform.system(),
        "warmup_iterations": WARMUP_ITERATIONS,
        "measured_iterations": ITERATIONS,
        "scenario_count": len(reports),
        "limitations": [LIMITATION_TEXT,
                         "Agent duration may include nested RAG or Financial Expert execution; "
                         "stage durations are not additive."],
        "voice_seam": "VoiceService.process: fake STT -> process_text_message -> fake TTS",
        "scenarios": reports,
    }


def run_baseline() -> dict[str, Any]:
    previous_history_store = chat.get_conversation_history_store
    chat.get_conversation_history_store = lambda: None
    try:
        return _run_baseline()
    finally:
        chat.get_conversation_history_store = previous_history_store


if __name__ == "__main__":
    report = run_baseline()
    output_path = Path("reports/j8_performance_baseline.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
