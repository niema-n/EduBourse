"""Integration bridge for the MCP & n8n page: fixed calls, no secrets, no proxy.

A fake transport replaces the network: no MCP, n8n, Groq or BGE-M3 is used.
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from app.api.integrations import BridgeConfig, HttpResult, get_bridge_config, get_transport
from app.main import app

TOKEN = "test-mcp-token-never-returned"
MCP_URL = "http://mcp:8000/mcp"
N8N_URL = "http://n8n:5678"
THREAD_RE = re.compile(
    r"^integration-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

CHAT_OK = {
    "answer": "Une action est un titre de propriété.",
    "language": "fr",
    "script": "latin",
    "route": "pedagogie",
    "blocked": False,
    "thread_id": "integration-00000000-0000-4000-8000-000000000000",
    "status": "ok",
    "grounded": True,
    "citations": [
        {
            "evidence_id": "S1",
            "chunk_id": "c1",
            "title": "Comprendre les instruments financiers",
            "page_start": 7,
            "page_end": 7,
            "secret_internal": "x",
        }
    ],
}
CHAT_BLOCKED = {
    "answer": "Je ne peux pas recommander un titre ou choisir un investissement pour vous.",
    "language": "fr",
    "script": "latin",
    "route": "securite",
    "blocked": True,
    "thread_id": "integration-00000000-0000-4000-8000-000000000000",
    "status": "blocked",
    "grounded": None,
    "citations": [],
}


class FakeTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls: list[dict] = []

    def request(self, method, url, *, payload, headers, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        return self.handler(method, url, payload, headers)


def mcp_rpc(structured):
    return HttpResult(
        200,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [{"type": "text", "text": json.dumps(structured)}],
                "structuredContent": structured,
                "isError": False,
            },
        },
    )


def healthy_mcp(tool_result):
    def handler(method, url, payload, headers):
        if url == MCP_URL:
            if headers.get("Authorization") != f"Bearer {TOKEN}":
                return HttpResult(401, None)
            if payload["method"] == "initialize":
                return HttpResult(
                    200, {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}}
                )
            return mcp_rpc(tool_result(payload["params"]))
        raise AssertionError(f"unexpected url {url}")

    return handler


def client_with(handler, token: str = TOKEN):
    transport = FakeTransport(handler)
    app.dependency_overrides[get_transport] = lambda: transport
    app.dependency_overrides[get_bridge_config] = lambda: BridgeConfig(
        mcp_url=MCP_URL, mcp_token=token, n8n_url=N8N_URL
    )
    return TestClient(app), transport


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def assert_no_secret(response):
    assert TOKEN not in response.text
    assert "Bearer" not in response.text


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_status_reports_real_probes_without_secrets():
    def handler(method, url, payload, headers):
        assert "Authorization" not in headers  # status probes never use the token
        if url == MCP_URL:
            return HttpResult(401, None)
        if url == f"{N8N_URL}/healthz":
            return HttpResult(200, {"status": "ok"})
        if url.endswith("/webhook/edubourse-health"):
            return HttpResult(200, {"status": "ok"})
        if url.endswith("/webhook/edubourse-backend-health"):
            return HttpResult(200, {"status": "ok"})
        if url.endswith("/webhook/edubourse-mcp-ask"):
            assert payload == {}  # validation-only probe: no MCP/backend call
            return HttpResult(400, None)
        raise AssertionError(url)

    client, transport = client_with(handler)
    response = client.get("/api/v1/integrations/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mcp"] == {
        "endpoint": "127.0.0.1:8011/mcp",
        "reachable": True,
        "auth_enforced": True,
        "bridge_configured": True,
        "tools": ["get_backend_health", "ask_edubourse"],
        "resources": ["edubourse://health", "edubourse://capabilities"],
    }
    assert body["n8n"] == {"url": "http://localhost:5678", "reachable": True}
    registered = {item["key"]: item["registered"] for item in body["workflows"]}
    assert registered == {
        "health": True,
        "backend_health": True,
        "mcp_ask": True,
        "rag_update": None,
    }
    assert_no_secret(response)
    assert {call["url"] for call in transport.calls} <= {
        MCP_URL,
        f"{N8N_URL}/healthz",
        f"{N8N_URL}/webhook/edubourse-health",
        f"{N8N_URL}/webhook/edubourse-backend-health",
        f"{N8N_URL}/webhook/edubourse-mcp-ask",
    }


def test_status_marks_unavailable_services_and_unregistered_webhooks():
    def handler(method, url, payload, headers):
        if url == MCP_URL:
            raise OSError("connection refused")
        if url == f"{N8N_URL}/healthz":
            return HttpResult(200, {"status": "ok"})
        return HttpResult(404, None)

    client, _ = client_with(handler, token="")
    body = client.get("/api/v1/integrations/status").json()
    assert body["mcp"]["reachable"] is False
    assert body["mcp"]["bridge_configured"] is False
    assert all(item["registered"] in (False, None) for item in body["workflows"])


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def test_mcp_health_calls_only_get_backend_health():
    client, transport = client_with(
        healthy_mcp(
            lambda params: {
                "status": "ok",
                "app": "Financial Education Assistant",
                "version": "0.1.0",
            }
        )
    )
    response = client.post("/api/v1/integrations/mcp/health-test")
    body = response.json()
    assert body["status"] == "ok"
    assert body["backend_health"] == {
        "status": "ok",
        "app": "Financial Education Assistant",
        "version": "0.1.0",
    }
    tool_calls = [
        call["payload"] for call in transport.calls if call["payload"]["method"] == "tools/call"
    ]
    assert tool_calls == [
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_backend_health", "arguments": {}},
        }
    ]
    assert all(call["headers"]["Host"] == "localhost:8011" for call in transport.calls)
    assert_no_secret(response)


def test_mcp_ask_forwards_message_and_generated_thread_and_bounds_fields():
    seen = {}

    def tool(params):
        seen.update(params)
        return CHAT_OK

    client, _ = client_with(healthy_mcp(tool))
    response = client.post(
        "/api/v1/integrations/mcp/ask-test", json={"message": "C'est quoi une action ?"}
    )
    body = response.json()
    assert body["status"] == "ok"
    assert body["integration"] == "mcp_ask"
    assert THREAD_RE.match(body["thread_id"])
    assert seen == {
        "name": "ask_edubourse",
        "arguments": {"message": "C'est quoi une action ?", "thread_id": body["thread_id"]},
    }
    assert body["result"]["route"] == "pedagogie"
    assert body["result"]["citations"] == [
        {
            "evidence_id": "S1",
            "chunk_id": "c1",
            "title": "Comprendre les instruments financiers",
            "page_start": 7,
            "page_end": 7,
        }
    ]
    assert_no_secret(response)


def test_mcp_ask_reuses_a_valid_thread_for_backend_owned_continuity():
    thread = "integration-12345678-1234-4234-8234-123456789abc"
    seen = []
    client, _ = client_with(
        healthy_mcp(lambda params: seen.append(params["arguments"]["thread_id"]) or CHAT_OK)
    )
    for message in ("C'est quoi une action ?", "Et quels sont ses avantages ?"):
        assert (
            client.post(
                "/api/v1/integrations/mcp/ask-test", json={"message": message, "thread_id": thread}
            ).json()["thread_id"]
            == thread
        )
    assert seen == [thread, thread]


def test_security_decision_passes_through_mcp_unchanged():
    client, _ = client_with(healthy_mcp(lambda params: CHAT_BLOCKED))
    body = client.post(
        "/api/v1/integrations/mcp/ask-test", json={"message": "Quelle action dois-je acheter ?"}
    ).json()
    assert body["status"] == "ok"
    assert body["result"]["route"] == "securite"
    assert body["result"]["blocked"] is True
    assert body["result"]["answer"] == CHAT_BLOCKED["answer"]


def test_mcp_not_configured_makes_no_network_call():
    client, transport = client_with(healthy_mcp(lambda params: CHAT_OK), token="")
    body = client.post(
        "/api/v1/integrations/mcp/ask-test", json={"message": "C'est quoi une action ?"}
    ).json()
    assert (body["status"], body["error"]) == ("error", "mcp_not_configured")
    assert transport.calls == []


@pytest.mark.parametrize(
    ("failure", "code"),
    [(OSError("refused"), "mcp_unavailable"), (TimeoutError("slow"), "integration_timeout")],
)
def test_mcp_failures_are_sanitized(failure, code):
    def handler(method, url, payload, headers):
        raise failure

    client, _ = client_with(handler)
    response = client.post(
        "/api/v1/integrations/mcp/ask-test", json={"message": "C'est quoi une action ?"}
    )
    body = response.json()
    assert (body["status"], body["error"]) == ("error", code)
    assert "refused" not in response.text and "slow" not in response.text


def test_mcp_rejected_token_is_reported_without_details():
    client, _ = client_with(lambda method, url, payload, headers: HttpResult(401, None))
    body = client.post("/api/v1/integrations/mcp/health-test").json()
    assert (body["status"], body["error"]) == ("error", "mcp_rejected")


def test_backend_error_returned_by_mcp_is_bounded():
    client, _ = client_with(
        healthy_mcp(lambda params: {"status": "error", "error": "backend_timeout"})
    )
    body = client.post(
        "/api/v1/integrations/mcp/ask-test", json={"message": "C'est quoi une action ?"}
    ).json()
    assert (body["status"], body["error"]) == ("error", "backend_timeout")


# ---------------------------------------------------------------------------
# n8n workflow
# ---------------------------------------------------------------------------


def test_n8n_ask_calls_only_the_mcp_ask_webhook():
    def handler(method, url, payload, headers):
        assert url == f"{N8N_URL}/webhook/edubourse-mcp-ask"
        assert "Authorization" not in headers
        return HttpResult(200, {**CHAT_OK, "thread_id": payload["thread_id"]})

    client, transport = client_with(handler)
    response = client.post(
        "/api/v1/integrations/n8n/mcp-ask-test", json={"message": "C'est quoi une action ?"}
    )
    body = response.json()
    assert body["status"] == "ok"
    assert body["integration"] == "n8n_mcp_ask"
    assert body["result"]["thread_id"] == body["thread_id"]
    assert len(transport.calls) == 1
    assert_no_secret(response)


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (OSError("refused"), "n8n_unavailable"),
        (TimeoutError("slow"), "integration_timeout"),
        (HttpResult(404, {"code": 404, "message": "not registered"}), "workflow_not_registered"),
        (HttpResult(400, {"status": "error", "error": "mcp_unavailable"}), "mcp_unavailable"),
    ],
)
def test_n8n_failures_are_sanitized(outcome, code):
    def handler(method, url, payload, headers):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client, _ = client_with(handler)
    response = client.post(
        "/api/v1/integrations/n8n/mcp-ask-test", json={"message": "C'est quoi une action ?"}
    )
    body = response.json()
    assert (body["status"], body["error"]) == ("error", code)
    assert "not registered" not in response.text


def test_security_decision_passes_through_n8n_unchanged():
    client, _ = client_with(lambda method, url, payload, headers: HttpResult(200, CHAT_BLOCKED))
    body = client.post(
        "/api/v1/integrations/n8n/mcp-ask-test", json={"message": "Quelle action dois-je acheter ?"}
    ).json()
    assert body["result"]["route"] == "securite" and body["result"]["blocked"] is True


# ---------------------------------------------------------------------------
# Input: no arbitrary tool, URL, header or thread
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "   "},
        {"message": "x" * 1001},
        {"message": "ok", "tool": "shell"},
        {"message": "ok", "url": "http://evil.example"},
        {"message": "ok", "headers": {"Authorization": "x"}},
        {"message": "ok", "thread_id": "user-niema"},
        {"message": "ok", "thread_id": "integration-../../etc"},
    ],
)
@pytest.mark.parametrize(
    "path", ["/api/v1/integrations/mcp/ask-test", "/api/v1/integrations/n8n/mcp-ask-test"]
)
def test_invalid_or_arbitrary_input_is_rejected_before_any_call(path, payload):
    client, transport = client_with(healthy_mcp(lambda params: CHAT_OK))
    assert client.post(path, json=payload).status_code == 422
    assert transport.calls == []


def test_no_generic_proxy_routes_exist():
    paths = {path for path in app.openapi()["paths"] if "integrations" in path}
    assert paths == {
        "/api/v1/integrations/status",
        "/api/v1/integrations/mcp/health-test",
        "/api/v1/integrations/mcp/ask-test",
        "/api/v1/integrations/n8n/mcp-ask-test",
    }
