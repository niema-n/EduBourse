"""Bounded retrieval, per-concept grounding and fail-closed comparison regressions."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.graph.agents import pedagogie_agent
from app.rag.comparison import (
    answer_covers,
    comparison_concepts,
    coverage,
    has_source_mechanics,
    rewrite_preserves_comparison,
)
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

QUESTIONS = [
    ("fr", "latin", "Quelle est la différence entre une action et une obligation ?"),
    ("en", "latin", "What is the difference between a stock and a bond?"),
    ("ar", "arabic", "ما الفرق بين السهم والسند؟"),
    ("ary", "arabic", "شنو الفرق بين السهم والسند؟"),
]
STOCK = (
    "Une action est un titre de propriété du capital. "
    "Une action donne des dividendes et un droit de vote. "
    "Une action expose à une perte en capital."
)
BOND = (
    "Une obligation est un titre de créance. "
    "Une obligation verse un coupon et prévoit un remboursement. "
    "Une obligation expose au risque de défaut."
)
DEFINITIONS = {
    "fr": (
        "Une action est un titre de propriété du capital. Une obligation est un titre de créance."
    ),
    "en": "A stock is an ownership share in a company. A bond is a debt instrument.",
    "ar": "السهم أداة ملكية في الشركة. السند أداة دين على الجهة المصدرة.",
    "ary": "السهم كيمثل حصة فملكية الشركة. السند كيمثل دين على الجهة اللي صدراتو.",
}
ANSWERS = {
    "fr": STOCK + " " + BOND,
    "en": DEFINITIONS["en"] + " A stock pays dividends and gives voting rights. "
    "A stock carries capital loss risk. A bond pays interest and provides repayment. "
    "A bond carries default risk.",
    "ar": DEFINITIONS["ar"] + " السهم يوزع أرباحاً ويمنح حق التصويت. "
    "السهم يعرض لخسارة رأس المال. السند يدفع فوائد ويتيح السداد. "
    "السند يعرض لمخاطر العجز.",
    "ary": DEFINITIONS["ary"] + " السهم كيقدر يعطيك أرباح وحق التصويت. "
    "السهم فيه خطر خسارة راس المال. السند كيخلص فوائد وكيعطي حق السداد. "
    "السند فيه خطر العجز على السداد.",
}


def chunk(key, text):
    return RetrievedChunk(
        chunk_id=key,
        source_id="approved-guide",
        title="Guide officiel",
        page=17 if key == "bond" else 8,
        page_start=8,
        page_end=17,
        text=text,
        rank=1,
        retrieval_score=0.1,
        score_type="cosine_distance",
    )


class Retrieval:
    def __init__(self, initial=None, supplement=None, status="ok"):
        self.initial = initial if initial is not None else [chunk("stock", STOCK)]
        self.supplement = supplement if supplement is not None else [chunk("bond", BOND)]
        self.status = status
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original", "french_adapted"],
            chunks=self.initial if len(self.requests) == 1 else self.supplement,
            retrieval_status="ok" if len(self.requests) == 1 else self.status,
        )


def provider(answer, ids=None):
    return SimpleNamespace(
        model=GENERATION_MODEL,
        generate=Mock(
            return_value={
                "answer": answer,
                "used_evidence_ids": ids or ["S1", "S2"],
                "insufficient_evidence": False,
            }
        ),
    )


@pytest.mark.parametrize("language,script,query", QUESTIONS)
def test_missing_concept_retrieved_before_one_coherent_answer(language, script, query):
    retrieval = Retrieval()
    llm = provider(ANSWERS[language])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=query, language=language, script=script)
    )
    assert result.grounded and result.generation_status == "ok"
    assert {c.chunk_id for c in result.citations} == {"stock", "bond"}
    assert all(c.source_id == "approved-guide" for c in result.citations)
    assert len(retrieval.requests) == 2
    targeted = retrieval.requests[1]
    assert targeted.language == language and targeted.script == script
    assert targeted.conversation_context is None
    assert (
        "obligation" if language == "fr" else "bond" if language == "en" else "السند"
    ) in targeted.original_query
    llm.generate.assert_called_once()
    system, payload = llm.generate.call_args.args
    assert "COMPARISON COMPLETENESS CONTRACT" in system
    assert STOCK in payload and BOND in payload
    assert "COMPARISON_CONCEPTS: stock, bond" in payload
    assert not has_source_mechanics(result.answer)
    assert all("definition" in coverage(result.answer, c) for c in comparison_concepts(query))


def test_complete_evidence_does_not_trigger_supplemental_retrieval():
    retrieval = Retrieval(initial=[chunk("both", STOCK + " " + BOND)])
    llm = provider(ANSWERS["en"], ["S1"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[1][2], language="en", script="latin")
    )
    assert result.grounded and len(retrieval.requests) == 1


def test_contents_page_is_not_a_definition_or_a_return_mechanism():
    toc = (
        "Table\ndes matières\nActions : propriété\nObligations : créance\n"
        "Rendement des obligations : coupons 17"
    )
    for c in comparison_concepts(QUESTIONS[0][2]):
        assert coverage(toc, c) == set()
    retrieval = Retrieval(initial=[chunk("toc", toc)], supplement=[])
    llm = provider(ANSWERS["fr"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[0][2], language="fr", script="latin")
    )
    assert len(retrieval.requests) == 3  # Each missing concept receives one search.
    assert result.comparison_incomplete and not result.grounded and result.citations == []
    assert not has_source_mechanics(result.answer)
    llm.generate.assert_not_called()


@pytest.mark.parametrize(
    "supplement,status", [([], "ok"), ([], "provider_error"), ([], "configuration_error")]
)
def test_missing_support_fails_closed_after_bounded_targeted_retrieval(supplement, status):
    retrieval = Retrieval(supplement=supplement, status=status)
    llm = provider(ANSWERS["en"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[1][2], language="en", script="latin")
    )
    assert len(retrieval.requests) == 2
    assert result.insufficient_evidence and result.comparison_incomplete
    assert not result.grounded and not result.citations
    llm.generate.assert_not_called()
    expert = SimpleNamespace(answer=Mock(side_effect=AssertionError("No knowledge fallback")))
    state = pedagogie_agent(
        {"user_input": QUESTIONS[1][2], "language": "en", "script": "latin"},
        grounded_service=SimpleNamespace(generate=lambda request: result),
        financial_expert_service=expert,
        financial_expert_fallback_enabled=True,
    )
    assert state["grounded"] is False
    expert.answer.assert_not_called()


@pytest.mark.parametrize(
    "answer,ids",
    [
        ("A stock is an ownership share in a company. A bond is also mentioned.", ["S1", "S2"]),
        (ANSWERS["en"] + " The document does not specify bond risks.", ["S1", "S2"]),
        (ANSWERS["en"] + " A stock pays a guaranteed 8% coupon.", ["S1", "S2"]),
        (ANSWERS["en"], ["S1"]),  # Uncited bond evidence cannot support the comparison.
    ],
)
def test_incomplete_uncited_or_unsupported_comparison_cannot_be_grounded(answer, ids):
    result = GroundedGenerationService(Retrieval(), provider=provider(answer, ids)).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[1][2], language="en", script="latin")
    )
    assert not result.grounded and result.citations == []
    assert result.comparison_incomplete


def test_invalid_citation_ids_keep_existing_grounding_rejection():
    result = GroundedGenerationService(
        Retrieval(), provider=provider(ANSWERS["en"], ["S99"])
    ).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[1][2], language="en", script="latin")
    )
    assert result.generation_status == "grounding_error" and not result.citations


def test_merge_deduplicates_chunks_and_preserves_authoritative_source_metadata():
    retrieval = Retrieval(supplement=[chunk("stock", STOCK), chunk("bond", BOND)])
    result = GroundedGenerationService(retrieval, provider=provider(ANSWERS["en"])).generate(
        GroundedGenerationRequest(original_query=QUESTIONS[1][2], language="en", script="latin")
    )
    assert result.grounded and len(result.citations) == 2
    assert next(c for c in result.citations if c.chunk_id == "bond").page == 17


@pytest.mark.parametrize(
    "query,keys",
    [
        ("Compare OPCVM et investissement direct", {"fund", "direct"}),
        ("IPO vs secondary market", {"ipo", "secondary"}),
        ("Compare stocks, bonds and mutual funds", {"stock", "bond", "fund"}),
        ("ما الفرق بين الأسهم والسندات؟", {"stock", "bond"}),
        ("chno lfer9 bin action w obligation?", {"stock", "bond"}),
        ("ETF vs mutual fund", {"etf", "fund"}),
        ("Compare exchange-traded funds and stocks", {"etf", "stock"}),
    ],
)
def test_comparison_entity_detection(query, keys):
    assert {c.key for c in comparison_concepts(query)} == keys


def test_single_concept_behavior_and_generation_prompt_are_unchanged():
    retrieval = Retrieval()
    llm = provider("An action is an ownership share.", ["S1"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query="What is a stock?", language="en", script="latin")
    )
    assert result.grounded and len(retrieval.requests) == 1
    assert "COMPARISON COMPLETENESS CONTRACT" not in llm.generate.call_args.args[0]


def test_localization_cannot_drop_concepts_or_inject_retrieval_wording():
    assert rewrite_preserves_comparison(ANSWERS["fr"], ANSWERS["ary"])
    assert not rewrite_preserves_comparison(ANSWERS["fr"], "السهم كيمثل حصة فملكية الشركة.")
    assert not rewrite_preserves_comparison(
        ANSWERS["fr"], ANSWERS["ary"] + " المصدر ما كيحددش التفاصيل."
    )


def test_return_mechanism_must_be_supported_for_the_same_concept():
    concepts = comparison_concepts(QUESTIONS[1][2])
    answer = ANSWERS["en"] + " A stock pays interest. A bond pays dividends."
    assert not answer_covers(answer, concepts, [chunk("stock", STOCK), chunk("bond", BOND)])


def test_explicit_return_and_risk_dimensions_cannot_be_silently_omitted():
    retrieval = Retrieval(initial=[chunk("stock", STOCK), chunk("bond", BOND)])
    result = GroundedGenerationService(retrieval, provider=provider(DEFINITIONS["en"])).generate(
        GroundedGenerationRequest(
            original_query="Compare stocks and bonds: definitions, returns and risks.",
            language="en",
            script="latin",
        )
    )
    assert len(retrieval.requests) == 1  # Both dimensions already have evidence.
    assert result.comparison_incomplete and not result.grounded


def test_localization_cannot_drop_supported_comparison_dimensions():
    source = ANSWERS["en"] + " A stock pays dividends. A bond pays interest."
    assert not rewrite_preserves_comparison(source, DEFINITIONS["en"])


def test_targeted_retrieval_runs_for_requested_missing_dimensions():
    retrieval = Retrieval(initial=[chunk("stock", STOCK), chunk("bond", DEFINITIONS["fr"])])
    answer = ANSWERS["en"]
    result = GroundedGenerationService(retrieval, provider=provider(answer)).generate(
        GroundedGenerationRequest(
            original_query="Compare stock and bond risks.", language="en", script="latin"
        )
    )
    assert len(retrieval.requests) == 2 and result.grounded
