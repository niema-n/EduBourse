import asyncio
import json

from mcp.server.auth.provider import AccessToken

from server import (
    MCP_ALLOWED_HOSTS,
    MCP_ALLOWED_ORIGINS,
    StaticTokenVerifier,
    ask_edubourse,
    capabilities_resource,
    get_backend_health,
    health_resource,
    mcp,
)


def test_protocol_surface_has_exactly_two_tools_and_two_resources() -> None:
    assert sorted(tool.name for tool in mcp._tool_manager.list_tools()) == [
        "ask_edubourse",
        "get_backend_health",
    ]
    assert sorted(str(resource.uri) for resource in mcp._resource_manager.list_resources()) == [
        "edubourse://capabilities",
        "edubourse://health",
    ]


def test_health_resource_uses_live_backend_health(monkeypatch) -> None:
    monkeypatch.setattr(
        "server._request_backend_health",
        lambda: {"status": "ok", "app": "Financial Education Assistant", "version": "0.1.0"},
    )
    assert json.loads(health_resource()) == {
        "app": "Financial Education Assistant",
        "status": "ok",
        "version": "0.1.0",
    }


def test_capabilities_resource_exposes_only_safe_surface() -> None:
    payload = json.loads(capabilities_resource())
    assert payload["tools"] == ["get_backend_health", "ask_edubourse"]
    assert payload["business_tools_enabled"] is True
    assert payload["authenticated"] is True
    assert payload["direct_rag_access"] is False
    assert payload["direct_database_access"] is False
    assert payload["direct_postgres_access"] is False
    assert payload["direct_chroma_access"] is False
    assert payload["direct_n8n_access"] is False
    assert payload["direct_filesystem_access"] is False
    assert payload["arbitrary_url_access"] is False
    assert payload["conversation_memory_in_mcp"] is False
    assert payload["backend_delegation_only"] is True


def test_transport_allowlist_is_local_and_non_wildcard() -> None:
    assert MCP_ALLOWED_HOSTS == ["127.0.0.1:8011", "localhost:8011"]
    assert MCP_ALLOWED_ORIGINS == ["http://127.0.0.1:6274", "http://localhost:6274"]
    assert "*" not in MCP_ALLOWED_HOSTS + MCP_ALLOWED_ORIGINS


def test_auth_token_verifier_rejects_missing_wrong_and_malformed(monkeypatch) -> None:
    verifier = StaticTokenVerifier()
    monkeypatch.delenv("EDUBOURSE_MCP_AUTH_TOKEN", raising=False)
    assert asyncio.run(verifier.verify_token("local-secret")) is None
    monkeypatch.setenv("EDUBOURSE_MCP_AUTH_TOKEN", "local-secret")
    assert asyncio.run(verifier.verify_token("")) is None
    assert asyncio.run(verifier.verify_token("wrong")) is None
    assert asyncio.run(verifier.verify_token("é")) is None


def test_auth_token_verifier_accepts_valid_token(monkeypatch) -> None:
    monkeypatch.setenv("EDUBOURSE_MCP_AUTH_TOKEN", "local-secret")
    token = asyncio.run(StaticTokenVerifier().verify_token("local-secret"))
    assert isinstance(token, AccessToken)
    assert token.client_id == "local-mcp"
    assert token.token == "local-secret"


def test_backend_health_is_bounded(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return (
                b'{"status":"ok","app":"Financial Education Assistant",'
                b'"version":"0.1.0","secret":"no"}'
            )

    monkeypatch.setattr("server.urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    assert get_backend_health() == {
        "status": "ok",
        "app": "Financial Education Assistant",
        "version": "0.1.0",
    }


def test_backend_unavailable_is_controlled(monkeypatch) -> None:
    monkeypatch.setattr(
        "server.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("private detail")),
    )
    assert get_backend_health() == {"status": "unavailable", "error": "backend_unavailable"}


def test_ask_edubourse_delegates_minimal_chat_contract(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return (
                b'{"answer":"Une action est une part d\\u0027une societe.",'
                b'"language":"fr","status":"ok"}'
            )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("server.urllib.request.urlopen", fake_urlopen)
    assert ask_edubourse("C'est quoi une action ?", "thread-1") == {
        "answer": "Une action est une part d'une societe.",
        "language": "fr",
        "status": "ok",
    }
    assert captured == {
        "url": "http://backend:8000/api/v1/chat",
        "payload": {"message": "C'est quoi une action ?", "thread_id": "thread-1"},
        "timeout": 300,
    }


def test_ask_edubourse_uses_configured_bounded_timeout(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"answer":"ok","status":"ok"}'

    def fake_urlopen(_request, timeout):
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("EDUBOURSE_MCP_BACKEND_TIMEOUT_SECONDS", "42")
    monkeypatch.setattr("server.urllib.request.urlopen", fake_urlopen)
    assert ask_edubourse("question", "thread")["status"] == "ok"
    assert captured["timeout"] == 42


def test_ask_edubourse_timeout_is_controlled(monkeypatch) -> None:
    monkeypatch.setenv("EDUBOURSE_MCP_BACKEND_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr(
        "server.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("private detail")),
    )
    assert ask_edubourse("question", "thread") == {
        "status": "error",
        "error": "backend_timeout",
    }


def test_ask_edubourse_bounds_input_and_controls_backend_failure(monkeypatch) -> None:
    assert ask_edubourse(" ", "thread") == {"status": "error", "error": "invalid_request"}
    assert ask_edubourse("question", " ") == {"status": "error", "error": "invalid_request"}
    monkeypatch.setattr(
        "server.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("private detail")),
    )
    assert ask_edubourse("question", "thread") == {
        "status": "error",
        "error": "backend_unavailable",
    }


def test_ask_edubourse_rejects_malformed_thread_ids() -> None:
    assert ask_edubourse("question", "thread\nheader") == {
        "status": "error",
        "error": "invalid_request",
    }
    assert ask_edubourse("question", "thread\x00id") == {
        "status": "error",
        "error": "invalid_request",
    }
    assert ask_edubourse("question", "x" * 201) == {
        "status": "error",
        "error": "invalid_request",
    }


def test_thread_continuity_is_caller_stable_without_mcp_memory(monkeypatch) -> None:
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"answer":"ok","status":"ok"}'

    def fake_urlopen(request, timeout):
        captured.append(json.loads(request.data)["thread_id"])
        return Response()

    monkeypatch.setattr("server.urllib.request.urlopen", fake_urlopen)
    ask_edubourse("question", "logical-thread")
    ask_edubourse("question", "logical-thread")
    ask_edubourse("question", "other-thread")
    assert captured == ["logical-thread", "logical-thread", "other-thread"]
