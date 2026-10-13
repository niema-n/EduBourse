"""Phase A response-quality policy: educational depth stays grounded in SOURCE CONTEXT."""

import json

import pytest

from app.graph.final_response_composer import _validate_final_answer_result
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GROUNDING_SYSTEM_PROMPT,
    GroqGroundedGenerationProvider,
    GroundedGenerationRequest,
    GroundedGenerationService,
    GroundedProviderOutput,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

IPO_EVIDENCE = [
    "L'introduction en bourse (IPO) consiste à mettre une partie du capital d'une entreprise "
    "à la disposition du public en contrepartie de nouveaux capitaux.",
    "Les grandes étapes : préparation, visa du prospectus par l'autorité, période de "
    "souscription, puis première cotation. Souscrire à une IPO équivaut à acheter des "
    "actions dont le cours peut fluctuer à la hausse comme à la baisse.",
]


def _chunk(index: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{index}",
        source_id="ammc-comprendre-les-ipo",
        title="Comprendre les IPO",
        page=index,
        page_start=index,
        page_end=index,
        heading="IPO",
        text=text,
        rank=index,
        retrieval_score=0.1,
        score_type="cosine_distance",
    )


class FakeRetrieval:
    def __init__(self, texts):
        self.chunks = [_chunk(index, text) for index, text in enumerate(texts, start=1)]

    def retrieve(self, request):
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["original"],
            chunks=self.chunks,
            retrieval_status="ok",
        )


class RecordingProvider:
    model = GENERATION_MODEL

    def __init__(self, output):
        self.output = output
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.output


def _request(query="C'est quoi une IPO ?", language="fr", script="latin"):
    return GroundedGenerationRequest(original_query=query, language=language, script=script)


# A. Definitions are asked to use the richer supported context, not only the first definition.
def test_definition_policy_keeps_additional_depth_conditional_on_the_request():
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "EDUCATIONAL DEPTH" in prompt
    assert "Use all the relevant information in SOURCE CONTEXT" in prompt
    for element in ("how it works", "role or", "simple example if the sources give one",
                    "main risks or limits if the sources", "takeaway"):
        assert element in prompt
    assert "only when asked" in prompt
    assert "no minimum word count" in prompt


def test_definition_answer_can_cite_every_supporting_chunk():
    answer = (
        "Une IPO (introduction en bourse) consiste à mettre une partie du capital d'une "
        "entreprise à la disposition du public contre de nouveaux capitaux.\n\n"
        "1. Préparation de l'opération\n2. Visa du prospectus\n3. Période de souscription\n"
        "4. Première cotation\n\nÀ retenir : le cours peut fluctuer à la hausse comme à la baisse."
    )
    provider = RecordingProvider(
        GroundedProviderOutput(answer=answer, used_evidence_ids=["S1", "S2"],
                               insufficient_evidence=False)
    )
    result = GroundedGenerationService(FakeRetrieval(IPO_EVIDENCE), provider=provider).generate(
        _request()
    )
    assert result.generation_status == "ok"
    assert result.grounded is True
    assert result.used_evidence_ids == ["S1", "S2"]
    system_prompt, user_prompt = provider.calls[0]
    assert system_prompt == GROUNDING_SYSTEM_PROMPT
    assert "[S1]" in user_prompt and "[S2]" in user_prompt


# B. Comparisons use parallel criteria.
def test_comparison_policy_uses_parallel_criteria():
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "Comparison: parallel criteria supported by the sources" in prompt
    for criterion in ("nature", "rights", "remuneration or return", "risks", "maturity"):
        assert criterion in prompt
    assert "criterion by criterion" in prompt


# C. Risk answers explain each risk instead of listing names.
def test_risk_policy_explains_each_risk():
    assert (
        "Risks: name each risk, then briefly explain what it means and what it implies for the\n"
        "  investor." in GROUNDING_SYSTEM_PROMPT
    )


def test_process_policy_covers_steps_actors_mechanism_and_purpose():
    assert "the steps in order, the actors involved, the mechanism and its" in (
        GROUNDING_SYSTEM_PROMPT
    )


# D. Depth never licenses unsupported facts; the grounding contract is unchanged.
def test_depth_policy_forbids_unsupported_facts_and_padding():
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "never add a fact, example, figure or risk that SOURCE CONTEXT does not state" in prompt
    assert "never pad, and answer more briefly when SOURCE CONTEXT is thin" in prompt
    assert "Answer the user's question ONLY from the supplied SOURCE CONTEXT." in prompt
    assert "Never use unsupported outside knowledge" in prompt
    assert "Never predict markets, recommend a buy or sell, or suggest a portfolio allocation" in (
        prompt
    )
    assert (
        "Return only a JSON object with exactly: answer, used_evidence_ids, insufficient_evidence."
        in prompt
    )


# Markdown structure belongs inside the answer string; a fenced response breaks json.loads.
def test_markdown_is_scoped_to_answer_string_and_response_stays_raw_json():
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "Inside the answer string only, use short paragraphs" in prompt
    assert prompt.rstrip().endswith(
        "The response itself must be that raw JSON object: no Markdown code fence and no text "
        "before\nor after it."
    )


def test_long_answer_citing_unknown_evidence_still_fails_closed():
    provider = RecordingProvider(
        GroundedProviderOutput(answer="Une IPO... " * 80, used_evidence_ids=["S1", "S9"],
                               insufficient_evidence=False)
    )
    result = GroundedGenerationService(FakeRetrieval(IPO_EVIDENCE), provider=provider).generate(
        _request()
    )
    assert result.generation_status == "grounding_error"
    assert result.answer is None
    assert result.grounded is False


# E. Arabic business terminology: bond = سند/سندات, stock = سهم/أسهم.
def test_arabic_bond_and_stock_terminology_rule():
    prompt = GROUNDING_SYSTEM_PROMPT
    assert "an obligation (bond) is سند, plural سندات" in prompt
    assert "(stock, share) is سهم, plural أسهم" in prompt
    assert "Never call a bond السهم الإلزامي" in prompt
    assert "Do not call a stock\nسند ملكية" in prompt


# F. A long educational JSON response stays valid within the larger token budget.
class _FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message, "finish_reason": "stop"})()
        return type("Response", (), {"choices": [choice]})()


@pytest.mark.parametrize(
    "answer",
    [
        "\n".join(f"{n}. Étape détaillée de l'introduction en bourse." for n in range(1, 40)),
        "\n".join(f"{n}. السند أداة دين تجعل المستثمر دائناً للمُصدر." for n in range(1, 40)),
    ],
)
def test_long_json_response_is_parsed_with_1200_token_budget(answer):
    provider = GroqGroundedGenerationProvider(api_key="test-key")
    fake = _FakeCompletions(
        json.dumps(
            {"answer": answer, "used_evidence_ids": ["S1", "S2"], "insufficient_evidence": False},
            ensure_ascii=False,
        )
    )
    provider._client = type("Client", (), {"chat": type("Chat", (), {"completions": fake})()})()
    output = provider.generate(GROUNDING_SYSTEM_PROMPT, "user prompt")
    assert fake.kwargs["max_completion_tokens"] == 1200
    assert fake.kwargs["temperature"] == 0
    assert "response_format" not in fake.kwargs
    parsed = GroundedProviderOutput.model_validate(output)
    assert parsed.answer == answer
    assert parsed.used_evidence_ids == ["S1", "S2"]


# G. The final composer still preserves the richer business content it receives.
LONG_BUSINESS_ANSWER = (
    "Une obligation est un titre de créance.\n"
    "- Rémunération : des coupons versés périodiquement.\n"
    "- Remboursement : le capital est rendu à l'échéance.\n"
    "- Risque de taux : le prix baisse quand les taux montent.\n"
    "- Risque de défaut : l'émetteur peut ne pas honorer ses engagements.\n"
    "- Risque de liquidité : il peut être difficile de revendre le titre."
)


def test_composer_accepts_faithful_presentation_of_long_business_answer():
    candidate = LONG_BUSINESS_ANSWER.replace("Une obligation est", "Une obligation est avant tout")
    result = _validate_final_answer_result(
        LONG_BUSINESS_ANSWER, candidate, "fr", "latin", {"status": "completed"}
    )
    assert result.accepted, result.reasons


def test_composer_rejects_dropping_supported_risk_items():
    compressed = "\n".join(LONG_BUSINESS_ANSWER.splitlines()[:3])
    result = _validate_final_answer_result(
        LONG_BUSINESS_ANSWER, compressed, "fr", "latin", {"status": "completed"}
    )
    assert not result.accepted
    assert "list_item_loss" in result.reasons
