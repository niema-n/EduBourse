"""Strict request and result contracts for the isolated expert."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BusinessLanguage = Literal["fr", "en", "ar", "ary"]
BusinessScript = Literal["latin", "arabic"]
FinancialExpertKnowledgeSource = Literal[
    "llm_general_financial_knowledge",
    "llm_web_grounded_financial_knowledge",
    "controlled_current_data_limitation",
]


class FinancialExpertWebSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str | None = None
    uri: str | None = None
    domain: str | None = None


class FinancialExpertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1, max_length=4000)
    language: BusinessLanguage
    script: BusinessScript
    memory_context: str | None = None


class FinancialExpertResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answer: str = Field(min_length=1)
    language: BusinessLanguage
    script: BusinessScript
    provider: str
    knowledge_source: FinancialExpertKnowledgeSource
    web_grounded: bool = False
    web_sources: list[FinancialExpertWebSource] = Field(default_factory=list)
    web_search_entry_point: str | None = None
