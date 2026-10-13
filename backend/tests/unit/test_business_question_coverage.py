"""Offline policy wiring and grounding regressions (live tests evaluate model coverage)."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.agents.answer_coverage import BUSINESS_QUESTION_COVERAGE
from app.financial_expert.prompt import build_system_prompt
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GROUNDING_SYSTEM_PROMPT,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk


@pytest.mark.parametrize(
    "language,script",
    [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ],
)
def test_existing_business_prompts_share_coverage_policy(language, script):
    assert BUSINESS_QUESTION_COVERAGE in GROUNDING_SYSTEM_PROMPT
    assert BUSINESS_QUESTION_COVERAGE in build_system_prompt(language, script)


def service_with_output(output):
    provider = SimpleNamespace(model=GENERATION_MODEL, generate=Mock(return_value=output))
    retrieval = SimpleNamespace(
        retrieve=Mock(
            return_value=RetrievalResult(
                original_query="question",
                language="fr",
                script="latin",
                policy_id="H1_LANGUAGE_ROUTED_V1",
                branches_used=["original"],
                retrieval_status="ok",
                chunks=[
                    RetrievedChunk(
                        chunk_id="source-chunk",
                        source_id="source",
                        title="Notice pédagogique",
                        page=1,
                        page_start=1,
                        page_end=1,
                        text="Un ETF est un fonds coté qui cherche à suivre un indice.",
                        rank=1,
                        retrieval_score=0.1,
                        score_type="cosine_distance",
                    )
                ],
            )
        )
    )
    return GroundedGenerationService(retrieval, provider=provider), provider, retrieval


def test_partial_answer_and_specific_gap_survive_validation_with_one_business_call():
    answer = (
        "Un ETF est un fonds coté qui suit un indice. Les sources ne précisent pas "
        "les frais annuels de conservation de votre courtier."
    )
    service, provider, retrieval = service_with_output(
        {
            "answer": answer,
            "used_evidence_ids": ["S1"],
            "insufficient_evidence": False,
        }
    )
    question = "Définis un ETF et précise les frais annuels de conservation chez mon courtier."
    result = service.generate(
        GroundedGenerationRequest(
            original_query=question,
            language="fr",
            script="latin",
        )
    )
    assert result.generation_status == "ok" and result.grounded
    assert result.answer == answer  # Validation must not discard the specific limitation.
    assert result.citations[0].chunk_id == "source-chunk"
    assert result.used_evidence_ids == ["S1"]
    provider.generate.assert_called_once()
    retrieval.retrieve.assert_called_once()
    prompt, payload = provider.generate.call_args.args
    assert BUSINESS_QUESTION_COVERAGE in prompt
    assert question in payload


@pytest.mark.parametrize("evidence", [[], ["S99"]])
def test_completeness_never_allows_uncited_or_unknown_evidence(evidence):
    service, _, _ = service_with_output(
        {
            "answer": "Un ETF est un fonds coté.",
            "used_evidence_ids": evidence,
            "insufficient_evidence": False,
        }
    )
    result = service.generate(
        GroundedGenerationRequest(
            original_query="Définis un ETF et donne ses frais.",
            language="fr",
            script="latin",
        )
    )
    assert result.generation_status == "grounding_error"
    assert not result.grounded and result.answer is None and result.citations == []


def test_no_supported_aspect_keeps_existing_insufficient_evidence_contract():
    service, _, _ = service_with_output(
        {
            "answer": "",
            "used_evidence_ids": [],
            "insufficient_evidence": True,
        }
    )
    result = service.generate(
        GroundedGenerationRequest(
            original_query="Quels sont les frais de mon courtier ?",
            language="fr",
            script="latin",
        )
    )
    assert result.generation_status == "insufficient_evidence"
    assert not result.grounded and result.citations == []
