"""Strict, language-neutral pedagogical profile models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LearningLevel = Literal["beginner", "intermediate", "advanced"]
LevelSource = Literal["diagnostic", "quiz_performance", "manual", "training_progress", "unknown"]
LEARNING_LEVELS: tuple[str, ...] = ("beginner", "intermediate", "advanced")
LEVEL_SOURCES: tuple[str, ...] = (
    "diagnostic", "quiz_performance", "manual", "training_progress", "unknown"
)


class QuizAttemptSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    quiz_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    level: LearningLevel
    score_percent: float = Field(ge=0, le=100)
    correct_count: int = Field(ge=0)
    total_questions: int = Field(gt=0)
    completed_at: str | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> "QuizAttemptSummary":
        if self.correct_count > self.total_questions:
            raise ValueError("correct_count cannot exceed total_questions")
        return self


class SharedLearningProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    learning_level: LearningLevel | None = None
    level_source: LevelSource | None = None
    quiz_history: list[QuizAttemptSummary] = Field(default_factory=list)
    completed_topics: list[str] = Field(default_factory=list)
    topics_mastered: list[str] = Field(default_factory=list)
    topics_to_review: list[str] = Field(default_factory=list)
    completed_modules: list[str] = Field(default_factory=list)
    current_learning_path: str | None = None
    last_quiz_score: float | None = Field(default=None, ge=0, le=100)
    diagnostic_completed: bool = False

    @model_validator(mode="after")
    def validate_profile_invariants(self) -> "SharedLearningProfile":
        if (self.learning_level is None) != (self.level_source is None):
            raise ValueError("learning_level and level_source must be set together")
        for field_name in (
            "completed_topics", "topics_mastered", "topics_to_review", "completed_modules"
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        if set(self.topics_mastered) & set(self.topics_to_review):
            raise ValueError("a topic cannot be both mastered and under review")
        return self
