"""Minimal local MCP interface for approved EduBourse capabilities."""

from __future__ import annotations

import hmac
import json
import os
import urllib.error
import urllib.request
from typing import Any

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

BACKEND_HEALTH_PATH = "/api/v1/health/live"
BACKEND_CHAT_PATH = "/api/v1/chat"
DEFAULT_BACKEND_URL = "http://backend:8000"
_HEALTH_KEYS = ("status", "app", "version")
_CHAT_KEYS = (
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
MCP_ALLOWED_HOSTS = ["127.0.0.1:8011", "localhost:8011"]
MCP_ALLOWED_ORIGINS = ["http://127.0.0.1:6274", "http://localhost:6274"]
BACKEND_HEALTH_TIMEOUT_SECONDS = 5
DEFAULT_BACKEND_TIMEOUT_SECONDS = 300
MAX_BACKEND_TIMEOUT_SECONDS = 300
MAX_THREAD_ID_LENGTH = 200


class StaticTokenVerifier:
    """Verify one local service token through the SDK bearer-auth contract."""

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = os.getenv("EDUBOURSE_MCP_AUTH_TOKEN", "")
        if not expected or not token or not expected.isascii() or not token.isascii():
            return None
        if not hmac.compare_digest(token, expected):
            return None
        return AccessToken(token=token, client_id="local-mcp", scopes=[])


def _auth_settings() -> AuthSettings:
    return AuthSettings(
        issuer_url="http://127.0.0.1:8011",
        resource_server_url="http://127.0.0.1:8011",
        validate_token_resource=False,
    )

mcp = FastMCP(
    "EduBourse MCP",
    instructions="Authenticated health, capabilities, and EduBourse conversation access.",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
    stateless_http=True,
    json_response=True,
    auth=_auth_settings(),
    token_verifier=StaticTokenVerifier(),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=MCP_ALLOWED_HOSTS,
        allowed_origins=MCP_ALLOWED_ORIGINS,
    ),
)


def _health_payload() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "Financial Education Assistant",
        "version": "0.1.0",
    }


def _backend_health_url() -> str:
    return os.getenv("EDUBOURSE_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/") + BACKEND_HEALTH_PATH


def _backend_url(path: str) -> str:
    return os.getenv("EDUBOURSE_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/") + path


def _backend_timeout_seconds() -> int:
    configured = os.getenv("EDUBOURSE_MCP_BACKEND_TIMEOUT_SECONDS", "")
    try:
        timeout = int(configured)
    except ValueError:
        return DEFAULT_BACKEND_TIMEOUT_SECONDS
    return min(max(timeout, 1), MAX_BACKEND_TIMEOUT_SECONDS)


def _request_backend_health() -> dict[str, str]:
    request = urllib.request.Request(_backend_health_url(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=BACKEND_HEALTH_TIMEOUT_SECONDS) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return {"status": "unavailable", "error": "backend_unavailable"}
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return {"status": "unavailable", "error": "backend_unavailable"}
    return {key: str(payload[key]) for key in _HEALTH_KEYS if key in payload}


def _request_backend_chat(message: str, thread_id: str) -> dict[str, Any]:
    if (
        not isinstance(message, str)
        or not 1 <= len(message.strip()) <= 4000
        or not isinstance(thread_id, str)
        or not 1 <= len(thread_id.strip()) <= MAX_THREAD_ID_LENGTH
        or "\x00" in thread_id
        or "\r" in thread_id
        or "\n" in thread_id
    ):
        return {"status": "error", "error": "invalid_request"}
    payload = json.dumps({"message": message, "thread_id": thread_id}).encode("utf-8")
    request = urllib.request.Request(
        _backend_url(BACKEND_CHAT_PATH),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_backend_timeout_seconds()) as response:
            body: Any = json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        return {"status": "error", "error": "backend_timeout"}
    except (OSError, ValueError, urllib.error.URLError):
        return {"status": "error", "error": "backend_unavailable"}
    if not isinstance(body, dict):
        return {"status": "error", "error": "invalid_backend_response"}
    result = {key: body[key] for key in _CHAT_KEYS if key in body}
    if "answer" not in result or "status" not in result:
        return {"status": "error", "error": "invalid_backend_response"}
    if isinstance(result.get("citations"), list):
        result["citations"] = result["citations"][:10]
    return result


@mcp.resource("edubourse://health")
def health_resource() -> str:
    """Return live bounded backend health without exposing internal details."""
    return json.dumps(_request_backend_health(), ensure_ascii=False, sort_keys=True)


@mcp.resource("edubourse://capabilities")
def capabilities_resource() -> str:
    """Describe the authenticated, deliberately small MCP capability surface."""
    return json.dumps(
        {
            "resources": ["edubourse://health", "edubourse://capabilities"],
            "tools": ["get_backend_health", "ask_edubourse"],
            "business_tools_enabled": True,
            "authenticated": True,
            "direct_rag_access": False,
            "direct_database_access": False,
            "direct_postgres_access": False,
            "direct_chroma_access": False,
            "direct_n8n_access": False,
            "direct_filesystem_access": False,
            "arbitrary_url_access": False,
            "conversation_memory_in_mcp": False,
            "backend_delegation_only": True,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


@mcp.tool()
def get_backend_health() -> dict[str, str]:
    """Read the canonical backend liveness endpoint without exposing internals."""
    return _request_backend_health()


@mcp.tool()
def ask_edubourse(message: str, thread_id: str) -> dict[str, Any]:
    """Delegate one text turn to the canonical backend conversation pipeline."""
    return _request_backend_chat(message, thread_id)


if __name__ == "__main__":
    if not os.getenv("EDUBOURSE_MCP_AUTH_TOKEN"):
        raise RuntimeError("EDUBOURSE_MCP_AUTH_TOKEN must be configured")
    mcp.run(transport="streamable-http")
