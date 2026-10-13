"""Tightly scoped integration bridge for the MCP & n8n page.

The browser must never hold the MCP bearer token, and the MCP server only
accepts local hosts and the MCP Inspector origin. This bridge therefore runs a
FIXED set of predefined calls server-side:

- status: MCP reachability (unauthenticated probe expecting 401), n8n /healthz,
  and whether the project's n8n webhooks are registered;
- MCP get_backend_health and MCP ask_edubourse (the only two tools);
- the n8n "EduBourse - MCP Ask" webhook.

It accepts no URL, no tool name and no header from the client, returns only
bounded public fields, and never echoes secrets or exception details. Business
logic stays in /api/v1/chat, reached through MCP exactly as n8n does.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(prefix="/integrations", tags=["Integrations"])

DEFAULT_MCP_URL = "http://mcp:8000/mcp"
DEFAULT_N8N_URL = "http://n8n:5678"
# MCP DNS-rebinding protection only allows these hosts (mcp/server.py).
MCP_HOST_HEADER = "localhost:8011"
MCP_PUBLIC_ENDPOINT = "127.0.0.1:8011/mcp"
N8N_PUBLIC_URL = "http://localhost:5678"
MCP_PROTOCOL_VERSION = "2025-06-18"

PROBE_TIMEOUT_SECONDS = 5.0
HEALTH_TIMEOUT_SECONDS = 15.0
# Below MCP's own 300 s business timeout and n8n's 330 s: the UI gets an answer.
ASK_TIMEOUT_SECONDS = 240.0

MCP_TOOLS = ("get_backend_health", "ask_edubourse")
MCP_RESOURCES = ("edubourse://health", "edubourse://capabilities")
CHAT_FIELDS = (
    "answer",
    "language",
    "script",
    "route",
    "blocked",
    "thread_id",
    "status",
    "grounded",
    "citations",
)
CITATION_FIELDS = (
    "evidence_id",
    "chunk_id",
    "source_id",
    "title",
    "page",
    "page_start",
    "page_end",
    "heading",
)
HEALTH_FIELDS = ("status", "app", "version")
MAX_CITATIONS = 10
THREAD_PREFIX = "integration-"

ErrorCode = Literal[
    "mcp_not_configured",
    "mcp_unavailable",
    "mcp_rejected",
    "n8n_unavailable",
    "workflow_not_registered",
    "integration_timeout",
    "invalid_request",
    "invalid_response",
    "backend_unavailable",
    "backend_timeout",
]
# Error strings MCP/n8n may return in their own bounded payloads.
PASSTHROUGH_ERRORS = {
    "backend_unavailable",
    "backend_timeout",
    "invalid_request",
    "invalid_backend_response",
    "mcp_unavailable",
}


class BridgeError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: Any


class IntegrationTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResult: ...


class UrllibTransport:
    """Plain HTTP client. Raises TimeoutError or OSError; never logs headers."""

    def request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResult:
        data = (
            json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        )
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
        except urllib.error.URLError as exc:
            # A connect timeout arrives wrapped in URLError: keep it distinguishable.
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError("integration request timed out") from exc
            raise
        try:
            body: Any = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            body = None
        return HttpResult(status=status, body=body)


@dataclass(frozen=True)
class BridgeConfig:
    mcp_url: str
    mcp_token: str
    n8n_url: str


def get_transport() -> IntegrationTransport:
    return UrllibTransport()


def get_bridge_config() -> BridgeConfig:
    return BridgeConfig(
        mcp_url=os.getenv("EDUBOURSE_MCP_URL", DEFAULT_MCP_URL).strip() or DEFAULT_MCP_URL,
        mcp_token=os.getenv("EDUBOURSE_MCP_AUTH_TOKEN", "").strip(),
        n8n_url=(os.getenv("EDUBOURSE_N8N_URL", DEFAULT_N8N_URL).strip() or DEFAULT_N8N_URL).rstrip(
            "/"
        ),
    )


Transport = Annotated[IntegrationTransport, Depends(get_transport)]
Config = Annotated[BridgeConfig, Depends(get_bridge_config)]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class IntegrationAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str = Field(min_length=1, max_length=1000)
    # Optional so the page can test backend-owned continuity on the same thread.
    thread_id: str | None = Field(
        default=None,
        pattern=r"^integration-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )

    @field_validator("message")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class WorkflowStatus(BaseModel):
    key: str
    name: str
    trigger: Literal["webhook", "manual"]
    webhook_path: str | None
    registered: bool | None = Field(
        description="Webhook answered in n8n; None when not probeable (manual trigger)."
    )


class McpStatus(BaseModel):
    endpoint: str = MCP_PUBLIC_ENDPOINT
    reachable: bool
    auth_enforced: bool
    bridge_configured: bool
    tools: list[str] = list(MCP_TOOLS)
    resources: list[str] = list(MCP_RESOURCES)


class N8nStatus(BaseModel):
    url: str = N8N_PUBLIC_URL
    reachable: bool


class IntegrationStatusResponse(BaseModel):
    backend: Literal["available"] = "available"
    mcp: McpStatus
    n8n: N8nStatus
    workflows: list[WorkflowStatus]


class ChatResult(BaseModel):
    answer: str
    language: str | None = None
    script: str | None = None
    route: str | None = None
    blocked: bool | None = None
    thread_id: str | None = None
    status: str
    grounded: bool | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)


class IntegrationAskResponse(BaseModel):
    integration: Literal["mcp_ask", "n8n_mcp_ask"]
    status: Literal["ok", "error"]
    error: str | None = None
    thread_id: str
    result: ChatResult | None = None
    duration_ms: int


class McpHealthResponse(BaseModel):
    integration: Literal["mcp_health"] = "mcp_health"
    status: Literal["ok", "error"]
    error: str | None = None
    backend_health: dict[str, str] | None = None
    duration_ms: int


# ---------------------------------------------------------------------------
# MCP (fixed calls only)
# ---------------------------------------------------------------------------


def _mcp_headers(config: BridgeConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.mcp_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": MCP_HOST_HEADER,
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    }


def _call_mcp_tool(
    transport: IntegrationTransport,
    config: BridgeConfig,
    tool: Literal["get_backend_health", "ask_edubourse"],
    arguments: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    if not config.mcp_token:
        raise BridgeError("mcp_not_configured")
    headers = _mcp_headers(config)
    try:
        init = transport.request(
            "POST",
            config.mcp_url,
            payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "edubourse-integrations-page", "version": "1.0"},
                },
            },
            headers=headers,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        if init.status in {401, 403}:
            raise BridgeError("mcp_rejected")
        if init.status != 200:
            raise BridgeError("mcp_unavailable")
        call = transport.request(
            "POST",
            config.mcp_url,
            payload={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
            headers=headers,
            timeout=timeout,
        )
    except TimeoutError as exc:
        raise BridgeError("integration_timeout") from exc
    except OSError as exc:
        raise BridgeError("mcp_unavailable") from exc
    if call.status in {401, 403}:
        raise BridgeError("mcp_rejected")
    if call.status != 200 or not isinstance(call.body, dict):
        raise BridgeError("mcp_unavailable")
    rpc_result = call.body.get("result")
    if call.body.get("error") or not isinstance(rpc_result, dict) or rpc_result.get("isError"):
        raise BridgeError("invalid_response")
    payload = rpc_result.get("structuredContent")
    if (
        isinstance(payload, dict)
        and set(payload) == {"result"}
        and isinstance(payload["result"], dict)
    ):
        payload = payload["result"]
    if not isinstance(payload, dict):
        text = next(
            (
                item.get("text")
                for item in rpc_result.get("content") or []
                if isinstance(item, dict) and item.get("type") == "text"
            ),
            None,
        )
        try:
            payload = json.loads(text) if isinstance(text, str) else None
        except ValueError:
            payload = None
    if not isinstance(payload, dict):
        raise BridgeError("invalid_response")
    return payload


def _bounded_chat(payload: dict[str, Any]) -> ChatResult:
    if payload.get("status") == "error" and "answer" not in payload:
        code = payload.get("error")
        raise BridgeError(
            code
            if code in PASSTHROUGH_ERRORS and code != "invalid_backend_response"
            else "invalid_response"
        )  # type: ignore[arg-type]
    fields = {key: payload[key] for key in CHAT_FIELDS if key in payload}
    if not isinstance(fields.get("answer"), str) or not isinstance(fields.get("status"), str):
        raise BridgeError("invalid_response")
    citations = fields.get("citations")
    fields["citations"] = [
        {key: item[key] for key in CITATION_FIELDS if key in item}
        for item in (citations if isinstance(citations, list) else [])[:MAX_CITATIONS]
        if isinstance(item, dict)
    ]
    try:
        return ChatResult.model_validate(fields)
    except ValueError as exc:
        raise BridgeError("invalid_response") from exc


def _elapsed(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _thread(request: IntegrationAskRequest) -> str:
    return request.thread_id or f"{THREAD_PREFIX}{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

WORKFLOWS = (
    (
        "health",
        "EduBourse - Health Webhook",
        "webhook",
        "edubourse-health",
        {"source": "edubourse", "action": "health"},
    ),
    (
        "backend_health",
        "EduBourse - Backend Health Bridge",
        "webhook",
        "edubourse-backend-health",
        {},
    ),
    # An empty body stops at the workflow's own validation: no MCP or backend call.
    ("mcp_ask", "EduBourse - MCP Ask", "webhook", "edubourse-mcp-ask", {}),
    ("rag_update", "EduBourse - RAG Update", "manual", None, None),
)


@router.get(
    "/status",
    response_model=IntegrationStatusResponse,
    summary="Read-only reachability of MCP, n8n and the project's n8n workflows",
    operation_id="integrations_status",
)
def integrations_status(transport: Transport, config: Config) -> IntegrationStatusResponse:
    mcp_reachable = False
    mcp_auth_enforced = False
    try:
        probe = transport.request(
            "POST",
            config.mcp_url,
            payload={"jsonrpc": "2.0", "id": 0, "method": "ping"},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Host": MCP_HOST_HEADER,
            },
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        mcp_reachable = True
        mcp_auth_enforced = probe.status == 401
    except OSError:
        pass

    n8n_reachable = False
    try:
        health = transport.request(
            "GET",
            f"{config.n8n_url}/healthz",
            payload=None,
            headers={},
            timeout=PROBE_TIMEOUT_SECONDS,
        )
        n8n_reachable = (
            health.status == 200
            and isinstance(health.body, dict)
            and health.body.get("status") == "ok"
        )
    except OSError:
        pass

    workflows: list[WorkflowStatus] = []
    for key, name, trigger, path, probe_body in WORKFLOWS:
        registered: bool | None = None
        if trigger == "webhook" and n8n_reachable and path is not None:
            try:
                answer = transport.request(
                    "POST",
                    f"{config.n8n_url}/webhook/{path}",
                    payload=probe_body,
                    headers={"Content-Type": "application/json"},
                    timeout=PROBE_TIMEOUT_SECONDS,
                )
                registered = answer.status != 404
            except OSError:
                registered = False
        elif trigger == "webhook":
            registered = False
        workflows.append(
            WorkflowStatus(
                key=key, name=name, trigger=trigger, webhook_path=path, registered=registered
            )
        )

    return IntegrationStatusResponse(
        mcp=McpStatus(
            reachable=mcp_reachable,
            auth_enforced=mcp_auth_enforced,
            bridge_configured=bool(config.mcp_token),
        ),
        n8n=N8nStatus(reachable=n8n_reachable),
        workflows=workflows,
    )


@router.post(
    "/mcp/health-test",
    response_model=McpHealthResponse,
    summary="Call the MCP tool get_backend_health server-side",
    operation_id="integrations_mcp_health_test",
)
def mcp_health_test(transport: Transport, config: Config) -> McpHealthResponse:
    started = time.perf_counter()
    try:
        payload = _call_mcp_tool(
            transport, config, "get_backend_health", {}, HEALTH_TIMEOUT_SECONDS
        )
    except BridgeError as exc:
        return McpHealthResponse(status="error", error=exc.code, duration_ms=_elapsed(started))
    health = {key: str(payload[key]) for key in HEALTH_FIELDS if key in payload}
    ok = health.get("status") == "ok"
    return McpHealthResponse(
        status="ok" if ok else "error",
        error=None if ok else "backend_unavailable",
        backend_health=health or None,
        duration_ms=_elapsed(started),
    )


@router.post(
    "/mcp/ask-test",
    response_model=IntegrationAskResponse,
    summary="Call the MCP tool ask_edubourse server-side",
    operation_id="integrations_mcp_ask_test",
)
def mcp_ask_test(
    request: IntegrationAskRequest, transport: Transport, config: Config
) -> IntegrationAskResponse:
    started = time.perf_counter()
    thread_id = _thread(request)
    try:
        payload = _call_mcp_tool(
            transport,
            config,
            "ask_edubourse",
            {"message": request.message, "thread_id": thread_id},
            ASK_TIMEOUT_SECONDS,
        )
        result = _bounded_chat(payload)
    except BridgeError as exc:
        return IntegrationAskResponse(
            integration="mcp_ask",
            status="error",
            error=exc.code,
            thread_id=thread_id,
            duration_ms=_elapsed(started),
        )
    return IntegrationAskResponse(
        integration="mcp_ask",
        status="ok",
        thread_id=thread_id,
        result=result,
        duration_ms=_elapsed(started),
    )


@router.post(
    "/n8n/mcp-ask-test",
    response_model=IntegrationAskResponse,
    summary="Call the n8n 'EduBourse - MCP Ask' webhook server-side",
    operation_id="integrations_n8n_mcp_ask_test",
)
def n8n_mcp_ask_test(
    request: IntegrationAskRequest, transport: Transport, config: Config
) -> IntegrationAskResponse:
    started = time.perf_counter()
    thread_id = _thread(request)
    try:
        try:
            answer = transport.request(
                "POST",
                f"{config.n8n_url}/webhook/edubourse-mcp-ask",
                payload={"message": request.message, "thread_id": thread_id},
                headers={"Content-Type": "application/json"},
                timeout=ASK_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise BridgeError("integration_timeout") from exc
        except OSError as exc:
            raise BridgeError("n8n_unavailable") from exc
        if answer.status == 404:
            raise BridgeError("workflow_not_registered")
        if not isinstance(answer.body, dict):
            raise BridgeError("n8n_unavailable" if answer.status >= 500 else "invalid_response")
        result = _bounded_chat(answer.body)
    except BridgeError as exc:
        return IntegrationAskResponse(
            integration="n8n_mcp_ask",
            status="error",
            error=exc.code,
            thread_id=thread_id,
            duration_ms=_elapsed(started),
        )
    return IntegrationAskResponse(
        integration="n8n_mcp_ask",
        status="ok",
        thread_id=thread_id,
        result=result,
        duration_ms=_elapsed(started),
    )
