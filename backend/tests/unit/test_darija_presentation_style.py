"""Darija presentation style: a teaching voice, not a report — grounding unchanged.

Style lives in two existing instructions: the comparison contract shapes the drafted
business answer, the composer's ary+arabic rule renders it in Darija. Nothing here
relaxes grounding: an unsupported claim or retrieval-report wording still fails closed.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.graph.final_response_composer import COMPOSER_SYSTEM_PROMPT
from app.rag.comparison import COMPARISON_INSTRUCTION, answer_covers, comparison_concepts
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GroundedGenerationRequest,
    GroundedGenerationService,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

QUESTION = "شنو الفرق بين السهم والسند؟"
STOCK_EVIDENCE = (
    "L'action est un titre de propriété d'une fraction du capital de la société. "
    "Le droit au dividende rémunère l'actionnaire et le droit de vote s'exerce en "
    "assemblée générale. Les risques associés aux actions sont la perte en capital "
    "et le risque de liquidité."
)
BOND_EVIDENCE = (
    "L'obligation est un titre de créance : l'investisseur prête à l'émetteur, reçoit "
    "un coupon d'intérêt et le remboursement du principal à l'échéance. Le risque de "
    "défaut de l'émetteur reste possible."
)
# A compact teaching answer: the distinction first, one idea per sentence, no report.
CONCISE = (
    "السهم كيمثّل حصة فملكية الشركة، أما السند فهو دين على الجهة المصدرة. "
    "ملي كتشري سهم كتولي مساهم، والعائد كيجي من الأرباح الموزعة، وعندك حق التصويت "
    "فالجمعية العامة، ولكن كاينة مخاطرة خسارة راس المال وصعوبة البيع. "
    "أما السند فكتسلف الفلوس للجهة المصدرة، وكتاخذ الفوائد، وكيتسدد ليك راس المال "
    "عند الاستحقاق، مع مخاطرة التعثر ديال المصدر. "
    "الخلاصة: السهم ملكية والسند دين."
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


EVIDENCE = [chunk("stock", STOCK_EVIDENCE), chunk("bond", BOND_EVIDENCE)]


class Retrieval:
    def __init__(self):
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original"],
            retrieval_status="ok",
            chunks=EVIDENCE,
        )


def run(answer, ids=("stock", "bond"), language="ary", script="arabic", query=QUESTION):
    retrieval = Retrieval()
    llm = SimpleNamespace(
        model=GENERATION_MODEL,
        generate=Mock(
            return_value={
                "answer": answer,
                "used_evidence_ids": list(ids),
                "insufficient_evidence": False,
            }
        ),
    )
    result = GroundedGenerationService(retrieval, provider=llm).generate(
        GroundedGenerationRequest(original_query=query, language=language, script=script)
    )
    return result, llm


def test_comparison_contract_asks_for_a_compact_teaching_shape():
    _result, llm = run(CONCISE)
    system = llm.generate.call_args.args[0]
    assert COMPARISON_INSTRUCTION in system
    assert "120-220 words" in system
    assert "prefer flowing prose over a multi-section report" in system
    assert "one short paragraph per" in system
    assert "expand only when the user asked for a detailed treatment" in system
    system_flat = " ".join(system.split())
    assert "replaces the general criterion-by-criterion presentation" in system_flat
    assert "no bullet list unless the user asked for one" in system_flat


def test_darija_rendering_rule_carries_the_style_contract_once():
    block = COMPOSER_SYSTEM_PROMPT.split("- ary + arabic:")[1].split("- ary + latin:")[0]
    # Wrapping is free to change; the contract is what must be there.
    rule = " ".join(block.split())
    assert "senior Moroccan capital-markets educator" in rule
    assert "one idea per short paragraph" in rule
    assert "the way a teacher says it aloud" in rule
    assert "Shorten the wording, never the content" in rule
    assert "compared instrument keeps its definition" in rule
    assert "الأرباح الموزعة" in rule
    assert "easy to read aloud" in rule
    assert "Write grammatically correct Darija" in rule
    assert "repair any malformed word or verb form" in rule
    # The contract lives in this one rule, not duplicated across the prompt.
    assert COMPOSER_SYSTEM_PROMPT.count("easy to read aloud") == 1
    assert COMPOSER_SYSTEM_PROMPT.count("Write grammatically correct Darija") == 1


def test_no_hardcoded_wording_correction_exists_in_production_code():
    """The grammar rule generalizes: no phrase-specific repair table anywhere."""
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[2] / "app"
    sources = [
        path.read_text(encoding="utf-8")
        for path in app_dir.rglob("*.py")
    ]
    assert sources
    for text in sources:
        assert "احتافظ" not in text
        assert "احتفظ" not in text


def test_concise_darija_comparison_stays_grounded():
    result, _llm = run(CONCISE)
    assert result.grounded and result.generation_status == "ok"
    assert [c.chunk_id for c in result.citations] == ["stock", "bond"]
    assert answer_covers(CONCISE, comparison_concepts(QUESTION), EVIDENCE)
    arabic = sum(1 for ch in result.answer if "؀" <= ch <= "ۿ")
    assert arabic > 0 and not any(ch.isascii() and ch.isalpha() for ch in result.answer)
    assert result.answer.startswith("السهم")


@pytest.mark.parametrize(
    "addition",
    [
        " والعائد ديال السند مضمون 7% فالعام.",  # unsupported figure
        " والسهم كيعطي كوبون ثابت.",  # mechanism of the other instrument
        " حسب المصدر، السند ما كيعطيش حق التصويت.",  # retrieval-report wording
        " المصادر المتوفرة ما كتذكرش المخاطر.",
    ],
)
def test_style_does_not_buy_an_unsupported_or_source_reporting_answer(addition):
    result, _llm = run(CONCISE + addition)
    assert not result.grounded and result.citations == []
    assert result.comparison_incomplete


def test_non_darija_language_rules_are_unchanged():
    for rule in (
        "- fr: use clear, professional and pedagogical French.",
        "- en: use natural professional English; do not translate French literally.",
        "- ar: use clear Modern Standard Arabic, not Darija.",
    ):
        assert rule in COMPOSER_SYSTEM_PROMPT
    french = (
        "Une action est un titre de propriété du capital et donne droit au dividende "
        "ainsi qu'au droit de vote, avec un risque de perte en capital. "
        "Une obligation est un titre de créance : elle verse un coupon d'intérêt et "
        "prévoit le remboursement du principal à l'échéance, avec un risque de défaut."
    )
    result, llm = run(
        french,
        language="fr",
        script="latin",
        query="Quelle est la différence entre une action et une obligation ?",
    )
    assert result.grounded and result.generation_status == "ok"
    assert "ary" not in llm.generate.call_args.args[1].split("requested_language: ")[1][:8]
