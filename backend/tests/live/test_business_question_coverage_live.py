"""Opt-in semantic probes of REAL business generation, before Azure rendering.

Run with EDUBOURSE_LIVE_COVERAGE=1. Fixtures are source context, not canned answers.
Concept cues allow paraphrases and arbitrary layout; saved answers also permit review.
"""

import json
import os
import re
from pathlib import Path

import pytest

from app.graph.intent import normalize_text
from app.graph.response_localizer import business_answer_locale
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroqGroundedGenerationProvider,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

pytestmark = pytest.mark.skipif(
    os.getenv("EDUBOURSE_LIVE_COVERAGE") != "1", reason="Opt-in real provider coverage evaluation"
)

OWNERSHIP = (
    "A stock represents ownership of part of a company. A bond is a debt: its holder is a "
    "creditor, not an owner. Stocks may pay dividends and generate a capital gain on resale. "
    "A bond generally pays interest and repays principal at maturity. A stock's price can "
    "fall, and dividends are not guaranteed. Bond holders face issuer default risk and "
    "a resale price that can fall when market interest rates rise."
)
EXCHANGE = (
    "A stock exchange is an organized market for securities. Licensed intermediaries transmit "
    "investors' buy and sell orders; matching compatible orders produces trades. The exchange "
    "organizes trading and price formation. It helps companies raise capital and investors "
    "trade existing securities. It does not guarantee profits."
)
CASES = [
    {
        "id": "fr_single",
        "language": "fr",
        "script": "latin",
        "question": "Qu'est-ce qu'un indice boursier ?",
        "source": "Un indice boursier mesure l'évolution d'un ensemble de titres sélectionnés.",
        "aspects": {"definition": [r"indic|mesur|indicateur", r"ensemble|panier|groupe"]},
        "max_words": 65,
    },
    {
        "id": "fr_multi",
        "language": "fr",
        "script": "latin",
        "question": "Qu'est-ce qu'une obligation et quels sont ses risques ?",
        "source": OWNERSHIP,
        "aspects": {
            "definition": [r"dette|creance|creancier"],
            "default": [r"defaut|rembours|honorer"],
            "rate_risk": [r"taux", r"bais|perte"],
        },
    },
    {
        "id": "fr_comparison",
        "language": "fr",
        "script": "latin",
        "question": "Compare une action et une obligation : propriété, rendement et risques.",
        "source": OWNERSHIP,
        "aspects": {
            "ownership_stock": [r"propriet|capital"],
            "ownership_bond": [r"creanc|dette"],
            "return_stock": [r"dividende", r"plus.value|gain"],
            "return_bond": [r"interet|coupon"],
            "risk_stock": [r"cours|prix", r"bais|perte"],
            "risk_bond": [r"defaut|non.remboursement", r"taux"],
        },
    },
    {
        "id": "fr_process",
        "language": "fr",
        "script": "latin",
        "question": (
            "Explique-moi une IPO, ses étapes, les acteurs impliqués et son objectif."
        ),
        "source": "Une IPO est la première mise à disposition d'actions d'une "
        "entreprise au public. "
        "Elle permet de lever des capitaux. L'entreprise et ses conseillers préparent "
        "l'opération. L'autorité examine le prospectus. Les investisseurs souscrivent "
        "puis la Bourse organise la première cotation.",
        "aspects": {
            "definition": [r"premier|introduction", r"public"],
            "preparation": [r"prepar"],
            "prospectus": [r"prospectus"],
            "subscription": [r"souscri|souscrip"],
            "listing": [r"cotation"],
            "actors": [r"entreprise", r"conseill", r"autorite", r"investisseur", r"bourse"],
            "objective": [r"capitaux|financ"],
        },
    },
    {
        "id": "en_multi",
        "language": "en",
        "script": "latin",
        "question": "What is a stock and what are its main sources of return and risk?",
        "source": OWNERSHIP,
        "aspects": {
            "definition": [r"owner|equity"],
            "dividends": [r"dividend"],
            "capital_gain": [r"capital gain|resale|sell|selling"],
            "price_risk": [r"price", r"fall|declin|loss|lose"],
            "income_risk": [r"dividend", r"not guaranteed|uncertain|no guarantee"],
        },
    },
    {
        "id": "ar_comparison",
        "language": "ar",
        "script": "arabic",
        "question": "ما الفرق بين السهم والسند من حيث الملكية والعائد والمخاطر؟",
        "source": OWNERSHIP,
        "aspects": {
            "ownership": [r"ملك|مالك", r"دين|داين"],
            "return_stock": [r"ارباح|توزيع", r"بيع|راس.*مال"],
            "return_bond": [r"فايد|فوايد"],
            "risks": [r"انخفاض|خسا|تراجع", r"تعثر|تخلف|سداد", r"فايد|فوايد"],
        },
    },
    {
        "id": "ary_arabic",
        "language": "ary",
        "script": "arabic",
        "question": "شرح ليا شنو هي البورصة وكيفاش كتخدم وشنو الدور ديالها.",
        "source": EXCHANGE,
        "aspects": {
            "definition": [r"سوق"],
            "mechanism": [r"اوامر|طلبات", r"بيع", r"شر"],
            "intermediaries": [r"وسط|وسيط"],
            "role": [r"تمويل|راس.*مال|اموال|فلوس"],
        },
    },
    {
        "id": "ary_latin",
        "language": "ary",
        "script": "latin",
        "question": "Chno howa fonds indiciel, kifach kaykhdem w chno l7odod dyalou?",
        "source": "An index fund is a collective investment fund aiming to track an index. "
        "It holds securities representing that index. Its value can fall when the "
        "index falls. It does not guarantee capital or returns.",
        "aspects": {
            "definition": [r"fond|sandou9|sando9", r"indic|index|mo2ach|moach"],
            "mechanism": [r"titres|securit|awra9|ashom|asham|as8om|saham"],
            "limits": [r"hbet|hbat|n9es|n9as|khser|khsar|baisse|tih|ti7|tn9es|yhbe|yhb"],
        },
    },
    {
        "id": "unsupported_aspect",
        "language": "fr",
        "script": "latin",
        "question": (
            "Définis un ETF et donne les frais annuels exacts de conservation "
            "chez mon courtier."
        ),
        "source": "Un ETF est un fonds négocié en Bourse qui cherche à suivre un indice.",
        "aspects": {
            "definition": [r"fonds", r"indice"],
            "specific_gap": [
                r"frais",
                r"courtier|conservation",
                r"pas|aucun|insuffisant|indisponible|manqu|absent",
            ],
        },
        "forbidden": [r"\d\s*%", r"\d\s*(?:euro|dirham|mad|eur)"],
    },
    {
        "id": "concise_simple",
        "language": "en",
        "script": "latin",
        "question": "Define a stock in one sentence.",
        "source": OWNERSHIP,
        "aspects": {"definition": [r"owner|equity", r"company|business"]},
        "max_words": 45,
        "forbidden": [r"dividend|risk|bond"],
    },
    {
        "id": "follow_up",
        "language": "fr",
        "script": "latin",
        "question": "Et son fonctionnement et ses limites ?",
        "memory": '{"user":"Explique un ordre à cours limité."}',
        "source": "Un ordre à cours limité fixe un prix maximal à l'achat ou minimal à la vente. "
        "Il n'est exécuté que si une contrepartie accepte ce prix. Son exécution peut "
        "être partielle ou ne jamais avoir lieu.",
        "aspects": {
            "mechanism": [r"prix", r"maxim|plafond", r"minim|plancher"],
            "limits": [r"partiel", r"jamais|non.execution|pas.*execut|aucune|sans execution"],
        },
    },
]


class SourceFixture:
    def __init__(self, source):
        self.source = source

    def retrieve(self, request):
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original"],
            retrieval_status="ok",
            chunks=[
                RetrievedChunk(
                    chunk_id="coverage-fixture",
                    source_id="coverage-source",
                    title="Educational fixture",
                    page=1,
                    page_start=1,
                    page_end=1,
                    text=self.source,
                    rank=1,
                    retrieval_score=0.1,
                    score_type="cosine_distance",
                )
            ],
        )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_real_business_answer_covers_requested_aspects(case):
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY unavailable")
    provider = GroqGroundedGenerationProvider(api_key=api_key, model=GENERATION_MODEL)
    answer_language, answer_script = business_answer_locale(case["language"], case["script"])
    service = GroundedGenerationService(SourceFixture(case["source"]), provider=provider)
    result = service.generate(
        GroundedGenerationRequest(
            original_query=case["question"],
            language=case["language"],
            script=case["script"],
            memory_context=case.get("memory"),
            answer_language=answer_language,
            answer_script=answer_script,
        )
    )
    answer = normalize_text(result.answer or "")
    aspects = case["aspects"]
    if case["id"] == "ary_latin":
        # The production pipeline generates in French before Darija localization.
        aspects = {
            "definition": [r"fonds", r"indic"],
            "mechanism": [r"detien|invest|compos|titres", r"indice"],
            "limits": [r"bais|perte|diminu", r"garanti"],
        }
    coverage = {
        aspect: all(re.search(pattern, answer) for pattern in patterns)
        for aspect, patterns in aspects.items()
    }
    output = Path(__file__).resolve().parents[2] / "reports" / "business-coverage-live"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{case['id']}.json").write_text(
        json.dumps(
            {
                "case": case,
                "result": result.model_dump(mode="json"),
                "coverage": coverage,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    assert result.generation_status == "ok", result
    assert result.grounded and result.used_evidence_ids == ["S1"]
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "coverage-fixture"
    assert all(coverage.values()), {"coverage": coverage, "answer": result.answer}
    if "max_words" in case:
        assert len(answer.split()) <= case["max_words"]
    for pattern in case.get("forbidden", []):
        assert not re.search(pattern, answer), result.answer
    assert "السهم الالزامي" not in answer
