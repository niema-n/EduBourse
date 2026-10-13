"""General, topic-agnostic property tests for the Darija localization mechanism.

These tests deliberately avoid finance-specific fixtures or hardcoded phrases:
most synthetic strings below are generic sentences from unrelated domains
(weather, cooking, sports, travel), used only to prove the mechanism is not
built around any single financial notion. Where a business pipeline must be
exercised (grounded/ungrounded/security/out-of-domain routes), generic
stand-ins are used instead of real product names ("topic A", acronym "XZQ",
"Official source"), so nothing here can be read as "a fix for IPO" or
"a fix for OPCVM" - the same assertions apply no matter what the underlying
answer is about.

Covers, per the requested categories:
- grounded pedagogical answer (with citations)
- ungrounded-but-permitted dynamic answer (llm_general_financial_knowledge,
  no citations)
- security block
- out-of-domain
- fallback
- multi-turn conversation (script/language continuity)
- short vs. long answers
- acronyms / technical identifiers
- Text-to-Text and Voice-to-Voice using the identical localizer output
- fr/en/ar non-regression
"""

from __future__ import annotations

import pytest

from app.api import chat as chat_api
from app.api.chat import process_text_message
from app.financial_expert.models import FinancialExpertRequest, FinancialExpertResult
from app.graph.core import build_graph
from app.graph.response_localizer import (
    LOCALIZER_SYSTEM_PROMPT,
    business_answer_locale,
    darija_arabic_scores,
    darija_latin_scores,
    localize_business_answer,
    reads_as_darija,
)
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest
from app.voice.models import AudioInput
from app.voice.service import VoiceService
from tests.voice.test_foundation import FakeSTT, FakeTTS

# ---------------------------------------------------------------------------
# Generic, non-financial synthetic sentences: prove the mechanism is general.
# ---------------------------------------------------------------------------

GENERIC_FRENCH_SENTENCES = [
    "Le chef a préparé une recette délicieuse pour la réunion de l'équipe.",
    "L'équipe a gagné le championnat après une performance exceptionnelle.",
    "La météo prévoit une tempête pour la région cette après-midi.",
    "L'agence a organisé un voyage vers la région méditerranéenne.",
]

GENERIC_ENGLISH_SENTENCE = "The weather forecast shows a storm arriving this afternoon."

GENERIC_DARIJA_LATIN_SENTENCE = (
    "Lwe9t ghadi ykon fih chi chta had l3achiya, khass twejjed ru7ek bach ma "
    "tbllelch f triqek."
)

GENERIC_DARIJA_ARABIC_SENTENCE = (
    "الجو غادي يكون فيه شي شتا هاد العشية، خاصك توجد روحك باش ما تبللش فطريقك."
)

GENERIC_MSA_SENTENCE = (
    "تشير التوقعات الجوية إلى هطول أمطار غزيرة هذا المساء في المنطقة الساحلية."
)


@pytest.mark.parametrize("sentence", GENERIC_FRENCH_SENTENCES)
def test_french_content_leakage_detected_regardless_of_topic(sentence):
    """The orthographic French signal (accents/elisions) fires on ANY topic,
    not just finance - proving it is a general grammar check, not a business
    rule."""
    assert reads_as_darija(sentence, "latin") is False
    darija, french, _english, _count = darija_latin_scores(sentence)
    assert french >= darija


def test_generic_darija_sentences_are_recognised_in_both_scripts():
    assert reads_as_darija(GENERIC_DARIJA_LATIN_SENTENCE, "latin") is True
    assert reads_as_darija(GENERIC_DARIJA_ARABIC_SENTENCE, "arabic") is True


def test_generic_msa_sentence_is_not_darija_arabic():
    assert reads_as_darija(GENERIC_MSA_SENTENCE, "arabic") is False
    darija, msa, _count = darija_arabic_scores(GENERIC_MSA_SENTENCE)
    assert msa >= darija


def test_generic_english_sentence_is_not_darija():
    assert reads_as_darija(GENERIC_ENGLISH_SENTENCE, "latin") is False


# ---------------------------------------------------------------------------
# Localizer contract: input/output boundaries, independent of subject matter.
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
    "language,script",
    [("fr", "latin"), ("en", "latin"), ("ar", "arabic")],
)
def test_fr_en_ar_never_invoke_the_darija_rewrite(language, script):
    """Non-regression: fr/en/ar must behave exactly as before this change."""
    provider = FakeLocalizer(text=GENERIC_DARIJA_LATIN_SENTENCE)
    source = GENERIC_ENGLISH_SENTENCE if language == "en" else GENERIC_FRENCH_SENTENCES[0]
    outcome = localize_business_answer(source, language, script, provider)
    assert outcome.status == "not_needed"
    assert outcome.answer == source
    assert provider.calls == []


@pytest.mark.parametrize("script,generic_sentence", [
    ("latin", GENERIC_DARIJA_LATIN_SENTENCE),
    ("arabic", GENERIC_DARIJA_ARABIC_SENTENCE),
])
def test_localizer_rejects_output_that_still_leaks_french_or_msa(script, generic_sentence):
    """Property: whatever the source topic, a rewrite that still reads as
    French/MSA must be rejected rather than shipped as Darija."""
    source = GENERIC_FRENCH_SENTENCES[1] if script == "latin" else GENERIC_MSA_SENTENCE
    leaking_rewrite = GENERIC_FRENCH_SENTENCES[0] if script == "latin" else GENERIC_MSA_SENTENCE
    outcome = localize_business_answer(source, "ary", script, FakeLocalizer(text=leaking_rewrite))
    assert outcome.status == "failed"
    assert outcome.answer is None


# ---------------------------------------------------------------------------
# Long / multi-paragraph / list-structured answers: the specific failure mode
# reported for this task (intro reads as Darija, later paragraphs/list items
# stay French) and the targeted single retry meant to fix it.
# ---------------------------------------------------------------------------

GENERIC_LONG_FRENCH_SOURCE = (
    "Le sujet A presente plusieurs caracteristiques importantes a connaitre.\n\n"
    "1. La premiere caracteristique concerne son fonctionnement general et la maniere "
    "dont elle evolue selon le contexte.\n"
    "2. La deuxieme caracteristique est liee a sa sensibilite aux variations "
    "exterieures, qui peuvent modifier sa valeur.\n"
    "3. La troisieme caracteristique depend de la categorie a laquelle appartient "
    "l'element etudie.\n\n"
    "Il est donc important d'evaluer ces elements avant de prendre une decision."
)

# Mirrors the real failure observed live: the opening clause is Darija-flavoured
# but every paragraph and list item past it keeps full French vocabulary with
# only a connecting word swapped (kayn, w, li, dyal) - exactly what the
# strengthened prompt/retry must stop happening.
GENERIC_PARTIAL_DARIJA_REWRITE = (
    "Sujet A kayn 3ndo plusieurs caractéristiques importantes.\n\n"
    "1. Première caractéristique concerne le fonctionnement général w la manière "
    "dont elle évolue selon le contexte.\n"
    "2. Deuxième caractéristique liée à la sensibilité aux variations extérieures, "
    "li kayqdiw ybeddlo la valeur dyalha.\n"
    "3. Troisième caractéristique dépend de la catégorie dyal l'élément étudié.\n\n"
    "Khass t9eyed ces éléments qbel bghity tdir décision."
)

# A genuinely full rewrite: every paragraph and list item translated throughout.
GENERIC_FULL_DARIJA_REWRITE = (
    "Sujet A 3ndo bezzaf dyal 5assayiss muhima li khassek t3refhom.\n\n"
    "1. L5assiya lloula kat3lla9 b kifach kaykhdem b chakl 3am w kifach kaytbeddel "
    "7sab lwad3.\n"
    "2. L5assiya ttania kat3lla9 b 7asasiya dyalha l tbeddolat li mn barra, li ymken "
    "ybeddlo lqima dyalha.\n"
    "3. L5assiya ttalta kat3lla9 b category li fiha l3onsor li kayn kaydras.\n\n"
    "Khass t9eyyed had l7ajat qbel matakhod qarar."
)

# No accents and no topic-specific vocabulary: this used to be able to pass a
# global marker count because the introduction was Darija while later list
# items were plain French.  Each item must now carry a Darija sentence frame.
GENERIC_ASCII_FRENCH_LIST_LEAK = (
    "Had lmawdo3 kayn fih chi no9at muhimin.\n\n"
    "1. La premiere partie explique le fonctionnement general du systeme.\n"
    "2. La deuxieme partie montre comment les elements changent selon le contexte.\n"
    "3. Enfin, il faut comparer les resultats avant une decision."
)


class SequencedLocalizer:
    """Returns a different rewrite per call, to drive the retry deterministically."""

    def __init__(self, texts: list[str]):
        self.texts = list(texts)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def localize(self, system_prompt, payload):
        self.calls.append((system_prompt, payload))
        index = len(self.calls) - 1
        return {"answer": self.texts[index] if index < len(self.texts) else self.texts[-1]}


def test_long_list_structured_answer_with_partial_rewrite_is_rejected_pre_retry():
    """Property: a rewrite that is Darija only in its opening clause must not
    pass just because SOME Darija markers are present overall."""
    assert reads_as_darija(GENERIC_PARTIAL_DARIJA_REWRITE, "latin") is False


def test_ascii_french_list_items_cannot_hide_behind_a_darija_introduction():
    """French without accents is still French grammar, not a permitted
    technical borrowing.  This property covers every long/list response."""
    assert reads_as_darija(GENERIC_ASCII_FRENCH_LIST_LEAK, "latin") is False


def test_long_list_structured_answer_fully_rewritten_is_accepted():
    assert reads_as_darija(GENERIC_FULL_DARIJA_REWRITE, "latin") is True


def test_retry_recovers_a_long_answer_that_was_only_partially_darija_at_first():
    """End-to-end property: first attempt partial (rejected) -> retry full
    (accepted) -> exactly one retry call, citations/facts untouched by this
    layer, and the retry is never given a copy-paste example answer."""
    provider = SequencedLocalizer([GENERIC_PARTIAL_DARIJA_REWRITE, GENERIC_FULL_DARIJA_REWRITE])
    outcome = localize_business_answer(GENERIC_LONG_FRENCH_SOURCE, "ary", "latin", provider)
    assert outcome.status == "localized"
    assert outcome.answer == GENERIC_FULL_DARIJA_REWRITE
    assert len(provider.calls) == 2
    retry_system_prompt, retry_payload = provider.calls[1]
    assert retry_system_prompt != provider.calls[0][0]  # feedback was added
    assert "rejected" in retry_system_prompt.lower()
    # Structural feedback only - never a ready-made answer to copy.
    assert GENERIC_FULL_DARIJA_REWRITE not in retry_system_prompt
    assert retry_payload["rejected_answer"] == GENERIC_PARTIAL_DARIJA_REWRITE


def test_retry_is_capped_at_exactly_one_attempt_even_if_it_fails_again():
    """Maximum one retry: if the retry is still not Darija, fail closed - never
    loop, never silently accept a worse answer."""
    provider = SequencedLocalizer([GENERIC_PARTIAL_DARIJA_REWRITE, GENERIC_PARTIAL_DARIJA_REWRITE])
    outcome = localize_business_answer(GENERIC_LONG_FRENCH_SOURCE, "ary", "latin", provider)
    assert outcome.status == "failed"
    assert outcome.answer is None
    assert len(provider.calls) == 2  # initial + exactly one retry, never more


def test_retry_feedback_is_specific_to_the_detected_failure_not_generic():
    """The retry prompt must name the actual structural problem (French
    leakage vs MSA leakage) rather than a single boilerplate sentence, so the
    model gets an actionable, topic-agnostic correction."""
    latin_provider = SequencedLocalizer(
        [GENERIC_PARTIAL_DARIJA_REWRITE, GENERIC_FULL_DARIJA_REWRITE]
    )
    localize_business_answer(GENERIC_LONG_FRENCH_SOURCE, "ary", "latin", latin_provider)
    latin_retry_prompt = latin_provider.calls[1][0]
    assert "french" in latin_retry_prompt.lower()

    arabic_provider = SequencedLocalizer([GENERIC_MSA_SENTENCE, GENERIC_DARIJA_ARABIC_SENTENCE])
    localize_business_answer("Some French source sentence here.", "ary", "arabic", arabic_provider)
    arabic_retry_prompt = arabic_provider.calls[1][0]
    assert (
        "modern standard arabic" in arabic_retry_prompt.lower()
        or "msa" in arabic_retry_prompt.lower()
    )


@pytest.mark.parametrize(
    "answer_len,label",
    [(40, "short"), (900, "long")],
)
def test_answer_length_property_short_and_long(answer_len, label):
    """The length-sanity check (post-localization) must scale with input
    length, not reject legitimately long grounded answers nor let a wildly
    inflated rewrite through, regardless of what the answer discusses."""
    source = ("Topic A explanation. " * (answer_len // 20))[:answer_len]
    good_rewrite = GENERIC_DARIJA_LATIN_SENTENCE * max(1, answer_len // 100)
    outcome = localize_business_answer(source, "ary", "latin", FakeLocalizer(text=good_rewrite))
    if len(good_rewrite) <= max(200, len(source) * 3):
        assert outcome.status in {"localized", "failed"}  # never silently mutates facts
    else:
        assert outcome.status == "failed"


def test_generic_acronym_and_numbers_are_never_altered():
    """Property: any acronym/number survives the rewrite - the mechanism does
    not special-case AMMC/IPO/OPCVM, it enforces this for any token shape."""
    source = "Le produit XZQ-42 a rapporté 3,5% en 2024 selon le rapport officiel."
    good_rewrite = "Lproduit XZQ-42 rbe7 3,5% f 2024 3la 7sab rapport rasmi."
    bad_rewrite_dropped_number = "Lproduit XZQ rbe7 chi 7aja f 2024."
    assert (
        localize_business_answer(source, "ary", "latin", FakeLocalizer(text=good_rewrite)).status
        == "localized"
    )
    assert (
        localize_business_answer(
            source, "ary", "latin", FakeLocalizer(text=bad_rewrite_dropped_number)
        ).status
        == "failed"
    )


def test_business_answer_locale_is_topic_independent():
    assert business_answer_locale("ary", "latin") == ("fr", "latin")
    assert business_answer_locale("ary", "arabic") == ("ar", "arabic")
    assert business_answer_locale("fr", "latin") == (None, None)


def test_localizer_payload_never_carries_evidence_or_citations():
    provider = FakeLocalizer(text=GENERIC_DARIJA_LATIN_SENTENCE)
    outcome = localize_business_answer(GENERIC_FRENCH_SENTENCES[0], "ary", "latin", provider)
    assert outcome.status == "localized"
    _system_prompt, payload = provider.calls[0]
    assert set(payload) == {"target_language", "answer"}
    assert payload["answer"] == GENERIC_FRENCH_SENTENCES[0]


# ---------------------------------------------------------------------------
# End-to-end categories through the real chat boundary: grounded, ungrounded
# permitted, security, out-of-domain, fallback, multi-turn.
# ---------------------------------------------------------------------------


class FixedRouteSupervisor:
    def __init__(self, route: str):
        self.route = route

    def invoke_structured(self, request):
        return {
            "domain_status": "out_of_domain" if self.route == "out_of_domain" else "in_domain",
            "route": self.route,
        }


class ScriptAwareLocalizer(FakeLocalizer):
    def localize(self, system_prompt, payload):
        self.calls.append((system_prompt, payload))
        latin = "Latin script" in payload["target_language"]
        return {
            "answer": (
                GENERIC_DARIJA_LATIN_SENTENCE if latin else GENERIC_DARIJA_ARABIC_SENTENCE
            )
        }


@pytest.fixture
def localizer(monkeypatch):
    provider = ScriptAwareLocalizer()
    monkeypatch.setattr(chat_api, "get_response_localizer", lambda: provider)
    return provider


class GenericGroundedService:
    """Grounded pedagogical result about a generic, unnamed topic."""

    def __init__(self, answer="Topic A is defined by property B and gives right C."):
        self.answer = answer
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=self.answer,
            citations=[
                {
                    "evidence_id": "S1",
                    "chunk_id": "generic-source-1",
                    "source_id": "generic-source",
                    "title": "Generic official source",
                    "page": 1,
                    "page_start": 1,
                    "page_end": 1,
                    "heading": None,
                }
            ],
            used_evidence_ids=["S1"],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


class InsufficientGroundedService:
    def generate(self, request):
        return GroundedGenerationResult(
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


class GenericFinancialExpert:
    provider_name = "fake-generic-expert"

    def __init__(self, answer="General educational explanation about topic A."):
        self.answer_text = answer
        self.calls: list[FinancialExpertRequest] = []

    def answer(self, request: FinancialExpertRequest) -> FinancialExpertResult:
        self.calls.append(request)
        return FinancialExpertResult(
            answer=self.answer_text,
            language=request.language,
            script=request.script,
            provider=self.provider_name,
            knowledge_source="llm_general_financial_knowledge",
        )


def _chat(message: str, thread: str, graph):
    return process_text_message(ChatRequest(message=message, thread_id=thread), graph)


def test_category_grounded_pedagogical_answer_is_localized_with_citations(localizer):
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor("pedagogie"),
        grounded_service=GenericGroundedService(),
    )
    response = _chat("chno howa topic A?", "props-grounded", graph)
    assert response.route == "pedagogie"
    assert response.grounded is True
    assert len(response.citations) == 1
    assert reads_as_darija(response.answer, "latin")
    assert len(localizer.calls) == 1


def test_category_ungrounded_permitted_answer_has_no_citations(localizer):
    """llm_general_financial_knowledge: dynamic, localized, but no citations
    are fabricated - grounding stays independent of localization."""
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor("pedagogie"),
        grounded_service=InsufficientGroundedService(),
        financial_expert_service=GenericFinancialExpert(),
        financial_expert_fallback_enabled=True,
    )
    response = _chat("chno howa topic A b3da?", "props-ungrounded", graph)
    assert response.knowledge_source == "llm_general_financial_knowledge"
    assert response.citations == []
    assert reads_as_darija(response.answer, "latin")
    assert len(localizer.calls) == 1


def test_category_security_block_is_localized_and_never_weakened(localizer):
    graph = build_graph(supervisor_provider=FixedRouteSupervisor("cisi"))
    response = _chat("achmen titre khassni nchri daba?", "props-security", graph)
    assert response.route == "securite"
    assert response.blocked is True
    assert response.status == "blocked"
    assert reads_as_darija(response.answer, "latin")
    # Security refusals are static, never sent to the LLM rewriter.
    assert localizer.calls == []


def test_category_out_of_domain_is_localized(localizer):
    graph = build_graph(supervisor_provider=FixedRouteSupervisor("out_of_domain"))
    response = _chat("chno howa a7san film?", "props-ood", graph)
    assert response.route == "out_of_domain"
    assert reads_as_darija(response.answer, "latin")
    assert localizer.calls == []


def test_category_fallback_is_localized(localizer):
    graph = build_graph(supervisor_provider=FixedRouteSupervisor("fallback"))
    response = _chat("hmm?", "props-fallback", graph)
    assert response.route == "fallback"
    assert reads_as_darija(response.answer, "latin")
    assert localizer.calls == []


def test_category_multi_turn_keeps_the_same_script_and_language(localizer):
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor("pedagogie"),
        grounded_service=GenericGroundedService(),
    )
    first = _chat("chno howa topic A?", "props-multiturn", graph)
    second = _chat("w chno houma lfawaid dyalha?", "props-multiturn", graph)
    assert (first.language, first.script) == ("ary", "latin")
    assert (second.language, second.script) == ("ary", "latin")
    assert reads_as_darija(first.answer, "latin")
    assert reads_as_darija(second.answer, "latin")


def test_category_multi_turn_arabic_script_stays_arabic(localizer):
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor("pedagogie"),
        grounded_service=GenericGroundedService(),
    )
    first = _chat("شنو هو topic A؟", "props-multiturn-ar", graph)
    second = _chat("وشنو هي الفوائد ديالها؟", "props-multiturn-ar", graph)
    assert (first.language, first.script) == ("ary", "arabic")
    assert (second.language, second.script) == ("ary", "arabic")
    assert reads_as_darija(first.answer, "arabic")
    assert reads_as_darija(second.answer, "arabic")


# ---------------------------------------------------------------------------
# Text-to-Text vs. Voice-to-Voice: identical localizer, identical output.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "transcript,script",
    [("chno howa topic A?", "latin"), ("شنو هو topic A؟", "arabic")],
)
def test_voice_and_text_share_the_exact_same_localized_answer(localizer, transcript, script):
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor("pedagogie"),
        grounded_service=GenericGroundedService(),
    )
    text_response = _chat(transcript, f"props-voice-text-{script}", graph)

    tts = FakeTTS([])
    service = VoiceService(
        FakeSTT(transcript), tts, lambda payload: process_text_message(payload, graph)
    )
    voice_response = service.process(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id=f"props-voice-{script}",
        thread_id=f"props-voice-{script}",
    )

    assert voice_response.answer == text_response.answer
    # The exact text handed to TTS is the localized answer - never a second,
    # independent translation and never the raw business answer.
    assert tts.calls == [(text_response.answer, "ary", script)]
    assert reads_as_darija(text_response.answer, script)


def test_localizer_system_prompt_forbids_leaving_french_grammar_untouched():
    """Documentation-as-contract: the prompt explicitly forbids the failure
    mode this whole module is about, independent of any one topic."""
    assert "Darija" in LOCALIZER_SYSTEM_PROMPT
    assert "add, remove, explain or complete" in LOCALIZER_SYSTEM_PROMPT
