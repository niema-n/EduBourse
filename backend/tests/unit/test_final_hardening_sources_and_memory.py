"""Approved-source enforcement for web grounding and the relevant-memory switch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from app.api import chat as chat_api
from app.database.base import Base
from app.financial_expert.models import FinancialExpertRequest
from app.financial_expert.provider import FinancialExpertGeneration
from app.financial_expert.service import FinancialExpertService
from app.financial_expert.source_policy import (
    all_sources_approved,
    approved_domains,
    parse_extra_domains,
    project_approved_hosts,
    source_host,
)
from app.memory import shared_context
from app.memory.shared_context import SharedMemoryRuntime
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import PersistenceDatabase
from app.persistence.thread_store import ConversationThreadStore

QUESTION = "le MASI a augmenté combien le vendredi 11/09 ?"
LIMITATION_FR = (
    "Je ne peux pas confirmer cette information à partir d'une source financière approuvée."
)


class FakeProvider:
    provider_name = "fake-gemini"
    model = "gemini-3.5-flash"

    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, question, system_prompt, *, use_web_grounding=False):
        self.calls.append(use_web_grounding)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def answer(sources, *, domains=None, text="Le MASI a progressé de 0,42 %."):
    provider = FakeProvider(
        FinancialExpertGeneration(text=text, web_grounded=bool(sources), web_sources=tuple(sources))
    )
    service = FinancialExpertService(provider, web_grounding_enabled=True, approved_domains=domains)
    result = service.answer(
        FinancialExpertRequest(question=QUESTION, language="fr", script="latin")
    )
    return provider, result


# ------------------------------------------------------------------ source policy


def test_project_official_hosts_come_from_the_rag_domain_policy():
    assert project_approved_hosts() == ("ecole-bourse.ma", "casablanca-bourse.com", "ammc.ma")


def test_approved_official_source_is_accepted():
    provider, result = answer(
        [
            {
                "domain": "casablanca-bourse.com",
                "title": "casablanca-bourse.com",
                "uri": "https://x.test/1",
            },
            {
                "title": "www.ammc.ma",
                "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/a",
            },
        ]
    )
    assert provider.calls == [True]
    assert result.knowledge_source == "llm_web_grounded_financial_knowledge"
    assert result.answer == "Le MASI a progressé de 0,42 %."
    assert len(result.web_sources) == 2


def test_subdomain_of_an_approved_host_is_accepted():
    _, result = answer([{"domain": "data.casablanca-bourse.com"}])
    assert result.knowledge_source == "llm_web_grounded_financial_knowledge"


def test_one_unapproved_source_rejects_the_whole_grounded_claim():
    _, result = answer(
        [
            {"domain": "casablanca-bourse.com"},
            {"domain": "random-finance-blog.example", "title": "Blog"},
        ]
    )
    assert result.knowledge_source == "controlled_current_data_limitation"
    assert result.answer == LIMITATION_FR
    assert "0,42" not in result.answer
    assert result.web_sources == []


@pytest.mark.parametrize(
    "sources",
    [
        [],
        [{"title": "Bourse de Casablanca"}],
        [{"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc"}],
        [{"domain": "fakecasablanca-bourse.com"}],
        [{"domain": "casablanca-bourse.com.evil.example"}],
    ],
)
def test_no_identifiable_approved_source_fails_closed(sources):
    _, result = answer(sources)
    assert result.knowledge_source == "controlled_current_data_limitation"
    assert "0,42" not in result.answer


def test_explicitly_configured_issuer_domain_is_accepted():
    domains = approved_domains(parse_extra_domains(" attijariwafabank.com , not a host, "))
    assert "attijariwafabank.com" in domains and "ammc.ma" in domains
    _, result = answer([{"domain": "ir.attijariwafabank.com"}], domains=domains)
    assert result.knowledge_source == "llm_web_grounded_financial_knowledge"


def test_quota_error_stays_a_controlled_limitation():
    provider = FakeProvider(RuntimeError("429 RESOURCE_EXHAUSTED"))
    service = FinancialExpertService(provider, web_grounding_enabled=True)
    result = service.answer(
        FinancialExpertRequest(question=QUESTION, language="fr", script="latin")
    )
    assert provider.calls == [True]
    assert result.knowledge_source == "controlled_current_data_limitation"
    assert result.answer == LIMITATION_FR


def test_source_host_never_trusts_google_redirect_hosts():
    assert (
        source_host({"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x"})
        is None
    )
    assert source_host({"uri": "https://www.ammc.ma/fr/page"}) == "ammc.ma"
    assert all_sources_approved([{"uri": "https://www.ammc.ma/fr"}], approved_domains()) is True


def test_from_environment_uses_the_configured_allowlist(monkeypatch):
    import app.financial_expert.service as service_module

    monkeypatch.setattr(
        service_module,
        "get_settings",
        lambda: SimpleNamespace(
            gemini_api_key="k",
            gemini_http_timeout_ms=1,
            gemini_financial_expert_model="gemini-3.5-flash",
            financial_expert_web_grounding_enabled=True,
            financial_expert_approved_domains="lesechos.ma",
        ),
    )
    service = FinancialExpertService.from_environment()
    assert service.approved_domains[:3] == project_approved_hosts()
    assert "lesechos.ma" in service.approved_domains


# ------------------------------------------------------------------ relevant memory switch


def make_store(tmp_path) -> SqlAlchemyConversationHistoryStore:
    database = PersistenceDatabase(
        enabled=True,
        database_url=f"sqlite:///{tmp_path / 'memory.db'}",
        engine_factory=lambda url, **kwargs: create_engine(url, **kwargs),
    )
    Base.metadata.create_all(database.get_engine())
    return SqlAlchemyConversationHistoryStore(database, ConversationThreadStore(database))


def forbid_semantic_memory(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("semantic memory must not be built")

    monkeypatch.setattr(shared_context, "ChromaMemoryVectorIndex", boom)
    monkeypatch.setattr(shared_context, "LocalBGEEmbedder", boom)


def test_disabled_relevant_memory_keeps_persisted_recent_context(tmp_path, monkeypatch):
    forbid_semantic_memory(monkeypatch)
    store = make_store(tmp_path)
    store.append_turn(
        "assistant-memory-thread", "C'est quoi une action ?", "Un titre de propriété."
    )
    runtime = SharedMemoryRuntime(store, relevant_enabled=False)

    context = runtime.resolve("assistant-memory-thread", "Et quels sont ses avantages ?")

    assert context.status == "ok"
    assert [t.user.content for t in context.recent.turns] == ["C'est quoi une action ?"]
    assert context.relevant_old.hits == ()
    projection = runtime.agent_context(
        {
            "thread_id": "assistant-memory-thread",
            "memory_status": "ok",
            "memory_relevant_message_ids": [],
        }
    ).projection
    assert "C'est quoi une action ?" in projection


def test_disabled_relevant_memory_never_indexes_or_loads_bge(tmp_path, monkeypatch):
    forbid_semantic_memory(monkeypatch)
    store = make_store(tmp_path)
    records = store.append_turn("assistant-memory-thread", "q", "a")
    runtime = SharedMemoryRuntime(store, relevant_enabled=False)
    assert runtime.index_canonical_messages("assistant-memory-thread", [r.id for r in records]) == 0
    assert runtime._services is None


def test_chat_runtime_reads_the_relevant_memory_flag(monkeypatch):
    monkeypatch.setattr(chat_api, "get_conversation_history_store", lambda: object())
    monkeypatch.setattr(
        chat_api,
        "get_settings",
        lambda: SimpleNamespace(relevant_memory_enabled=False),
    )
    chat_api.get_memory_runtime.cache_clear()
    try:
        runtime = chat_api.get_memory_runtime()
        assert runtime is not None and runtime.relevant_enabled is False
    finally:
        chat_api.get_memory_runtime.cache_clear()


def test_relevant_memory_setting_defaults_on_and_is_independent_of_persistence(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("RELEVANT_MEMORY_ENABLED", "false")
    settings = Settings(_env_file=None)
    assert settings.persistence_enabled is True
    assert settings.relevant_memory_enabled is False
    monkeypatch.delenv("RELEVANT_MEMORY_ENABLED")
    assert Settings(_env_file=None).relevant_memory_enabled is True
