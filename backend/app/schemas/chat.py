from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "examples": [
                {"message": "C'est quoi une action en Bourse ?", "thread_id": "demo-fr-001"},
                {"message": "What is a stock market index?", "thread_id": "demo-en-001"},
                {"message": "chno hiya action f lborsa?", "thread_id": "demo-ary-001"},
                {
                    "message": "ما هو السهم في البورصة؟",
                    "thread_id": "demo-ar-001",
                },
            ]
        },
    )

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="Text message to send to the multilingual educational assistant.",
    )
    thread_id: str = Field(
        min_length=1,
        max_length=200,
        description="Client-provided conversation identifier.",
    )

    @field_validator("message", "thread_id")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class ChatResponse(BaseModel):
    answer: str = Field(
        description="Educational answer returned in the detected language and script."
    )
    language: Literal["fr", "en", "ar", "ary"] = Field(
        description="Detected business language: fr, en, ar or ary."
    )
    script: Literal["latin", "arabic"] = Field(description="Output script: latin or arabic.")
    route: str = Field(description="Selected EduBourse business workflow.")
    blocked: bool = Field(
        description="Whether financial-safety policy blocked normal agent execution."
    )
    thread_id: str = Field(description="Conversation identifier echoed from the request.")
    status: Literal["ok", "blocked", "fallback", "error"] = Field(
        description="Response status: ok, blocked, fallback or error."
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "answer": "Une action represente une part du capital d'une societe.",
                "language": "fr",
                "script": "latin",
                "route": "pedagogie",
                "blocked": False,
                "thread_id": "demo-fr-001",
                "status": "ok",
            }
        },
    )


class APIError(BaseModel):
    error: str = Field(description="Stable public error code.")
    message: str = Field(description="Safe, user-facing error message.")
    status: int = Field(description="HTTP status code.")
    request_id: str | None = Field(
        default=None,
        description="Request identifier for support and logs.",
    )
