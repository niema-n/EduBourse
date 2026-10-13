"""Deterministic operations over the shared pedagogical profile."""

from collections.abc import Iterable

from app.learning.models import (
    LearningLevel,
    LevelSource,
    QuizAttemptSummary,
    SharedLearningProfile,
)
from app.learning.store import LearningProfileStore

TOPIC_ALIASES = {
    "opvcm": "opcvm",
    "market order": "market_orders",
    "market orders": "market_orders",
    "risk return": "risk_return",
    "risk/return": "risk_return",
}


def normalize_topic(topic: str) -> str:
    normalized = "_".join(topic.strip().casefold().replace("/", " ").replace("-", " ").split())
    if not normalized:
        raise ValueError("topic must not be blank")
    return TOPIC_ALIASES.get(normalized, normalized)


def _topics(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        topic = normalize_topic(value)
        if topic not in result:
            result.append(topic)
    return result


def _dedup_values(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


class LearningProfileService:
    def __init__(self, store: LearningProfileStore) -> None:
        self.store = store

    def get_profile(self, profile_key: str) -> SharedLearningProfile:
        return self.store.get(profile_key)

    def set_level(
        self, profile_key: str, learning_level: LearningLevel, level_source: LevelSource
    ) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        updated = profile.model_dump(mode="python")
        updated["learning_level"] = learning_level
        updated["level_source"] = level_source
        return self.store.save(profile_key, SharedLearningProfile.model_validate(updated))

    def mark_diagnostic_completed(self, profile_key: str) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        profile.diagnostic_completed = True
        return self.store.save(profile_key, profile)

    def record_quiz_attempt(
        self,
        profile_key: str,
        *,
        quiz_id: str,
        topic: str,
        level: LearningLevel,
        score_percent: float,
        correct_count: int,
        total_questions: int,
        completed_at: str | None = None,
    ) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        attempt = QuizAttemptSummary(
            quiz_id=quiz_id,
            topic=normalize_topic(topic),
            level=level,
            score_percent=score_percent,
            correct_count=correct_count,
            total_questions=total_questions,
            completed_at=completed_at,
        )
        profile.quiz_history.append(attempt)
        profile.last_quiz_score = score_percent
        return self.store.save(profile_key, profile)

    def mark_topic_mastered(self, profile_key: str, topic: str) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        normalized = normalize_topic(topic)
        profile.topics_to_review = [item for item in profile.topics_to_review if item != normalized]
        profile.topics_mastered = _topics([*profile.topics_mastered, normalized])
        return self.store.save(profile_key, profile)

    def mark_topic_to_review(self, profile_key: str, topic: str) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        normalized = normalize_topic(topic)
        profile.topics_mastered = [item for item in profile.topics_mastered if item != normalized]
        profile.topics_to_review = _topics([*profile.topics_to_review, normalized])
        return self.store.save(profile_key, profile)

    def mark_module_completed(self, profile_key: str, module: str) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        module = module.strip()
        if not module:
            raise ValueError("module must not be blank")
        profile.completed_modules = _dedup_values([*profile.completed_modules, module])
        return self.store.save(profile_key, profile)

    def mark_topic_completed(self, profile_key: str, topic: str) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        profile.completed_topics = _topics([*profile.completed_topics, topic])
        return self.store.save(profile_key, profile)

    def set_learning_path(
        self, profile_key: str, learning_path: str | None
    ) -> SharedLearningProfile:
        profile = self.get_profile(profile_key)
        if learning_path is not None and not learning_path.strip():
            raise ValueError("learning_path must not be blank")
        profile.current_learning_path = learning_path
        return self.store.save(profile_key, profile)
