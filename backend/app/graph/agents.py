from __future__ import annotations

from app.graph.catalog import TrainingCatalog
from app.graph.state import GraphState
from app.graph.workflows import formation_workflow


def pedagogie_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je peux expliquer les actions, obligations, indices, ordres et "
            "concepts de marché à visée éducative."
        ),
        "status": "completed",
    }


def formation_agent(state: GraphState, catalog: TrainingCatalog | None = None) -> GraphState:
    return formation_workflow(state, catalog) | {"status": "completed"}


def cisi_agent(state: GraphState) -> GraphState:
    return {
        "selected_route": "cisi",
        "cisi_delegated": state.get("selected_route") == "formation_elearning",
        "business_answer": (
            "Les informations détaillées sur les certifications CISI nécessitent "
            "un catalogue officiel; cette intégration sera ajoutée derrière un port dédié."
        ),
        "status": "completed",
    }


def quiz_agent(state: GraphState) -> GraphState:
    answers = list(state.get("assessment_answers", []))
    if answers:
        from app.graph.workflows import assessment_node, learner_profile_node

        assessed = assessment_node(state)
        return (
            assessed
            | learner_profile_node(state | assessed)
            | {
                "business_answer": (
                    "Le quiz éducatif a alimenté l'état d'évaluation; ce résultat n'est "
                    "pas une certification officielle."
                ),
                "status": "completed",
            }
        )
    return {
        "business_answer": (
            "Un quiz éducatif court peut être lancé sur les notions de marché, risque "
            "et instruments."
        ),
        "status": "completed",
    }


def championnat_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je peux présenter le Championnat de la Bourse et e-Bourse à titre éducatif. "
            "Les classements et portfolios en direct ne sont pas connectés."
        ),
        "status": "completed",
    }


def orientation_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je peux vous orienter vers un parcours e-learning, un quiz, des notions "
            "pédagogiques ou des informations CISI, sans recommander d'investissement."
        ),
        "status": "completed",
    }


def support_ecole_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je peux aider avec l'accès, l'inscription, la connexion, la récupération "
            "de mot de passe et la navigation de l'École de la Bourse, sans accéder à "
            "votre compte."
        ),
        "status": "completed",
    }


def securite_agent(state: GraphState) -> GraphState:
    return {
        "security_status": "blocked",
        "risk_level": "high",
        "business_answer": (
            "Je ne peux pas choisir un titre, recommander une vente ou répartir votre "
            "argent. Je peux expliquer des critères généraux d'analyse financière."
        ),
        "status": "completed",
    }


def out_of_domain_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je suis spécialisé en Bourse, marchés de capitaux et éducation financière."
        ),
        "status": "completed",
    }


def fallback_agent(state: GraphState) -> GraphState:
    return {
        "business_answer": (
            "Je n'ai pas compris la demande. Je peux aider sur la Bourse, l'éducation "
            "financière, les formations et les services associés."
        ),
        "status": "completed",
    }
