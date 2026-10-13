# ruff: noqa
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

OrientationAction = Literal['diagnostic', 'review_topic', 'continue_formation', 'take_quiz', 'next_learning_topic']

class OrientationRecommendation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    action: OrientationAction
    current_level: str | None = None
    recommended_topic: str | None = None
    reason: str = Field(min_length=1)
    next_agent: str = Field(min_length=1)
    needs_diagnostic: bool = False
    evidence: tuple[str, ...] = ()
