import pytest

from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.api.chat import process_text_message
from app.formation.agent import FormationAgent
from app.formation.content import LOCALES, modules_for
from app.formation.models import FormationSession
from app.graph.state import create_turn_input
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.multilingual.models import LanguageAnalysis
from app.schemas.chat import ChatRequest

# ruff: noqa: E501


def make_agent(level=None):
    service = LearningProfileService(InMemoryLearningProfileStore())
    if level:
        for key in ("formation", "locale", "life"):
            service.set_level(key, level, "manual")
    return FormationAgent(service), service


def test_formation_consumes_contract_and_shared_policy():
    agent, _ = make_agent("beginner")
    assert agent.contract is AGENT_CONTRACTS["formation_elearning"]
    assert agent.contract.specialization_id == "FORMATION_EXPERT_V1"
    assert agent.policy is SHARED_POLICY


@pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
def test_known_level_starts_matching_explicit_path(level):
    agent, service = make_agent(level)
    result = agent(create_turn_input("formation", language="en", script="latin", thread_id="formation"))
    session = result["formation_session"]
    assert session.level == level
    assert session.path_id == f"{level}_financial_learning"
    assert session.status == "active"
    assert service.get_profile("formation").learning_level == level
    assert result["business_answer"]


def test_unknown_level_asks_for_manual_level():
    agent, service = make_agent()
    result = agent(
        create_turn_input(
            "Je veux commencer une formation", language="fr", script="latin", thread_id="formation"
        )
    )
    assert result["formation_session"] is None
    assert result["workflow_context"].workflow_step == "learning_level"
    assert result["assessment_required"] is False
    assert "niveau actuel" in result["business_answer"]
    assert service.get_profile("formation").learning_level is None


def test_progress_completes_one_module_and_preserves_level():
    agent, service = make_agent("beginner")
    first = agent(create_turn_input("formation", language="fr", script="latin", thread_id="formation"))
    second = agent(
        create_turn_input("suivant", language="fr", script="latin", thread_id="formation") | first
    )
    assert second["formation_session"].current_module_index == 1
    assert first["formation_session"].formation_id == second["formation_session"].formation_id
    assert second["formation_session"].completed_modules == ["beginner_market_basics"]
    assert "beginner_market_basics" in service.get_profile("formation").completed_modules
    assert service.get_profile("formation").learning_level == "beginner"


@pytest.mark.parametrize("language,script", [("fr", "latin"), ("en", "latin"), ("ar", "arabic"), ("ary", "latin"), ("ary", "arabic")])
def test_formation_presentation_locale_is_persisted(language, script):
    agent, _ = make_agent("beginner")
    first = agent(create_turn_input("formation", language=language, script=script, thread_id="locale"))
    session = first["formation_session"]
    assert (session.language, session.script) == (language, script)
    continued = agent(create_turn_input("next", thread_id="locale") | first)
    assert (continued["formation_session"].language, continued["formation_session"].script) == (
        language,
        script,
    )
    text = continued["business_answer"]
    if language == "ary" and script == "latin":
        assert all(ord(char) < 0x600 for char in text)
    if script == "arabic":
        assert any(ord(char) >= 0x600 for char in text)


def test_pause_resume_and_cancel_do_not_mutate_progress_on_pause():
    agent, _ = make_agent("intermediate")
    first = agent(create_turn_input("formation", language="en", script="latin", thread_id="life"))
    paused = agent(create_turn_input("pause", thread_id="life") | first)
    assert paused["formation_session"].status == "paused"
    assert paused["formation_session"].current_module_index == 0
    resumed = agent(create_turn_input("continue", thread_id="life") | paused)
    assert resumed["formation_session"].status == "active"
    cancelled = agent(create_turn_input("cancel formation", thread_id="life") | resumed)
    assert cancelled["formation_session"].status == "cancelled"
    assert cancelled["formation_session"].current_module_index == 1


def test_paths_have_real_content_for_all_five_locales():
    for level in ("beginner", "intermediate", "advanced"):
        modules = modules_for(level)
        assert len(modules) == 8
        for module in modules:
            for locale in LOCALES:
                content = module["content"][locale]
                assert all(content[field] for field in ("title", "objective", "lesson", "key_points", "checkpoint"))
                assert "{topic}" not in str(content)
                assert "buy a specific stock" not in str(content).lower()


def test_levels_and_arabic_locales_have_distinct_content():
    beginner = modules_for("beginner")
    intermediate = modules_for("intermediate")
    advanced = modules_for("advanced")
    assert beginner[0]["content"]["en/latin"] != intermediate[0]["content"]["en/latin"]
    assert intermediate[0]["content"]["en/latin"] != advanced[0]["content"]["en/latin"]
    assert beginner[0]["content"]["ar/arabic"] != beginner[0]["content"]["ary/arabic"]
    for module in beginner + intermediate + advanced:
        for value in module["content"]["ary/latin"].values():
            assert not any(
                "\u0600" <= char <= "\u06ff" for char in str(value)
            )


def test_formation_session_is_strict_and_typed():
    session = FormationSession(
        formation_id="formation-1",
        level="advanced",
        language="ary",
        script="arabic",
        path_id="advanced_financial_learning",
        status="active",
    )
    assert session.model_config["extra"] == "forbid"
    with pytest.raises(ValueError):
        FormationSession.model_validate({**session.model_dump(), "unexpected": True})


def test_formation_runtime_continuation_uses_persisted_locale(monkeypatch):
    import app.api.chat as chat_api

    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level("runtime", "beginner", "manual")

    class FormationSupervisor:
        def invoke_structured(self, request):
            return {"domain_status": "in_domain", "route": "formation_elearning"}

    graph = __import__("app.graph.core", fromlist=["build_graph"]).build_graph(
        supervisor_provider=FormationSupervisor(), learning_profile_service=service
    )
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="en" if text == "start formation" else "fr",
            script="latin",
            normalized_text=text,
            confidence=1.0,
        ),
    )
    first = process_text_message(
        ChatRequest(message="start formation", thread_id="runtime"), graph
    )
    second = process_text_message(ChatRequest(message="next", thread_id="runtime"), graph)
    assert first.language == second.language == "en"
    assert first.script == second.script == "latin"
    assert second.route == "formation_elearning"
    assert "Path" in second.answer


@pytest.mark.parametrize(
    "language,script,continuation",
    [("fr", "latin", "suivant"), ("en", "latin", "next"), ("ar", "arabic", "\u0627\u0644\u062a\u0627\u0644\u064a"), ("ary", "latin", "kmel"), ("ary", "arabic", "\u0643\u0645\u0644")],
)
def test_shared_pipeline_continuation_matrix(monkeypatch, language, script, continuation):
    import app.api.chat as chat_api
    from app.graph.core import build_graph

    thread_id = f"formation-matrix-{language}-{script}"
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level(thread_id, "beginner", "manual")

    class FormationSupervisor:
        def invoke_structured(self, request):
            return {"domain_status": "in_domain", "route": "formation_elearning"}

    graph = build_graph(supervisor_provider=FormationSupervisor(), learning_profile_service=service)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language=(f"ary-{script}" if language == "ary" else language),
            script=script,
            normalized_text=text,
            confidence=1.0,
        ),
    )
    first = process_text_message(ChatRequest(message="start formation", thread_id=thread_id), graph)
    second = process_text_message(ChatRequest(message=continuation, thread_id=thread_id), graph)

    assert first.route == second.route == "formation_elearning"
    assert first.language == second.language == language
    assert first.script == second.script == script
    assert second.answer
    assert "\ufffd" not in second.answer
    assert not any(marker in second.answer for marker in ("Ã", "Â", "Ø", "Ù"))
    session = graph.get_state({"configurable": {"thread_id": thread_id}}).values["formation_session"]
    assert session.current_module_index == 1
    assert session.completed_modules == ["beginner_market_basics"]
