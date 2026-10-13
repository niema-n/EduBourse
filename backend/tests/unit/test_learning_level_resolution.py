import pytest

from app.formation.agent import FormationAgent
from app.graph.core import build_graph, router_node
from app.graph.state import create_turn_input
from app.learning.level_resolution import LEVEL_VARIANTS, extract_level
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.orientation.agent import OrientationAgent
from app.quiz.agent import QuizAgent


@pytest.fixture
def service():
    return LearningProfileService(InMemoryLearningProfileStore())


CASES = [
    (
        "Je suis débutant en Bourse. Propose-moi un parcours e-learning adapté.",
        "beginner",
        "fr",
        "latin",
    ),
    ("J'ai un niveau intermédiaire. Quels modules dois-je suivre ?", "intermediate", "fr", "latin"),
    ("Je suis avancé en Bourse. Propose-moi une formation adaptée.", "advanced", "fr", "latin"),
    ("I am a beginner. Show me the training modules.", "beginner", "en", "latin"),
    ("أنا مبتدئ في البورصة", "beginner", "ar", "arabic"),
    ("مستواي متوسط", "intermediate", "ar", "arabic"),
    ("أنا متقدمة في البورصة", "advanced", "ar", "arabic"),
    ("ana mobtadi2 f lboursa", "beginner", "ary", "latin"),
    ("ana motawassit f lboursa", "intermediate", "ary", "latin"),
    ("ana mota9adim f lboursa", "advanced", "ary", "latin"),
    ("أنا مبتدئة فالبورصة", "beginner", "ary", "arabic"),
]


@pytest.mark.parametrize("agent_type", [FormationAgent, OrientationAgent])
@pytest.mark.parametrize("message,level,language,script", CASES)
def test_explicit_level_starts_matching_modules(
    service, agent_type, message, level, language, script
):
    result = agent_type(service)(
        create_turn_input(message, language=language, script=script, thread_id="t")
    )
    profile = service.get_profile("t")
    assert (profile.learning_level, profile.level_source) == (level, "manual")
    assert result["assessment_required"] is False
    assert result["formation_session"].level == level
    assert result["formation_session"].path_id == f"{level}_financial_learning"
    assert result["formation_session"].current_module_index == 0
    assert "quiz_session" not in result


@pytest.mark.parametrize("level,variants", LEVEL_VARIANTS.items())
def test_all_variants_in_pending_answer(level, variants):
    for variant in variants:
        assert extract_level(variant + ".", allow_bare=True) == level
        assert extract_level(variant) is None


@pytest.mark.parametrize(
    "message",
    [
        "niveau avancé du marché",
        "Je veux un cours avancé",
        "Je ne suis pas débutant",
        "I am not a beginner",
        "Mon ami est débutant",
        "Le marché est avancé",
        "أنا لست مبتدئ",
        "ana machi mobtadi",
        "Je suis débutant ou je suis avancé",
    ],
)
def test_no_unjustified_self_report(message):
    assert extract_level(message, allow_bare=True) is None


class Supervisor:
    def __init__(self, route):
        self.route = route
        self.calls = 0

    def invoke_structured(self, request):
        self.calls += 1
        return {"domain_status": "in_domain", "route": self.route}


@pytest.mark.parametrize("route", ["formation_elearning", "orientation"])
@pytest.mark.parametrize(
    "language,script,answer",
    [
        ("fr", "latin", "intermédiaire"),
        ("en", "latin", "intermediate"),
        ("ar", "arabic", "متوسط"),
        ("ary", "latin", "motawassit"),
        ("ary", "arabic", "متوسط"),
    ],
)
def test_clarification_continues_on_same_thread(service, route, language, script, answer):
    supervisor = Supervisor(route)
    graph = build_graph(supervisor_provider=supervisor, learning_profile_service=service)
    config = {"configurable": {"thread_id": "t"}}
    first = graph.invoke(
        create_turn_input(
            "Je veux suivre une formation en Bourse.",
            language=language,
            script=script,
            thread_id="t",
        ),
        config,
    )
    assert first["workflow_context"].workflow_step == "learning_level"
    assert first["assessment_required"] is False
    assert not first.get("quiz_session")
    second = graph.invoke(
        create_turn_input(answer, language=language, script=script, thread_id="t"), config
    )
    assert supervisor.calls == 1
    assert second["formation_session"].level == "intermediate"
    assert service.get_profile("t").level_source == "manual"
    assert not second.get("quiz_session")


@pytest.mark.parametrize(
    "message",
    [
        "Je veux évaluer mon niveau en Bourse.",
        "Teste mon niveau.",
        "Je ne connais pas mon niveau, fais-moi un diagnostic.",
        "Assess my level",
        "اختبر مستواي",
        "testi niveau dyali",
    ],
)
@pytest.mark.parametrize("stored", [None, "advanced"])
def test_intentional_diagnostic_preserved(service, message, stored):
    if stored:
        service.set_level("t", stored, "manual")
    result = QuizAgent(service)(
        create_turn_input(message, language="fr", script="latin", thread_id="t")
    )
    assert result["quiz_session"].phase == "diagnostic"
    assert len(result["quiz_session"].questions) == 6
    assert service.get_profile("t").learning_level == stored


def test_unrelated_turn_uses_supervisor_after_clarification(service):
    first = FormationAgent(service)(create_turn_input("formation", thread_id="t"))
    supervisor = Supervisor("pedagogie")
    result = router_node(create_turn_input("Explique les obligations") | first, supervisor)
    assert result["selected_route"] == "pedagogie"
    assert supervisor.calls == 1


def test_manual_level_replaces_existing_path(service):
    service.set_level("t", "beginner", "diagnostic")
    agent = FormationAgent(service)
    first = agent(create_turn_input("formation", thread_id="t"))
    second = agent(first | create_turn_input("Je suis avancé en Bourse", thread_id="t"))
    assert second["formation_session"].level == "advanced"
    assert service.get_profile("t").level_source == "manual"
