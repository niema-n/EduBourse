import logging
import os
import re
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends

from app.config import get_settings
from app.financial_expert.service import FinancialExpertService
from app.graph.core import build_graph
from app.graph.final_response_composer import (
    get_final_response_composer,
    rejected_validation_reasons,
)
from app.graph.language_adapter import normalize_business_language
from app.graph.localization import localize_answer, validate_localized_script
from app.graph.response_localizer import get_response_localizer, localize_business_answer
from app.graph.state import create_turn_input, safe_thread_id
from app.llm.base import ProviderUnavailable
from app.llm.factory import create_provider
from app.memory.embeddings import LocalBGEEmbedder, MemoryEmbeddingUnavailableError
from app.memory.shared_context import SharedMemoryRuntime, clear_current_memory_context
from app.multilingual.service import MultilingualService
from app.observability.context import ensure_turn_context
from app.observability.logging import emit, thread_ref
from app.observability.timing import elapsed_ms, start_timer
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.thread_store import ConversationThreadStore
from app.rag.comparison import comparison_concepts, limitation, rewrite_preserves_comparison
from app.rag.grounded_generation import (
    GroundedGenerationResult,
    grounded_provider_from_environment,
    safe_grounding_failure_message,
)
from app.rag.runtime import get_retrieval_service
from app.schemas.chat import MAX_WEB_SOURCES, APIError, ChatRequest, ChatResponse

router = APIRouter(tags=["Assistant"])
multilingual = MultilingualService()
logger = logging.getLogger(__name__)
_cached_chat_graph: Any | None = None


def _provider_init_error_fields(exc: Exception) -> dict[str, object]:
    """Return bounded, secret-free diagnostics for provider construction errors."""
    response = getattr(exc, "response", None)
    status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
    code = getattr(exc, "code", None)
    body = getattr(exc, "body", None)
    if code is None and isinstance(body, dict):
        error = body.get("error")
        code = body.get("code") or (error.get("code") if isinstance(error, dict) else None)
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    message = re.sub(
        r"(?i)(authorization|api[_ -]?key|token)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        message,
    )
    message = re.sub(r"https?://\S+", "[url-redacted]", message)
    return {
        "exception_type": type(exc).__name__,
        "error_message_sanitized": message[:500],
        "http_status": status,
        "provider_error_code": code,
    }


def _current_turn_knowledge_source(result: dict[str, Any], route: str) -> str | None:
    """Keep provenance only when the current route proves it produced it."""
    source = result.get("knowledge_source")
    if route != "pedagogie" or not isinstance(source, str):
        return None
    if source == "rag":
        return source if result.get("grounded") is True else None
    if source in {
        "llm_general_financial_knowledge",
        "llm_web_grounded_financial_knowledge",
        "controlled_current_data_limitation",
    }:
        return source
    return None


def _current_turn_web_sources(result: dict[str, Any], provenance: str | None) -> list[dict]:
    """Bounded title/uri pairs, only for a web-grounded answer actually returned."""
    if (
        provenance != "llm_web_grounded_financial_knowledge"
        or result.get("web_grounded") is not True
    ):
        return []
    sources = []
    for source in result.get("web_sources") or []:
        if not isinstance(source, dict):
            continue
        title = source.get("title") if isinstance(source.get("title"), str) else None
        uri = source.get("uri") if isinstance(source.get("uri"), str) else None
        if uri is not None and not uri.startswith("https://"):
            uri = None
        if title is None and uri is None:
            continue
        sources.append(
            {"title": title[:300] if title else None, "uri": uri[:2000] if uri else None}
        )
        if len(sources) == MAX_WEB_SOURCES:
            break
    return sources


@lru_cache(maxsize=1)
def get_conversation_history_store() -> SqlAlchemyConversationHistoryStore | None:
    settings = get_settings()
    if not settings.persistence_enabled:
        return None
    database = PersistenceDatabase(settings=settings)
    return SqlAlchemyConversationHistoryStore(database, ConversationThreadStore(database))


def shared_retrieval_embedding_provider() -> Any:
    """Reuse the BGE-M3 instance already loaded by RAG: never load a second one."""
    retrieval = get_retrieval_service()
    if retrieval is None:
        raise MemoryEmbeddingUnavailableError("shared BGE-M3 provider unavailable")
    return retrieval.embedding_provider


@lru_cache(maxsize=1)
def get_memory_runtime() -> SharedMemoryRuntime | None:
    history_store = get_conversation_history_store()
    if history_store is None:
        return None
    return SharedMemoryRuntime(
        history_store,
        embedder=LocalBGEEmbedder(provider_factory=shared_retrieval_embedding_provider),
        relevant_enabled=get_settings().relevant_memory_enabled,
    )


class UnavailableProvider:
    def invoke_structured(self, request: object) -> object:
        raise ProviderUnavailable("supervisor provider unavailable")


class UnavailableGroundedService:
    def generate(self, request):
        return GroundedGenerationResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            answer=safe_grounding_failure_message(request.language, request.script),
            citations=[],
            used_evidence_ids=[],
            retrieval_status="configuration_error",
            generation_status="retrieval_configuration_error",
            grounded=False,
            insufficient_evidence=False,
            provider_retryable=False,
        )


def _create_grounded_service() -> Any:
    try:
        # Shared with the read-only RAG API so BGE-M3 is loaded only once.
        retrieval = get_retrieval_service()
        if retrieval is None:
            return UnavailableGroundedService()
        return __import__(
            "app.rag.grounded_generation", fromlist=["GroundedGenerationService"]
        ).GroundedGenerationService(
            retrieval,
            provider=grounded_provider_from_environment(),
        )
    except Exception as exc:
        logger.error("grounded service initialization failed error_type=%s", type(exc).__name__)
        return UnavailableGroundedService()


@lru_cache(maxsize=1)
def get_chat_graph() -> Any:
    global _cached_chat_graph
    settings = get_settings()
    try:
        provider = create_provider(model=settings.groq_model or None)
    except ProviderUnavailable as exc:
        emit(
            "supervisor.provider_init_failed",
            level=logging.WARNING,
            **_provider_init_error_fields(exc),
            provider=os.getenv("LLM_PROVIDER", "groq").strip().lower(),
            model=os.getenv("GROQ_MODEL", "").strip() or None,
            stage="provider_initialization",
        )
        provider = UnavailableProvider()
    financial_expert_service = (
        FinancialExpertService.from_environment()
        if settings.financial_expert_fallback_enabled
        else None
    )
    _cached_chat_graph = build_graph(
        supervisor_provider=provider,
        grounded_service=_create_grounded_service(),
        financial_expert_service=financial_expert_service,
        financial_expert_fallback_enabled=settings.financial_expert_fallback_enabled,
        memory_runtime=get_memory_runtime(),
    )
    return _cached_chat_graph


def close_cached_chat_graph() -> None:
    """Close a lazily-created persistent checkpointer without initializing it."""
    global _cached_chat_graph
    graph = _cached_chat_graph
    _cached_chat_graph = None
    get_chat_graph.cache_clear()
    if graph is None:
        return
    checkpointer = getattr(graph, "checkpointer", None)
    close = getattr(checkpointer, "close", None)
    if callable(close):
        close()


def _index_committed_messages(runtime, thread_id: str, message_ids: list[int]) -> None:
    """Rebuildable semantic enrichment; canonical history is already committed."""
    started = start_timer()
    try:
        runtime.index_canonical_messages(thread_id, message_ids)
    except Exception as exc:
        emit(
            "memory.index.failed", level=logging.WARNING,
            duration_ms=elapsed_ms(started), error_type=type(exc).__name__,
            stage="memory_index", thread_ref=thread_ref(thread_id),
        )
        return
    emit(
        "memory.index.completed", duration_ms=elapsed_ms(started),
        stage="memory_index", thread_ref=thread_ref(thread_id),
    )


def _process_text_message(
    payload: ChatRequest,
    graph: Annotated[Any, Depends(get_chat_graph)],
    *,
    apply_final_response_composer: bool = False,
    post_response_tasks: BackgroundTasks | None = None,
) -> tuple[ChatResponse, dict[str, Any]]:
    thread_reference = thread_ref(payload.thread_id.strip())
    emit("request.started", stage="business", thread_ref=thread_reference)
    language_started = start_timer()
    analysis = multilingual.analyze(payload.message.strip())
    emit("language.completed", duration_ms=elapsed_ms(language_started), stage="language")
    business_language, business_script = normalize_business_language(
        analysis.language, None if analysis.language.startswith("ary-") else analysis.script
    )
    state = create_turn_input(
        payload.message.strip(),
        language=analysis.language,
        script=business_script,
        thread_id=payload.thread_id.strip(),
    )
    state["normalized_message"] = analysis.normalized_text
    graph_started = start_timer()
    clear_current_memory_context()
    try:
        try:
            result = graph.invoke(
                state,
                config={"configurable": {"thread_id": safe_thread_id(payload.thread_id.strip())}},
            )
        except Exception as exc:
            logger.error("chat graph invocation failed error_type=%s", type(exc).__name__)
            result = {
                **state,
                "selected_route": "fallback",
                "status": "error",
                "error": "graph_failure",
            }
    finally:
        clear_current_memory_context()
    graph_duration = elapsed_ms(graph_started)
    emit("graph.completed", duration_ms=graph_duration, thread_ref=thread_reference)
    route = str(result.get("selected_route", "fallback"))
    quiz_session = result.get("quiz_session")
    response_key = result.get("response_key")
    if response_key == "quiz" and quiz_session is not None:
        # A/B/C/D carries no reliable language signal; the active quiz owns
        # the presentation locale for its dynamic response.
        effective_language = getattr(quiz_session, "language", None)
        effective_script = getattr(quiz_session, "script", None)
        if isinstance(quiz_session, dict):
            effective_language = quiz_session.get("language")
            effective_script = quiz_session.get("script")
        if effective_language and effective_script:
            business_language = effective_language
            business_script = effective_script
    if route == "formation_elearning" and result.get("formation_session") is not None:
        formation_session = result["formation_session"]
        effective_language = getattr(formation_session, "language", None)
        effective_script = getattr(formation_session, "script", None)
        if isinstance(formation_session, dict):
            effective_language = formation_session.get("language")
            effective_script = formation_session.get("script")
        if effective_language and effective_script:
            business_language = effective_language
            business_script = effective_script
    blocked = route == "securite" or result.get("security_status") == "sensitive"
    error = bool(result.get("error")) and not blocked
    business_answer = str(result.get("business_answer", ""))
    valid_business_turn = bool(business_answer.strip()) and not blocked and not error
    finalization_failed_after_valid_turn = False
    result["raw_agent_answer"] = business_answer
    # The selected route can remain the originating workflow when that
    # workflow delegates to QuizAgent. The produced response key is the
    # authoritative type for finalization decisions.
    structured_quiz = response_key == "quiz" and quiz_session is not None
    grounded_status = result.get("grounded_status")
    is_grounded_path = bool(grounded_status)
    is_formation_path = (
        route == "formation_elearning"
        and result.get("formation_session") is not None
        and bool(business_answer.strip())
    )
    is_orientation_path = (
        route == "orientation"
        and result.get("orientation_recommendation") is not None
        and bool(business_answer.strip())
    )
    is_specialist_path = (
        route in {"cisi", "championnat", "support_ecole", "out_of_domain"}
        and result.get("response_key") == route
        and bool(business_answer.strip())
    )
    answer = business_answer
    if False and not validate_localized_script(answer, business_language, business_script):
        answer = localize_answer(
            "", business_language, business_script, route="fallback", blocked=blocked, error=error
        )
        if not validate_localized_script(answer, business_language, business_script):
            answer = {
                "latin": "A controlled response is unavailable.",
                "arabic": "الرد المتحكم فيه غير متاح.",
            }[business_script]
    def legacy_fallback_answer() -> str:
        """Keep the previous presentation path as a secondary fallback."""
        nonlocal finalization_failed_after_valid_turn, grounded_status
        fallback_answer = (
            business_answer
            if is_grounded_path
            or is_formation_path
            or is_orientation_path
            or is_specialist_path
            else localize_answer(
                business_answer,
                business_language,
                business_script,
                route=route,
                response_key=result.get("response_key"),
                blocked=blocked,
                error=error,
            )
        )
        if business_language == "ary" and fallback_answer.strip():
            localization_started = start_timer()
            localization = localize_business_answer(
                fallback_answer,
                business_language,
                business_script,
                get_response_localizer(),
            )
            emit(
                "localization.stage",
                duration_ms=elapsed_ms(localization_started),
                localization_status=localization.status,
                localization_provider=localization.provider,
                localization_retry_count=localization.retry_count,
                localization_guard_result=localization.guard_result,
                stage="localization_fallback",
            )
            if localization.status == "failed" or localization.answer is None:
                finalization_failed_after_valid_turn = valid_business_turn
                fallback_answer = safe_grounding_failure_message(
                    business_language, business_script
                )
                result["grounded"] = False
                result["grounded_citations"] = []
                result["knowledge_source"] = None
                result["web_grounded"] = False
                result["web_sources"] = []
                if is_grounded_path:
                    grounded_status = "localization_error"
            else:
                fallback_answer = localization.answer
        if not validate_localized_script(fallback_answer, business_language, business_script):
            fallback_answer = localize_answer(
                "",
                business_language,
                business_script,
                route="fallback",
                blocked=blocked,
                error=error,
            )
            if not validate_localized_script(fallback_answer, business_language, business_script):
                fallback_answer = safe_grounding_failure_message(
                    business_language, business_script
                )
        return fallback_answer

    composer_started = start_timer()
    composer = (
        get_final_response_composer()
        if apply_final_response_composer and not structured_quiz
        else None
    )
    composer_status = "unavailable"
    fallback_used = False
    composer_retry_count = 0
    composer_validation_reasons: list[str] = []
    final_response_provider = "legacy"
    fallback_provider: str | None = None
    fallback_reason: str | None = None
    fallback_status: str | None = None
    language_degraded = False
    if structured_quiz:
        # QuizAgent owns the canonical question/options/order. Never send this
        # structured payload through a generative presentation layer.
        answer = business_answer
        composer_status = "bypassed_quiz"
        final_response_provider = "quiz_business"
    elif not apply_final_response_composer:
        answer = legacy_fallback_answer()
        composer_status = "disabled"
    elif composer is not None:
        try:
            answer = composer.compose(
                business_answer,
                business_language,
                business_script,
                route=route,
                blocked=blocked,
                status=str(result.get("status")) if result.get("status") else None,
            )
            composer_status = "accepted"
            final_response_provider = "azure_openai"
            composer_retry_count = max(0, len(composer.validation_attempts) - 1)
            composer_validation_reasons = rejected_validation_reasons(
                composer.validation_attempts
            )
        except Exception as exc:
            composer_status = "failed"
            fallback_used = True
            finalization_failed_after_valid_turn = valid_business_turn
            composer_retry_count = max(0, len(composer.validation_attempts) - 1)
            composer_validation_reasons = rejected_validation_reasons(
                composer.validation_attempts
            )
            emit(
                "final_response.composer_failed",
                level=logging.WARNING,
                error_type=type(exc).__name__,
                language=business_language,
                script=business_script,
                route=route,
                stage="final_response",
            )
            fallback_reason = "azure_composition_failed"
            if business_language == "ary" and business_script == "latin":
                # A rejected long composer rewrite must never fall back to the
                # French pivot. Re-run the existing Darija localization guard
                # over the grounded business answer; if it is unavailable,
                # return the controlled Darija message instead.
                if "wrong_language" in composer_validation_reasons:
                    localization = localize_business_answer(
                        business_answer,
                        business_language,
                        business_script,
                        get_response_localizer(),
                    )
                    if localization.status != "failed" and localization.answer:
                        answer = localization.answer
                        composer_status = "degraded_localized_answer"
                        fallback_provider = localization.provider
                        fallback_status = localization.status
                        final_response_provider = "darija_localizer_fallback"
                        language_degraded = True
                    else:
                        answer = safe_grounding_failure_message(
                            business_language, business_script
                        )
                        result["grounded"] = False
                        result["grounded_citations"] = []
                        result["knowledge_source"] = None
                        result["web_grounded"] = False
                        result["web_sources"] = []
                        grounded_status = "localization_error"
                        final_response_provider = "controlled"
                else:
                    # Preserve the historical grounded-answer fallback only
                    # when no language defect was detected.
                    if (
                        is_grounded_path
                        and result.get("grounded") is True
                        and bool(business_answer.strip())
                        and not blocked
                        and not error
                    ):
                        answer = business_answer
                        composer_status = "degraded_business_answer"
                        fallback_provider = "business_answer"
                        fallback_status = "degraded"
                        language_degraded = True
                        final_response_provider = "business_answer_fallback"
                    else:
                        fallback_status = "disabled"
                        composer_status = "failed_controlled"
                        answer = safe_grounding_failure_message(
                            business_language, business_script
                        )
                        result["grounded"] = False
                        result["grounded_citations"] = []
                        result["knowledge_source"] = None
                        result["web_grounded"] = False
                        result["web_sources"] = []
                        if is_grounded_path:
                            grounded_status = "localization_error"
                        final_response_provider = "controlled"
            else:
                answer = legacy_fallback_answer()
    else:
        fallback_used = True
        answer = legacy_fallback_answer()
    # Every presentation path, including the legacy Darija fallback, must keep
    # the concepts and supported dimensions of a grounded comparison.
    if (
        route == "pedagogie"
        and result.get("grounded") is True
        and not blocked
        and comparison_concepts(payload.message)
        and not rewrite_preserves_comparison(business_answer, answer)
    ):
        answer = limitation(business_language, business_script)
        result["grounded"] = False
        result["grounded_citations"] = []
        result["knowledge_source"] = None
        result["web_grounded"] = False
        result["web_sources"] = []
        grounded_status = "localization_error"
        finalization_failed_after_valid_turn = valid_business_turn
        composer_status = "failed_comparison_coverage"
        final_response_provider = "controlled"
        composer_validation_reasons.append("comparison_coverage_loss")
    composer_latency = elapsed_ms(composer_started)
    emit(
        "final_response.composed",
        final_response_provider=final_response_provider,
        language=business_language,
        script=business_script,
        route=route,
        composer_status=composer_status,
        retry_count=composer_retry_count,
        # Why an attempt was rejected; never the drafted answer itself.
        validation_reasons=composer_validation_reasons,
        fallback_used=fallback_used,
        fallback_provider=fallback_provider,
        fallback_reason=fallback_reason,
        fallback_status=fallback_status,
        language_degraded=language_degraded,
        latency_ms=composer_latency,
        stage="final_response",
    )
    result["localized_answer"] = answer
    status = (
        "blocked"
        if blocked
        else "error"
        if error
        or (
            is_grounded_path
            and grounded_status not in {"ok", "insufficient_evidence", "external_research"}
        )
        else "fallback"
        if route == "fallback"
        else "ok"
    )
    current_provenance = (
        _current_turn_knowledge_source(result, route) if not blocked and status == "ok" else None
    )
    response = ChatResponse(
        answer=answer,
        language=business_language,
        script=business_script,
        route=route,
        blocked=blocked,
        thread_id=payload.thread_id.strip(),
        status=status,
        grounded=result.get("grounded") if is_grounded_path else None,
        citations=result.get("grounded_citations", []) if is_grounded_path else [],
        internal_pedagogical_source=(
            result.get("internal_pedagogical_source")
            if route == "formation_elearning" and response_key == "formation_elearning"
            and not blocked and status == "ok"
            else None
        ),
        knowledge_source=current_provenance,
        web_sources=_current_turn_web_sources(result, current_provenance),
    )
    should_persist_history = response.status in {"ok", "blocked"} or (
        response.status == "error" and finalization_failed_after_valid_turn
    )
    if should_persist_history:
        history_store = get_conversation_history_store()
        if history_store is not None:
            history_started = start_timer()
            try:
                history_answer = (
                    business_answer
                    if finalization_failed_after_valid_turn
                    else response.answer
                )
                records = history_store.append_turn(
                    response.thread_id,
                    payload.message.strip(),
                    history_answer,
                    language=response.language,
                    script=response.script,
                    route=response.route,
                    knowledge_source=current_provenance,
                )
                emit(
                    "persistence.history.append.completed",
                    duration_ms=elapsed_ms(history_started),
                    thread_ref=thread_ref(response.thread_id),
                )
                memory_runtime = get_memory_runtime()
                if memory_runtime is not None:
                    args = (memory_runtime, response.thread_id, [r.id for r in (records or [])])
                    if post_response_tasks is not None:
                        post_response_tasks.add_task(_index_committed_messages, *args)
                    else:
                        _index_committed_messages(*args)

            except Exception as exc:
                emit(
                    "persistence.history.failed",
                    level=logging.ERROR,
                    duration_ms=elapsed_ms(history_started),
                    error_type=type(exc).__name__,
                    stage="history",
                    thread_ref=thread_ref(response.thread_id),
                )
                raise
            emit(
                "persistence.history.completed",
                duration_ms=elapsed_ms(history_started),
                thread_ref=thread_ref(response.thread_id),
            )
    return response, {
        "route": response.route,
        "response_status": response.status,
        "language": response.language,
        "script": response.script,
        "knowledge_source": current_provenance,
        "grounded": result.get("grounded"),
        "web_grounded": result.get("web_grounded"),
        "final_response_provider": final_response_provider,
        "composer_status": composer_status,
        "composer_retry_count": composer_retry_count,
        "composer_latency_ms": composer_latency,
        "fallback_used": fallback_used,
        "fallback_provider": fallback_provider,
        "fallback_reason": fallback_reason,
        "fallback_status": fallback_status,
        "language_degraded": language_degraded,
        "business_pipeline_latency_ms": graph_duration,
        "thread_ref": thread_ref(response.thread_id),
    }


def process_text_message(
    payload: ChatRequest,
    graph: Annotated[Any, Depends(get_chat_graph)],
    *,
    apply_final_response_composer: bool = False,
    post_response_tasks: BackgroundTasks | None = None,
) -> ChatResponse:
    with ensure_turn_context("text"):
        started = start_timer()
        try:
            response, metadata = _process_text_message(
                payload,
                graph,
                apply_final_response_composer=apply_final_response_composer,
                post_response_tasks=post_response_tasks,
            )
        except Exception as exc:
            emit(
                "request.failed",
                level=logging.ERROR,
                duration_ms=elapsed_ms(started),
                error_type=type(exc).__name__,
                stage="business",
                thread_ref=thread_ref(payload.thread_id.strip()),
            )
            raise
        total_latency = elapsed_ms(started)
        emit(
            "request.completed",
            **metadata,
            total_chat_latency_ms=total_latency,
            duration_ms=total_latency,
        )
        return response


def chat(
    payload: ChatRequest,
    graph: Annotated[Any, Depends(get_chat_graph)],
) -> ChatResponse:
    return process_text_message(payload, graph, apply_final_response_composer=True)


router.add_api_route(
    "/chat",
    chat,
    methods=["POST"],
    response_model=ChatResponse,
    summary="Send a text message to the EduBourse assistant",
    description=(
        "Send a text message to the multilingual educational assistant. "
        "The language is detected automatically, the response uses the same language "
        "and script, and LangGraph selects the appropriate educational workflow. "
        "The service provides financial education and does not give personalized "
        "investment recommendations."
    ),
    operation_id="chat",
    responses={500: {"model": APIError, "description": "Controlled internal API error."}},
)

legacy_router = APIRouter(tags=["Assistant"])
legacy_router.add_api_route(
    "/chat",
    chat,
    methods=["POST"],
    response_model=ChatResponse,
    summary="Send a text message to the EduBourse assistant (legacy)",
    description="Compatibility alias for POST /api/v1/chat.",
    operation_id="chat_legacy",
    deprecated=True,
    responses={500: {"model": APIError, "description": "Controlled internal API error."}},
)
