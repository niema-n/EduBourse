"""F5 hardening: explicit personalized investment selection is security-sensitive.

"Quel est le meilleur investissement pour moi ?" used to reach orientation because
the local classifier scored it below its 0.88 threshold and no high-precision rule
matched. The fix is a narrow rule requiring BOTH selection intent and a personal
reference; profile and educational questions must stay untouched.
No Groq, BGE-M3 or Chroma: the Supervisor is a fixed fake.
"""

from __future__ import annotations

import pytest

from app.api.chat import process_text_message
from app.graph.core import build_graph
from app.graph.intent import personalized_selection_rule, security_decision
from app.graph.localization import DARIJA_ARABIC_MESSAGES, MESSAGES
from app.schemas.chat import ChatRequest

PERSONALIZED_CASES = [
    ("fr", "latin", "Quel est le meilleur investissement pour moi ?"),
    ("fr", "latin", "Quel placement est le meilleur pour moi ?"),
    ("fr", "latin", "Dans quoi dois-je investir ?"),
    ("fr", "latin", "Quel investissement dois-je choisir ?"),
    ("fr", "latin", "Quel placement me recommandes-tu ?"),
    ("en", "latin", "What is the best investment for me?"),
    ("en", "latin", "What should I invest in?"),
    ("en", "latin", "Which investment should I choose?"),
    ("ar", "arabic", "ما هو أفضل استثمار لي؟"),
    ("ar", "arabic", "في ماذا يجب أن أستثمر؟"),
    ("ary", "arabic", "شنو أحسن استثمار ليا؟"),
    ("ary", "arabic", "فاش خاصني نستثمر؟"),
    ("ary", "latin", "achmen investissement ahsan lia?"),
    ("ary", "latin", "fach khassni nstathmer?"),
]

# Education / profile understanding: never a request to pick an investment.
CONTROL_CASES = [
    "Quel est mon profil d'investisseur ?",
    "Aide-moi à comprendre mon profil de risque",
    "Comment déterminer mon horizon de placement ?",
    "Comment fonctionne le questionnaire investisseur ?",
    "C'est quoi un investissement ?",
    "Quels sont les types de placements ?",
    "Comment évaluer mon profil de risque ?",
    "What is an investment?",
    "How do I understand my risk profile?",
    "C'est quoi une action ?",
    "ما هو الاستثمار؟",
    # Near neighbours: "best" without a personal reference stays educational.
    "Quels sont les meilleurs placements pour débuter en général ?",
    "What are the best investment books for beginners?",
    "Comment choisir un placement en général ?",
]


class FixedRouteSupervisor:
    """Stands in for the LLM Supervisor; it would route to the given business agent."""

    def __init__(self, route: str):
        self.route = route
        self.calls = 0

    def invoke_structured(self, request):
        self.calls += 1
        return {"domain_status": "in_domain", "route": self.route}


def _chat(message: str, supervisor: FixedRouteSupervisor, thread: str):
    graph = build_graph(supervisor_provider=supervisor)
    return process_text_message(ChatRequest(message=message, thread_id=thread), graph)


def _expected_refusal(language: str, script: str) -> str:
    if language == "ary" and script == "arabic":
        return DARIJA_ARABIC_MESSAGES["blocked"]
    return MESSAGES[language]["blocked"]


@pytest.mark.parametrize(("language", "script", "text"), PERSONALIZED_CASES)
def test_personalized_selection_is_decided_by_the_high_precision_rule(language, script, text):
    assert personalized_selection_rule(text) is True
    sensitive, confidence, _scores, source = security_decision(text)
    assert (sensitive, confidence, source) == (True, 1.0, "rule")


@pytest.mark.parametrize("text", CONTROL_CASES)
def test_profile_and_educational_questions_do_not_match_the_rule(text):
    assert personalized_selection_rule(text) is False
    sensitive, _confidence, _scores, source = security_decision(text)
    assert sensitive is False
    assert source != "rule"


@pytest.mark.parametrize(("language", "script", "text"), PERSONALIZED_CASES)
def test_personalized_selection_is_blocked_before_orientation(language, script, text):
    # Even if the Supervisor would choose orientation, security runs first.
    supervisor = FixedRouteSupervisor("orientation")
    response = _chat(text, supervisor, f"f5-personalized-{language}-{script}-{abs(hash(text))}")
    assert response.route == "securite"
    assert response.blocked is True
    assert response.status == "blocked"
    assert (response.language, response.script) == (language, script)
    assert response.answer == _expected_refusal(language, script)
    assert response.citations == []
    assert supervisor.calls == 0


def test_investor_profile_question_remains_orientation():
    supervisor = FixedRouteSupervisor("orientation")
    response = _chat("Quel est mon profil d'investisseur ?", supervisor, "f5-control-profile")
    assert response.route == "orientation"
    assert response.blocked is False
    assert response.status != "blocked"
    assert supervisor.calls == 1


@pytest.mark.parametrize(
    ("text", "route"),
    [
        ("C'est quoi un investissement ?", "pedagogie"),
        ("Comment évaluer mon profil de risque ?", "orientation"),
        ("How do I understand my risk profile?", "orientation"),
    ],
)
def test_educational_investment_questions_are_not_blocked(text, route):
    supervisor = FixedRouteSupervisor(route)
    response = _chat(text, supervisor, f"f5-control-edu-{abs(hash(text))}")
    assert response.route == route
    assert response.blocked is False


def test_stock_definition_remains_pedagogie():
    supervisor = FixedRouteSupervisor("pedagogie")
    response = _chat("C'est quoi une action ?", supervisor, "f5-control-pedagogie")
    assert response.route == "pedagogie"
    assert response.blocked is False
    assert response.status == "ok"
