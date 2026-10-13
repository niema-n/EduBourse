"""Strict temporary quiz state and question contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuizPhase = Literal["diagnostic", "quiz", "paused", "completed", "cancelled"]
QuizLevel = Literal["beginner", "intermediate", "advanced"]
Choice = Literal["A", "B", "C", "D"]


class QuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    question_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    level: QuizLevel
    prompt: str = Field(min_length=1)
    options: dict[Choice, str]
    correct_option: Choice
    explanation: str = Field(min_length=1)
    localized_prompts: dict[str, str] = Field(default_factory=dict)
    localized_options: dict[str, dict[Choice, str]] = Field(default_factory=dict)
    localized_explanations: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> "QuizQuestion":
        if set(self.options) != {"A", "B", "C", "D"}:
            raise ValueError("quiz questions require exactly A, B, C and D")
        if any(not value.strip() for value in self.options.values()):
            raise ValueError("quiz options must not be blank")
        return self

    def render(self, language: str, script: str) -> tuple[str, dict[Choice, str], str]:
        locale = f"{language}/{script}"
        return (
            self.localized_prompts.get(locale, self.prompt),
            self.localized_options.get(locale, self.options),
            self.localized_explanations.get(locale, self.explanation),
        )


class QuizSession(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    quiz_id: str = Field(min_length=1)
    profile_key: str = Field(min_length=1)
    phase: QuizPhase
    level: QuizLevel | None = None
    topic: str = Field(min_length=1)
    questions: list[QuizQuestion] = Field(min_length=1)
    current_question_index: int = Field(default=0, ge=0)
    correct_count: int = Field(default=0, ge=0)
    answers: list[Choice] = Field(default_factory=list)
    correct_answers: list[bool] = Field(default_factory=list)
    started_at: str | None = None
    language: Literal["fr", "en", "ar", "ary"] = "fr"
    script: Literal["latin", "arabic"] = "latin"

    @model_validator(mode="after")
    def validate_progress(self) -> "QuizSession":
        if self.current_question_index > len(self.questions):
            raise ValueError("question index is outside the quiz")
        if len(self.answers) != len(self.correct_answers):
            raise ValueError("answer and result histories must align")
        if self.correct_count != sum(self.correct_answers):
            raise ValueError("correct_count must match answer history")
        if self.phase == "quiz" and self.level is None:
            raise ValueError("normal quiz requires a level")
        return self

    @property
    def complete(self) -> bool:
        return self.current_question_index >= len(self.questions)
