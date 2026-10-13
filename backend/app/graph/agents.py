from __future__ import annotations

import logging

from app.championnat.agent import championnat_agent as run_championnat_agent
from app.cisi.agent import cisi_agent as run_cisi_agent
from app.financial_expert.freshness import (
    requires_live_market_data,
    requires_verified_market_facts,
)
from app.financial_expert.models import FinancialExpertRequest
from app.financial_expert.service import FinancialExpertService
from app.formation.agent import run_formation_agent
from app.graph.catalog import TrainingCatalog
from app.graph.response_localizer import business_answer_locale
from app.graph.state import GraphState
from app.graph.workflows import formation_workflow
from app.memory.shared_context import AgentMemoryContext
from app.observability.logging import emit
from app.observability.timing import elapsed_ms, start_timer
from app.orientation.agent import run_orientation_agent
from app.out_of_domain.agent import out_of_domain_agent as run_out_of_domain_agent
from app.quiz.agent import run_quiz_agent
from app.rag.grounded_generation import (
    GroundedGenerationRequest,
    GroundedGenerationService,
    safe_grounding_failure_message,
)
from app.support_ecole.agent import support_ecole_agent as run_support_ecole_agent

logger = logging.getLogger(__name__)


def _external_financial_research(
    state: GraphState,
    financial_expert_service: FinancialExpertService,
    memory_context: AgentMemoryContext | None,
    grounded_status: str,
) -> GraphState:
    """Approved external research after security and Supervisor; fail closed."""
    language = state.get("language", "fr")
    script = state.get("script", "latin")
    expert_started = start_timer()
    try:
        expert_result = financial_expert_service.answer(
            FinancialExpertRequest(
                question=state.get("user_input", ""),
                language=language,
                script=script,
                memory_context=memory_context.projection if memory_context else None,
            )
        )
    except Exception as exc:
        emit(
            "financial_expert.failed",
            level=logging.ERROR,
            duration_ms=elapsed_ms(expert_started),
            error_type=type(exc).__name__,
            stage="financial_expert",
        )
        logger.error("financial expert fallback failed error_type=%s", type(exc).__name__)
        return {
            "business_answer": safe_grounding_failure_message(language, script),
            "response_key": "pedagogie",
            "grounded_status": grounded_status,
            "grounded_citations": [],
            "grounded": False,
            "knowledge_source": "provider_unavailable",
            "web_grounded": False,
            "web_sources": [],
            "error": None,
            "status": "completed",
        }
    emit(
        "financial_expert.completed",
        duration_ms=elapsed_ms(expert_started),
        mode=("web_grounded" if expert_result.web_grounded else "general"),
        grounded=expert_result.web_grounded,
    )
    return {
        "business_answer": expert_result.answer,
        "response_key": "pedagogie",
        "grounded_status": grounded_status,
        "grounded_citations": [],
        "grounded": False,
        "knowledge_source": expert_result.knowledge_source,
        "web_grounded": expert_result.web_grounded,
        "web_sources": [source.model_dump() for source in expert_result.web_sources],
        "web_search_entry_point": expert_result.web_search_entry_point,
        "error": None,
        "status": "completed",
    }


def pedagogie_agent(
    state: GraphState,
    grounded_service: GroundedGenerationService | None = None,
    financial_expert_service: FinancialExpertService | None = None,
    financial_expert_fallback_enabled: bool = False,
    memory_context: AgentMemoryContext | None = None,
) -> GraphState:
    if grounded_service is None:
        return {
            "business_answer": (
                "Je peux expliquer les actions, obligations, indices, ordres et "
                "concepts de marché à visée éducative."
            ),
            "response_key": "pedagogie",
            "status": "completed",
        }
    if grounded_service is not None:
        language = state.get("language", "fr")
        script = state.get("script", "latin")
        # Darija is written after grounding: the business answer is generated in
        # a pivot language, then localized once at the chat boundary.
        answer_language, answer_script = business_answer_locale(language, script)
        if (
            financial_expert_fallback_enabled
            and financial_expert_service
            and requires_live_market_data(state.get("user_input", ""))
        ):
            # A current or dated market value can never be in the static corpus:
            # go straight to approved external research (or its limitation).
            return _external_financial_research(
                state, financial_expert_service, memory_context, "external_research"
            )
        rag_started = start_timer()
        try:
            result = grounded_service.generate(
                GroundedGenerationRequest(
                    original_query=state.get("user_input", ""),
                    language=language,
                    script=script,
                    memory_context=memory_context.projection if memory_context else None,
                    answer_language=answer_language,
                    answer_script=answer_script,
                )
            )
        except Exception as exc:
            emit(
                "rag.failed",
                level=logging.ERROR,
                duration_ms=elapsed_ms(rag_started),
                error_type=type(exc).__name__,
                stage="rag",
            )
            raise
        emit(
            "rag.completed",
            duration_ms=elapsed_ms(rag_started),
            generation_status=result.generation_status,
            grounded=result.generation_status == "ok" and bool(result.answer),
            citation_count=len(result.citations),
            insufficient_evidence=result.insufficient_evidence,
        )
        citations = [citation.model_dump() for citation in result.citations]
        if result.generation_status == "ok" and result.answer:
            return {
                "business_answer": result.answer,
                "response_key": "pedagogie",
                "grounded_answer": result.answer,
                "grounded_status": result.generation_status,
                "grounded_citations": citations,
                "grounded": True,
                "knowledge_source": "rag",
                "web_grounded": False,
                "web_sources": [],
                # Bounded observability only; never part of the chat API contract.
                "retrieval_query": (getattr(result, "retrieval_query", None) or "")[:300],
                "status": "completed",
            }
        if (
            financial_expert_fallback_enabled
            and financial_expert_service
            and not getattr(result, "comparison_incomplete", False)
            and (
                result.insufficient_evidence
                # A verifiable market fact the corpus could not ground (e.g. a
                # grounding_error) is researched externally, never left unsupported.
                or requires_verified_market_facts(state.get("user_input", ""), language, script)
            )
        ):
            return _external_financial_research(
                state,
                financial_expert_service,
                memory_context,
                # Chat keeps insufficient_evidence; any other corpus failure is
                # reported as external research so a sourced answer is not an error.
                result.generation_status if result.insufficient_evidence else "external_research",
            )
        answer = result.answer or safe_grounding_failure_message(language, script)
        return {
            "business_answer": answer,
            "response_key": "pedagogie",
            "grounded_status": result.generation_status,
            "grounded_citations": citations,
            "grounded": False,
            "knowledge_source": "rag",
            "web_grounded": False,
            "web_sources": [],
            "error": None,
            "status": "completed",
        }
    return {
        "business_answer": (
            "Je peux expliquer les actions, obligations, indices, ordres et "
            "concepts de marchÃ© Ã  visÃ©e Ã©ducative."
        ),
        "response_key": "pedagogie",
        "status": "completed",
    }


def formation_agent(
    state: GraphState,
    catalog: TrainingCatalog | None = None,
    profile_service=None,
    memory_context: AgentMemoryContext | None = None,
) -> GraphState:
    if profile_service is not None:
        # Preserve the established assessment/catalog state contract for legacy
        # callers that explicitly provide assessment results.
        if (
            "language" not in state
            or state.get("assessment_answers")
            or (state.get("assessment_completed") and state.get("assessment_level"))
        ):
            return formation_workflow(state, catalog) | {"status": "completed"}
        return run_formation_agent(state, profile_service)
    return formation_workflow(state, catalog) | {"status": "completed"}


def cisi_agent(state: GraphState, memory_context: AgentMemoryContext | None = None) -> GraphState:
    result = run_cisi_agent(state)
    text = state.get("normalized_message") or state.get("user_input", "")
    delegated = state.get("selected_route") == "formation_elearning" or (
        "formation" in text.casefold()
        and any(term in text.casefold() for term in ("cisi", "certification"))
    )
    updates: GraphState = {"selected_route": "cisi", "cisi_delegated": delegated}
    return result | updates


def quiz_agent(
    state: GraphState,
    profile_service=None,
    memory_context: AgentMemoryContext | None = None,
) -> GraphState:
    return run_quiz_agent(state, profile_service)


def championnat_agent(
    state: GraphState, memory_context: AgentMemoryContext | None = None
) -> GraphState:
    return run_championnat_agent(state)


def orientation_agent(
    state: GraphState,
    profile_service=None,
    memory_context: AgentMemoryContext | None = None,
) -> GraphState:
    return run_orientation_agent(state, profile_service)


def support_ecole_agent(
    state: GraphState, memory_context: AgentMemoryContext | None = None
) -> GraphState:
    return run_support_ecole_agent(state)


def securite_agent(state: GraphState) -> GraphState:
    return {
        "security_status": "sensitive",
        "response_status": "blocked",
        "risk_level": "high",
        "business_answer": (
            "Je ne peux pas choisir un titre, recommander une vente ou répartir votre "
            "argent. Je peux expliquer des critères généraux d'analyse financière."
        ),
        "response_key": "securite",
        "status": "completed",
    }


def out_of_domain_agent(state: GraphState) -> GraphState:
    return run_out_of_domain_agent(state)


def fallback_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je n'ai pas compris la demande. Je peux aider sur la Bourse, l'éducation "
            "financière, les formations et les services associés."
        ),
        "response_key": "fallback",
        "status": "completed",
    }
