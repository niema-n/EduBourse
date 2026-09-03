from __future__ import annotations

from datetime import UTC, datetime

from app.graph.catalog import EmptyTrainingCatalog, TrainingCatalog, match_training
from app.graph.state import GraphState, LearnerProfile, is_assessment_recent

ASSESSMENT_QUESTIONS = [
    {
        "id": "actions",
        "topic": "actions",
        "prompt": "Une action représente une part du capital d'une entreprise.",
    },
    {
        "id": "obligations",
        "topic": "obligations",
        "prompt": "Une obligation est une dette émise par une organisation.",
    },
    {
        "id": "orders",
        "topic": "ordres",
        "prompt": "Un ordre à cours limité fixe un prix maximum ou minimum.",
    },
    {
        "id": "indices",
        "topic": "indices",
        "prompt": "Un indice suit l'évolution d'un ensemble de valeurs.",
    },
    {
        "id": "markets",
        "topic": "marches",
        "prompt": "Le marché secondaire permet d'échanger des titres déjà émis.",
    },
    {
        "id": "risk",
        "topic": "risques",
        "prompt": "La diversification peut réduire certains risques, sans les supprimer.",
    },
]

# Provisional educational defaults, subject to later pedagogical validation.
LEVEL_THRESHOLDS = {"debutant": (0.0, 0.49), "intermediaire": (0.5, 0.79), "avance": (0.8, 1.0)}


def score_assessment(answers: list[bool]) -> tuple[float, str, list[str], list[str]]:
    score = sum(answers) / len(answers) if answers else 0.0
    level = next(level for level, (low, high) in LEVEL_THRESHOLDS.items() if low <= score <= high)
    understood = [
        question["topic"]
        for question, answer in zip(ASSESSMENT_QUESTIONS, answers, strict=True)
        if answer
    ]
    weak = [
        question["topic"]
        for question, answer in zip(ASSESSMENT_QUESTIONS, answers, strict=True)
        if not answer
    ]
    return score, level, understood, weak


def assessment_node(state: GraphState) -> GraphState:
    answers = list(state.get("assessment_answers", []))
    score, level, understood, weak = score_assessment(answers)
    return {
        "assessment_completed": True,
        "assessment_required": False,
        "assessment_score": score,
        "assessment_level": level,
        "assessment_timestamp": datetime.now(UTC).isoformat(),
        "assessment_topics": understood,
        "assessment_weak_topics": weak,
    }


def learner_profile_node(state: GraphState) -> GraphState:
    profile: LearnerProfile = {
        "level": state.get("assessment_level", "debutant"),
        "learning_goal": "professional_certification"
        if any(
            keyword in state.get("user_input", "").lower()
            for keyword in ("cisi", "certification", "compliance")
        )
        else "financial_education",
        "strong_topics": list(state.get("assessment_topics", [])),
        "weak_topics": list(state.get("assessment_weak_topics", [])),
        "preferred_language": state.get("language", "unknown"),
    }
    return {"learner_profile": profile}


def formation_workflow(state: GraphState, catalog: TrainingCatalog | None = None) -> GraphState:
    if is_assessment_recent(state):
        next_state = {"assessment_required": False}
    else:
        next_state = {"assessment_required": True}
        if not state.get("assessment_answers"):
            return next_state | {
                "business_answer": (
                    "Une courte évaluation est nécessaire avant de proposer un parcours."
                )
            }
        next_state |= assessment_node(state)
    profile_state = state | next_state
    profile = learner_profile_node(profile_state)
    profile_state |= profile
    catalog = catalog or EmptyTrainingCatalog()
    candidates, recommendation = match_training(
        profile_state["learner_profile"], catalog.search(profile_state["learner_profile"])
    )
    return profile_state | {
        "training_candidates": candidates,
        "recommended_training": recommendation,
        "business_answer": "Votre profil pédagogique a été réutilisé pour orienter le parcours.",
    }
