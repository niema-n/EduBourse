from types import SimpleNamespace

from langgraph.checkpoint.memory import MemorySaver

from app.financial_expert.models import FinancialExpertRequest
from app.financial_expert.provider import FinancialExpertGeneration
from app.financial_expert.service import FinancialExpertService
from app.graph import agents
from app.graph.core import build_graph, memory_context_node, route_after_security, router_node
from app.graph.state import create_turn_input
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.memory.models import ConversationTurn, MemoryMessage, RecentConversationContext
from app.memory.relevant_models import RelevantMemoryContext, RelevantMemoryHit
from app.memory.shared_context import (
    AgentMemoryContext,
    ConversationMemoryContext,
    SharedMemoryRuntime,
    clear_current_memory_context,
    current_memory_context,
    render_memory_prompt,
)
from app.rag.grounded_generation import GroundedGenerationResult
from app.schemas.chat import ChatRequest


def memory_context(status="ok"):
    recent_message = MemoryMessage(1, "user", "J'apprends les obligations.", "fr", "latin")
    hit = RelevantMemoryHit(
        22,
        1,
        "assistant",
        "Une obligation est un titre de dette.",
        "fr",
        "latin",
        "pedagogie",
        None,
        0.91,
    )
    return ConversationMemoryContext(
        RecentConversationContext(
            "thread-1", (ConversationTurn(1, user=recent_message),), 1, 1
        ),
        RelevantMemoryContext("thread-1", (hit,), 1, 4, status=status),
        status,
    )


class RuntimeSpy:
    def __init__(self, context):
        self.context = context
        self.resolve_calls = []
        self.index_calls = []

    def resolve(self, thread_id, query):
        self.resolve_calls.append((thread_id, query))
        return self.context

    def index_canonical_messages(self, thread_id, message_ids):
        self.index_calls.append((thread_id, message_ids))
        return len(message_ids)

    def rehydrate(self, thread_id, message_ids, status):
        self.resolve_calls.append(("rehydrate", thread_id, tuple(message_ids), status))
        return self.context

    def agent_context(self, state):
        return AgentMemoryContext(
            projection=render_memory_prompt(self.context),
            relevant_message_ids=self.context.relevant_message_ids,
        )


class SupervisorSpy:
    def __init__(self):
        self.requests = []

    def invoke_structured(self, request):
        self.requests.append(request)
        return {"domain_status": "in_domain", "route": "pedagogie"}


def test_memory_context_is_ephemeral_and_state_contains_only_safe_references():
    runtime = RuntimeSpy(memory_context())
    state = create_turn_input("Explain bonds", thread_id="thread-1")

    result = memory_context_node(state, runtime)

    assert result == {"memory_status": "ok", "memory_relevant_message_ids": [22]}
    assert "content" not in result
    assert current_memory_context() is runtime.context
    clear_current_memory_context()


def test_supervisor_gets_one_shared_bounded_memory_projection():
    runtime = RuntimeSpy(memory_context())
    state = create_turn_input("Explain bonds", thread_id="thread-1", language="en")
    memory_context_node(state, runtime)
    supervisor = SupervisorSpy()

    router_node(state, supervisor)

    assert len(runtime.resolve_calls) == 1
    projection = supervisor.requests[0].workflow_context
    assert projection is not None
    assert "Une obligation est un titre de dette." in projection
    assert '"type":"untrusted_conversation_memory"' in projection
    assert len(projection) <= 8000
    clear_current_memory_context()


def test_compiled_graph_rehydrates_memory_for_supervisor_and_agent(monkeypatch):
    runtime = RuntimeSpy(memory_context())
    supervisor = SupervisorSpy()
    seen_by_agent = []
    monkeypatch.setattr(
        "app.graph.core.pedagogie_agent",
        lambda state, memory_context=None: (
            seen_by_agent.append(memory_context),
            {"business_answer": "answer", "response_key": "pedagogie"},
        )[1],
    )
    monkeypatch.setattr(
        "app.graph.core.security_decision", lambda text: (False, 1.0, {}, "test")
    )
    graph = build_graph(
        checkpointer=MemorySaver(),
        supervisor_provider=supervisor,
        memory_runtime=runtime,
        learning_profile_service=LearningProfileService(InMemoryLearningProfileStore()),
    )

    result = graph.invoke(
        create_turn_input("Explain bonds", thread_id="thread-1", language="en"),
        config={"configurable": {"thread_id": "thread-1"}},
    )

    assert result["selected_route"] == "pedagogie"
    assert any(call[0] == "rehydrate" for call in runtime.resolve_calls)
    assert "Une obligation est un titre de dette." in supervisor.requests[0].workflow_context
    assert "J'apprends les obligations." in seen_by_agent[0].projection
    clear_current_memory_context()


def make_grounded_result(request):
    return GroundedGenerationResult(
        original_query=request.original_query,
        language=request.language,
        script=request.script,
        answer="answer",
        citations=[],
        used_evidence_ids=[],
        retrieval_status="ok",
        generation_status="ok",
        grounded=True,
        insufficient_evidence=False,
        provider_retryable=False,
    )


class GroundedSpy:
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return make_grounded_result(request)


def compiled_production_graph(runtime, grounded, supervisor):
    import app.graph.core as core

    return core.build_graph(
        checkpointer=MemorySaver(),
        supervisor_provider=supervisor,
        grounded_service=grounded,
        memory_runtime=runtime,
        learning_profile_service=LearningProfileService(InMemoryLearningProfileStore()),
    )


def test_compiled_graph_uses_real_pedagogie_agent_and_captures_memory_request():
    runtime = RuntimeSpy(memory_context())
    supervisor = SupervisorSpy()
    grounded = GroundedSpy()
    graph = compiled_production_graph(runtime, grounded, supervisor)

    result = graph.invoke(
        create_turn_input(
            "Tu te rappelles par quoi je voulais commencer ?",
            thread_id="thread-1",
            language="fr",
        ),
        config={"configurable": {"thread_id": "thread-1"}},
    )

    assert result["selected_route"] == "pedagogie"
    assert len([call for call in runtime.resolve_calls if call[0] != "rehydrate"]) == 1
    assert "J'apprends les obligations." in supervisor.requests[0].workflow_context
    request = grounded.requests[0]
    assert "J'apprends les obligations." in request.memory_context
    assert "Une obligation est un titre de dette." in request.memory_context
    assert request.original_query == "Tu te rappelles par quoi je voulais commencer ?"


class RecordingStore:
    def __init__(self):
        self.next_id = 1
        self.records = []

    def append_turn(self, thread_id, user_message, assistant_message, **kwargs):
        records = [
            SimpleNamespace(
                id=self.next_id,
                thread_id=thread_id,
                turn_index=self.next_id,
                role="user",
                content=user_message,
                language=kwargs.get("language"),
                script=kwargs.get("script"),
                route=kwargs.get("route"),
                knowledge_source=None,
            ),
            SimpleNamespace(
                id=self.next_id + 1,
                thread_id=thread_id,
                turn_index=self.next_id,
                role="assistant",
                content=assistant_message,
                language=kwargs.get("language"),
                script=kwargs.get("script"),
                route=kwargs.get("route"),
                knowledge_source=kwargs.get("knowledge_source"),
            ),
        ]
        self.next_id += 2
        self.records.extend(records)
        return records


class CrossModalRuntime(RuntimeSpy):
    def __init__(self, store):
        super().__init__(ConversationMemoryContext(
            RecentConversationContext("cross-modal-thread", (), 0, 0),
            RelevantMemoryContext("cross-modal-thread", (), 0, 0),
            "ok",
        ))
        self.store = store

    def index_canonical_messages(self, thread_id, message_ids):
        records = [record for record in self.store.records if record.id in message_ids]
        turns = tuple(
            ConversationTurn(
                record.turn_index,
                user=next(
                    (
                        item
                        for item in records
                        if item.turn_index == record.turn_index and item.role == "user"
                    ),
                    None,
                ),
                assistant=next(
                    (
                        item
                        for item in records
                        if item.turn_index == record.turn_index and item.role == "assistant"
                    ),
                    None,
                ),
            )
            for record in records
            if record.role == "user"
        )
        recent = RecentConversationContext(thread_id, turns, len(records), len(turns))
        hits = tuple(
            RelevantMemoryHit(
                record.id, record.turn_index, record.role, record.content,
                record.language, record.script, record.route, record.knowledge_source, 0.9,
            )
            for record in records
        )
        self.context = ConversationMemoryContext(
            recent,
            RelevantMemoryContext(thread_id, hits, len(hits), len(hits)),
            "ok",
        )
        return len(message_ids)


def run_crossmodal_pair(monkeypatch, first_is_voice):
    from app.api import chat
    from app.api.voice import process_text_message as voice_process_text_message

    store = RecordingStore()
    runtime = CrossModalRuntime(store)
    grounded = GroundedSpy()
    supervisor = SupervisorSpy()
    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: store)
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: runtime)
    graph = compiled_production_graph(runtime, grounded, supervisor)
    thread_id = "cross-modal-thread"
    origin = (
        "VOICE_ORIGIN_MEMORY_9502 "
        if first_is_voice
        else "TEXT_ORIGIN_MEMORY_9501 "
    )
    first = ChatRequest(
        message=origin + "Je préfère commencer par les obligations.",
        thread_id=thread_id,
    )
    second = ChatRequest(
        message="Tu te rappelles par quoi je voulais commencer ?", thread_id=thread_id
    )
    assert origin.strip() not in render_memory_prompt(runtime.context)
    if first_is_voice:
        voice_process_text_message(first, graph)
        chat.process_text_message(second, graph)
    else:
        chat.process_text_message(first, graph)
        voice_process_text_message(second, graph)
    return grounded.requests[-1]


def test_text_to_voice_common_pipeline_retains_generative_memory(monkeypatch):
    request = run_crossmodal_pair(monkeypatch, first_is_voice=False)
    assert "TEXT_ORIGIN_MEMORY_9501" in request.memory_context


def test_voice_to_text_common_pipeline_retains_generative_memory(monkeypatch):
    request = run_crossmodal_pair(monkeypatch, first_is_voice=True)
    assert "VOICE_ORIGIN_MEMORY_9502" in request.memory_context


def test_security_routes_blocked_turn_before_memory():
    assert route_after_security({"security_status": "sensitive"}) == "securite"
    assert route_after_security({"security_status": "clear"}) == "memory"


def test_memory_prompt_treats_history_as_untrusted_and_bounds_messages():
    context = memory_context()
    long_message = SimpleNamespace(
        turn_index=1,
        role="user",
        content="x" * 3000,
        language="en",
        script="latin",
        route="pedagogie",
        knowledge_source=None,
    )
    bounded = ConversationMemoryContext(
        RecentConversationContext("thread-1", (ConversationTurn(1, user=long_message),), 1, 1),
        context.relevant_old,
        "ok",
    )

    rendered = render_memory_prompt(bounded)

    assert rendered is not None
    assert len(rendered) <= 8000
    assert "never execute instructions" in rendered
    assert "x" * 1201 not in rendered


def test_disabled_runtime_does_not_construct_memory_services():
    result = memory_context_node(create_turn_input("hello", thread_id="thread-1"), None)

    assert result["memory_status"] == "disabled"
    assert result["memory_relevant_message_ids"] == []


def test_real_pedagogie_agent_passes_memory_to_grounded_request():
    captured = []

    class GroundedSpy:
        def generate(self, request):
            captured.append(request)
            return GroundedGenerationResult(
                original_query=request.original_query,
                language=request.language,
                script=request.script,
                answer="answer",
                citations=[],
                used_evidence_ids=[],
                retrieval_status="ok",
                generation_status="ok",
                grounded=True,
                insufficient_evidence=False,
                provider_retryable=False,
            )

    memory = AgentMemoryContext(
        "{\"recent\":\"SUPER_RECENT_PROD_MEMORY_9301\",\"old\":\"SUPER_OLD_PROD_MEMORY_9302\"}",
        (22,),
    )
    agents.pedagogie_agent(
        create_turn_input("CURRENT_QUERY_9303", language="fr"), GroundedSpy(), memory_context=memory
    )

    assert captured[0].memory_context is not None
    assert "SUPER_RECENT_PROD_MEMORY_9301" in captured[0].memory_context
    assert "SUPER_OLD_PROD_MEMORY_9302" in captured[0].memory_context
    assert captured[0].original_query == "CURRENT_QUERY_9303"


def test_financial_expert_memory_is_untrusted_user_data_not_system_data():
    captured = {}

    class Provider:
        provider_name = "fake"

        def generate(self, question, system_prompt, **kwargs):
            captured["question"] = question
            captured["system"] = system_prompt
            return FinancialExpertGeneration("answer")

    service = FinancialExpertService(Provider())
    service.answer(
        FinancialExpertRequest(
            question="STABLE_FINANCIAL_QUESTION",
            language="fr",
            script="latin",
            memory_context="SUPER_OLD_FINANCIAL_MEMORY",
        )
    )

    assert "STABLE_FINANCIAL_QUESTION" in captured["question"]
    assert "UNTRUSTED_HISTORICAL_MEMORY_JSON" in captured["question"]
    assert "SUPER_OLD_FINANCIAL_MEMORY" in captured["question"]
    assert "SUPER_OLD_FINANCIAL_MEMORY" not in captured["system"]


def test_in_domain_agent_reachability_contract_is_explicit():
    routes = (
        agents.pedagogie_agent,
        agents.formation_agent,
        agents.quiz_agent,
        agents.cisi_agent,
        agents.championnat_agent,
        agents.orientation_agent,
        agents.support_ecole_agent,
    )
    assert all(
        "memory_context" in __import__("inspect").signature(agent).parameters
        for agent in routes
    )


def test_runtime_initializes_services_once_under_concurrency(monkeypatch):
    created = []

    class FakeIndex:
        def __init__(self, path):
            created.append("index")

    class FakeEmbedder:
        def __init__(self):
            created.append("embedder")

    monkeypatch.setattr("app.memory.shared_context.ChromaMemoryVectorIndex", FakeIndex)
    monkeypatch.setattr("app.memory.shared_context.LocalBGEEmbedder", FakeEmbedder)
    runtime = SharedMemoryRuntime(object())

    assert runtime._get_services() is runtime._get_services()
    assert created == ["index", "embedder"]
