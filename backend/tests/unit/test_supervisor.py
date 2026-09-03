import pytest
from pydantic import ValidationError

from app.graph.supervisor import (
    SupervisorDecision,
    SupervisorRouteDecision,
    SupervisorRequest,
    classify,
    controlled_fallback,
    derive_decision_basis,
    parse_route_decision,
    parse_decision,
)


def request() -> SupervisorRequest:
    return SupervisorRequest(
        user_message="شنو هو MASI؟",
        business_language="ary",
        script="arabic",
    )


def test_valid_decision_and_language_script_are_preserved() -> None:
    decision = parse_decision(
        {
            "domain_status": "in_domain",
            "route": "pedagogie",
            "decision_basis": "general_financial_education",
        }
    )
    assert decision.route == "pedagogie"
    assert request().business_language == "ary"
    assert request().script == "arabic"


def test_domain_route_consistency_is_strict() -> None:
    with pytest.raises(ValidationError):
        SupervisorDecision(
            domain_status="out_of_domain",
            route="pedagogie",
            decision_basis="outside_domain",
        )
    with pytest.raises(ValidationError):
        SupervisorDecision(
            domain_status="in_domain",
            route="out_of_domain",
            decision_basis="general_financial_education",
        )


def test_extra_fields_and_malformed_output_fail() -> None:
    with pytest.raises(ValidationError):
        parse_decision(
            {
                "domain_status": "in_domain",
                "route": "pedagogie",
                "decision_basis": "general_financial_education",
                "reasoning": "hidden chain",
            }
        )
    with pytest.raises(ValueError):
        parse_decision("not-json")


def test_provider_exception_and_malformed_output_use_explicit_fallback() -> None:
    class BrokenProvider:
        def invoke_structured(self, request: SupervisorRequest) -> object:
            raise TimeoutError

    class MalformedProvider:
        def invoke_structured(self, request: SupervisorRequest) -> object:
            return {"route": "pedagogie"}

    expected = controlled_fallback()
    assert classify(BrokenProvider(), request()) == expected
    assert classify(MalformedProvider(), request()) == expected
    assert expected.route == "fallback"


def test_general_financial_education_contract() -> None:
    decision = SupervisorDecision(
        domain_status="in_domain",
        route="pedagogie",
        decision_basis="general_financial_education",
    )
    assert decision.route == "pedagogie"


def test_minimal_route_contract_derives_basis_locally() -> None:
    decision = parse_route_decision({"domain_status": "in_domain", "route": "quiz"})
    assert isinstance(decision, SupervisorRouteDecision)
    assert derive_decision_basis(decision.route) == "assessment"


def test_minimal_route_contract_rejects_redundant_basis() -> None:
    with pytest.raises(ValidationError):
        parse_route_decision(
            {"domain_status": "in_domain", "route": "pedagogie", "decision_basis": "assessment"}
        )
