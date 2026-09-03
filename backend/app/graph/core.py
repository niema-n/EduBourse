from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

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
from app.graph.intent import (
    MissingRouterArtifact,
    MissingSecurityArtifact,
    route_decision,
    security_decision,
)
from app.graph.routing import is_in_domain, route_request
from app.graph.state import GraphState, Route, safe_thread_id
from app.graph.supervisor import SupervisorRequest, parse_route_decision

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


def security_guard_node(state: GraphState) -> GraphState:
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
        return {
            "security_status": "sensitive",
            "risk_level": "high",
            "selected_route": "securite",
            "security_confidence": confidence,
            "security_scores": scores,
            "security_source": source,
            "status": "secured",
        }
    return {
        "security_status": "clear",
        "risk_level": "none",
        "security_confidence": confidence,
        "security_scores": scores,
        "security_source": source,
        "status": "secured",
    }


def router_node(state: GraphState, supervisor_provider: Any | None = None) -> GraphState:
    text = state.get("user_input", "")
    if supervisor_provider is not None:
        try:
            request = SupervisorRequest(
                user_message=state.get("normalized_message", text),
                business_language=state.get("language", "fr"),
                script=state.get("script", "latin"),
            )
            decision = parse_route_decision(supervisor_provider.invoke_structured(request))
            return {
                "domain_status": decision.domain_status,
                "selected_route": decision.route,
                "route_confidence": 1.0,
                "route_scores": {},
            }
        except Exception:
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
    return {
        "domain_status": "in_domain" if route != "out_of_domain" else "out_of_domain",
        "selected_route": route,
        "route_confidence": confidence,
        "route_scores": scores,
    }


def route_after_security(state: GraphState) -> str:
    return "securite" if state.get("security_status") == "sensitive" else "router"


def route_to_agent(state: GraphState) -> str:
    route = state.get("selected_route", "fallback")
    return route if route in SUPPORTED_ROUTES else "fallback"


def route_after_formation(state: GraphState) -> str:
    text = state.get("normalized_message", state.get("user_input", "")).casefold()
    return (
        "cisi"
        if any(keyword in text for keyword in ("cisi", "certification", "compliance"))
        else "output_guard"
    )


def output_guard(state: GraphState) -> GraphState:
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
    if route != "securite":
        try:
            sensitive, _, _, _ = security_decision(state.get("user_input", ""))
        except MissingSecurityArtifact:
            sensitive = True
        if sensitive:
            return {
                "selected_route": "securite",
                "security_status": "sensitive",
                "business_answer": (
                    "Je ne peux pas fournir une recommandation financiere personnalisee."
                ),
                "status": "completed",
                "error": None,
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


def build_graph(
    *,
    checkpointer: Any | None = None,
    training_catalog: TrainingCatalog | None = None,
    supervisor_provider: Any | None = None,
):
    graph = StateGraph(GraphState)
    graph.add_node("security_guard", safe_node(security_guard_node))
    graph.add_node("router", safe_node(lambda state: router_node(state, supervisor_provider)))
    graph.add_node("pedagogie", safe_node(pedagogie_agent))
    graph.add_node(
        "formation_elearning", safe_node(lambda state: formation_agent(state, training_catalog))
    )
    graph.add_node("cisi", safe_node(cisi_agent))
    graph.add_node("quiz", safe_node(quiz_agent))
    graph.add_node("championnat", safe_node(championnat_agent))
    graph.add_node("orientation", safe_node(orientation_agent))
    graph.add_node("support_ecole", safe_node(support_ecole_agent))
    graph.add_node("securite", safe_node(securite_agent))
    graph.add_node("out_of_domain", safe_node(out_of_domain_agent))
    graph.add_node("fallback", safe_node(fallback_agent))
    graph.add_node("output_guard", safe_node(output_guard))
    graph.add_edge(START, "security_guard")
    graph.add_conditional_edges(
        "security_guard", route_after_security, {"securite": "securite", "router": "router"}
    )
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {route: route for route in SUPPORTED_ROUTES if route != "securite"},
    )
    for route in SUPPORTED_ROUTES:
        if route != "formation_elearning":
            graph.add_edge(route, "output_guard")
    graph.add_conditional_edges(
        "formation_elearning",
        route_after_formation,
        {"cisi": "cisi", "output_guard": "output_guard"},
    )
    graph.add_edge("output_guard", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


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
