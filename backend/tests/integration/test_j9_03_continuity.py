from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.graph.core import build_graph
from app.graph.state import create_turn_input
from app.rag.grounded_generation import GroundedGenerationResult


class StubSupervisor:
    def invoke_structured(self, request):
        return {"domain_status": "in_domain", "route": "pedagogie"}


class StubGroundedService:
    def generate(self, request):
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=f"Stub answer for: {request.original_query}",
            citations=[],
            used_evidence_ids=[],
            retrieval_status="ok",
            generation_status="ok",
            grounded=True,
            insufficient_evidence=False,
            provider_retryable=False,
        )


def test_same_memorysaver_graph_reuses_thread_checkpoint_without_persistence():
    thread_id = "j903-offline-continuity-001"
    config = {"configurable": {"thread_id": thread_id}}
    checkpointer = MemorySaver()
    graph = build_graph(
        checkpointer=checkpointer,
        supervisor_provider=StubSupervisor(),
        grounded_service=StubGroundedService(),
    )

    turn_one = graph.invoke(
        create_turn_input(
            "C'est quoi une action ?",
            language="fr",
            script="latin",
            thread_id=thread_id,
        ),
        config=config,
    )
    turn_two = graph.invoke(
        create_turn_input(
            "Et quels sont les risques ?",
            language="fr",
            script="latin",
            thread_id=thread_id,
        ),
        config=config,
    )

    assert turn_one["status"] == "completed"
    assert turn_two["status"] == "completed"
    assert turn_one["thread_id"] == turn_two["thread_id"] == thread_id
    assert turn_two["business_answer"] == "Stub answer for: Et quels sont les risques ?"

    checkpoints = list(graph.get_state_history(config))
    assert len(checkpoints) >= 2
    assert {item.config["configurable"]["thread_id"] for item in checkpoints} == {thread_id}
    assert set(checkpointer.storage) == {thread_id}

    fresh_graph = build_graph(
        checkpointer=MemorySaver(),
        supervisor_provider=StubSupervisor(),
        grounded_service=StubGroundedService(),
    )
    assert fresh_graph.get_state(config).values == {}
