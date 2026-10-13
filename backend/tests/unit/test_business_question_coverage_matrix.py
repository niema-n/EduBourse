"""Scenario matrix: every requested item reaches one business call and survives validation.

Complements test_business_question_coverage.py (policy wiring and grounding contracts).
Assertions are structural: never exact prose, headings or word counts of model output.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.agents.answer_coverage import BUSINESS_QUESTION_COVERAGE
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk


def _retrieval(language: str, script: str, evidence_texts: list[str]):
    chunks = [
        RetrievedChunk(
            chunk_id=f"chunk-{index}",
            source_id="authorized-source",
            title="Guide pedagogique",
            page=index,
            page_start=index,
            page_end=index,
            text=text,
            rank=index,
            retrieval_score=0.1,
            score_type="cosine_distance",
        )
        for index, text in enumerate(evidence_texts, start=1)
    ]
    return SimpleNamespace(
        retrieve=Mock(
            return_value=RetrievalResult(
                original_query="question",
                language=language,
                script=script,
                policy_id="H1_LANGUAGE_ROUTED_V1",
                branches_used=["original"],
                retrieval_status="ok",
                chunks=chunks,
            )
        )
    )


def _provider(answer: str, ids: list[str]):
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


FR_IPO_QUESTION = "Explique-moi une IPO, ses etapes et les principaux acteurs impliques."
FR_IPO_ANSWER = (
    "Une IPO est une introduction en bourse.\n"
    "Etapes : preparation, visa, souscription, premiere cotation.\n"
    "Acteurs : l emetteur, la societe de bourse et le regulateur."
)
AR_COMPARISON_QUESTION = "ما الفرق بين السهم والسند من حيث الملكية والعائد والمخاطر؟"
AR_COMPARISON_ANSWER = (
    "الملكية: السهم أداة ملكية، والسند أداة دين.\n"
    "العائد: أرباح موزعة للسهم، وكوبون للسند.\n"
    "المخاطر: خسارة رأس المال للسهم، ومخاطر العجز للسند."
)
ARY_ARABIC_QUESTION = "شرح ليا شنو هي البورصة وكيفاش كتخدم وشنو الدور ديالها."
ARY_ARABIC_ANSWER = (
    "البورصة سوق منظم لتداول الأوراق المالية.\n"
    "كيفاش كتخدم: أوامر البيع والشراء كيتلاقاو فنظام التسعير.\n"
    "الدور ديالها: تمويل الشركات وتوفير السيولة."
)

SCENARIOS = [
    pytest.param(
        "fr",
        "latin",
        "C est quoi une IPO ?",
        ["Une IPO est une introduction en bourse."],
        "Une IPO est une introduction en bourse.",
        ["S1"],
        ("IPO",),
        id="single_aspect_fr",
    ),
    pytest.param(
        "fr",
        "latin",
        FR_IPO_QUESTION,
        [
            "Une IPO est une introduction en bourse.",
            "Les etapes sont la preparation, le visa, la souscription puis la cotation.",
            "Les acteurs sont l emetteur, la societe de bourse et le regulateur.",
        ],
        FR_IPO_ANSWER,
        ["S1", "S2", "S3"],
        ("IPO", "Etapes", "Acteurs"),
        id="multi_part_fr",
    ),
    pytest.param(
        "fr",
        "latin",
        "Compare l action et l obligation selon la nature, le rendement et le risque.",
        [
            "L action est un titre de propriete; l obligation est un titre de creance.",
            "L action rapporte des dividendes; l obligation verse des coupons.",
            "L action expose a la perte en capital; l obligation au risque de defaut.",
        ],
        "Nature : l action est un titre de propriete; l obligation est un titre de creance.\n"
        "Rendement : l action verse des dividendes; l obligation verse des coupons.\n"
        "Risque : l action expose a la perte en capital; l obligation au risque de defaut.",
        ["S1", "S2", "S3"],
        ("Nature", "Rendement", "Risque"),
        id="comparison_three_criteria",
    ),
    pytest.param(
        "fr",
        "latin",
        "Comment se deroule une introduction en bourse, qui y participe et dans quel but ?",
        [
            "L operation suit un calendrier: preparation, visa, souscription, cotation.",
            "L emetteur, les intermediaires et le regulateur interviennent.",
            "L objectif est de lever des capitaux pour financer le developpement.",
        ],
        "Deroule : preparation, visa, souscription, cotation.\n"
        "Participants : emetteur, intermediaires, regulateur.\n"
        "But : lever des capitaux pour financer le developpement.",
        ["S1", "S2", "S3"],
        ("Deroule", "Participants", "But"),
        id="process_steps_actors_purpose",
    ),
    pytest.param(
        "en",
        "latin",
        "What is a stock and what are its main sources of return and risk?",
        [
            "A stock is an ownership share in a company.",
            "Returns come from dividends and capital gains.",
            "Risks include capital loss and liquidity risk.",
        ],
        "A stock is an ownership share in a company.\n"
        "Return: dividends and capital gains.\n"
        "Risk: capital loss and liquidity risk.",
        ["S1", "S2", "S3"],
        ("stock", "Return", "Risk"),
        id="multi_part_en",
    ),
    pytest.param(
        "en",
        "latin",
        "What is a stock, and what custody fee does my broker charge?",
        ["A stock is an ownership share in a company."],
        "A stock is an ownership share in a company. The available sources do not "
        "establish the custody fee charged by your broker.",
        ["S1"],
        ("stock", "do not establish"),
        id="unsupported_aspect_is_named_not_invented",
    ),
    pytest.param(
        "ar",
        "arabic",
        AR_COMPARISON_QUESTION,
        [
            "السهم أداة ملكية والسند أداة دين.",
            "السهم يوزع أرباحاً والسند يدفع كوبوناً.",
            "السهم يعرض لخسارة رأس المال والسند لمخاطر العجز.",
        ],
        AR_COMPARISON_ANSWER,
        ["S1", "S2", "S3"],
        ("الملكية", "العائد", "المخاطر"),
        id="multi_part_ar",
    ),
    pytest.param(
        "ary",
        "arabic",
        ARY_ARABIC_QUESTION,
        [
            "البورصة سوق منظم لتداول الأوراق المالية.",
            "كتخدم بأوامر البيع والشراء اللي كتلتقى فنظام التسعير.",
            "الدور ديالها هو تمويل الشركات وتوفير السيولة.",
        ],
        ARY_ARABIC_ANSWER,
        ["S1", "S2", "S3"],
        ("البورصة", "كيفاش", "الدور"),
        id="multi_part_darija_arabic",
    ),
    pytest.param(
        "ary",
        "latin",
        "chno hiya lborsa, kifach katkhdem w chno dour dyalha?",
        [
            "La Bourse est un marche organise de titres.",
            "Les ordres d achat et de vente se rencontrent dans le systeme de cotation.",
            "Son role est de financer les entreprises et d apporter de la liquidite.",
        ],
        "Lborsa hiya marche mounaddam dyal titres.\n"
        "Kifach katkhdem: les ordres dyal achat w vente kaytla9aw f systeme de cotation.\n"
        "Dour dyalha: tmwil charikat w toufir dyal liquidite.",
        ["S1", "S2", "S3"],
        ("Lborsa", "Kifach", "Dour"),
        id="multi_part_darija_latin",
    ),
]


@pytest.mark.parametrize(
    ("language", "script", "question", "evidence", "answer", "ids", "expected_items"),
    SCENARIOS,
)
def test_requested_items_reach_one_business_call_and_survive_validation(
    language, script, question, evidence, answer, ids, expected_items
):
    retrieval = _retrieval(language, script, evidence)
    provider = _provider(answer, list(ids))

    result = GroundedGenerationService(retrieval, provider=provider).generate(
        GroundedGenerationRequest(original_query=question, language=language, script=script)
    )

    assert result.generation_status == "ok" and result.grounded
    # Completeness is decided at business generation; validation returns it untouched.
    assert result.answer == answer
    for item in expected_items:
        assert item in result.answer
    assert result.used_evidence_ids == list(ids)
    assert [citation.evidence_id for citation in result.citations] == list(ids)
    # Exactly one business call: no extra stage recovers missing content.
    provider.generate.assert_called_once()
    system_prompt, user_prompt = provider.generate.call_args.args
    assert BUSINESS_QUESTION_COVERAGE in system_prompt
    assert question in user_prompt  # every requested part is visible to the model
    for text in evidence:
        assert text in user_prompt


def test_simple_question_answer_is_never_expanded_downstream():
    """Adaptive depth: a concise supported answer stays concise end to end."""
    concise = "Un dividende est une part des benefices versee aux actionnaires."
    retrieval = _retrieval("fr", "latin", ["Un dividende est une part des benefices versee."])
    provider = _provider(concise, ["S1"])

    result = GroundedGenerationService(retrieval, provider=provider).generate(
        GroundedGenerationRequest(
            original_query="C est quoi un dividende ?", language="fr", script="latin"
        )
    )

    assert result.answer == concise
    assert len(result.answer.split()) <= 20
