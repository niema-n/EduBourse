from typing import get_args

import pytest
from pydantic import ValidationError

from app.rag.domain_policy import (
    APPROVED_AUTHORITY_PRIORITY,
    APPROVED_SOURCE_HOSTS,
    DOMAIN_CATEGORIES,
    GENERAL_PURPOSE_ASSISTANT,
    SUPPORTED_RESPONSE_LANGUAGES,
    CorpusCategory,
    CorpusDocumentManifest,
    ExpertResponsePolicy,
    FinancialSafetyDecision,
    GroundingDecision,
    J6ResponseContract,
)

SHA256 = "A" * 64


def valid_manifest(**overrides):
    payload = {
        "source_id": "ammc-guide-actions",
        "title": "Guide pedagogique",
        "authority": "ammc",
        "source_type": "pdf",
        "language": "fr",
        "category": ["stocks", "market_basics"],
        "file_path": "backend/data/rag/raw/ammc/guide.pdf",
        "document_hash": SHA256,
        "agents_or_capabilities": [" pedagogie "],
        "status": "active",
    }
    payload.update(overrides)
    return payload


def safety(intent="education_information", restricted=False, redirect=False):
    return FinancialSafetyDecision(
        intent=intent,
        restricted=restricted,
        requires_educational_redirect=redirect,
    )


def test_policy_and_taxonomy_are_explicit_and_canonical() -> None:
    assert APPROVED_AUTHORITY_PRIORITY == (
        "ecole_bourse",
        "bourse_casablanca",
        "ammc",
        "internal_approved",
    )
    assert set(DOMAIN_CATEGORIES) == set(get_args(CorpusCategory))
    assert {
        "crowdfunding",
        "pea",
        "general_assemblies",
        "information_documents",
        "savings",
    } <= set(DOMAIN_CATEGORIES)
    assert GENERAL_PURPOSE_ASSISTANT is False
    assert set(SUPPORTED_RESPONSE_LANGUAGES) == {"fr", "en", "ar", "ary"}


@pytest.mark.parametrize("audience", ["debutant", "intermediaire", "avance"])
def test_senior_expert_policy_is_explicit(audience) -> None:
    policy = ExpertResponsePolicy(audience_level=audience)

    assert policy.expertise_level == "senior"
    assert policy.audience_level == audience
    assert policy.grounded_facts_required
    assert policy.unsupported_facts_must_not_be_invented
    assert policy.professional_terminology_required
    assert policy.answer_depth_adapts_to_audience
    assert policy.mention_risk_when_relevant
    assert policy.citations_required_for_grounded_answers


@pytest.mark.parametrize(
    "kwargs",
    [
        {"intent": "personalized_investment_advice", "restricted": False, "redirect": False},
        {"intent": "personalized_investment_advice", "restricted": True, "redirect": False},
        {"intent": "education_information", "restricted": True, "redirect": False},
        {"intent": "education_information", "restricted": False, "redirect": True},
    ],
)
def test_safety_rejects_contradictory_states(kwargs) -> None:
    with pytest.raises(ValidationError):
        safety(**kwargs)


def test_personalized_advice_requires_restriction_and_redirect() -> None:
    decision = safety("personalized_investment_advice", True, True)
    assert decision.restricted is True
    assert decision.requires_educational_redirect is True


def test_grounding_invariants_and_diagnostic_insufficient_evidence() -> None:
    with pytest.raises(ValidationError):
        GroundingDecision(status="SUPPORTED_BY_CORPUS")
    with pytest.raises(ValidationError):
        GroundingDecision(status="OUT_OF_DOMAIN", source_ids=["candidate"])
    assert GroundingDecision(status="SUPPORTED_BY_CORPUS", source_ids=["source-1"])
    assert GroundingDecision(status="INSUFFICIENT_EVIDENCE", source_ids=["diagnostic-candidate"])


def test_response_contract_rejects_blocked_safe_state_and_accepts_blocked_advice() -> None:
    with pytest.raises(ValidationError):
        J6ResponseContract(
            original_query="What is a stock?",
            user_language="en",
            user_script="latin",
            grounding=GroundingDecision(status="BLOCKED_FINANCIAL_ADVICE"),
            safety=safety(),
        )
    contract = J6ResponseContract(
        original_query="Which stock should I buy?",
        user_language="en",
        user_script="latin",
        grounding=GroundingDecision(status="BLOCKED_FINANCIAL_ADVICE"),
        safety=safety("personalized_investment_advice", True, True),
    )
    assert contract.grounding.status == "BLOCKED_FINANCIAL_ADVICE"


def test_manifest_requires_french_and_canonicalizes_metadata() -> None:
    manifest = CorpusDocumentManifest(**valid_manifest())
    assert manifest.language == "fr"
    assert manifest.file_path == "data/rag/raw/ammc/guide.pdf"
    assert manifest.document_hash == SHA256.lower()
    assert manifest.agents_or_capabilities == ["pedagogie"]


@pytest.mark.parametrize(
    "path",
    [
        "../raw/guide.pdf",
        "data/rag/../../app/config.py",
        "/etc/shadow",
        "C:/Users/hp/.env",
        "\\\\evil-host\\share\\x.pdf",
        "backend/app/config.py",
        "backend/data/rag/raw/guide.pdf\x00.txt",
    ],
)
def test_manifest_rejects_unsafe_file_paths(path) -> None:
    with pytest.raises(ValidationError):
        CorpusDocumentManifest(**valid_manifest(file_path=path))


def test_manifest_accepts_windows_shaped_relative_rag_path() -> None:
    manifest = CorpusDocumentManifest(
        **valid_manifest(file_path=r"backend\data\rag\raw\ammc\guide.pdf")
    )
    assert manifest.file_path == "data/rag/raw/ammc/guide.pdf"


@pytest.mark.parametrize(
    "source_url",
    [
        "http://www.ammc.ma/education",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/plain,hello",
        "https://ammc.ma.evil.com/education",
    ],
)
def test_manifest_rejects_unsafe_source_urls(source_url) -> None:
    with pytest.raises(ValidationError):
        CorpusDocumentManifest(
            **valid_manifest(
                source_type="official_web_page",
                file_path=None,
                source_url=source_url,
                retrieved_at="2026-09-05T10:00:00Z",
            )
        )


@pytest.mark.parametrize(
    ("authority", "source_url"),
    [
        ("ammc", "https://www.ecole-bourse.ma/education"),
        ("ecole_bourse", "https://www.ammc.ma/education"),
        ("internal_approved", "https://ammc.ma/education"),
    ],
)
def test_manifest_rejects_authority_hostname_mismatch(authority, source_url) -> None:
    with pytest.raises(ValidationError):
        CorpusDocumentManifest(
            **valid_manifest(
                authority=authority,
                source_type="official_web_page",
                file_path=None,
                source_url=source_url,
                retrieved_at="2026-09-05T10:00:00Z",
            )
        )


def test_manifest_accepts_approved_official_https_source() -> None:
    manifest = CorpusDocumentManifest(
        **valid_manifest(
            authority="ammc",
            source_type="official_web_page",
            file_path=None,
            source_url="https://education.ammc.ma/guides",
            retrieved_at="2026-09-05T10:00:00Z",
        )
    )
    assert manifest.source_url == "https://education.ammc.ma/guides"
    assert manifest.retrieved_at.tzinfo is not None
    assert APPROVED_SOURCE_HOSTS["ammc"] == ("ammc.ma",)


@pytest.mark.parametrize(
    "overrides",
    [
        {"authority": "random_blog"},
        {"source_type": "forum_post"},
        {"language": "en"},
        {"category": ["cooking"]},
        {"document_hash": "not-a-sha256"},
        {"agents_or_capabilities": ["", "pedagogie"]},
        {"source_type": "official_web_page", "file_path": None, "source_url": "https://ammc.ma"},
    ],
)
def test_manifest_rejects_invalid_metadata(overrides) -> None:
    with pytest.raises(ValidationError):
        CorpusDocumentManifest(**valid_manifest(**overrides))


@pytest.mark.parametrize(
    ("language", "script"),
    [("fr", "latin"), ("en", "latin"), ("ar", "arabic"), ("ary", "latin"), ("ary", "arabic")],
)
def test_supported_language_script_pairs_are_accepted(language, script) -> None:
    contract = J6ResponseContract(
        original_query="What is MASI?",
        user_language=language,
        user_script=script,
        grounding=GroundingDecision(status="INSUFFICIENT_EVIDENCE"),
        safety=safety(),
    )
    assert contract.user_language == language


@pytest.mark.parametrize("language,script", [("ar", "latin"), ("fr", "arabic"), ("en", "arabic")])
def test_unsupported_language_script_pairs_are_rejected(language, script) -> None:
    with pytest.raises(ValidationError):
        J6ResponseContract(
            original_query="What is MASI?",
            user_language=language,
            user_script=script,
            grounding=GroundingDecision(status="INSUFFICIENT_EVIDENCE"),
            safety=safety(),
        )
