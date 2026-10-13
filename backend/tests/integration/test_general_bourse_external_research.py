"""Generic Bourse external research: no entity special case, security first, fail closed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api import chat as chat_api
from app.api.chat import process_text_message
from app.financial_expert.freshness import (
    market_fact_intent,
    requires_live_market_data,
    requires_verified_market_facts,
)
from app.financial_expert.provider import FinancialExpertGeneration
from app.financial_expert.service import FinancialExpertService
from app.graph.core import build_graph
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest

APPROVED = ({"domain": "casablanca-bourse.com", "uri": "https://www.casablanca-bourse.com/x"},)

# (question, expected intent). Entities vary on purpose: no ticker is special.
CURRENT = [
    "cours IAM aujourd'hui",
    "action de SGTM fait combien aujourd'hui",
    "combien vaut GTM maintenant ?",
    "le MASI a augmenté de combien aujourd'hui ?",
    "variation de Label Vie aujourd'hui",
    "cours de Maroc Telecom actuellement",
]
DATED = [
    "quel était le cours de GTM le 11/09 ?",
    "le MASI a augmenté de combien vendredi ?",
    "quelle était la variation d'Attijariwafa bank hier ?",
    "quel était le cours de IAM le 13 septembre ?",
    "le MASI a clôturé à combien le 2026-09-11 ?",
]
EVENTS = [
    "quel dividende a annoncé Maroc Telecom récemment ?",
    "quelle est la dernière société introduite à la Bourse de Casablanca ?",
    "Label Vie a-t-elle publié ses derniers résultats ?",
    "une augmentation de capital a-t-elle été annoncée par Addoha en 2026 ?",
]
LISTING = [
    "SGTM est-elle cotée en bourse ?",
    "la cotation de Delta Holding est-elle suspendue ?",
    "Is Maroc Telecom still listed?",
]
STABLE = [
    "C'est quoi une action ?",
    "Comment fonctionne le MASI ?",
    "Qu'est-ce qu'un OPCVM ?",
    "Comment fonctionne un dividende ?",
    "Qu'est-ce qu'une introduction en bourse ?",
    "What is a stock market index?",
]
MULTILINGUAL_CURRENT = [
    ("what is the current MASI level?", "en"),
    ("ما هو سعر سهم اتصالات المغرب اليوم؟", "ar"),
    ("شحال داير MASI اليوم؟", "ary"),
    ("ch7al dayr MASI lyoum?", "ary"),
    ("le MASI a fait combien aujourd'hui ?", "fr"),
]
LOCALIZED_TEXT = {
    ("fr", "latin"): "Selon la Bourse de Casablanca, la valeur est confirmée.",
    ("en", "latin"): "According to the Casablanca Stock Exchange, the value is confirmed.",
    ("ar", "arabic"): "حسب بورصة الدار البيضاء، القيمة مؤكدة.",
    ("ary", "arabic"): "حسب بورصة الدار البيضاء، القيمة مأكدة.",
    ("ary", "latin"): "3la hsab boursa dyal Casablanca, lqima m2akda.",
}


# ------------------------------------------------------------------ detector


@pytest.mark.parametrize("question", CURRENT)
def test_generic_current_price_detection(question):
    assert market_fact_intent(question) == "current_data"
    assert requires_live_market_data(question)


@pytest.mark.parametrize("question", DATED)
def test_dated_market_value_detection(question):
    assert market_fact_intent(question) == "dated_data"
    assert requires_live_market_data(question)


@pytest.mark.parametrize("question", EVENTS)
def test_corporate_event_detection(question):
    assert market_fact_intent(question) == "market_event"
    assert not requires_live_market_data(question)
    assert requires_verified_market_facts(question, "fr", "latin")


@pytest.mark.parametrize("question", LISTING)
def test_listing_status_detection(question):
    assert market_fact_intent(question) == "listing_status"
    assert requires_verified_market_facts(question, "fr", "latin")


@pytest.mark.parametrize("question", STABLE)
def test_stable_educational_questions_are_not_market_facts(question):
    assert market_fact_intent(question) is None
    assert not requires_verified_market_facts(question, "fr", "latin")


@pytest.mark.parametrize(
    "question",
    ["Qui a gagné le match hier ?", "Quel téléphone acheter ?", "Donne-moi une recette de pizza"],
)
def test_non_market_time_questions_are_not_market_facts(question):
    assert market_fact_intent(question) is None


@pytest.mark.parametrize(
    "question",
    ["What should I know about currency risk?", "Explain how a nowcast differs from a forecast."],
)
def test_substrings_of_time_words_do_not_force_verified_facts(question):
    assert not requires_verified_market_facts(question, "en", "latin")


# ------------------------------------------------------------------ pipeline


class FakeExpert:
    provider_name = "fake-gemini"
    model = "gemini-3.5-flash"

    def __init__(self, response):
        self.response = response
        self.calls: list[bool] = []

    def generate(self, question, system_prompt, *, use_web_grounding=False):
        self.calls.append(use_web_grounding)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeRag:
    def __init__(self, insufficient: bool):
        self.insufficient = insufficient
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Sources insuffisantes." if self.insufficient else "Réponse du corpus approuvé.",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="insufficient_evidence" if self.insufficient else "ok",
            grounded=not self.insufficient,
            insufficient_evidence=self.insufficient,
            provider_retryable=False,
        )


@pytest.fixture(autouse=True)
def offline_localizer(monkeypatch):
    monkeypatch.setattr(
        chat_api,
        "localize_business_answer",
        lambda answer, language, script, localizer: SimpleNamespace(
            status="ok",
            answer=answer,
            provider="test",
            retry_count=0,
            guard_result="accepted",
        ),
    )


def run(question, *, route="pedagogie", rag=None, expert=None, thread="t-general"):
    rag = rag or FakeRag(insufficient=True)
    expert = expert or FakeExpert(
        FinancialExpertGeneration(
            text=LOCALIZED_TEXT[("fr", "latin")], web_grounded=True, web_sources=APPROVED
        )
    )
    graph = build_graph(
        supervisor_provider=SimpleNamespace(
            invoke_structured=lambda request: {
                "domain_status": "out_of_domain" if route == "out_of_domain" else "in_domain",
                "route": route,
            }
        ),
        grounded_service=rag,
        financial_expert_service=FinancialExpertService(expert, web_grounding_enabled=True),
        financial_expert_fallback_enabled=True,
    )
    response = process_text_message(ChatRequest(message=question, thread_id=thread), graph)
    return response, rag, expert


@pytest.mark.parametrize("question", CURRENT + DATED)
def test_current_and_dated_values_go_to_approved_external_research(question):
    response, rag, expert = run(question, rag=FakeRag(insufficient=False))
    # The static corpus cannot hold live values: RAG is bypassed even if it "has" text.
    assert rag.calls == 0
    assert expert.calls == [True]
    assert response.status == "ok"
    assert response.knowledge_source == "llm_web_grounded_financial_knowledge"
    assert [s.uri for s in response.web_sources] == ["https://www.casablanca-bourse.com/x"]


@pytest.mark.parametrize("question", EVENTS + LISTING)
def test_events_and_listing_use_web_research_when_rag_is_insufficient(question):
    response, rag, expert = run(question, rag=FakeRag(insufficient=True))
    assert rag.calls == 1
    assert expert.calls == [True]
    assert response.knowledge_source == "llm_web_grounded_financial_knowledge"


@pytest.mark.parametrize("question", EVENTS + LISTING)
def test_events_answered_by_the_corpus_do_not_search(question):
    response, rag, expert = run(question, rag=FakeRag(insufficient=False))
    assert rag.calls == 1 and expert.calls == []
    assert response.knowledge_source == "rag"


@pytest.mark.parametrize("question", STABLE)
def test_stable_educational_questions_never_search(question):
    response, rag, expert = run(question, rag=FakeRag(insufficient=False))
    assert rag.calls == 1 and expert.calls == []
    assert response.knowledge_source == "rag"


def test_stable_question_with_missing_evidence_may_use_general_explanation_but_not_web():
    expert = FakeExpert(FinancialExpertGeneration(text="Un dividende est une distribution."))
    response, _, _ = run("Comment fonctionne un dividende ?", expert=expert)
    assert expert.calls == [False]
    assert response.knowledge_source == "llm_general_financial_knowledge"


def test_listing_status_never_falls_back_to_unsupported_model_memory():
    # Search returns nothing verifiable: the model's own belief must not be served.
    expert = FakeExpert(FinancialExpertGeneration(text="Oui, SGTM est cotée depuis 2025."))
    response, _, _ = run("SGTM est-elle cotée en bourse ?", expert=expert)
    assert expert.calls == [True]
    assert response.knowledge_source == "controlled_current_data_limitation"
    assert "2025" not in response.answer


def test_unapproved_source_is_rejected_for_any_entity():
    expert = FakeExpert(
        FinancialExpertGeneration(
            text="Le cours de Label Vie est de 4 200 MAD.",
            web_grounded=True,
            web_sources=({"domain": "some-forum.example"},),
        )
    )
    response, _, _ = run("variation de Label Vie aujourd'hui", expert=expert)
    assert response.knowledge_source == "controlled_current_data_limitation"
    assert "4 200" not in response.answer and response.web_sources == []


def test_quota_exhaustion_fails_closed():
    expert = FakeExpert(RuntimeError("429 RESOURCE_EXHAUSTED"))
    response, _, _ = run("cours IAM aujourd'hui", expert=expert)
    assert expert.calls == [True]
    assert response.status == "ok"
    assert response.knowledge_source == "controlled_current_data_limitation"
    assert response.web_sources == []


@pytest.mark.parametrize(
    "question",
    ["Quelle action dois-je acheter ?", "Quel est le meilleur investissement pour moi ?"],
)
def test_security_is_never_bypassed_by_external_research(question):
    response, rag, expert = run(question)
    assert response.route == "securite" and response.blocked is True
    assert expert.calls == [] and rag.calls == 0


@pytest.mark.parametrize(
    "question",
    ["Donne-moi une recette de pizza", "Qui a gagné le match hier ?", "Quel téléphone acheter ?"],
)
def test_out_of_domain_is_never_researched(question):
    response, rag, expert = run(question, route="out_of_domain")
    # "acheter" can already be caught by the security guard first: both are safe.
    assert response.route in {"out_of_domain", "securite"}
    assert expert.calls == [] and rag.calls == 0
    assert response.knowledge_source is None


@pytest.mark.parametrize(("question", "language"), MULTILINGUAL_CURRENT)
def test_same_mechanism_for_every_business_language(question, language):
    response_probe, _, _ = run(question, expert=FakeExpert(RuntimeError("probe")))
    key = (response_probe.language, response_probe.script)
    expert = FakeExpert(
        FinancialExpertGeneration(text=LOCALIZED_TEXT[key], web_grounded=True, web_sources=APPROVED)
    )
    response, rag, _ = run(question, expert=expert, rag=FakeRag(insufficient=False))
    assert response.language == language
    assert rag.calls == 0 and expert.calls == [True]
    assert response.knowledge_source == "llm_web_grounded_financial_knowledge"


class GroundingErrorRag(FakeRag):
    def generate(self, request):
        self.calls += 1
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="grounding_error",
            grounded=False,
            insufficient_evidence=False,
            provider_retryable=False,
        )


@pytest.mark.parametrize("question", CURRENT + DATED + EVENTS + LISTING)
def test_supervisor_out_of_domain_label_cannot_drop_a_market_fact_question(question):
    # Live regression: the LLM Supervisor labelled "cours IAM aujourd'hui" out_of_domain.
    response, _, expert = run(question, route="out_of_domain", rag=FakeRag(insufficient=True))
    assert response.route == "pedagogie"
    assert expert.calls == [True]


@pytest.mark.parametrize("question", EVENTS + LISTING)
def test_grounding_error_on_a_market_fact_goes_to_external_research(question):
    # Live regression: dividend/IPO questions returned grounding_error, not insufficiency.
    response, rag, expert = run(question, rag=GroundingErrorRag(insufficient=True))
    assert rag.calls == 1 and expert.calls == [True]
    assert response.status == "ok"
    assert response.knowledge_source == "llm_web_grounded_financial_knowledge"


def test_grounding_error_on_a_stable_question_keeps_the_safe_failure():
    expert = FakeExpert(FinancialExpertGeneration(text="must not run"))
    response, _, _ = run("Comment fonctionne le MASI ?", rag=GroundingErrorRag(True), expert=expert)
    assert expert.calls == []
    assert response.knowledge_source is None
