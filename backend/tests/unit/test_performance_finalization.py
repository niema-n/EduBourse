"""BGE-M3 background warm-up and the bounded Groq grounded-generation retry."""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from groq import APITimeoutError, BadRequestError, InternalServerError, RateLimitError

from app.rag import grounded_generation as gg
from app.rag import runtime, warmup

REQUEST = httpx.Request("POST", "https://api.groq.test/openai/v1/chat/completions")


def status_error(cls, status: int, retry_after: str | None = None):
    headers = {"retry-after": retry_after} if retry_after else {}
    return cls(
        "provider error",
        response=httpx.Response(status, request=REQUEST, headers=headers),
        body=None,
    )


def ok_response():
    message = SimpleNamespace(
        content='{"answer": "ok", "used_evidence_ids": ["S1"], "insufficient_evidence": false}'
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def provider_with(outcomes, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(gg, "_sleep", sleeps.append)
    provider = gg.GroqGroundedGenerationProvider.__new__(gg.GroqGroundedGenerationProvider)
    completions = FakeCompletions(outcomes)
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider.model = gg.GENERATION_MODEL
    return provider, completions, sleeps


# ------------------------------------------------------------------ generation retry


def test_first_call_success_does_not_retry(monkeypatch):
    provider, completions, sleeps = provider_with([ok_response()], monkeypatch)
    assert provider.generate("system", "user")["answer"] == "ok"
    assert completions.calls == 1 and sleeps == []


def test_429_then_success_retries_once_with_bounded_delay(monkeypatch):
    provider, completions, sleeps = provider_with(
        [status_error(RateLimitError, 429, retry_after="2"), ok_response()], monkeypatch
    )
    assert provider.generate("system", "user")["answer"] == "ok"
    assert completions.calls == 2
    assert sleeps == [2.0]


def test_retry_delay_is_capped_at_eight_seconds(monkeypatch):
    provider, _, sleeps = provider_with(
        [status_error(RateLimitError, 429, retry_after="60"), ok_response()], monkeypatch
    )
    provider.generate("system", "user")
    assert sleeps == [8.0]


def test_two_consecutive_429_fail_after_exactly_one_retry(monkeypatch):
    provider, completions, sleeps = provider_with(
        [status_error(RateLimitError, 429), status_error(RateLimitError, 429), ok_response()],
        monkeypatch,
    )
    with pytest.raises(RateLimitError):
        provider.generate("system", "user")
    assert completions.calls == 2 and len(sleeps) == 1


def test_two_consecutive_429_become_a_controlled_generation_failure(monkeypatch):
    provider, _, _ = provider_with(
        [status_error(RateLimitError, 429), status_error(RateLimitError, 429)], monkeypatch
    )
    retrieval = SimpleNamespace(
        retrieval_status="ok",
        chunks=[
            SimpleNamespace(
                chunk_id="c1",
                source_id="s1",
                title="T",
                page=1,
                page_start=1,
                page_end=1,
                heading=None,
                text="Une action est un titre de propriété.",
            )
        ],
        retrieval_query=None,
    )
    service = gg.GroundedGenerationService(
        SimpleNamespace(retrieve=lambda request: retrieval), provider=provider
    )
    result = service.generate(
        gg.GroundedGenerationRequest(
            original_query="C'est quoi une action ?", language="fr", script="latin"
        )
    )
    assert result.generation_status == "generation_provider_error"
    assert result.answer is None and result.citations == []


def test_5xx_is_retried_once(monkeypatch):
    provider, completions, _ = provider_with(
        [status_error(InternalServerError, 503), ok_response()], monkeypatch
    )
    provider.generate("system", "user")
    assert completions.calls == 2


@pytest.mark.parametrize(
    "error",
    [
        status_error(BadRequestError, 400),
        APITimeoutError(request=REQUEST),
        ValueError("invalid JSON"),
    ],
)
def test_non_transient_errors_are_not_retried(monkeypatch, error):
    provider, completions, sleeps = provider_with([error, ok_response()], monkeypatch)
    with pytest.raises(type(error)):
        provider.generate("system", "user")
    assert completions.calls == 1 and sleeps == []


def test_retry_policy_constants():
    assert gg.GroqGroundedGenerationProvider.MAX_RETRIES == 1
    assert gg.GroqGroundedGenerationProvider.MAX_RETRY_DELAY_SECONDS == 8.0


# ------------------------------------------------------------------ warm-up


class RecordingService:
    """Stands in for the shared RetrievalService during warm-up."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.queries: list[tuple[str, int]] = []
        self.embedding_provider = SimpleNamespace(
            embed_queries=lambda texts: pytest.fail("warm-up must reuse the shared service")
        )
        self.collection = SimpleNamespace(
            add=lambda **kwargs: pytest.fail("corpus write"),
            upsert=lambda **kwargs: pytest.fail("corpus write"),
            delete=lambda **kwargs: pytest.fail("corpus write"),
        )
        self.query_adapter = SimpleNamespace(
            generate=lambda payload: pytest.fail("no provider call during warm-up")
        )

    def _query(self, query, n_results):
        if self.fail:
            raise RuntimeError("retrieval failed")
        self.queries.append((query, n_results))
        return ["chunk"], [0.1]


@pytest.fixture
def fresh_warmup(monkeypatch):
    monkeypatch.setattr(warmup, "_thread", None)
    monkeypatch.setattr(warmup, "_run_count", 0)
    monkeypatch.setattr(runtime, "_service", None)
    monkeypatch.setattr(runtime, "_state", "not_loaded")


def test_warmup_uses_the_shared_service_and_primes_read_only_queries(monkeypatch, fresh_warmup):
    service = RecordingService()
    monkeypatch.setattr(runtime, "get_retrieval_service", lambda: service)

    assert warmup.run_warmup() is True
    assert [query for query, _ in service.queries] == list(warmup.WARMUP_QUERIES)


def test_warmup_starts_only_once_per_process(monkeypatch, fresh_warmup):
    service = RecordingService()
    monkeypatch.setattr(runtime, "get_retrieval_service", lambda: service)

    assert warmup.start_background_warmup() is True
    assert warmup.start_background_warmup() is False
    warmup._thread.join(timeout=5)
    assert warmup._run_count == 1
    assert len(service.queries) == len(warmup.WARMUP_QUERIES)


@pytest.mark.parametrize("failure", ["service_raises", "embedding_raises", "service_unavailable"])
def test_warmup_failure_never_raises_and_allows_a_later_lazy_load(
    monkeypatch, fresh_warmup, failure
):
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    if failure == "service_raises":
        monkeypatch.setattr(
            runtime, "get_retrieval_service", lambda: (_ for _ in ()).throw(OSError("x"))
        )
    elif failure == "embedding_raises":
        monkeypatch.setattr(
            runtime,
            "get_retrieval_service",
            lambda: RecordingService(fail=True),
        )
    else:

        def unavailable():
            runtime._state = "unavailable"
            return None

        monkeypatch.setattr(runtime, "get_retrieval_service", unavailable)

    assert warmup.run_warmup() is False
    if failure == "service_unavailable":
        assert runtime.retrieval_state() == "not_loaded"


def test_warmup_and_first_request_share_one_retrieval_service(monkeypatch, fresh_warmup):
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    created: list[object] = []

    class SlowService:
        def __init__(self, root, *, query_adapter=None):
            time.sleep(0.2)  # model loading window where a user request arrives
            self.embedding_provider = SimpleNamespace()
            created.append(self)

    monkeypatch.setattr(runtime, "RetrievalService", SlowService)
    monkeypatch.setattr(runtime, "GroqQueryAdapterProvider", lambda api_key: object())

    warmup.start_background_warmup()
    seen: list[object] = []
    request = threading.Thread(target=lambda: seen.append(runtime.get_retrieval_service()))
    request.start()
    request.join(timeout=5)
    warmup._thread.join(timeout=5)

    assert len(created) == 1
    assert seen == created


def test_warmup_is_disabled_by_default():
    from app.config import Settings

    assert Settings(_env_file=None).rag_warmup_enabled is False
