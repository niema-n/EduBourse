import json
import logging
from types import SimpleNamespace

import pytest

import app.api.chat as chat_api
from app.llm.base import ProviderUnavailable


def _settings():
    return SimpleNamespace(
        persistence_enabled=False,
        financial_expert_fallback_enabled=False,
        groq_model="",
    )


@pytest.fixture
def isolated_chat_graph(monkeypatch):
    chat_api.get_chat_graph.cache_clear()
    monkeypatch.setattr(chat_api, "get_settings", _settings)
    monkeypatch.setattr(chat_api, "_create_grounded_service", lambda: None)
    monkeypatch.setattr(chat_api, "get_memory_runtime", lambda: None)
    yield
    chat_api.get_chat_graph.cache_clear()


def test_provider_init_failure_is_logged_and_unavailable_provider_is_kept(
    monkeypatch, caplog, isolated_chat_graph
):
    del isolated_chat_graph

    class ProviderInitError(ProviderUnavailable):
        status_code = 401
        code = "invalid_api_key"

    def fail_create_provider(model=None):
        del model
        raise ProviderInitError("api_key=secret-value")

    monkeypatch.setattr(chat_api, "create_provider", fail_create_provider)
    monkeypatch.setattr(
        chat_api,
        "build_graph",
        lambda **kwargs: kwargs["supervisor_provider"],
    )
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_MODEL", "qwen/test-model")
    caplog.set_level(logging.WARNING, logger="app.observability")

    provider = chat_api.get_chat_graph()

    assert isinstance(provider, chat_api.UnavailableProvider)
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.message.startswith("{")
    ]
    event = next(item for item in events if item["event"] == "supervisor.provider_init_failed")
    assert event["exception_type"] == "ProviderInitError"
    assert event["http_status"] == 401
    assert event["provider_error_code"] == "invalid_api_key"
    assert event["error_message_sanitized"] == "api_key=[redacted]"
    assert event["provider"] == "groq"
    assert event["model"] == "qwen/test-model"
    assert event["stage"] == "provider_initialization"


def test_provider_init_success_has_no_failure_event(monkeypatch, caplog, isolated_chat_graph):
    del isolated_chat_graph
    provider = object()
    monkeypatch.setattr(chat_api, "create_provider", lambda model=None: provider)
    monkeypatch.setattr(
        chat_api,
        "build_graph",
        lambda **kwargs: kwargs["supervisor_provider"],
    )
    caplog.set_level(logging.WARNING, logger="app.observability")

    assert chat_api.get_chat_graph() is provider
    assert not any(
        record.message.startswith("{")
        and json.loads(record.message).get("event") == "supervisor.provider_init_failed"
        for record in caplog.records
    )
