from typing import Any, Literal

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


KnowledgeSource = Literal[
    "rag",
    "llm_general_financial_knowledge",
    "llm_web_grounded_financial_knowledge",
    "controlled_current_data_limitation",
]
MAX_WEB_SOURCES = 10


class WebSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=300)
    uri: str | None = Field(default=None, max_length=2000)


class InternalPedagogicalSource(BaseModel):
    """Internal module provenance, independent of RAG grounding and citations."""

    model_config = ConfigDict(extra="forbid")

    label: str
    description: str
    level: Literal["beginner", "intermediate", "advanced"]
    path_id: str
    module_id: str
    module_title: str
    module_number: int = Field(ge=1)
    module_count: int = Field(ge=1)


class ChatResponse(BaseModel):
    answer: str = Field(
        min_length=1,
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
    grounded: bool | None = Field(default=None)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    internal_pedagogical_source: InternalPedagogicalSource | None = Field(
        default=None, description="Internal EduBourse module metadata; not a RAG citation."
    )
    knowledge_source: KnowledgeSource | None = Field(
        default=None,
        description=(
            "Provenance of this turn's answer when the pedagogie route proves it: "
            "approved RAG corpus, general financial knowledge, web-grounded financial "
            "research, or the controlled current-data limitation."
        ),
    )
    web_sources: list[WebSource] = Field(
        default_factory=list,
        max_length=MAX_WEB_SOURCES,
        description="Sources returned by the authorized web-grounded financial research.",
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
