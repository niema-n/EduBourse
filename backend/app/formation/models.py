"""Typed Formation workflow state."""
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FormationStatus = Literal["active", "waiting_for_diagnostic", "paused", "completed", "cancelled"]


class FormationSession(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    formation_id: str = Field(min_length=1)
    level: Literal["beginner", "intermediate", "advanced"] | None = None
    language: Literal["fr", "en", "ar", "ary"] = "fr"
    script: Literal["latin", "arabic"] = "latin"
    path_id: str = Field(min_length=1)
    current_module_index: int = Field(default=0, ge=0)
    current_step_index: int = Field(default=0, ge=0)
    status: FormationStatus
    completed_modules: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

