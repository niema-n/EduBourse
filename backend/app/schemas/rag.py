"""Public, read-only RAG schemas. They never carry paths, vectors or secrets."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RagOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_name: str
    embedding_model: str
    embedding_dimension: int
    distance_metric: str
    index_version: int
    indexed_chunk_count: int = Field(description="Chunks declared by the frozen index manifest.")
    live_chunk_count: int | None = Field(
        default=None, description="Chunks counted in the loaded collection, when loaded."
    )
    source_count: int
    corpus_languages: list[str]
    authorities: list[str]
    index_status: Literal["available", "not_loaded", "unavailable"] = Field(
        description="available: collection loaded and counted; not_loaded: loads on first search."
    )


class RagSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    authority: str
    categories: list[str]
    language: str
    source_type: str
    chunk_count: int


class RagSourcesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_sources: int
    total_chunks: int
    sources: list[RagSource]


class RagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class RagSearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    chunk_id: str
    source_id: str
    title: str
    authority: str | None
    categories: list[str]
    page_start: int
    page_end: int
    heading: str | None
    excerpt: str = Field(description="Original retrieved source text, never translated.")
    source_language: str | None = Field(default=None, description="Language of the source.")
    score: float
    score_type: Literal["cosine_distance", "rrf"]
    # Additive, display-only fields: a translated preview of `excerpt`.
    translated_excerpt: str | None = None
    translated_language: Literal["en", "ar", "ary"] | None = None
    translated_script: Literal["latin", "arabic"] | None = None
    translation_status: Literal["not_needed", "translated", "unavailable"] = "not_needed"


class RagSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    language: Literal["fr", "en", "ar", "ary"]
    script: Literal["latin", "arabic"]
    retrieval_query: str | None = Field(
        description="French query actually embedded when the language needs adaptation."
    )
    branches: list[str]
    top_k: int
    results: list[RagSearchHit]
