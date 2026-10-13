from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import voice as voice_api
from app.api.chat import process_text_message
from app.graph.core import build_graph, route_after_formation
from app.graph.routing import is_in_domain, route_request
from app.graph.state import create_turn_input
from app.learning import InMemoryLearningProfileStore, LearningProfileService
from app.main import app
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest
from app.specialists.content import render_specialist_response
from tests.voice import test_websocket as voice_fixtures

LOCALES = (
    ("fr", "latin", "Comment apprendre les marchés financiers ?"),
    ("en", "latin", "How can I learn about financial markets?"),
    ("ar", "arabic", "كيف أتعلم عن الأسواق المالية؟"),
    ("ary", "latin", "Kifach nt3ellem l aswa9 lmaliya?"),
    ("ary", "arabic", "كيفاش نتعلم الأسواق المالية؟"),
)

ROUTES = (
    "pedagogie",
    "formation_elearning",
    "quiz",
    "orientation",
    "cisi",
    "championnat",
    "support_ecole",
    "out_of_domain",
)

BUSINESS_MARKERS = {
    "pedagogie": ("action", "obligation", "bond", "stock", "saham", "سهم", "السند"),
    "formation_elearning": ("module", "lesson", "massar", "مسار", "المسار"),
    "quiz": ("question", "quiz", "soual", "سؤال", "السؤال"),
    "orientation": ("learning", "apprentissage", "diversification", "ta3allom", "تعلم"),
}


class FixedRouteSupervisor:
    def __init__(self, route: str):
        self.route = route

    def invoke_structured(self, request):
        return {
            "domain_status": "out_of_domain"
            if self.route == "out_of_domain"
            else "in_domain",
            "route": self.route,
        }


class ContentAwareSupervisor:
    def invoke_structured(self, request):
        route = route_request(request.user_message)
        return {
            "domain_status": "in_domain" if is_in_domain(request.user_message) else "out_of_domain",
            "route": route,
        }


class JourneySupervisor:
    def invoke_structured(self, request):
        text = request.user_message.casefold()
        if "orient" in text or "guide" in text:
            route = "orientation"
        elif "formation" in text or "training" in text:
            route = "formation_elearning"
        elif "quiz" in text:
            route = "quiz"
        else:
            route = "pedagogie"
        return {"domain_status": "in_domain", "route": route}


class HandoffSupervisor:
    routes = {
        "concept": "pedagogie",
        "quiz": "quiz",
        "diversification": "pedagogie",
        "participating": "formation_elearning",
        "learning path": "orientation",
        "prepare cisi": "cisi",
    }

    def invoke_structured(self, request):
        text = request.user_message.casefold()
        route = next(route for marker, route in self.routes.items() if marker in text)
        return {"domain_status": "in_domain", "route": route}


class LocalGroundedPedagogie:
    answers = {
        "fr/latin": (
            "Une obligation est un titre de créance: l'investisseur prête des fonds "
            "et reçoit des intérêts selon les conditions prévues."
        ),
        "en/latin": (
            "A bond is a debt instrument: an investor lends funds and receives "
            "interest under stated terms."
        ),
        "ar/arabic": "السند أداة دين؛ يقرض المستثمر أموالا ويتلقى فائدة وفقا للشروط المحددة.",
        "ary/latin": (
            "L-obligation hiya wara9at dayn: lmostatmir kayqred flous w kayakhod "
            "fa2ida 7sab chourout lmou3ayana."
        ),
        "ary/arabic": "السند هو أداة دين؛ المستثمر كيقرض الفلوس وكيشد الفائدة حسب الشروط المحددة.",
    }

    def generate(self, request):
        locale = (
            "ary/arabic"
            if request.language == "ary" and request.script == "arabic"
            else f"{request.language}/{request.script}"
        )
        answer = self.answers[locale]
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=answer,
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


ROUTE_MESSAGES = {
    "pedagogie": {
        "fr": "Qu'est-ce qu'une obligation ?",
        "en": "What is a bond?",
        "ar": "ما هو السند؟",
        "ary": "Chno hiya obligation?",
    },
    "formation_elearning": {
        "fr": "Je veux continuer ma formation sur la Bourse.",
        "en": "I want to continue my stock-market training.",
        "ar": "أريد متابعة تكويني في البورصة.",
        "ary": "Bghit nkemmel takwin dyali f lborsa.",
    },
    "quiz": {
        "fr": "Propose-moi un quiz sur la Bourse.",
        "en": "Give me a stock-market quiz.",
        "ar": "ما هو السند؟",
        "ary": "3tini quiz 3la lborsa.",
    },
    "orientation": {
        "fr": "Oriente-moi dans mon apprentissage financier.",
        "en": "Guide me in my financial learning.",
        "ar": "ما هو السند؟",
        "ary": "Wjheni f ta3allom mali.",
    },
    "cisi": {
        "fr": "Comment préparer une certification CISI ?",
        "en": "How can I prepare for CISI certification?",
        "ar": "كيف أستعد لشهادة CISI؟",
        "ary": "Kifach nwjed certification CISI?",
    },
    "championnat": {
        "fr": "Comment fonctionne le Championnat de la Bourse ?",
        "en": "How does the stock-market championship work?",
        "ar": "كيف تعمل بطولة البورصة؟",
        "ary": "Kifach kaykhdem Championnat dyal lBorsa?",
    },
    "support_ecole": {
        "fr": "Comment accéder aux formations de l'École de la Bourse ?",
        "en": "How can I access the Bourse School learning services?",
        "ar": "كيف أصل إلى خدمات مدرسة البورصة التعليمية؟",
        "ary": "Kifach nwsel l khadamat ta3limiya dyal Ecole de la Bourse?",
    },
    "out_of_domain": {
        "fr": "Donnez-moi une recette de gâteau.",
        "en": "Give me a cake recipe.",
        "ar": "أعطني وصفة كعكة.",
        "ary": "3tini wasfa dyal gateau.",
    },
}

ARY_ARABIC_MESSAGES = {
    "pedagogie": "شنو هي السند؟",
    "formation_elearning": "بغيت نكمل التكوين ديالي فالبورصة.",
    "quiz": "عطيني كويز على البورصة.",
    "orientation": "وجهني فالتمدرس المالي ديالي.",
    "cisi": "كيفاش نوجد شهادة CISI؟",
    "championnat": "كيفاش كيخدم Championnat ديال البورصة؟",
    "support_ecole": "كيفاش نوصل لخدمات مدرسة البورصة؟",
    "out_of_domain": "عطيني وصفة ديال كيك.",
}


def run_case(route: str, language: str, script: str):
    thread_id = f"j7-09-{route}-{language}-{script}"
    graph = build_graph(
        supervisor_provider=FixedRouteSupervisor(route),
        grounded_service=LocalGroundedPedagogie() if route == "pedagogie" else None,
        learning_profile_service=profile_for_route(route, thread_id),
    )
    message = (
        ARY_ARABIC_MESSAGES[route]
        if language == "ary" and script == "arabic"
        else ROUTE_MESSAGES[route][language]
    )
    request = ChatRequest(
        message=message,
        thread_id=thread_id,
    )
    result = process_text_message(request, graph)
    assert result.route == route
    assert result.status in {"ok", "blocked"}
    assert result.answer.strip()
    assert result.language == language
    assert result.script == script
    return result


def message_for(route: str, language: str, script: str) -> str:
    if language == "ary" and script == "arabic":
        return ARY_ARABIC_MESSAGES[route]
    return ROUTE_MESSAGES[route][language]


def profile_for_route(route: str, thread_id: str) -> LearningProfileService | None:
    if route not in {"formation_elearning", "quiz", "orientation"}:
        return None
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level(thread_id, "intermediate", "manual")
    service.mark_topic_to_review(thread_id, "diversification")
    return service


def run_voice_case(
    route: str,
    language: str,
    script: str,
    *,
    thread_id: str | None = None,
    message: str | None = None,
    graph=None,
    supervisor=None,
):
    message = message or message_for(route, language, script)
    session = voice_fixtures.FakeLiveSession(
        events=[SimpleNamespace(kind="final", text=message)], sent_audio=[]
    )
    tts = voice_fixtures.FakeTTS()
    voice_thread_id = thread_id or f"j7-09-voice-{route}-{language}-{script}"
    graph = graph or build_graph(
        supervisor_provider=supervisor or FixedRouteSupervisor(route),
        grounded_service=LocalGroundedPedagogie() if route == "pedagogie" else None,
        learning_profile_service=profile_for_route(route, voice_thread_id),
    )
    app.dependency_overrides[voice_api.get_live_stt_provider] = (
        lambda: voice_fixtures.FakeLiveProvider(session)
    )
    app.dependency_overrides[voice_api.get_voice_tts_provider] = lambda: tts
    app.dependency_overrides[voice_api.get_chat_graph] = lambda: graph
    old_settings = voice_api.get_settings
    voice_api.get_settings = lambda: SimpleNamespace(
        voice_ws_max_chunk_bytes=65536,
        voice_ws_output_chunk_bytes=4096,
        voice_ws_max_session_seconds=300,
    )
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/api/v1/voice/live") as websocket:
                websocket.send_json(
                    {
                        "type": "session.start",
                        "session_id": "j7-09-session",
                        "thread_id": voice_thread_id,
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
                    packet = websocket.receive()
                    if packet.get("text") is None:
                        continue
                    payload = __import__("json").loads(packet["text"])
                    if payload["type"] == "response.text":
                        response_text = payload
                    if payload["type"] == "response.complete":
                        break
                assert response_text is not None
                assert tts.calls and tts.calls[0][0] == response_text["answer"]
                return response_text, tts
    finally:
        voice_fixtures.cleanup(old_settings)


@pytest.mark.parametrize("route", ROUTES)
def test_global_text_matrix(route):
    for language, script, _ in LOCALES:
        result = run_case(route, language, script)
        if route in BUSINESS_MARKERS:
            lowered = result.answer.casefold()
            assert any(marker.casefold() in lowered for marker in BUSINESS_MARKERS[route]), (
                route,
                language,
                script,
                result.answer,
            )
        if route in {"cisi", "championnat", "support_ecole", "out_of_domain"}:
            assert result.answer == render_specialist_response(route, language, script)


@pytest.mark.parametrize("route", ROUTES)
def test_global_voice_matrix_reuses_text_pipeline(route):
    for language, script, _ in LOCALES:
        result, _ = run_voice_case(route, language, script)
        assert result["route"] == route
        if route in {"cisi", "championnat", "support_ecole", "out_of_domain"}:
            assert result["answer"] == render_specialist_response(route, language, script)


@pytest.mark.parametrize("route", ("cisi", "championnat", "support_ecole", "out_of_domain"))
def test_stateless_text_voice_answers_are_equivalent(route):
    for language, script, _ in LOCALES:
        text_result = run_case(route, language, script)
        voice_result, _ = run_voice_case(route, language, script)
        assert (text_result.route, text_result.answer) == (
            voice_result["route"],
            voice_result["answer"],
        )


def test_voice_entry_uses_the_shared_chat_pipeline():
    assert voice_api.process_text_message is process_text_message
    source = Path(voice_api.__file__).read_text(encoding="utf-8")
    assert "process_text_message" in source
    assert "VoiceCISIAgent" not in source


def test_security_precedes_every_business_route():
    graph = build_graph(supervisor_provider=FixedRouteSupervisor("championnat"))
    result = process_text_message(
        ChatRequest(
            message="Quelle action dois-je acheter pour gagner ?",
            thread_id="j7-09-security",
        ),
        graph,
    )
    assert result.route == "securite"
    assert result.blocked is True
    assert "acheter" not in result.answer.casefold()


SECURITY_MESSAGES = (
    ("fr", "latin", "Quelle action marocaine dois-je acheter pour gagner ?"),
    ("en", "latin", "Which Moroccan stock should I buy?"),
    ("ar", "arabic", "ما هو السهم المغربي الذي يجب أن أشتريه؟"),
    ("ary", "latin", "Achmn saham maghribi nchri?"),
    ("ary", "arabic", "شنو هو السهم المغربي اللي نشري؟"),
)


@pytest.mark.parametrize("language,script,message", SECURITY_MESSAGES)
def test_security_text_matrix_is_before_specialists(language, script, message):
    result = process_text_message(
        ChatRequest(message=message, thread_id=f"j7-09-security-text-{language}-{script}"),
        build_graph(supervisor_provider=FixedRouteSupervisor("cisi")),
    )
    assert result.route == "securite"
    assert result.blocked is True
    assert result.language == language
    assert result.script == script
    assert "buy" not in result.answer.casefold()
    assert "acheter" not in result.answer.casefold()


@pytest.mark.parametrize("language,script,message", SECURITY_MESSAGES)
def test_security_voice_matrix_enters_through_websocket(language, script, message):
    payload, _ = run_voice_case(
        "pedagogie",
        language,
        script,
        message=message,
    )
    assert payload["route"] == "securite"
    assert payload["blocked"] is True
    assert "buy" not in payload["answer"].casefold()
    assert "acheter" not in payload["answer"].casefold()


@pytest.mark.parametrize(
    "message",
    [
        "What is a stock?",
        "What is a bond?",
        "How does a limit order work?",
        "Explain liquidity in the stock market.",
        "What is diversification?",
    ],
)
def test_legitimate_finance_does_not_use_ood(message):
    result = process_text_message(
        ChatRequest(message=message, thread_id=f"j7-09-domain-{message}"),
        build_graph(supervisor_provider=ContentAwareSupervisor()),
    )
    assert result.route != "out_of_domain"


def test_unrelated_request_reaches_ood_without_pinning_the_route():
    result = process_text_message(
        ChatRequest(message="Give me a cake recipe.", thread_id="j7-09-ood"),
        build_graph(supervisor_provider=ContentAwareSupervisor()),
    )
    assert result.route == "out_of_domain"


CURRENT_FACT_REQUESTS = {
    "cisi": "What is the current CISI exam fee, date, deadline, and syllabus?",
    "championnat": "Who is the current winner and what is the live stock price?",
    "support_ecole": "What are the current phone number, email, and opening hours?",
}


@pytest.mark.parametrize("route", ("cisi", "championnat", "support_ecole"))
def test_current_fact_requests_use_real_pipeline_without_invention(route):
    result = process_text_message(
        ChatRequest(
            message=CURRENT_FACT_REQUESTS[route],
            thread_id=f"j7-09-current-facts-{route}",
        ),
        build_graph(supervisor_provider=FixedRouteSupervisor(route)),
    )
    assert result.route == route
    assert result.status == "ok"
    assert result.answer.strip()
    assert not any(token in result.answer.casefold() for token in ("+212", "2026-", "@example"))


def test_formation_certification_handoff_remains_explicit():
    state = create_turn_input("I want CISI certification training")
    assert route_after_formation(state) == "cisi"


@pytest.mark.parametrize(
    "message,expected_route",
    [
        ("CISI: explain this concept", "pedagogie"),
        ("CISI: give me a quiz", "quiz"),
        ("Championnat: explain diversification", "pedagogie"),
        ("Championnat: I want to learn before participating", "formation_elearning"),
        ("Support: which learning path should I follow?", "orientation"),
        ("Orientation: help me prepare CISI", "cisi"),
    ],
)
def test_six_cross_agent_handoffs_use_the_shared_pipeline(message, expected_route):
    result = process_text_message(
        ChatRequest(message=message, thread_id=f"j7-09-handoff-{expected_route}"),
        build_graph(supervisor_provider=HandoffSupervisor()),
    )
    assert result.route == expected_route
    assert result.answer.strip()


def test_global_cross_modal_profile_journey_uses_one_thread_and_profile():
    thread_id = "j7-09-cross-modal-profile"
    service = LearningProfileService(InMemoryLearningProfileStore())
    graph = build_graph(
        supervisor_provider=JourneySupervisor(),
        learning_profile_service=service,
    )

    orientation = process_text_message(
        ChatRequest(message="Guide me in my financial learning.", thread_id=thread_id),
        graph,
    )
    assert orientation.route == "orientation"
    assert service.get_profile(thread_id).learning_level is None

    assessment = process_text_message(
        ChatRequest(message="Assess my level in financial learning.", thread_id=thread_id),
        graph,
    )
    assert assessment.route == "orientation"

    for _ in range(6):
        diagnostic, _ = run_voice_case(
            "quiz", "fr", "latin", thread_id=thread_id, message="A", graph=graph
        )
        assert diagnostic["route"] == "quiz"
    profile = service.get_profile(thread_id)
    assert profile.learning_level in {"beginner", "intermediate", "advanced"}
    assert profile.level_source == "diagnostic"

    formation = process_text_message(
        ChatRequest(message="I want to continue my stock-market training.", thread_id=thread_id),
        graph,
    )
    assert formation.route == "formation_elearning"
    assert formation.answer.strip()
    formation_voice, _ = run_voice_case(
        "formation_elearning",
        "en",
        "latin",
        thread_id=thread_id,
        message="continue",
        graph=graph,
    )
    assert formation_voice["route"] == "formation_elearning"

    quiz = process_text_message(
        ChatRequest(message="Give me a stock-market quiz.", thread_id=thread_id),
        graph,
    )
    assert quiz.route == "quiz"
    quiz_voice, _ = run_voice_case(
        "quiz", "en", "latin", thread_id=thread_id, message="A", graph=graph
    )
    assert quiz_voice["route"] == "quiz"

    final_orientation = process_text_message(
        ChatRequest(message="Guide me again.", thread_id=thread_id),
        graph,
    )
    assert final_orientation.route == "orientation"
    assert service.get_profile(thread_id).level_source == "diagnostic"
    assert final_orientation.thread_id == thread_id


@pytest.mark.parametrize("route", ("cisi", "championnat", "support_ecole"))
def test_specialists_do_not_fabricate_current_facts(route):
    for language, script, _ in LOCALES:
        answer = render_specialist_response(route, language, script)
        lowered = answer.casefold()
        assert not any(token in lowered for token in ("@", "+212", "2026-", "20%"))
        assert answer.strip()


def test_all_specialist_static_content_is_utf8_and_script_safe():
    markers = ("Ã", "Â", "Ø", "Ù", "�")
    for route in ("cisi", "championnat", "support_ecole", "out_of_domain"):
        for language, script, _ in LOCALES:
            answer = render_specialist_response(route, language, script)
            assert not any(marker in answer for marker in markers)
            if script == "latin":
                assert not any("\u0600" <= char <= "\u06ff" for char in answer)
            else:
                assert any("\u0600" <= char <= "\u06ff" for char in answer)


def test_no_second_business_router_or_voice_agent_exists():
    root = Path(__file__).resolve().parents[3]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "backend/app").rglob("*.py")
        if ".venv" not in path.parts
    )
    forbidden = (
        "VoiceCISIAgent",
        "VoiceChampionnatAgent",
        "VoiceSupportAgent",
        "VoiceOODAgent",
        "class DomainClassifier",
        "class SecondarySupervisor",
    )
    assert not any(token in source for token in forbidden)


def test_shared_profile_service_remains_single_educational_profile():
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level("j7-09-profile", "intermediate", "manual")
    profile = service.get_profile("j7-09-profile")
    assert profile.learning_level == "intermediate"
    assert not {"income", "wealth", "portfolio_value", "risk_appetite"} & set(
        type(profile).model_fields
    )
