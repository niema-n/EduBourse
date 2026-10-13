from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.contracts import SHARED_POLICY
from app.learning import (
    InMemoryLearningProfileStore,
    LearningProfileService,
    SharedLearningProfile,
    normalize_topic,
)


@pytest.fixture
def service():
    return LearningProfileService(InMemoryLearningProfileStore())


def test_profile_starts_unknown_and_not_beginner(service):
    profile = service.get_profile("thread-a")
    assert profile.learning_level is None
    assert profile.level_source is None


@pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
def test_valid_levels_and_explicit_source(service, level):
    profile = service.set_level("a", level, "manual")
    assert profile.learning_level == level
    assert profile.level_source == "manual"


@pytest.mark.parametrize(
    "level", ["expert", "novice", "advanced_plus", "conservative", "aggressive"]
)
def test_service_rejects_arbitrary_learning_levels_without_persisting(service, level):
    service.set_level("a", "beginner", "diagnostic")
    with pytest.raises(ValidationError):
        service.set_level("a", level, "manual")
    profile = service.get_profile("a")
    assert profile.learning_level == "beginner"
    assert profile.level_source == "diagnostic"


def test_service_rejects_invalid_level_source_atomically(service):
    service.set_level("a", "beginner", "diagnostic")
    with pytest.raises(ValidationError):
        service.set_level("a", "advanced", "invented_source")
    profile = service.get_profile("a")
    assert profile.learning_level == "beginner"
    assert profile.level_source == "diagnostic"


def test_profile_assignment_rejects_invalid_level():
    profile = SharedLearningProfile()
    with pytest.raises(ValidationError):
        profile.learning_level = "expert"
    assert profile.learning_level is None


def test_invalid_level_and_unpaired_level_rejected():
    with pytest.raises(ValidationError):
        SharedLearningProfile(learning_level="expert")
    with pytest.raises(ValidationError):
        SharedLearningProfile(learning_level="beginner")
    with pytest.raises(ValidationError):
        SharedLearningProfile(level_source="manual")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"score_percent": -1},
        {"score_percent": 101},
        {"correct_count": 4, "total_questions": 3},
        {"correct_count": 0, "total_questions": 0},
    ],
)
def test_quiz_attempt_validation(service, kwargs):
    base = dict(
        quiz_id="q1", topic="actions", level="beginner", score_percent=50,
        correct_count=1, total_questions=2,
    )
    base.update(kwargs)
    with pytest.raises((ValidationError, ValueError)):
        service.record_quiz_attempt("a", **base)


def test_quiz_history_and_score_do_not_promote_level(service):
    service.set_level("a", "beginner", "manual")
    profile = service.record_quiz_attempt(
        "a", quiz_id="q1", topic="actions", level="beginner", score_percent=95,
        correct_count=19, total_questions=20,
    )
    assert len(profile.quiz_history) == 1
    assert profile.last_quiz_score == 95
    assert profile.learning_level == "beginner"


def test_topics_are_normalized_deduplicated_and_moved(service):
    profile = service.mark_topic_to_review("a", "OPVCM")
    assert profile.topics_to_review == ["opcvm"]
    profile = service.mark_topic_mastered("a", "opcvm")
    assert profile.topics_mastered == ["opcvm"]
    assert profile.topics_to_review == []
    profile = service.mark_topic_to_review("a", "opcvm")
    assert profile.topics_mastered == []
    assert profile.topics_to_review == ["opcvm"]


def test_completed_modules_topics_and_learning_path(service):
    profile = service.mark_module_completed("a", "module-1")
    profile = service.mark_module_completed("a", "module-1")
    profile = service.mark_topic_completed("a", "market orders")
    profile = service.mark_topic_completed("a", "market_orders")
    profile = service.set_learning_path("a", "capital-markets-foundations")
    assert profile.completed_modules == ["module-1"]
    assert profile.completed_topics == ["market_orders"]
    assert profile.current_learning_path == "capital-markets-foundations"


def test_profiles_are_isolated_by_explicit_profile_key(service):
    service.set_level("user-a", "advanced", "diagnostic")
    assert service.get_profile("user-b").learning_level is None
    first = service.get_profile("user-a")
    first.completed_topics.append("mutated-outside")
    assert "mutated-outside" not in service.get_profile("user-a").completed_topics


def test_profile_is_educational_only_and_language_neutral():
    fields = set(SharedLearningProfile.model_fields)
    assert not fields & {"income", "wealth", "portfolio_value", "risk_appetite", "allocation"}
    assert normalize_topic("Risk/Return") == "risk_return"
    assert SHARED_POLICY.policy_id == "SENIOR_FINANCIAL_AGENT_POLICY_V1"
    assert not hasattr(
        __import__("app.agents.contracts", fromlist=["x"]), "COMMON_FINANCIAL_AGENT_POLICY"
    )


def test_no_future_j7_workflow_or_new_classifier_files():
    root = Path(__file__).resolve().parents[3]
    assert not (root / "backend/app/learning/diagnostic.py").exists()
    assert not (root / "backend/app/agents/domain_classifier.py").exists()
