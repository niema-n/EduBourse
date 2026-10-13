"""Stable J6 domain, source-authority, safety, and grounding policy.

This module declares contracts only. It does not retrieve, index, translate,
or generate answers.
"""

from datetime import datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Final, Literal, get_args
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Authority = Literal[
    "ammc",
    "ecole_bourse",
    "bourse_casablanca",
    "internal_approved",
]
SourceType = Literal["pdf", "official_web_page", "internal_document"]
CorpusLanguage = Literal["fr"]
ResponseLanguage = Literal["fr", "en", "ar", "ary"]
ExpertiseLevel = Literal["senior"]
AudienceLevel = Literal["debutant", "intermediaire", "avance"]
CorpusStatus = Literal["active", "deprecated", "review_required"]
GroundingStatus = Literal[
    "SUPPORTED_BY_CORPUS",
    "INSUFFICIENT_EVIDENCE",
    "OUT_OF_DOMAIN",
    "BLOCKED_FINANCIAL_ADVICE",
]
SafetyIntent = Literal["education_information", "personalized_investment_advice"]
CorpusCategory = Literal[
    "market_basics",
    "financial_instruments",
    "stocks",
    "bonds",
    "opcvm",
    "ipo",
    "public_offerings",
    "corporate_actions",
    "indices",
    "masi",
    "orders",
    "market_mechanisms",
    "investor_profile",
    "risk",
    "diversification",
    "investor_protection",
    "financial_literacy",
    "regulation",
    "ecole_bourse",
    "formation",
    "elearning",
    "cisi",
    "championnat",
    "support",
    "crowdfunding",
    "pea",
    "general_assemblies",
    "information_documents",
    "savings",
]

APPROVED_AUTHORITY_PRIORITY: Final[tuple[Authority, ...]] = (
    "ecole_bourse",
    "bourse_casablanca",
    "ammc",
    "internal_approved",
)
SUPPORTED_RESPONSE_LANGUAGES: Final[tuple[ResponseLanguage, ...]] = (
    "fr",
    "en",
    "ar",
    "ary",
)
DOMAIN_CATEGORIES: Final[tuple[CorpusCategory, ...]] = (
    get_args(CorpusCategory)
)
GENERAL_PURPOSE_ASSISTANT: Final[bool] = False
RAG_DATA_ROOT_PARTS: Final[tuple[str, str]] = ("data", "rag")
APPROVED_SOURCE_HOSTS: Final[dict[Authority, tuple[str, ...]]] = {
    "ecole_bourse": ("ecole-bourse.ma",),
    "bourse_casablanca": ("casablanca-bourse.com",),
    "ammc": ("ammc.ma",),
}


class ExpertResponsePolicy(BaseModel):
    """Future grounded-generation policy; no model prompt or call is defined here."""

    model_config = ConfigDict(extra="forbid")

    expertise_level: ExpertiseLevel = "senior"
    audience_level: AudienceLevel
    grounded_facts_required: bool = True
    unsupported_facts_must_not_be_invented: bool = True
    professional_terminology_required: bool = True
    answer_depth_adapts_to_audience: bool = True
    mention_risk_when_relevant: bool = True
    citations_required_for_grounded_answers: bool = True


class CorpusDocumentManifest(BaseModel):
    """Metadata contract for one approved corpus document."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authority: Authority
    source_type: SourceType
    language: CorpusLanguage
    category: list[CorpusCategory] = Field(min_length=1)
    file_path: str | None = Field(default=None, min_length=1)
    source_url: str | None = Field(default=None, min_length=1)
    document_hash: str = Field(min_length=1)
    retrieved_at: datetime | None = None
    version: str | None = Field(default=None, min_length=1)
    agents_or_capabilities: list[str] = Field(default_factory=list)
    status: CorpusStatus

    @field_validator("file_path")
    @classmethod
    def confine_file_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("file_path must not contain null bytes")
        normalized = value.replace("\\", "/")
        windows_path = PureWindowsPath(normalized)
        if (
            PurePosixPath(normalized).is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
        ):
            raise ValueError("file_path must be relative")
        parts = tuple(part for part in PurePosixPath(normalized).parts if part)
        if ".." in parts:
            raise ValueError("file_path must not contain parent traversal")
        if parts[:3] == ("backend", "data", "rag"):
            parts = parts[1:]
        if parts[:2] != RAG_DATA_ROOT_PARTS or len(parts) < 4:
            raise ValueError("file_path must be under backend/data/rag/")
        return PurePosixPath(*parts).as_posix()

    @field_validator("document_hash")
    @classmethod
    def canonicalize_sha256(cls, value: str) -> str:
        import re

        if re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
            raise ValueError("document_hash must be a 64-character SHA-256 hex value")
        return value.lower()

    @field_validator("agents_or_capabilities")
    @classmethod
    def reject_blank_capabilities(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("agents_or_capabilities must not contain blank values")
        return normalized

    @model_validator(mode="after")
    def require_document_location(self) -> "CorpusDocumentManifest":
        if self.source_type == "official_web_page":
            if self.source_url is None or self.retrieved_at is None or self.file_path is not None:
                raise ValueError("official web pages require source_url and retrieved_at")
            if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
                raise ValueError("retrieved_at must be timezone-aware")
            self.validate_source_url(self.source_url, self.authority)
        elif self.file_path is None or self.source_url is not None:
            raise ValueError("local documents require file_path")
        if self.source_type == "pdf" and not self.file_path.startswith("data/rag/raw/"):
            raise ValueError("pdf file_path must be under data/rag/raw/")
        return self

    @staticmethod
    def validate_source_url(source_url: str, authority: Authority) -> str:
        parsed = urlsplit(source_url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme.lower() != "https" or not hostname:
            raise ValueError("source_url must use HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source_url must not contain credentials")
        approved_hosts = APPROVED_SOURCE_HOSTS.get(authority, ())
        if not any(hostname == host or hostname.endswith(f".{host}") for host in approved_hosts):
            raise ValueError("source_url host is not approved for its authority")
        return source_url


class GroundingDecision(BaseModel):
    """Future answer-generation outcome, kept explicit for anti-hallucination.

    ``source_ids`` may contain diagnostic retrieval candidates for
    ``INSUFFICIENT_EVIDENCE``; that status never claims those sources support
    the answer.
    """

    model_config = ConfigDict(extra="forbid")

    status: GroundingStatus
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_grounding_invariants(self) -> "GroundingDecision":
        if self.status == "SUPPORTED_BY_CORPUS" and not self.source_ids:
            raise ValueError("SUPPORTED_BY_CORPUS requires at least one source_id")
        if self.status == "OUT_OF_DOMAIN" and self.source_ids:
            raise ValueError("OUT_OF_DOMAIN must not contain source_ids")
        return self


class FinancialSafetyDecision(BaseModel):
    """Safety intent contract for education versus individualized advice."""

    model_config = ConfigDict(extra="forbid")

    intent: SafetyIntent
    restricted: bool
    requires_educational_redirect: bool

    @model_validator(mode="after")
    def enforce_safety_invariants(self) -> "FinancialSafetyDecision":
        if self.intent == "personalized_investment_advice":
            if not self.restricted or not self.requires_educational_redirect:
                raise ValueError(
                    "personalized advice requires restriction and educational redirect"
                )
        elif self.restricted or self.requires_educational_redirect:
            raise ValueError("education information cannot be marked as restricted advice")
        return self


class J6ResponseContract(BaseModel):
    """Language and grounding contract for a future J6 generated answer."""

    model_config = ConfigDict(extra="forbid")

    original_query: str = Field(min_length=1)
    user_language: ResponseLanguage
    user_script: Literal["latin", "arabic"]
    grounding: GroundingDecision
    safety: FinancialSafetyDecision

    @model_validator(mode="after")
    def enforce_response_invariants(self) -> "J6ResponseContract":
        expected_scripts = {
            "fr": {"latin"},
            "en": {"latin"},
            "ar": {"arabic"},
            "ary": {"latin", "arabic"},
        }
        if self.user_script not in expected_scripts[self.user_language]:
            raise ValueError("user_language and user_script are not a supported business pair")
        if self.grounding.status == "BLOCKED_FINANCIAL_ADVICE":
            if (
                self.safety.intent != "personalized_investment_advice"
                or not self.safety.restricted
                or not self.safety.requires_educational_redirect
            ):
                raise ValueError("blocked advice requires restricted educational redirection")
        return self
