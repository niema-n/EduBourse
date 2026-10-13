from pathlib import Path

from app.agents.contracts import (
    AGENT_CONTRACTS,
    COMMON_FINANCIAL_AGENT_POLICY_ID,
    FINANCIAL_DOMAIN_TOPICS,
    OUT_OF_DOMAIN_MESSAGES,
    SHARED_POLICY,
    SUPPORTED_BUSINESS_LANGUAGES,
    SUPPORTED_BUSINESS_SCRIPTS,
)
from app.graph.core import SUPPORTED_ROUTES


def test_all_business_agents_share_senior_identity_and_unique_specializations():
    assert len(AGENT_CONTRACTS) == 8
    assert all(
        contract.role.startswith("Senior") or contract.role == "Educational Scope Guard"
        for contract in AGENT_CONTRACTS.values()
    )
    ids = [contract.specialization_id for contract in AGENT_CONTRACTS.values()]
    assert len(ids) == len(set(ids))
    assert SHARED_POLICY.policy_id == COMMON_FINANCIAL_AGENT_POLICY_ID


def test_specialization_contracts_cover_existing_routes():
    assert set(AGENT_CONTRACTS) == set(SUPPORTED_ROUTES) - {"securite", "fallback"}
    assert AGENT_CONTRACTS["pedagogie"].default_financial_education_route
    assert set(AGENT_CONTRACTS["formation_elearning"].future_levels) == {
        "beginner", "intermediate", "advanced"
    }
    assert "assessment" in AGENT_CONTRACTS["quiz"].topics
    assert AGENT_CONTRACTS["orientation"].educational_only
    assert AGENT_CONTRACTS["championnat"].simulation_distinguished_from_real
    assert "platform services" in AGENT_CONTRACTS["support_ecole"].topics


def test_scope_guard_is_professional_and_financial_topics_are_in_scope():
    assert len(OUT_OF_DOMAIN_MESSAGES) == 5
    assert "marchés" in OUT_OF_DOMAIN_MESSAGES[("fr", "latin")]
    assert "financial" in OUT_OF_DOMAIN_MESSAGES[("en", "latin")]
    assert "الأسواق" in OUT_OF_DOMAIN_MESSAGES[("ar", "arabic")]
    assert "lmaliya" in OUT_OF_DOMAIN_MESSAGES[("ary", "latin")]
    assert "الأسواق" in OUT_OF_DOMAIN_MESSAGES[("ary", "arabic")]
    assert "stocks" in FINANCIAL_DOMAIN_TOPICS
    assert "bonds" in FINANCIAL_DOMAIN_TOPICS
    assert "opcvm" in FINANCIAL_DOMAIN_TOPICS
    assert "ammc" in FINANCIAL_DOMAIN_TOPICS


def test_security_and_multilingual_contracts_are_preserved():
    assert "upstream security remains authoritative" in SHARED_POLICY.rules
    assert SUPPORTED_BUSINESS_LANGUAGES == ("fr", "en", "ar", "ary")
    assert SUPPORTED_BUSINESS_SCRIPTS["ary"] == ("latin", "arabic")
    assert all(
        "buy" not in rule.lower() or "no personalized" in rule.lower()
        for rule in SHARED_POLICY.rules
    )


def test_no_new_detector_or_domain_classifier_and_j6_files_are_untouched():
    root = Path(__file__).resolve().parents[3]
    assert not (root / "backend/app/agents/language_detector.py").exists()
    assert not (root / "backend/app/agents/domain_classifier.py").exists()
    assert (root / "backend/app/rag/retrieval_service.py").is_file()
    assert (root / "backend/app/rag/hybrid_policy.py").is_file()
