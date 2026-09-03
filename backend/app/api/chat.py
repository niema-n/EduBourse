import logging
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.graph.core import build_graph, security_guard_node
from app.graph.language_adapter import normalize_business_language
from app.graph.localization import localize_answer, validate_localized_script
from app.graph.state import create_turn_input, safe_thread_id
from app.llm.base import ProviderUnavailable
from app.llm.factory import create_provider
from app.multilingual.service import MultilingualService
from app.schemas.chat import APIError, ChatRequest, ChatResponse

router = APIRouter(tags=["Assistant"])
multilingual = MultilingualService()
logger = logging.getLogger(__name__)


class UnavailableProvider:
    def invoke_structured(self, request: object) -> object:
        raise ProviderUnavailable("supervisor provider unavailable")


@lru_cache(maxsize=1)
def get_chat_graph() -> Any:
    try:
        provider = create_provider()
    except ProviderUnavailable:
        provider = UnavailableProvider()
    return build_graph(supervisor_provider=provider)


def chat(
    payload: ChatRequest,
    graph: Annotated[Any, Depends(get_chat_graph)],
) -> ChatResponse:
    analysis = multilingual.analyze(payload.message.strip())
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
    security_before_graph = security_guard_node(state)
    try:
        result = graph.invoke(
            state,
            config={"configurable": {"thread_id": safe_thread_id(payload.thread_id.strip())}},
        )
    except Exception:
        logger.exception("chat graph invocation failed", extra={"thread_id": payload.thread_id})
        security_failed_closed = security_before_graph.get("security_status") == "sensitive"
        result = {
            **state,
            "selected_route": "securite" if security_failed_closed else "fallback",
            "status": "error",
            "error": "graph_failure",
            "security_status": security_before_graph.get("security_status", "sensitive"),
            "risk_level": security_before_graph.get("risk_level", "high"),
        }
    route = str(result.get("selected_route", "fallback"))
    blocked = route == "securite" or result.get("security_status") == "sensitive"
    error = bool(result.get("error")) and not blocked
    business_answer = str(result.get("business_answer", ""))
    result["raw_agent_answer"] = business_answer
    answer = localize_answer(
        business_answer,
        business_language,
        business_script,
        route=route,
        blocked=blocked,
        error=error,
    )
    if not validate_localized_script(answer, business_language, business_script):
        answer = localize_answer(
            "", business_language, business_script, route="fallback", blocked=blocked, error=error
        )
        if not validate_localized_script(answer, business_language, business_script):
            answer = {
                "latin": "A controlled response is unavailable.",
                "arabic": "الرد المتحكم فيه غير متاح.",
            }[business_script]
    result["localized_answer"] = answer
    status = (
        "blocked" if blocked else "error" if error else "fallback" if route == "fallback" else "ok"
    )
    return ChatResponse(
        answer=answer,
        language=business_language,
        script=business_script,
        route=route,
        blocked=blocked,
        thread_id=payload.thread_id.strip(),
        status=status,
    )


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
