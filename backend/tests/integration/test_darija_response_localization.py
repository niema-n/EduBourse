"""Darija output localization at the canonical chat boundary.

No BGE-M3, Chroma or Groq: grounded results, supervisor and localizer are fakes.
"""

from __future__ import annotations

import pytest

from app.agents.contracts import OUT_OF_DOMAIN_MESSAGES
from app.api import chat as chat_api
from app.api.chat import process_text_message
from app.graph.core import build_graph
from app.graph.localization import DARIJA_ARABIC_MESSAGES, MESSAGES
from app.graph.response_localizer import (
    LOCALIZER_SYSTEM_PROMPT,
    business_answer_locale,
    darija_arabic_scores,
    darija_latin_scores,
    localize_business_answer,
    reads_as_darija,
)
from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GROUNDING_SYSTEM_PROMPT,
    GroundedCitation,
    GroundedGenerationRequest,
    GroundedGenerationResult,
    GroundedGenerationService,
    _safe_insufficient_message,
    safe_grounding_failure_message,
)
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk
from app.schemas.chat import ChatRequest
from app.specialists.content import render_specialist_response
from app.voice.models import AudioInput
from app.voice.service import VoiceService
from tests.voice.test_foundation import FakeSTT, FakeTTS

FRENCH_ANSWER = (
    "Une action est un titre de propriété qui représente une fraction du capital d'une "
    "société. Elle donne des droits à son détenteur, comme le droit de vote et le droit "
    "aux dividendes."
)
MSA_ANSWER = (
    "السهم هو ورقة مالية تمثل حصة في رأس مال الشركة، ويمنح حامله الحق في التصويت "
    "والحصول على الأرباح. ويمكن أن ترتفع قيمته أو تنخفض حسب أداء الشركة."
)
DARIJA_ARABIC_ANSWER = (
    "السهم هو واحد الورقة المالية اللي كتمثل جزء من رأس المال ديال الشركة. اللي عندو "
    "سهم كيولي شريك فالشركة، وكيقدر ياخد جزء من الأرباح ديالها، وعندو الحق يصوت."
)
DARIJA_LATIN_ANSWER = (
    "Saham howa wara9a maliya li kat3ni joz2 mn ras lmal dyal charika. Li 3ndo saham "
    "kayweli cherik f charika, w kay9der yakhod jiha mn lerba7 dyalha w ysowet."
)
ENGLISH_ANSWER = (
    "A stock is a security that represents a share of a company's capital and gives "
    "its holder voting rights and dividends."
)

CITATION = GroundedCitation(
    evidence_id="S1",
    chunk_id="ammc-instruments-p007-c001-abcdef01",
    source_id="ammc-instruments",
    title="Comprendre les instruments financiers et leurs mécanismes",
    page=7,
    page_start=7,
    page_end=7,
    heading="Les titres de capital",
)


# ---------------------------------------------------------------------------
# Deterministic dialect validation
# ---------------------------------------------------------------------------


def test_french_and_english_do_not_read_as_darija_latin():
    assert reads_as_darija(FRENCH_ANSWER, "latin") is False
    assert reads_as_darija(ENGLISH_ANSWER, "latin") is False
    darija, french, _english, _count = darija_latin_scores(FRENCH_ANSWER)
    assert french > darija


def test_darija_latin_answer_reads_as_darija():
    assert reads_as_darija(DARIJA_LATIN_ANSWER, "latin") is True


def test_msa_control_is_distinguishable_from_darija_arabic():
    assert reads_as_darija(MSA_ANSWER, "arabic") is False
    assert reads_as_darija(DARIJA_ARABIC_ANSWER, "arabic") is True
    msa_darija, _msa, _ = darija_arabic_scores(MSA_ANSWER)
    darija_darija, darija_msa, _ = darija_arabic_scores(DARIJA_ARABIC_ANSWER)
    assert darija_darija > msa_darija
    assert darija_darija >= darija_msa


def test_script_mismatch_never_reads_as_darija():
    assert reads_as_darija(DARIJA_ARABIC_ANSWER, "latin") is False
    assert reads_as_darija(DARIJA_LATIN_ANSWER, "arabic") is False


def test_existing_fixed_darija_messages_already_pass():
    fixed = [(MESSAGES["ary"][key], "latin") for key in MESSAGES["ary"]]
    fixed += [(text, "arabic") for text in DARIJA_ARABIC_MESSAGES.values()]
    for script in ("latin", "arabic"):
        fixed.append((OUT_OF_DOMAIN_MESSAGES[("ary", script)], script))
        fixed.append((render_specialist_response("out_of_domain", "ary", script), script))
    for script in ("latin", "arabic"):
        fixed.append((_safe_insufficient_message("ary", script), script))
        fixed.append((safe_grounding_failure_message("ary", script), script))
    assert [text for text, script in fixed if not reads_as_darija(text, script)] == []


# ---------------------------------------------------------------------------
# Localizer unit behaviour
# ---------------------------------------------------------------------------


class FakeLocalizer:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls: list[tuple[str, dict[str, str]]] = []

    def localize(self, system_prompt, payload):
        self.calls.append((system_prompt, payload))
        if self.error:
            raise self.error
        return {"answer": self.text}


@pytest.mark.parametrize(
    "language,script,answer",
    [("fr", "latin", FRENCH_ANSWER), ("en", "latin", ENGLISH_ANSWER), ("ar", "arabic", MSA_ANSWER)],
)
def test_non_darija_languages_are_not_rewritten(language, script, answer):
    provider = FakeLocalizer(text=DARIJA_LATIN_ANSWER)
    outcome = localize_business_answer(answer, language, script, provider)
    assert outcome.status == "not_needed"
    assert outcome.answer == answer
    assert provider.calls == []


def test_answer_already_in_darija_is_kept_without_provider_call():
    provider = FakeLocalizer(text="unused")
    outcome = localize_business_answer(DARIJA_ARABIC_ANSWER, "ary", "arabic", provider)
    assert outcome.status == "already_localized"
    assert outcome.answer == DARIJA_ARABIC_ANSWER
    assert provider.calls == []


def test_french_grounded_answer_is_rewritten_into_darija_latin_from_answer_only():
    provider = FakeLocalizer(text=DARIJA_LATIN_ANSWER)
    outcome = localize_business_answer(FRENCH_ANSWER, "ary", "latin", provider)
    assert outcome.status == "localized"
    assert outcome.answer == DARIJA_LATIN_ANSWER
    assert len(provider.calls) == 1
    system_prompt, payload = provider.calls[0]
    assert system_prompt == LOCALIZER_SYSTEM_PROMPT
    # Only the user-facing answer is sent: no evidence, chunks or citations.
    assert set(payload) == {"target_language", "answer"}
    assert payload["answer"] == FRENCH_ANSWER
    assert "Latin script" in payload["target_language"]


@pytest.mark.parametrize(
    "provider",
    [
        None,
        FakeLocalizer(error=RuntimeError("429")),
        FakeLocalizer(text=FRENCH_ANSWER),
        FakeLocalizer(text=""),
        FakeLocalizer(text=MSA_ANSWER),
    ],
    ids=["no-provider", "provider-error", "still-french", "empty", "wrong-script"],
)
def test_localization_failures_are_reported_not_hidden(provider):
    outcome = localize_business_answer(FRENCH_ANSWER, "ary", "latin", provider)
    assert outcome.status == "failed"
    assert outcome.answer is None


def test_msa_rewrite_for_darija_arabic_is_rejected():
    outcome = localize_business_answer(
        FRENCH_ANSWER, "ary", "arabic", FakeLocalizer(text=MSA_ANSWER)
    )
    assert outcome.status == "failed"


def test_rewrite_that_changes_numbers_is_rejected():
    source = "L'introduction en bourse concerne 25 sociétés et 3,5 milliards de dirhams."
    changed = "Introduction en bourse kat3ni 30 charika w bzaf dyal lflous li kayjm3o."
    outcome = localize_business_answer(source, "ary", "latin", FakeLocalizer(text=changed))
    assert outcome.status == "failed"


# ---------------------------------------------------------------------------
# Canonical chat boundary (text) and shared voice path
# ---------------------------------------------------------------------------


class FixedRouteSupervisor:
    def __init__(self, route: str):
        self.route = route

    def invoke_structured(self, request):
        return {
            "domain_status": "out_of_domain" if self.route == "out_of_domain" else "in_domain",
            "route": self.route,
        }


class GroundedByLocale:
    """Grounded pedagogie result; the generator's answer text is chosen per test."""

    def __init__(self, answers: dict[tuple[str, str], str]):
        self.answers = answers
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        locale = (
            request.answer_language or request.language,
            request.answer_script or request.script,
        )
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=self.answers[locale],
            citations=[CITATION],
            used_evidence_ids=["S1"],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


GENERATOR_ANSWERS = {
    ("fr", "latin"): FRENCH_ANSWER,
    ("en", "latin"): ENGLISH_ANSWER,
    ("ar", "arabic"): MSA_ANSWER,
}


class ScriptAwareLocalizer(FakeLocalizer):
    def localize(self, system_prompt, payload):
        self.calls.append((system_prompt, payload))
        latin = "Latin script" in payload["target_language"]
        return {"answer": DARIJA_LATIN_ANSWER if latin else DARIJA_ARABIC_ANSWER}


def _graph(route: str = "pedagogie", grounded=None):
    return build_graph(
        supervisor_provider=FixedRouteSupervisor(route),
        grounded_service=grounded or GroundedByLocale(GENERATOR_ANSWERS),
    )


def test_grounded_service_retrieves_in_darija_and_writes_business_answer_in_pivot():
    class Retrieval:
        def __init__(self):
            self.requests = []

        def retrieve(self, request):
            self.requests.append(request)
            chunk = RetrievedChunk(
                chunk_id=CITATION.chunk_id,
                source_id=CITATION.source_id,
                title=CITATION.title,
                page=7,
                page_start=7,
                page_end=7,
                heading=CITATION.heading,
                text="Une action est un titre de propriété.",
                rank=1,
                retrieval_score=0.3,
                score_type="cosine_distance",
            )
            return RetrievalResult(
                original_query=request.original_query,
                language=request.language,
                script=request.script,
                policy_id="H1_LANGUAGE_ROUTED_V1",
                branches_used=["french"],
                adapted_query_fr="Qu'est-ce qu'une action ?",
                chunks=[chunk],
                retrieval_status="ok",
            )

    class Provider:
        model = GENERATION_MODEL

        def __init__(self):
            self.prompts = []

        def generate(self, system_prompt, user_prompt):
            self.prompts.append((system_prompt, user_prompt))
            return {
                "answer": FRENCH_ANSWER,
                "used_evidence_ids": ["S1"],
                "insufficient_evidence": False,
            }

    retrieval, provider = Retrieval(), Provider()
    result = GroundedGenerationService(retrieval, provider=provider).generate(
        GroundedGenerationRequest(
            original_query="chno howa saham?",
            language="ary",
            script="latin",
            answer_language="fr",
            answer_script="latin",
        )
    )
    assert (retrieval.requests[0].language, retrieval.requests[0].script) == ("ary", "latin")
    system_prompt, user_prompt = provider.prompts[0]
    assert system_prompt == GROUNDING_SYSTEM_PROMPT  # frozen prompt untouched
    assert "requested_language: fr\nrequested_script: latin" in user_prompt
    assert result.generation_status == "ok" and result.grounded is True
    assert (result.language, result.script) == ("ary", "latin")
    assert [citation.chunk_id for citation in result.citations] == [CITATION.chunk_id]


def test_business_answer_locale_pivots_only_darija():
    assert business_answer_locale("ary", "latin") == ("fr", "latin")
    assert business_answer_locale("ary", "arabic") == ("ar", "arabic")
    for language, script in (("fr", "latin"), ("en", "latin"), ("ar", "arabic")):
        assert business_answer_locale(language, script) == (None, None)


def test_mixed_darija_words_in_french_sentences_is_not_darija():
    mixed = (
        "Saham (action) howa titre de propriété (titre de capital) li ywakkil darja min "
        "capital d'une entreprise. Huma mnin titres de capital li y'atoun haqq fi darja min "
        "fonds propres w l'haqqat l'khra li makhassa biha l-malikin."
    )
    assert reads_as_darija(mixed, "latin") is False


def _chat(message: str, thread: str, graph=None):
    return process_text_message(ChatRequest(message=message, thread_id=thread), graph or _graph())


@pytest.fixture
def localizer(monkeypatch):
    provider = ScriptAwareLocalizer()
    monkeypatch.setattr(chat_api, "get_response_localizer", lambda: provider)
    return provider


@pytest.mark.parametrize(
    "message,language,script,expected",
    [
        ("C'est quoi une action ?", "fr", "latin", FRENCH_ANSWER),
        ("What is a stock?", "en", "latin", ENGLISH_ANSWER),
        ("ما هو السهم؟", "ar", "arabic", MSA_ANSWER),
        ("شنو هو السهم؟", "ary", "arabic", DARIJA_ARABIC_ANSWER),
        ("chno howa saham?", "ary", "latin", DARIJA_LATIN_ANSWER),
    ],
)
def test_grounded_answer_follows_user_language_and_keeps_citations(
    localizer, message, language, script, expected
):
    response = _chat(message, f"darija-loc-{language}-{script}")
    assert (response.language, response.script, response.route) == (language, script, "pedagogie")
    assert response.answer == expected
    assert response.status == "ok"
    assert response.grounded is True
    # Citations are the retrieved evidence, untouched by localization.
    assert [
        citation if isinstance(citation, dict) else citation.model_dump()
        for citation in response.citations
    ] == [CITATION.model_dump()]
    if language == "ary":
        assert reads_as_darija(response.answer, script)
        assert len(localizer.calls) == 1
    else:
        assert localizer.calls == []


@pytest.mark.parametrize(
    "message,script,pivot",
    [("chno howa saham?", "latin", ("fr", "latin")), ("شنو هو السهم؟", "arabic", ("ar", "arabic"))],
)
def test_darija_retrieval_keeps_user_locale_and_generation_uses_pivot(
    localizer, message, script, pivot
):
    grounded = GroundedByLocale(GENERATOR_ANSWERS)
    response = _chat(message, f"darija-loc-pivot-{script}", _graph(grounded=grounded))
    request = grounded.requests[0]
    # Retrieval and the result metadata stay in the user's Darija locale.
    assert (request.language, request.script) == ("ary", script)
    assert (request.answer_language, request.answer_script) == pivot
    assert (response.language, response.script) == ("ary", script)
    assert reads_as_darija(response.answer, script)


def test_darija_latin_never_returns_the_french_generation(localizer):
    response = _chat("chno howa saham?", "darija-loc-no-french")
    assert response.answer != FRENCH_ANSWER
    darija, french, _english, _count = darija_latin_scores(response.answer)
    assert darija > french


def test_darija_arabic_answer_differs_from_msa_control(localizer):
    darija = _chat("شنو هو السهم؟", "darija-loc-ary-arabic")
    msa = _chat("ما هو السهم؟", "darija-loc-ar-control")
    assert msa.language == "ar" and msa.answer == MSA_ANSWER
    assert darija.language == "ary" and darija.answer != msa.answer
    assert reads_as_darija(darija.answer, "arabic") and not reads_as_darija(msa.answer, "arabic")


def test_localization_failure_fails_closed_and_is_truthful(monkeypatch):
    monkeypatch.setattr(
        chat_api, "get_response_localizer", lambda: FakeLocalizer(error=RuntimeError("down"))
    )
    response = _chat("chno howa saham?", "darija-loc-failure")
    assert (response.language, response.script) == ("ary", "latin")
    assert response.answer == safe_grounding_failure_message("ary", "latin")
    assert response.answer != FRENCH_ANSWER
    assert response.status == "error"
    assert response.grounded is False
    assert response.citations == []


@pytest.mark.parametrize(
    "message,script",
    [("شنو السهم اللي خاصني نشري؟", "arabic"), ("achmen saham khassni nchri?", "latin")],
)
def test_darija_security_block_is_preserved_and_localized(localizer, message, script):
    response = _chat(message, f"darija-loc-security-{script}", _graph("cisi"))
    assert response.route == "securite"
    assert response.blocked is True
    assert response.status == "blocked"
    assert (response.language, response.script) == ("ary", script)
    assert reads_as_darija(response.answer, script)
    assert response.citations == []
    assert localizer.calls == []


@pytest.mark.parametrize(
    "message,script",
    [("شنو هو أحسن فيلم هاد العام؟", "arabic"), ("chno howa a7san film had l3am?", "latin")],
)
def test_darija_out_of_domain_is_preserved_and_localized(localizer, message, script):
    response = _chat(message, f"darija-loc-ood-{script}", _graph("out_of_domain"))
    assert response.route == "out_of_domain"
    assert response.blocked is False
    assert (response.language, response.script) == ("ary", script)
    # The deterministic specialist refusal, already in Darija: never sent to the LLM.
    assert response.answer == render_specialist_response("out_of_domain", "ary", script)
    assert reads_as_darija(response.answer, script)
    assert response.citations == []
    assert localizer.calls == []


@pytest.mark.parametrize(
    "transcript,script,expected",
    [
        ("chno howa saham?", "latin", DARIJA_LATIN_ANSWER),
        ("شنو هو السهم؟", "arabic", DARIJA_ARABIC_ANSWER),
    ],
)
def test_voice_hands_tts_the_same_localized_text_as_text_chat(
    localizer, transcript, script, expected
):
    graph = _graph()
    text_response = _chat(transcript, f"darija-loc-text-{script}", graph)

    tts = FakeTTS([])
    service = VoiceService(
        FakeSTT(transcript), tts, lambda payload: process_text_message(payload, graph)
    )
    voice = service.process(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id=f"darija-loc-voice-{script}",
        thread_id=f"darija-loc-voice-{script}",
    )

    assert text_response.answer == expected
    assert voice.answer == text_response.answer
    assert tts.calls == [(text_response.answer, "ary", script)]
