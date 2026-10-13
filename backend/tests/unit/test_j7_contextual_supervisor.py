import json
import logging
from pathlib import Path

import pytest

from app.graph.core import build_graph, router_node
from app.graph.state import create_turn_input
from app.graph.workflow_context import ConversationWorkflowContext, WorkflowContextService


class FakeSupervisor:
    def __init__(self, route="pedagogie"):
        self.route = route
        self.calls = 0

    def invoke_structured(self, request):
        self.calls += 1
        if self.route == "out_of_domain":
            return {"domain_status": "out_of_domain", "route": "out_of_domain"}
        return {"domain_status": "in_domain", "route": self.route}


@pytest.fixture
def quiz_context():
    return WorkflowContextService().start_workflow(
        active_agent="quiz",
        active_workflow="quiz_session",
        workflow_step="question_1",
        expected_input_kind="choice",
        expected_input_values=("A", "B", "C", "D"),
    )


def test_context_model_supports_active_workflow_and_expected_input(quiz_context):
    assert quiz_context.active_agent == "quiz"
    assert quiz_context.active_workflow == "quiz_session"
    assert quiz_context.workflow_step == "question_1"
    assert quiz_context.status == "waiting_user"
    assert quiz_context.expected_input_kind == "choice"


@pytest.mark.parametrize("value", ["B", "b"])
def test_expected_choice_short_circuits_existing_supervisor(quiz_context, value):
    supervisor = FakeSupervisor(route="pedagogie")
    result = router_node(
        create_turn_input(value, language="en", script="latin")
        | {"workflow_context": quiz_context},
        supervisor,
    )
    assert result["selected_route"] == "quiz"
    assert result["workflow_context"].turn_count == 1
    assert supervisor.calls == 0


def test_no_context_uses_existing_supervisor():
    supervisor = FakeSupervisor(route="pedagogie")
    result = router_node(create_turn_input("Explain an OPCVM"), supervisor)
    assert result["selected_route"] == "pedagogie"
    assert supervisor.calls == 1


def test_supervisor_failure_logs_diagnostics_without_changing_fallback(caplog):
    class BrokenSupervisor:
        last_retries_taken = 2

        def invoke_structured(self, request):
            del request
            error = RuntimeError("provider failed for https://provider.invalid?token=secret")
            error.status_code = 503
            error.code = "temporarily_unavailable"
            raise error

    caplog.set_level(logging.WARNING, logger="app.observability")
    result = router_node(
        create_turn_input("chno hiya obligation?", language="ary", script="latin"),
        BrokenSupervisor(),
    )

    assert result["selected_route"] == "fallback"
    assert result["route_confidence"] == 0.0
    assert result["status"] == "error"
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.message.startswith("{")
    ]
    event = next(item for item in events if item.get("event") == "supervisor.failed")
    assert event["exception_type"] == "RuntimeError"
    assert event["http_status"] == 503
    assert event["provider_error_code"] == "temporarily_unavailable"
    assert "secret" not in event["error_message_sanitized"]
    assert event["language"] == "ary"
    assert event["script"] == "latin"
    assert event["retries_taken"] == 2
    assert event["stage"] == "supervisor"


def test_supervisor_success_logs_no_failure_event(caplog):
    caplog.set_level(logging.WARNING, logger="app.observability")
    result = router_node(
        create_turn_input("Explain an OPCVM", language="en", script="latin"),
        FakeSupervisor(route="pedagogie"),
    )

    assert result["selected_route"] == "pedagogie"
    assert not any(
        record.message.startswith('{"timestamp"')
        and json.loads(record.message).get("event") == "supervisor.failed"
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "message", ["Explain an OPCVM", "How do bonds work?", "How to cook pasta?"]
)
def test_non_matching_input_can_switch_agent_or_domain(quiz_context, message):
    route = "out_of_domain" if "pasta" in message else "pedagogie"
    supervisor = FakeSupervisor(route=route)
    result = router_node(
        create_turn_input(message, language="en", script="latin")
        | {"workflow_context": quiz_context},
        supervisor,
    )
    assert result["selected_route"] == route
    assert supervisor.calls == 1


def test_none_status_and_free_text_never_capture_arbitrary_input():
    service = WorkflowContextService()
    context = service.start_workflow(
        active_agent="formation_elearning",
        active_workflow="formation_assessment",
        workflow_step="awaiting_text",
        expected_input_kind="free_text",
    )
    assert not service.resolve_continuation(context, "anything").is_continuation
    assert not service.resolve_continuation(service.complete_workflow(context), "A").is_continuation
    assert not service.resolve_continuation(None, "A").is_continuation


def test_confirmation_requires_explicit_configured_value():
    service = WorkflowContextService()
    context = service.start_workflow(
        active_agent="formation_elearning",
        active_workflow="formation_assessment",
        workflow_step="confirm",
        expected_input_kind="confirmation",
        expected_input_values=("yes", "no"),
    )
    assert service.resolve_continuation(context, "yes").route == "formation_elearning"
    assert not service.resolve_continuation(context, "maybe").is_continuation


def test_same_thread_preserves_context_and_different_thread_isolated(quiz_context):
    supervisor = FakeSupervisor(route="pedagogie")
    graph = build_graph(supervisor_provider=supervisor)
    first = create_turn_input("start", language="en", script="latin")
    first["workflow_context"] = quiz_context
    graph.invoke(first, config={"configurable": {"thread_id": "thread-a"}})
    second = graph.invoke(
        create_turn_input("B", language="en", script="latin"),
        config={"configurable": {"thread_id": "thread-a"}},
    )
    assert second["selected_route"] == "quiz"
    assert second["workflow_context"].turn_count == 1
    other = graph.invoke(
        create_turn_input("B", language="en", script="latin"),
        config={"configurable": {"thread_id": "thread-b"}},
    )
    assert "workflow_context" not in other or other["workflow_context"].status == "idle"
    assert supervisor.calls == 2


def test_security_precedes_contextual_continuation(quiz_context):
    graph = build_graph(supervisor_provider=FakeSupervisor(route="pedagogie"))
    first = create_turn_input("start", language="fr", script="latin")
    first["workflow_context"] = quiz_context
    graph.invoke(first, config={"configurable": {"thread_id": "secure-context"}})
    result = graph.invoke(
        create_turn_input(
            "Quelle action dois-je acheter maintenant ?", language="fr", script="latin"
        ),
        config={"configurable": {"thread_id": "secure-context"}},
    )
    assert result["selected_route"] == "securite"
    assert result["security_status"] == "sensitive"


def test_context_service_clear_and_completion_are_not_routing_locks(quiz_context):
    service = WorkflowContextService()
    completed = service.complete_workflow(quiz_context)
    cleared = service.clear_workflow()
    assert completed.status == "completed"
    assert cleared.status == "idle"
    assert cleared.active_agent is None


def test_j7_03_does_not_add_classifier_or_quiz_state():
    root = Path(__file__).resolve().parents[3]
    assert not (root / "backend/app/graph/context_classifier.py").exists()
    assert not (root / "backend/app/graph/quiz_state.py").exists()
    assert not hasattr(ConversationWorkflowContext, "quiz_questions")
