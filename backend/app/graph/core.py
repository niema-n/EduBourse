from __future__ import annotations

import re
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
from app.graph.state import GraphState, Route

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

SECURITY_PATTERNS = (
    r"\b(quelle action|quel titre).*(acheter|prendre)",
    r"\b(dois[- ]je|je dois).*(acheter|vendre)",
    r"\b(investis|investir|place).*(\d+|mon argent|mon portefeuille)",
    r"\b(what should i buy|should i sell|where should i invest)",
    r"\b(quelle valeur|quel titre).*(monter|baisser|demain|hausser)",
    r"\b(شنو|ماذا).*(نشري|نبيع|نستثمر)",
)


def security_domain_node(state: GraphState) -> GraphState:
    text = state.get("user_input", "").lower()
    if any(re.search(pattern, text) for pattern in SECURITY_PATTERNS):
        return {
            "domain_status": "in_domain",
            "security_status": "blocked",
            "risk_level": "high",
            "selected_route": "securite",
            "status": "secured",
        }
    in_domain = any(
        token in text
        for token in (
            "bourse",
            "casablanca",
            "action",
            "obligation",
            "marché",
            "marche",
            "investissement",
            "formation",
            "cisi",
            "quiz",
            "championnat",
            "ebourse",
            "e-bourse",
            "école",
            "ecole",
            "stock",
            "bond",
            "investment",
            "support",
            "connexion",
            "login",
            "mot de passe",
            "inscription",
            "password",
        )
    )
    return {
        "domain_status": "in_domain" if in_domain else "out_of_domain",
        "security_status": "clear",
        "risk_level": "low" if in_domain else "none",
        "status": "secured",
    }


def route_request(state: GraphState) -> GraphState:
    text = state.get("user_input", "").lower()
    if state.get("domain_status") != "in_domain":
        route: Route = "out_of_domain"
    elif any(
        word in text
        for word in (
            "support",
            "connexion",
            "login",
            "mot de passe",
            "inscription",
            "account",
            "password",
        )
    ):
        route = "support_ecole"
    elif re.search(r"\bformation\b|e-learning|elearning", text):
        route = "formation_elearning"
    elif "cisi" in text or "certification" in text or "compliance" in text:
        route = "cisi"
    elif "quiz" in text or "questionnaire" in text:
        route = "quiz"
    elif "championnat" in text or "e-bourse" in text or "ebourse" in text:
        route = "championnat"
    elif "orientation" in text or "parcours" in text:
        route = "orientation"
    elif any(
        word in text
        for word in ("action", "obligation", "indice", "ordre", "marché", "marche", "bourse")
    ):
        route = "pedagogie"
    else:
        route = "fallback"
    return {"selected_route": route}


def route_after_security(state: GraphState) -> str:
    return "securite" if state.get("security_status") == "blocked" else "router"


def route_to_agent(state: GraphState) -> str:
    route = state.get("selected_route", "fallback")
    return route if route in SUPPORTED_ROUTES else "fallback"


def route_after_formation(state: GraphState) -> str:
    text = state.get("user_input", "").lower()
    return (
        "cisi"
        if "cisi" in text or "certification" in text or "compliance" in text
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
    *, checkpointer: Any | None = None, training_catalog: TrainingCatalog | None = None
):
    graph = StateGraph(GraphState)
    graph.add_node("security_domain", safe_node(security_domain_node))
    graph.add_node("router", safe_node(route_request))
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
    graph.add_edge(START, "security_domain")
    graph.add_conditional_edges(
        "security_domain", route_after_security, {"securite": "securite", "router": "router"}
    )
    graph.add_conditional_edges(
        "router", route_to_agent, {route: route for route in SUPPORTED_ROUTES}
    )
    for route in SUPPORTED_ROUTES:
        if route not in {"formation_elearning"}:
            graph.add_edge(route, "output_guard")
    graph.add_conditional_edges(
        "formation_elearning",
        route_after_formation,
        {"cisi": "cisi", "output_guard": "output_guard"},
    )
    graph.add_edge("output_guard", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())
