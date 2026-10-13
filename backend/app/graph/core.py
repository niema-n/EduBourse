from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.financial_expert.freshness import market_fact_intent
from app.graph.agents import (
    championnat_agent,
    cisi_agent,
    fallback_agent,
    formation_agent,
    orientation_agent,
    out_of_domain_agent,
    pedagogie_agent,
    quiz_agent,
    securite_agent,
    support_ecole_agent,
)
from app.graph.catalog import TrainingCatalog
from app.graph.conversation_context import append_recent_turn, render_recent_turns
from app.graph.intent import (
    MissingRouterArtifact,
    MissingSecurityArtifact,
    route_decision,
    security_decision,
)
from app.graph.routing import is_in_domain, route_request
from app.graph.state import GraphState, Route, safe_thread_id
from app.graph.supervisor import SupervisorRequest, parse_route_decision
from app.graph.workflow_context import ConversationWorkflowContext, WorkflowContextService
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.memory.shared_context import (
    AgentMemoryContext,
    SharedMemoryRuntime,
    clear_current_memory_context,
    current_memory_context,
    empty_memory_context,
    render_memory_prompt,
    set_current_memory_context,
)
from app.observability.logging import emit, thread_ref
from app.observability.timing import elapsed_ms, start_timer
from app.persistence.checkpointer import create_graph_checkpointer
from app.persistence.database import PersistenceDatabase
from app.persistence.learning_profile_store import SqlAlchemyLearningProfileStore
from app.persistence.thread_store import ConversationThreadStore

SUPPORTED_ROUTES: tuple[Route, ...] = (
    "pedagogie",
    "formation_elearning",
    "cisi",
    "quiz",
    "championnat",
    "orientation",
    "support_ecole",
    "securite",
    "out_of_domain",
    "fallback",
)


def create_learning_profile_service() -> LearningProfileService:
    """Create the one shared profile service at the application composition seam."""
    settings = get_settings()
    if not settings.persistence_enabled:
        return LearningProfileService(InMemoryLearningProfileStore())
    database = PersistenceDatabase(settings=settings)
    thread_store = ConversationThreadStore(database)
    profile_store = SqlAlchemyLearningProfileStore(database, thread_store)
    return LearningProfileService(profile_store)


def security_guard_node(state: GraphState) -> GraphState:
    clear_current_memory_context()
    text = state.get("user_input", "")
    try:
        sensitive, confidence, scores, source = security_decision(text)
    except MissingSecurityArtifact:
        return {
            "security_status": "sensitive",
            "risk_level": "high",
            "selected_route": "securite",
            "security_confidence": 1.0,
            "security_source": "missing_artifact_fail_closed",
            "status": "secured",
        }
    if sensitive:
        context = state.get("workflow_context")
        if isinstance(context, dict):
            context = ConversationWorkflowContext.model_validate(context)
        paused = (
            {"quiz_session": state["quiz_session"].model_copy(update={"phase": "paused"})}
            if context is not None
            and context.active_agent in {"quiz", "formation_elearning"}
            and state.get("quiz_session") is not None
            else {}
        )
        if (
            context is not None
            and context.active_agent == "formation_elearning"
            and state.get("formation_session") is not None
        ):
            paused = {
                "formation_session": state["formation_session"].model_copy(
                    update={"status": "paused"}
                )
            }
        return {
            "security_status": "sensitive",
            "risk_level": "high",
            "selected_route": "securite",
            "security_confidence": confidence,
            "security_scores": scores,
            "security_source": source,
            "status": "secured",
            **paused,
            **(
                {"workflow_context": WorkflowContextService().pause_workflow(context)}
                if context is not None
                and context.active_agent in {"quiz", "formation_elearning"}
                and (
                    state.get("quiz_session") is not None
                    or state.get("formation_session") is not None
                )
                else {}
            ),
        }
    return {
        "security_status": "clear",
        "risk_level": "none",
        "security_confidence": confidence,
        "security_scores": scores,
        "security_source": source,
        "status": "secured",
    }


def _ambiguous_decision_as_fallback(payload: object) -> object:
    """Keep an ambiguous request on the controlled fallback path.

    The routing prompt asks for route=fallback on ambiguity, but providers
    sometimes pair it with domain_status=out_of_domain, which the strict
    contract rejects and turns into an error. Only that exact two-field pairing
    is normalised, and only towards fallback, never towards a business route.
    Every other malformed output still fails closed.
    """
    if (
        isinstance(payload, dict)
        and set(payload) == {"domain_status", "route"}
        and payload["route"] == "fallback"
        and payload["domain_status"] == "out_of_domain"
    ):
        return {"domain_status": "in_domain", "route": "fallback"}
    return payload


def _market_fact_domain_rescue(text: str, domain_status: str, route: str) -> tuple[str, str]:
    """Keep verifiable market-fact questions inside EduBourse.

    The LLM Supervisor may label "cours IAM aujourd'hui" as out of domain (an
    unknown ticker, "cours" read as a lesson). A deterministic market-fact
    intent (value + time, dated value, corporate event, listing status) is by
    definition Bourse domain, so it goes to the pedagogie route where RAG and
    approved external research apply. Runs after the security guard: blocked
    requests never reach the router, and questions without such intent keep the
    Supervisor decision.
    """
    if route in {"out_of_domain", "fallback"} and market_fact_intent(text) is not None:
        return "in_domain", "pedagogie"
    return domain_status, route


def _supervisor_error_fields(exc: Exception) -> dict[str, object]:
    """Extract bounded provider diagnostics without logging payloads or secrets."""
    response = getattr(exc, "response", None)
    status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
    code = getattr(exc, "code", None)
    body = getattr(exc, "body", None)
    if code is None and isinstance(body, dict):
        code = body.get("code") or body.get("error", {}).get("code")
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    message = re.sub(
        r"(?i)(authorization|api[_ -]?key|token)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        message,
    )
    message = re.sub(r"https?://\S+", "[url-redacted]", message)
    return {
        "exception_type": type(exc).__name__,
        "error_message_sanitized": message[:500],
        "http_status": status,
        "provider_error_code": code,
    }


def router_node(state: GraphState, supervisor_provider: Any | None = None) -> GraphState:
    text = state.get("user_input", "")
    context = state.get("workflow_context")
    if isinstance(context, dict):
        context = ConversationWorkflowContext.model_validate(context)
    continuation = WorkflowContextService().resolve_continuation(context, text)
    if continuation.is_continuation:
        return {
            "domain_status": "in_domain",
            "selected_route": continuation.route,
            "route_confidence": 1.0,
            "route_scores": {},
            "workflow_context": WorkflowContextService().record_continuation(context),
        }
    if supervisor_provider is not None:
        try:
            request = SupervisorRequest(
                user_message=state.get("normalized_message", text),
                business_language=state.get("language", "fr"),
                script=state.get("script", "latin"),
                workflow_context=(
                    render_memory_prompt(current_memory_context())
                    or render_recent_turns(state.get("recent_turns"))
                ),
            )
            supervisor_started = start_timer()
            try:
                raw_decision = supervisor_provider.invoke_structured(request)
            finally:
                # Internal timing log only: duration and SDK retry count, no content.
                emit(
                    "supervisor.provider.completed",
                    duration_ms=elapsed_ms(supervisor_started),
                    retries_taken=getattr(supervisor_provider, "last_retries_taken", None),
                    stage="supervisor",
                )
            decision = parse_route_decision(_ambiguous_decision_as_fallback(raw_decision))
            domain_status, selected_route = _market_fact_domain_rescue(
                text, decision.domain_status, decision.route
            )
            updates = {
                "domain_status": domain_status,
                "selected_route": selected_route,
                "route_confidence": 1.0,
                "route_scores": {},
            }
            if (
                context is not None
                and context.active_agent == "quiz"
                and state.get("quiz_session") is not None
                and decision.route != "quiz"
            ):
                updates["workflow_context"] = WorkflowContextService().pause_workflow(context)
                updates["quiz_session"] = state["quiz_session"].model_copy(
                    update={"phase": "paused"}
                )
            if (
                context is not None
                and context.active_agent == "formation_elearning"
                and state.get("formation_session") is not None
                and decision.route != "formation_elearning"
            ):
                updates["workflow_context"] = WorkflowContextService().pause_workflow(context)
                updates["formation_session"] = state["formation_session"].model_copy(
                    update={"status": "paused"}
                )
            return updates
        except Exception as exc:
            emit(
                "supervisor.failed",
                level=logging.WARNING,
                **_supervisor_error_fields(exc),
                retries_taken=getattr(supervisor_provider, "last_retries_taken", None),
                language=state.get("language", "fr"),
                script=state.get("script", "latin"),
                thread_ref=thread_ref(state.get("thread_id")),
                stage="supervisor",
            )
            return {
                "domain_status": "unknown",
                "selected_route": "fallback",
                "route_confidence": 0.0,
                "route_scores": {},
                "error": "supervisor_failure",
                "status": "error",
            }
    try:
        route, confidence, scores = route_decision(text)
    except MissingRouterArtifact:
        return {
            "domain_status": "unknown",
            "selected_route": "fallback",
            "route_confidence": 0.0,
            "route_scores": {},
            "error": "router_artifact_unavailable",
        }
    if confidence < 0.50:
        # The ML model remains primary; this narrow contract tie-break only
        # resolves low-confidence legacy phrasing and preserves true fallback.
        route = route_request(text) if is_in_domain(text) else "out_of_domain"
    domain_status, route = _market_fact_domain_rescue(
        text, "in_domain" if route != "out_of_domain" else "out_of_domain", route
    )
    return {
        "domain_status": domain_status,
        "selected_route": route,
        "route_confidence": confidence,
        "route_scores": scores,
    }


def route_after_security(state: GraphState) -> str:
    return "securite" if state.get("security_status") == "sensitive" else "memory"


def memory_context_node(
    state: GraphState, memory_runtime: SharedMemoryRuntime | None = None
) -> GraphState:
    thread_id = safe_thread_id(state.get("thread_id"))
    started = start_timer()
    if memory_runtime is None:
        context = empty_memory_context(thread_id)
    else:
        context = memory_runtime.resolve(thread_id, state.get("user_input", ""))
    emit(
        "memory.context.completed",
        duration_ms=elapsed_ms(started),
        memory_status=context.status,
        recent_turns=len(getattr(context.recent, "turns", ()) or ()),
        stage="memory_read",
    )
    set_current_memory_context(context)
    return {
        "memory_status": context.status,
        "memory_relevant_message_ids": list(context.relevant_message_ids),
    }


def _rehydrate_memory(state: GraphState, memory_runtime: SharedMemoryRuntime | None = None):
    if memory_runtime is None:
        return
    started = start_timer()
    context = memory_runtime.rehydrate(
        safe_thread_id(state.get("thread_id")),
        state.get("memory_relevant_message_ids", []),
        state.get("memory_status", "unavailable"),
    )
    emit("memory.rehydrate.completed", duration_ms=elapsed_ms(started), stage="memory_read")
    set_current_memory_context(context)


def route_to_agent(state: GraphState) -> str:
    route = state.get("selected_route", "fallback")
    return route if route in SUPPORTED_ROUTES else "fallback"


def route_after_orientation(state: GraphState) -> str:
    recommendation = state.get("orientation_recommendation")
    if state.get("assessment_required") and getattr(recommendation, "needs_diagnostic", False):
        return "quiz"
    return "output_guard"


def route_after_formation(state: GraphState) -> str:
    text = state.get("normalized_message", state.get("user_input", "")).casefold()
    if any(keyword in text for keyword in ("cisi", "certification", "compliance")):
        return "cisi"
    formation_session = state.get("formation_session")
    if (
        formation_session is not None
        and getattr(formation_session, "status", None) == "waiting_for_diagnostic"
    ):
        return "quiz"
    return "output_guard"


def observed_node(node: Callable[[GraphState], dict[str, Any]], event: str, name: str):
    """Observe one real graph node without changing its result or errors."""

    def wrapped(state: GraphState) -> dict[str, Any]:
        started = start_timer()
        try:
            result = node(state)
        except Exception as exc:
            emit(
                f"{event}.failed",
                level=40,
                duration_ms=elapsed_ms(started),
                error_type=type(exc).__name__,
                stage=name,
            )
            raise
        fields = {
            "duration_ms": elapsed_ms(started),
            "route": result.get("selected_route", name),
        }
        if event == "security":
            fields.update(
                security_status=result.get("security_status"),
                risk_level=result.get("risk_level"),
            )
        elif event == "routing":
            fields["confidence"] = result.get("route_confidence")
        else:
            fields["response_status"] = result.get("status")
        emit(f"{event}.completed", **fields)
        return result

    return wrapped


def _output_guard_decision(state: GraphState) -> GraphState:
    route = state.get("selected_route", "fallback")
    if route not in SUPPORTED_ROUTES:
        return {
            "selected_route": "fallback",
            "business_answer": "Une réponse contrôlée n'est pas disponible pour cette demande.",
            "status": "completed",
            "error": None,
        }
    if state.get("error"):
        return {
            "selected_route": "fallback",
            "business_answer": (
                "Une erreur contrôlée est survenue; veuillez reformuler votre demande."
            ),
            "status": "error",
            "error": "agent_failure_handled",
        }
    if state.get("security_status") == "sensitive" and route != "securite":
        return {
            "selected_route": "securite",
            "security_status": "sensitive",
            "business_answer": (
                "Je ne peux pas fournir une recommandation financière personnalisée."
            ),
            "status": "completed",
            "error": None,
        }
    if not state.get("business_answer", "").strip():
        return {
            "selected_route": "fallback",
            "business_answer": "Une réponse contrôlée n'est pas disponible pour cette demande.",
            "status": "completed",
            "error": None,
        }
    return {"status": "completed", "error": None}


# A generic fallback answered no financial question, so it must never carry
# grounding metadata. This guards only the fallback path; every other route
# keeps whatever evidence it legitimately produced.
_FALLBACK_GROUNDING_RESET: dict[str, Any] = {
    "grounded_answer": "",
    "grounded_status": "",
    "grounded_citations": [],
    "grounded": False,
    "knowledge_source": "",
    "web_grounded": False,
    "web_sources": [],
    "retrieval_query": "",
}


def output_guard(state: GraphState) -> GraphState:
    result = _output_guard_decision(state)
    route = result.get("selected_route", state.get("selected_route", "fallback"))
    if route == "fallback":
        result.update(_FALLBACK_GROUNDING_RESET)
    answer = result.get("business_answer", state.get("business_answer", ""))
    result["recent_turns"] = append_recent_turn(state, answer, route)
    return result


def safe_node(node: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    def wrapped(state: GraphState) -> dict[str, Any]:
        try:
            return node(state)
        except Exception:
            return {
                "error": "agent_failure",
                "status": "error",
                "business_answer": (
                    "Une erreur contrôlée est survenue; veuillez reformuler votre demande."
                ),
            }

    return wrapped


def _call_agent(agent, state: GraphState, args: tuple[Any, ...], memory: AgentMemoryContext):
    parameters = inspect.signature(agent).parameters
    if "memory_context" in parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    ):
        return agent(state, *args, memory_context=memory)
    return agent(state, *args)


def build_graph(
    *,
    checkpointer: Any | None = None,
    training_catalog: TrainingCatalog | None = None,
    supervisor_provider: Any | None = None,
    grounded_service: Any | None = None,
    financial_expert_service: Any | None = None,
    financial_expert_fallback_enabled: bool = False,
    learning_profile_service: LearningProfileService | None = None,
    memory_runtime: SharedMemoryRuntime | None = None,
):
    profile_service = learning_profile_service or create_learning_profile_service()
    graph = StateGraph(GraphState)
    graph.add_node(
        "security_guard", observed_node(safe_node(security_guard_node), "security", "security")
    )
    graph.add_node(
        "router",
        observed_node(
            safe_node(
                lambda state: (
                    _rehydrate_memory(state, memory_runtime),
                    router_node(state, supervisor_provider),
                )[1]
            ),
            "routing",
            "router",
        ),
    )
    graph.add_node(
        "memory_context",
        safe_node(lambda state: memory_context_node(state, memory_runtime)),
    )

    def agent_node(agent, *args):
        def wrapped(state: GraphState) -> GraphState:
            context_started = start_timer()
            memory = (
                memory_runtime.agent_context(state)
                if memory_runtime is not None
                else AgentMemoryContext(None, ())
            )
            if memory_runtime is not None:
                emit(
                    "memory.agent_context.completed",
                    duration_ms=elapsed_ms(context_started),
                    stage="memory_read",
                )
            return _call_agent(agent, state, args, memory)

        return safe_node(wrapped)

    def pedagogie_node(
        state: GraphState, memory_context: AgentMemoryContext | None = None
    ) -> GraphState:
        if memory_context is None or memory_context.projection is None:
            # Same fallback source as the Supervisor: without a persistence
            # projection, follow-ups resolve against the bounded thread window.
            window = render_recent_turns(state.get("recent_turns"))
            if window is not None:
                memory_context = AgentMemoryContext(window, ())
        if (
            grounded_service is None
            and financial_expert_service is None
            and not financial_expert_fallback_enabled
        ):
            return _call_agent(pedagogie_agent, state, (), memory_context)
        return _call_agent(
            pedagogie_agent,
            state,
            (
                grounded_service,
                financial_expert_service,
                financial_expert_fallback_enabled,
            ),
            memory_context,
        )

    graph.add_node("pedagogie", observed_node(agent_node(pedagogie_node), "agent", "pedagogie"))
    graph.add_node(
        "formation_elearning",
        observed_node(
            agent_node(formation_agent, training_catalog, profile_service),
            "agent",
            "formation_elearning",
        ),
    )
    graph.add_node("cisi", observed_node(agent_node(cisi_agent), "agent", "cisi"))
    graph.add_node(
        "quiz",
        observed_node(agent_node(quiz_agent, profile_service), "agent", "quiz"),
    )
    graph.add_node(
        "championnat", observed_node(agent_node(championnat_agent), "agent", "championnat")
    )
    graph.add_node(
        "orientation",
        observed_node(
            agent_node(orientation_agent, profile_service),
            "agent",
            "orientation",
        ),
    )
    graph.add_node(
        "support_ecole",
        observed_node(agent_node(support_ecole_agent), "agent", "support_ecole"),
    )
    graph.add_node("securite", observed_node(safe_node(securite_agent), "agent", "securite"))
    graph.add_node(
        "out_of_domain",
        observed_node(safe_node(out_of_domain_agent), "agent", "out_of_domain"),
    )
    graph.add_node("fallback", observed_node(safe_node(fallback_agent), "agent", "fallback"))
    graph.add_node("output_guard", safe_node(output_guard))
    graph.add_edge(START, "security_guard")
    graph.add_conditional_edges(
        "security_guard",
        route_after_security,
        {"securite": "securite", "memory": "memory_context"},
    )
    graph.add_edge("memory_context", "router")
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {route: route for route in SUPPORTED_ROUTES if route != "securite"},
    )
    for route in SUPPORTED_ROUTES:
        if route not in {"formation_elearning", "orientation"}:
            graph.add_edge(route, "output_guard")
    graph.add_conditional_edges(
        "orientation",
        route_after_orientation,
        {"quiz": "quiz", "output_guard": "output_guard"},
    )
    graph.add_conditional_edges(
        "formation_elearning",
        route_after_formation,
        {"cisi": "cisi", "quiz": "quiz", "output_guard": "output_guard"},
    )
    graph.add_edge("output_guard", END)
    selected_checkpointer = (
        checkpointer if checkpointer is not None else create_graph_checkpointer(get_settings())
    )
    return graph.compile(checkpointer=selected_checkpointer)


def invoke_graph(graph: Any, state: GraphState, *, thread_id: str | None = None) -> GraphState:
    """Application boundary that never exposes LangGraph's missing-thread error."""
    selected_thread = safe_thread_id(thread_id or state.get("thread_id"))
    try:
        return graph.invoke(state, config={"configurable": {"thread_id": selected_thread}})
    except ValueError:
        return {
            **state,
            "selected_route": "fallback",
            "status": "error",
            "error": "invalid_graph_invocation",
            "business_answer": "La demande ne peut pas être traitée dans cette session.",
        }
