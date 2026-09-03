from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict
from uuid import uuid4

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
    language: str
    script: str
    domain_status: str
    security_status: str
    risk_level: str
    selected_route: Route
    business_answer: str
    error: str | None
    status: str
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
        "language": language or "unknown",
        "script": script or "unknown",
        "domain_status": "unchecked",
        "security_status": "unchecked",
        "risk_level": "none",
        "selected_route": "fallback",
        "business_answer": "",
        "error": None,
        "status": "initialized",
        "assessment_required": False,
    }
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
