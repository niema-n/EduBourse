from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict
from uuid import uuid4

from app.formation.models import FormationSession
from app.graph.language_adapter import normalize_business_language
from app.graph.workflow_context import ConversationWorkflowContext
from app.quiz.models import QuizSession

Route = Literal[
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
]


class LearnerProfile(TypedDict, total=False):
    level: str
    learning_goal: str
    strong_topics: list[str]
    weak_topics: list[str]
    user_type: str
    preferred_language: str


class TrainingRecord(TypedDict, total=False):
    id: str
    title: str
    level: str
    topics: list[str]
    goals: list[str]
    source: str


class GraphState(TypedDict, total=False):
    user_input: str
    raw_user_message: str
    normalized_message: str
    language: str
    script: str
    domain_status: str
    security_status: str
    response_status: str
    security_confidence: float
    security_scores: dict[str, float]
    security_source: str
    risk_level: str
    selected_route: Route
    business_answer: str
    response_key: str
    raw_agent_answer: str
    localized_answer: str
    grounded_answer: str
    grounded_status: str
    grounded_citations: list[dict[str, Any]]
    grounded: bool
    knowledge_source: str
    web_grounded: bool
    web_sources: list[dict[str, Any]]
    web_search_entry_point: str | None
    error: str | None
    status: str
    route_confidence: float
    route_scores: dict[str, float]
    thread_id: str
    session_id: str
    assessment_completed: bool
    assessment_required: bool
    assessment_score: float
    assessment_level: str
    assessment_timestamp: str
    assessment_topics: list[str]
    assessment_weak_topics: list[str]
    assessment_answers: list[bool]
    learner_profile: LearnerProfile
    training_candidates: list[TrainingRecord]
    recommended_training: TrainingRecord | None
    cisi_delegated: bool
    metadata: dict[str, Any]
    workflow_context: ConversationWorkflowContext
    quiz_session: QuizSession
    formation_session: FormationSession
    internal_pedagogical_source: dict[str, Any] | None
    orientation_recommendation: Any
    memory_status: str
    memory_relevant_message_ids: list[int]
    recent_turns: list[dict[str, str]]
    retrieval_query: str


def create_initial_state(
    user_input: str,
    *,
    language: str | None = None,
    script: str | None = None,
    thread_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphState:
    """Backward-compatible first-turn helper; persistent fields are not reset."""
    return create_turn_input(
        user_input,
        language=language,
        script=script,
        thread_id=thread_id,
        session_id=session_id,
        metadata=metadata,
    )


def create_turn_input(
    user_input: str,
    *,
    language: str | None = None,
    script: str | None = None,
    thread_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphState:
    """Create only per-turn fields so checkpointed session data survives."""
    state: GraphState = {
        "user_input": user_input,
        "raw_user_message": user_input,
        "domain_status": "unchecked",
        "security_status": "unchecked",
        "risk_level": "none",
        "selected_route": "fallback",
        "business_answer": "",
        "response_key": "",
        "raw_agent_answer": "",
        "localized_answer": "",
        "error": None,
        "status": "initialized",
        "assessment_required": False,
        "internal_pedagogical_source": None,
        # Grounding is a per-turn result. The checkpointer merges this input
        # onto the thread's stored state, so leaving these set would let the
        # previous turn's citations resurface on a turn that never ran RAG.
        "grounded_answer": "",
        "grounded_status": "",
        "grounded_citations": [],
        "grounded": False,
        "knowledge_source": "",
        "web_grounded": False,
        "web_sources": [],
        "web_search_entry_point": None,
        "retrieval_query": "",
        "response_status": "",
        "route_confidence": 0.0,
        "route_scores": {},
    }
    if language is not None:
        # J2 supplies script-specific Darija labels; their mapped script wins.
        mapped_script = script if language == "ary" else None
        business_language, business_script = normalize_business_language(language, mapped_script)
        state["language"] = business_language
        state["script"] = business_script
    elif script is not None:
        state["script"] = script
    if thread_id is not None:
        state["thread_id"] = thread_id
    if session_id is not None:
        state["session_id"] = session_id
    if metadata is not None:
        state["metadata"] = metadata
    return state


def is_assessment_recent(state: GraphState, *, now: datetime | None = None) -> bool:
    """J3 provisional policy: completed within the last 30 days in this thread."""
    if not state.get("assessment_completed") or not state.get("assessment_timestamp"):
        return False
    try:
        timestamp = datetime.fromisoformat(state["assessment_timestamp"])
    except (TypeError, ValueError):
        return False
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return False
    current = now or datetime.now(UTC)
    try:
        age_seconds = (current - timestamp).total_seconds()
    except (TypeError, ValueError):
        return False
    return 0 <= age_seconds <= 30 * 24 * 60 * 60


def safe_thread_id(thread_id: str | None) -> str:
    return thread_id or f"stateless-{uuid4()}"
