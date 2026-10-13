"""Regressions for the live Darija comparison rejection of 2026-09-23.

The generator produced a correct comparison that was refused because lexical feature
attribution charged creditor repayment to the stock, because the shareholder
information right was not recognised, and because a pedagogical enrichment dimension
(stock risk) had no retrieved evidence. Grounding itself is unchanged: an unsupported
dimension still fails closed.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from app.rag.comparison import (
    CONCEPTS,
    answer_covers,
    comparison_concepts,
    comparison_gaps,
    concepts_in,
    coverage,
    desired_dimensions,
    features_in,
    has_source_mechanics,
    required_dimensions,
)
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

STOCK = next(c for c in CONCEPTS if c.key == "stock")
BOND = next(c for c in CONCEPTS if c.key == "bond")

QUESTION = "شنو الفرق بين السهم والسند؟"

# Base evidence: the stock is defined with its return and rights, the bond only has a
# right. This is the shape the live retrieval produced for this question.
STOCK_BASE = (
    "L'action est un titre de propriété représentant une fraction du capital de la "
    "société. Le droit au dividende : la rémunération versée aux actionnaires. "
    "Le droit de vote lors des assemblées générales. "
    "Le droit à l'information sur la situation de l'entreprise."
)
BOND_BASE = "L'obligation prévoit un remboursement du principal à l'échéance."
STOCK_RISK = (
    "Les risques associés aux actions : le risque de perte en capital, "
    "le risque de liquidité et le risque de défaut de l'entreprise."
)
BOND_FULL = (
    "L'obligation est un titre de créance : l'investisseur prête de l'argent à "
    "l'émetteur, qui verse un coupon d'intérêt et rembourse le principal à l'échéance. "
    "Le risque de défaut de l'émetteur existe."
)
ANSWER = (
    "السهم هو أداة ملكية كتمثل حصة من راس مال الشركة، وكيعطي الحق فالأرباح الموزعة "
    "وحق التصويت وحق الحصول على المعلومات، وفيه خطر خسارة راس المال. "
    "أما السند فهو أداة دين: المستثمر كيسلف الفلوس للجهة المصدرة، وكياخذ فوايد (كوبون)، "
    "وكيتسدد ليه راس المال فتاريخ الاستحقاق، وفيه خطر التعثر."
)


def chunk(key, text):
    return RetrievedChunk(
        chunk_id=key,
        source_id="approved-corpus",
        title="Guide officiel",
        page=8,
        page_start=8,
        page_end=8,
        text=text,
        rank=1,
        retrieval_score=0.1,
        score_type="cosine_distance",
    )


class Retrieval:
    """Answers the base search, then one enrichment search per concept."""

    def __init__(self, base, stock_gap=None, bond_gap=None):
        self.base = base
        self.stock_gap = stock_gap
        self.bond_gap = bond_gap
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            chunks = self.base
        elif "السهم" in request.original_query:
            chunks = self.stock_gap or []
        else:
            chunks = self.bond_gap or []
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original", "french_adapted"],
            retrieval_status="ok",
            chunks=chunks,
        )


def provider(answer, ids):
    return SimpleNamespace(
        model=GENERATION_MODEL,
        generate=Mock(
            return_value={
                "answer": answer,
                "used_evidence_ids": ids,
                "insufficient_evidence": False,
            }
        ),
    )


def test_darija_comparison_is_grounded_after_per_concept_enrichment():
    retrieval = Retrieval(
        [chunk("stock", STOCK_BASE), chunk("bond", BOND_BASE)],
        stock_gap=[chunk("stock-risk", STOCK_RISK)],
        bond_gap=[chunk("bond-full", BOND_FULL)],
    )
    llm = provider(ANSWER, ["stock", "bond-full", "stock-risk"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=QUESTION, language="ary", script="arabic")
    )
    # One base search plus one bounded enrichment search per compared concept.
    assert len(retrieval.requests) == 3
    assert "السهم" in retrieval.requests[1].original_query
    assert "المخاطر" in retrieval.requests[1].original_query
    assert retrieval.requests[1].conversation_context is None
    assert result.grounded and result.generation_status == "ok"
    assert not result.comparison_incomplete
    assert {c.chunk_id for c in result.citations} == {"stock", "bond-full", "stock-risk"}
    system, payload = llm.generate.call_args.args
    assert "COMPARISON COMPLETENESS CONTRACT" in system
    assert "COMPARISON_SUPPORTED: stock=" in payload and "bond=" in payload
    for concept in (STOCK, BOND):
        assert {"definition", "return", "risk", "rights"} <= coverage(result.answer, concept)


def test_creditor_repayment_is_not_a_stock_feature():
    arabic = (
        "السهم كيعطي حق التصفية: من بعد تسديد ديون الدائنين، "
        "كياخد المساهم حصة من صافي الأصول."
    )
    french = "L'action donne droit à une part du patrimoine après remboursement des créanciers."
    for text in (arabic, french):
        assert "repayment" not in features_in(text, STOCK)


def test_shareholder_information_right_validates_against_its_evidence():
    assert "information" in features_in(STOCK_BASE, STOCK)
    assert "information" in features_in(ANSWER, STOCK)
    assert answer_covers(
        ANSWER,
        comparison_concepts(QUESTION),
        [chunk("stock", STOCK_BASE), chunk("stock-risk", STOCK_RISK), chunk("bond", BOND_FULL)],
        required=required_dimensions(QUESTION),
    )


def test_issuer_legal_duty_is_not_a_bond_mention():
    duty = (
        "L'émetteur de l'action a l'obligation de mettre à votre disposition le bilan "
        "et le droit à l'information est garanti."
    )
    assert {c.key for c in concepts_in(duty)} == {"stock"}
    assert "information" in features_in(duty, STOCK)


def test_bond_principal_repayment_is_supported_when_stated():
    assert "repayment" in features_in(BOND_FULL, BOND)
    assert "rights" in coverage(BOND_FULL, BOND)


def test_unsupported_stock_risk_still_fails_closed():
    assert not answer_covers(
        ANSWER,
        comparison_concepts(QUESTION),
        [chunk("stock", STOCK_BASE), chunk("bond", BOND_FULL)],
        required=required_dimensions(QUESTION),
    )


def test_retrieval_report_wording_is_detected_without_flagging_the_issuer():
    reports = [
        "المصادر المتوفرة ما كتقدمش تعريف مباشر للسند.",
        "المقاطع المرفقة ما كتذكرش الحقوق المرتبطة بالسند.",
        "لا يذكر المصدر صراحةً حقوقاً غير مالية للسند.",
        "على حساب المعلومات المتوفرة، الفرق كيتوضح كالتالي.",
        "The sources do not define a bond.",
    ]
    prose = [
        "السند هو قرض كتعطيه للجهة المصدرة، والمصدر كيخلص ليك الفوائد.",
        "السهم كيعطي حقوق مالية وحقوق غير مالية بحال حق التصويت.",
        "السند ما كيعطيش حق التصويت.",
        "السهم أداة ملكية والسند أداة دين على الجهة المصدرة.",
    ]
    assert all(has_source_mechanics(text) for text in reports)
    assert not any(has_source_mechanics(text) for text in prose)


def test_rejection_reasons_name_the_failing_predicate():
    gaps = comparison_gaps(
        ANSWER,
        comparison_concepts(QUESTION),
        [chunk("stock", STOCK_BASE), chunk("bond", BOND_FULL)],
        required=required_dimensions(QUESTION),
    )
    assert "stock.risk_claimed_without_cited_evidence" in gaps
    assert not comparison_gaps(
        ANSWER,
        comparison_concepts(QUESTION),
        [chunk("stock", STOCK_BASE), chunk("stock-risk", STOCK_RISK), chunk("bond", BOND_FULL)],
        required=required_dimensions(QUESTION),
    )


def test_generic_difference_query_requires_only_definitions():
    assert required_dimensions(QUESTION) == {"definition"}
    assert desired_dimensions(QUESTION) == {"definition", "return", "risk", "rights"}
    explicit = "Compare stocks and bonds: returns and risks."
    assert {"definition", "return", "risk"} <= required_dimensions(explicit)


def test_single_concept_question_is_not_enriched():
    retrieval = Retrieval([chunk("stock", STOCK_BASE)])
    llm = provider("Une action est un titre de propriété du capital.", ["stock"])
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(
            original_query="Qu'est-ce qu'une action ?", language="fr", script="latin"
        )
    )
    assert len(retrieval.requests) == 1 and result.grounded
    system, payload = llm.generate.call_args.args
    assert "COMPARISON COMPLETENESS CONTRACT" not in system
    assert "COMPARISON_SUPPORTED" not in payload
