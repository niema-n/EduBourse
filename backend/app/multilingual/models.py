from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LanguageCode = Literal["fr", "en", "ar", "ary-latin", "ary-arabic"]
ScriptCode = Literal["latin", "arabic", "mixed"]


class LanguageAnalysis(BaseModel):
    language: LanguageCode
    script: ScriptCode
    normalized_text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class ScriptValidationResult(BaseModel):
    valid: bool
    expected_script: ScriptCode
    detected_script: ScriptCode
    reason: str

    model_config = ConfigDict(extra="forbid")
