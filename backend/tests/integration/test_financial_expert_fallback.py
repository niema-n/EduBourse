from __future__ import annotations

import pytest

from app.api.chat import process_text_message
from app.financial_expert.models import FinancialExpertRequest, FinancialExpertResult
from app.graph.core import build_graph
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest


class FixedSupervisor:
    def __init__(self, route: str = "pedagogie") -> None:
        self.route = route
        self.calls = 0

    def invoke_structured(self, request: object) -> object:
        self.calls += 1
        return {
            "domain_status": "out_of_domain"
            if self.route == "out_of_domain"
            else "in_domain",
            "route": self.route,
        }


class ControlledGroundedService:
    def __init__(self, *, insufficient: bool) -> None:
        self.insufficient = insufficient
        self.calls: list[object] = []

    def generate(self, request: object) -> GroundedGenerationResult:
        self.calls.append(request)
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=(
                "Official grounded answer."
                if not self.insufficient
                else "Sources are insufficient."
            ),
            citations=[] if self.insufficient else [
                {
                    "evidence_id": "S1",
                    "chunk_id": "official-1",
                    "source_id": "official",
                    "title": "Official source",
                    "page": 1,
                    "page_start": 1,
                    "page_end": 1,
                    "heading": "Markets",
                }
            ],
            used_evidence_ids=[] if self.insufficient else ["S1"],
            retrieval_status="ok",
            generation_status="insufficient_evidence" if self.insufficient else "ok",
            grounded=not self.insufficient,
            insufficient_evidence=self.insufficient,
            provider_retryable=False,
        )


class RecordingFinancialExpert:
    provider_name = "fake-gemini"

    def __init__(self, answer: str = "General financial-market explanation.") -> None:
        self.response_text = answer
        self.calls: list[FinancialExpertRequest] = []

    def answer(self, request: FinancialExpertRequest) -> FinancialExpertResult:
        self.calls.append(request)
        return FinancialExpertResult(
            answer=self.response_text,
            language=request.language,
            script=request.script,
            provider=self.provider_name,
            knowledge_source="llm_general_financial_knowledge",
        )


class FailingFinancialExpert(RecordingFinancialExpert):
    def answer(self, request: FinancialExpertRequest) -> FinancialExpertResult:
        self.calls.append(request)
        raise RuntimeError("provider failure with secret-like details")


def run_message(
    message: str,
    *,
    language: str | None = None,
    grounded: ControlledGroundedService | None = None,
    expert: RecordingFinancialExpert | None = None,
    enabled: bool = True,
    route: str = "pedagogie",
):
    graph = build_graph(
        supervisor_provider=FixedSupervisor(route),
        grounded_service=grounded,
        financial_expert_service=expert,
        financial_expert_fallback_enabled=enabled,
    )
    request = ChatRequest(message=message, thread_id=f"fallback-{language or route}")
    return process_text_message(request, graph), expert


def test_sufficient_rag_answer_wins_and_does_not_call_financial_expert():
    grounded = ControlledGroundedService(insufficient=False)
    expert = RecordingFinancialExpert()
    result, _ = run_message("What is the role of AMMC?", grounded=grounded, expert=expert)

    assert result.answer == "Official grounded answer."
    assert result.grounded is True
    assert result.citations[0]["source_id"] == "official"
    assert expert.calls == []


@pytest.mark.parametrize(
    ("message", "language", "script", "answer"),
    [
        ("Explique les obligations", "fr", "latin", "Réponse générale sur les marchés."),
        ("What is a stock?", "en", "latin", "A general explanation of financial markets."),
        ("ما هو السند؟", "ar", "arabic", "شرح عام للأسواق المالية."),
        ("Chno howa sanad?", "ary", "latin", "Jawab 3am 3la l aswa9 lmaliya."),
        ("شنو هو السند؟", "ary", "arabic", "شرح عام على الأسواق المالية."),
    ],
)
def test_insufficient_rag_calls_expert_once_with_existing_locale(
    message, language, script, answer
):
    grounded = ControlledGroundedService(insufficient=True)
    expert = RecordingFinancialExpert(answer)
    result, _ = run_message(message, grounded=grounded, expert=expert)

    assert len(expert.calls) == 1
    assert expert.calls[0].question == message
    assert expert.calls[0].language == language
    assert expert.calls[0].script == script
    assert result.answer == answer
    assert result.citations == []
    assert result.grounded is False


def test_fallback_provenance_is_internal_and_rag_has_no_fake_citations():
    grounded = ControlledGroundedService(insufficient=True)
    expert = RecordingFinancialExpert()
    supervisor = FixedSupervisor()
    graph = build_graph(
        supervisor_provider=supervisor,
        grounded_service=grounded,
        financial_expert_service=expert,
        financial_expert_fallback_enabled=True,
    )
    state = {
        "user_input": "Why do long-duration bonds react more strongly?",
        "language": "en",
        "script": "latin",
        "thread_id": "provenance",
    }
    result = graph.invoke(state, config={"configurable": {"thread_id": "provenance"}})

    assert result["knowledge_source"] == "llm_general_financial_knowledge"
    assert result["grounded_citations"] == []


def test_disabled_flag_preserves_insufficient_evidence_behavior():
    grounded = ControlledGroundedService(insufficient=True)
    expert = RecordingFinancialExpert()
    result, _ = run_message(
        "Explain an unfamiliar market concept",
        grounded=grounded,
        expert=expert,
        enabled=False,
    )

    assert expert.calls == []
    assert result.answer == "Sources are insufficient."


def test_current_data_fallback_keeps_no_live_data_policy():
    grounded = ControlledGroundedService(insufficient=True)
    expert = RecordingFinancialExpert(
        "I cannot reliably confirm SGTM's current price without a validated current source."
    )
    result, _ = run_message(
        "What is SGTM's price today?", grounded=grounded, expert=expert
    )

    assert "cannot reliably confirm" in result.answer
    assert not any(char.isdigit() for char in result.answer)
    assert len(expert.calls) == 1


def test_security_preempts_fallback():
    expert = RecordingFinancialExpert()
    graph = build_graph(
        supervisor_provider=FixedSupervisor(),
        grounded_service=ControlledGroundedService(insufficient=True),
        financial_expert_service=expert,
        financial_expert_fallback_enabled=True,
    )
    result = process_text_message(
        ChatRequest(message="Which Moroccan stock should I buy?", thread_id="security"), graph
    )

    assert result.route == "securite"
    assert result.blocked is True
    assert expert.calls == []


def test_out_of_domain_preempts_fallback():
    expert = RecordingFinancialExpert()
    result, _ = run_message(
        "How do I cook pasta?",
        grounded=ControlledGroundedService(insufficient=True),
        expert=expert,
        route="out_of_domain",
    )

    assert result.route == "out_of_domain"
    assert expert.calls == []


@pytest.mark.parametrize(
    "route",
    ("formation_elearning", "quiz", "orientation", "cisi", "championnat", "support_ecole"),
)
def test_other_agents_do_not_use_financial_expert(route):
    expert = RecordingFinancialExpert()
    result, _ = run_message(
        "Continue my financial learning",
        grounded=ControlledGroundedService(insufficient=True),
        expert=expert,
        route=route,
    )

    assert result.route == route
    assert expert.calls == []


def test_provider_failure_is_controlled_without_stack_trace_or_secret():
    expert = FailingFinancialExpert()
    result, _ = run_message(
        "Explain a bond",
        grounded=ControlledGroundedService(insufficient=True),
        expert=expert,
    )

    assert result.answer
    assert "secret-like" not in result.answer
    assert "traceback" not in result.answer.casefold()
