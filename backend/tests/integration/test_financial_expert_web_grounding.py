from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.api.chat import process_text_message
from app.financial_expert.freshness import requires_current_information
from app.financial_expert.models import FinancialExpertRequest
from app.financial_expert.provider import FinancialExpertGeneration
from app.financial_expert.service import FinancialExpertService
from app.graph.core import build_graph
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest


class FakeExpertProvider:
    provider_name = "fake-gemini"
    model = "gemini-2.5-flash"

    def __init__(self, response: FinancialExpertGeneration | Exception):
        self.response = response
        self.calls: list[dict[str, object]] = []

    def generate(self, question, system_prompt, *, use_web_grounding=False):
        self.calls.append(
            {
                "question": question,
                "system_prompt": system_prompt,
                "use_web_grounding": use_web_grounding,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def request(language: str, script: str, question: str) -> FinancialExpertRequest:
    return FinancialExpertRequest(question=question, language=language, script=script)


def grounded_response(language: str, script: str) -> FinancialExpertGeneration:
    answer = {
        ("fr", "latin"): "Le cours actuel est confirmé par une source web.",
        ("en", "latin"): "The current quote is supported by a web source.",
        ("ar", "arabic"): "السعر الحالي تؤكده مصادر الويب.",
        ("ary", "latin"): "Taman daba m2akked b masdar mn lweb.",
        ("ary", "arabic"): "الثمن دابا مؤكد بمصدر من الويب.",
    }[(language, script)]
    return FinancialExpertGeneration(
        text=answer,
        web_grounded=True,
        web_sources=(
            {"title": "casablanca-bourse.com"},
            {"domain": "ammc.ma", "uri": "https://www.ammc.ma/quote"},
        ),
    )


@pytest.mark.parametrize(
    ("language", "script", "question"),
    [
        ("fr", "latin", "Quel est le cours de SGTM aujourd'hui ?"),
        ("en", "latin", "What is SGTM's price today?"),
        ("ar", "arabic", "ما هو سعر السهم اليوم؟"),
        ("ary", "latin", "Ch7al taman dyal SGTM lyoma?"),
        ("ary", "arabic", "شنو هو الثمن ديال السهم اليوم؟"),
    ],
)
def test_current_questions_use_web_grounding_and_preserve_locale(language, script, question):
    provider = FakeExpertProvider(grounded_response(language, script))
    result = FinancialExpertService(provider, web_grounding_enabled=True).answer(
        request(language, script, question)
    )

    assert provider.calls[0]["use_web_grounding"] is True
    assert result.language == language
    assert result.script == script
    assert result.knowledge_source == "llm_web_grounded_financial_knowledge"
    assert result.web_grounded is True
    assert result.web_sources[0].title == "casablanca-bourse.com"
    assert result.web_sources[1].uri == "https://www.ammc.ma/quote"


def test_general_finance_does_not_use_web_grounding():
    provider = FakeExpertProvider(
        FinancialExpertGeneration(text="Duration explains bond sensitivity.")
    )
    result = FinancialExpertService(provider, web_grounding_enabled=True).answer(
        request("en", "latin", "Why do bond prices react to interest rates?")
    )

    assert provider.calls[0]["use_web_grounding"] is False
    assert result.knowledge_source == "llm_general_financial_knowledge"
    assert result.web_grounded is False


def test_sgtm_and_masi_are_current_information_requests():
    assert requires_current_information("What is SGTM's price today?", "en", "latin")
    assert requires_current_information("What is the MASI today?", "en", "latin")


def test_current_answer_without_grounding_metadata_is_limited():
    provider = FakeExpertProvider(FinancialExpertGeneration(text="SGTM is 123 MAD."))
    result = FinancialExpertService(provider, web_grounding_enabled=True).answer(
        request("en", "latin", "What is SGTM's price today?")
    )

    assert result.knowledge_source == "controlled_current_data_limitation"
    assert result.web_grounded is False
    assert "123" not in result.answer


def test_grounding_failure_is_limited_without_stale_answer():
    provider = FakeExpertProvider(RuntimeError("provider secret payload"))
    result = FinancialExpertService(provider, web_grounding_enabled=True).answer(
        request("en", "latin", "What is SGTM's price today?")
    )

    assert result.knowledge_source == "controlled_current_data_limitation"
    assert "secret" not in result.answer
    assert "123" not in result.answer


def test_web_flag_disabled_keeps_j7_11_b_current_data_safety():
    provider = FakeExpertProvider(FinancialExpertGeneration(text="SGTM is 123 MAD."))
    result = FinancialExpertService(provider, web_grounding_enabled=False).answer(
        request("en", "latin", "What is SGTM's price today?")
    )

    # No approved research available: limitation, never a model-memory figure.
    assert provider.calls == []
    assert result.knowledge_source == "controlled_current_data_limitation"
    assert "123" not in result.answer


def test_actual_provider_shape_parses_sdk_grounding_metadata_without_network():
    from app.financial_expert.provider import GeminiFinancialExpertProvider

    web = SimpleNamespace(title="AMMC", uri="https://ammc.ma")
    metadata = SimpleNamespace(
        grounding_chunks=[SimpleNamespace(web=web)],
        search_entry_point=SimpleNamespace(rendered_content="search attribution"),
    )
    response = SimpleNamespace(
        text="The grounded answer.",
        candidates=[SimpleNamespace(grounding_metadata=metadata)],
    )

    class Models:
        def generate_content(self, **kwargs):
            assert kwargs["config"]["tools"]
            return response

    provider = GeminiFinancialExpertProvider(
        api_key="test-only", client=SimpleNamespace(models=Models())
    )
    result = provider.generate("What is SGTM today?", "prompt", use_web_grounding=True)

    assert result.web_grounded is True
    assert result.web_sources == ({"title": "AMMC", "uri": "https://ammc.ma"},)
    assert result.web_search_entry_point == "search attribution"


def test_shared_voice_websocket_path_uses_same_grounded_business_result():
    from app.api import voice as voice_api
    from app.graph.core import build_graph
    from tests.voice.test_websocket import FakeLiveSession, cleanup, make_client

    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="Quel est le cours de SGTM aujourd'hui ?")],
        sent_audio=[],
    )
    grounded = SimpleNamespace(
        generate=lambda request: __import__(
            "app.rag.grounded_generation", fromlist=["GroundedGenerationResult"]
        ).GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Sources are insufficient.",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="insufficient_evidence",
            grounded=False,
            insufficient_evidence=True,
            provider_retryable=False,
        )
    )
    expert = FakeExpertProvider(
        FinancialExpertGeneration(
            text="Le cours actuel est confirmé par une source web.",
            web_grounded=True,
            web_sources=({"domain": "casablanca-bourse.com", "uri": "https://example.test/quote"},),
        )
    )
    graph = build_graph(
        supervisor_provider=SimpleNamespace(
            invoke_structured=lambda request: {
                "domain_status": "in_domain",
                "route": "pedagogie",
            }
        ),
        grounded_service=grounded,
        financial_expert_service=FinancialExpertService(expert, web_grounding_enabled=True),
        financial_expert_fallback_enabled=True,
    )
    client, _, tts, old_settings = make_client(session)
    from app.main import app

    app.dependency_overrides[voice_api.get_chat_graph] = lambda: graph
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(
                {
                    "type": "session.start",
                    "session_id": "web-grounded-session",
                    "thread_id": "web-grounded-thread",
                    "audio": {
                        "mime_type": "audio/pcm",
                        "sample_rate": 16000,
                        "channels": 1,
                        "sample_width_bytes": 2,
                    },
                }
            )
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            response_text = None
            while True:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    continue
                message = json.loads(message["text"])
                if message["type"] == "response.text":
                    response_text = message["answer"]
                if message["type"] == "response.complete":
                    break
    finally:
        cleanup(old_settings)

    assert response_text == "Le cours actuel est confirmé par une source web."
    assert tts.calls[0][0] == response_text
    assert expert.calls[0]["use_web_grounding"] is True


@pytest.mark.parametrize(
    "language,script,question",
    [
        (
            "fr",
            "latin",
            "Quelles entreprises sont cotées à la Bourse de Casablanca ?",
        ),
        (
            "en",
            "latin",
            "Which companies are listed on the Casablanca Stock Exchange?",
        ),
        (
            "ar",
            "arabic",
            (
                "\u0645\u0627 \u0647\u064a \u0627\u0644\u0634\u0631\u0643\u0627\u062a "
                "\u0627\u0644\u0645\u062f\u0631\u062c\u0629 \u0641\u064a "
                "\u0628\u0648\u0631\u0635\u0629 "
                "\u0627\u0644\u062f\u0627\u0631 \u0627\u0644\u0628\u064a\u0636\u0627\u0621\u061f"
            ),
        ),
        (
            "ary",
            "latin",
            "Chno homa charikat li kaynin f boursa dyal Casablanca?",
        ),
        (
            "ary",
            "arabic",
            (
                "\u0634\u0646\u0648 \u0647\u0645\u0627 \u0627\u0644\u0634\u0631\u0643\u0627\u062a "
                "\u0627\u0644\u0644\u064a \u0643\u0627\u064a\u0646\u064a\u0646 \u0641\u064a "
                "\u0628\u0648\u0631\u0635\u0629 "
                "\u0627\u0644\u062f\u0627\u0631 \u0627\u0644\u0628\u064a\u0636\u0627\u0621\u061f"
            ),
        ),
    ],
)
def test_listed_company_collections_trigger_current_policy(language, script, question):
    assert requires_current_information(question, language, script) is True


@pytest.mark.parametrize(
    "language,script,question",
    [
        ("fr", "latin", "C'est quoi une société cotée ?"),
        ("en", "latin", "What does listed company mean?"),
        (
            "ar",
            "arabic",
            (
                "\u0645\u0627 \u0645\u0639\u0646\u0649 \u0634\u0631\u0643\u0629 "
                "\u0645\u062f\u0631\u062c\u0629 \u0641\u064a "
                "\u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f"
            ),
        ),
        ("ary", "latin", "Chno kat3ni charika cotee?"),
        (
            "ary",
            "arabic",
            (
                "\u0634\u0646\u0648 \u0643\u062a\u0639\u0646\u064a \u0634\u0631\u0643\u0629 "
                "\u0645\u062f\u0631\u062c\u0629 \u0641\u0627"
                "\u0644\u0628\u0648\u0631\u0635\u0629\u061f"
            ),
        ),
    ],
)
def test_listed_company_concepts_remain_general_policy(language, script, question):
    assert requires_current_information(question, language, script) is False


class ListedPipelineGrounded:
    def __init__(self, insufficient: bool):
        self.insufficient = insufficient

    def generate(self, request):
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer="Sources are insufficient." if self.insufficient else "Official list answer.",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="insufficient_evidence" if self.insufficient else "ok",
            grounded=not self.insufficient,
            insufficient_evidence=self.insufficient,
            provider_retryable=False,
        )


def test_listed_company_pipeline_uses_web_only_after_insufficient_rag():
    question = "Quelles entreprises sont cotées à la Bourse de Casablanca ?"
    provider = FakeExpertProvider(
        FinancialExpertGeneration(
            text="La liste actuelle est confirmée par une source web.",
            web_grounded=True,
            web_sources=({"title": "casablanca-bourse.com", "uri": "https://example.test/list"},),
        )
    )
    expert = FinancialExpertService(provider, web_grounding_enabled=True)
    insufficient_graph = build_graph(
        supervisor_provider=SimpleNamespace(
            invoke_structured=lambda request: {
                "domain_status": "in_domain",
                "route": "pedagogie",
            }
        ),
        grounded_service=ListedPipelineGrounded(insufficient=True),
        financial_expert_service=expert,
        financial_expert_fallback_enabled=True,
    )
    result = process_text_message(
        ChatRequest(message=question, thread_id="listed-insufficient"), insufficient_graph
    )

    assert result.answer == "La liste actuelle est confirmée par une source web."
    assert len(provider.calls) == 1
    assert provider.calls[0]["use_web_grounding"] is True

    sufficient_provider = FakeExpertProvider(FinancialExpertGeneration(text="Must not be called."))
    sufficient_graph = build_graph(
        supervisor_provider=SimpleNamespace(
            invoke_structured=lambda request: {
                "domain_status": "in_domain",
                "route": "pedagogie",
            }
        ),
        grounded_service=ListedPipelineGrounded(insufficient=False),
        financial_expert_service=FinancialExpertService(
            sufficient_provider, web_grounding_enabled=True
        ),
        financial_expert_fallback_enabled=True,
    )
    sufficient = process_text_message(
        ChatRequest(message=question, thread_id="listed-sufficient"), sufficient_graph
    )

    assert sufficient.answer == "Official list answer."
    assert sufficient_provider.calls == []
