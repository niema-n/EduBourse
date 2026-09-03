"""Provider-neutral structured routing contract for the J3 supervisor study."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from app.llm.base import LLMProvider

DomainStatus = Literal["in_domain", "out_of_domain"]
Route = Literal[
    "pedagogie",
    "formation_elearning",
    "orientation",
    "cisi",
    "quiz",
    "championnat",
    "support_ecole",
    "out_of_domain",
    "fallback",
]
DecisionBasis = Literal[
    "general_financial_education",
    "structured_learning",
    "learning_orientation",
    "professional_certification",
    "assessment",
    "simulation",
    "school_support",
    "outside_domain",
    "ambiguous",
]


class SupervisorDecision(BaseModel):
    """The only output accepted from an LLM routing provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    domain_status: DomainStatus
    route: Route
    decision_basis: DecisionBasis

    @model_validator(mode="after")
    def validate_consistency(self) -> SupervisorDecision:
        if self.domain_status == "out_of_domain" and self.route != "out_of_domain":
            raise ValueError("out_of_domain decisions must route to out_of_domain")
        if self.domain_status == "in_domain" and self.route == "out_of_domain":
            raise ValueError("in_domain decisions cannot route to out_of_domain")
        return self


class SupervisorRouteDecision(BaseModel):
    """Minimal provider-facing output for the frozen FIX3F6 evaluation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    domain_status: DomainStatus
    route: Route

    @model_validator(mode="after")
    def validate_consistency(self) -> SupervisorRouteDecision:
        if self.domain_status == "out_of_domain" and self.route != "out_of_domain":
            raise ValueError("out_of_domain decisions must route to out_of_domain")
        if self.domain_status == "in_domain" and self.route == "out_of_domain":
            raise ValueError("in_domain decisions cannot route to out_of_domain")
        return self


class SupervisorRequest(BaseModel):
    """Minimum context supplied to a supervisor provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    user_message: str = Field(min_length=1)
    business_language: Literal["fr", "en", "ar", "ary"]
    script: Literal["latin", "arabic"]
    workflow_context: str | None = None


SUPERVISOR_INSTRUCTION = """You classify and route. You do not answer the user's question.
Return only JSON with exactly these two fields: domain_status and route.
The exact allowed domain_status values are: in_domain, out_of_domain.
The exact allowed route values are: pedagogie, formation_elearning, orientation, cisi,
quiz, championnat, support_ecole, out_of_domain, fallback.
Use semantic domain understanding, not a keyword whitelist or known-phrase lookup.
The authorized domain includes Bourse, capital and financial markets, investment education,
financial instruments, indices and MASI, IPOs, dividends, orders, liquidity, risk,
Bourse de Casablanca, Ecole de la Bourse, e-learning, CISI, e-Bourse, and the
Championnat de la Bourse.
For safe in-domain general financial education with no specialized workflow, use pedagogie.
Use formation_elearning for structured courses or modules; orientation for learning-path
guidance; cisi for professional finance certification; quiz for assessment or practice;
championnat for educational trading competition or simulation; support_ecole for school
account, access, registration, platform, or navigation support.
Clearly unrelated requests use domain_status=out_of_domain and route=out_of_domain.
Ambiguous or unavailable cases use route=fallback and decision_basis=ambiguous.
Malformed or inconsistent output is rejected by the caller.
Do not return decision_basis, explanations, rationale, or prose."""


def parse_decision(payload: object) -> SupervisorDecision:
    """Strictly validate provider output; never silently default to pedagogie."""

    if isinstance(payload, SupervisorDecision):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("supervisor output must be a JSON object")
    return SupervisorDecision.model_validate(payload)


def parse_route_decision(payload: object) -> SupervisorRouteDecision:
    """Strictly validate the minimal FIX3F6 provider response."""

    if isinstance(payload, SupervisorRouteDecision):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("supervisor output must be a JSON object")
    return SupervisorRouteDecision.model_validate(payload)


def derive_decision_basis(route: Route) -> DecisionBasis:
    """Derive compatibility metadata locally, never ask the provider for it."""

    return {
        "pedagogie": "general_financial_education",
        "formation_elearning": "structured_learning",
        "orientation": "learning_orientation",
        "cisi": "professional_certification",
        "quiz": "assessment",
        "championnat": "simulation",
        "support_ecole": "school_support",
        "out_of_domain": "outside_domain",
        "fallback": "ambiguous",
    }[route]


def controlled_fallback() -> SupervisorDecision:
    """Represent an unavailable, ambiguous, or malformed decision safely."""

    return SupervisorDecision(
        domain_status="in_domain",
        route="fallback",
        decision_basis="ambiguous",
    )


def classify(provider: LLMProvider, request: SupervisorRequest) -> SupervisorDecision:
    """Convert provider failures and malformed output into explicit fallback."""

    try:
        return parse_decision(provider.invoke_structured(request))
    except Exception:
        return controlled_fallback()
