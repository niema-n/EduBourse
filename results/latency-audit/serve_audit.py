"""Diagnostic-only launcher: observe provider attempts without changing policies."""
import time
from urllib.parse import urlsplit
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
import httpx
from app.observability.logging import emit

azure_host = urlsplit(os.getenv("AZURE_OPENAI_ENDPOINT", "")).hostname

def provider_for(request):
    host = request.url.host
    if host == azure_host or host.endswith('.openai.azure.com') or host.endswith('.services.ai.azure.com'):
        return "azure"
    if host.endswith("groq.com"):
        return "groq"
    if "generativelanguage.googleapis.com" in host:
        return "gemini"
    return None

original_send = httpx.Client.send
def observed_send(self, request, *args, **kwargs):
    provider = provider_for(request)
    start = time.perf_counter()
    response = None
    error = None
    try:
        response = original_send(self, request, *args, **kwargs)
        return response
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        if provider:
            emit("audit.provider.attempt", provider=provider,
                 duration_ms=round((time.perf_counter()-start)*1000, 2),
                 status_code=response.status_code if response is not None else None,
                 error_type=error, sdk_retry=request.headers.get("x-stainless-retry-count"))
httpx.Client.send = observed_send

original_async_send = httpx.AsyncClient.send
async def observed_async_send(self, request, *args, **kwargs):
    provider = provider_for(request)
    start = time.perf_counter()
    response = None
    error = None
    try:
        response = await original_async_send(self, request, *args, **kwargs)
        return response
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        if provider:
            emit("audit.provider.attempt", provider=provider,
                 duration_ms=round((time.perf_counter()-start)*1000, 2),
                 status_code=response.status_code if response is not None else None,
                 error_type=error, sdk_retry=request.headers.get("x-stainless-retry-count"))
httpx.AsyncClient.send = observed_async_send

# Installed OpenAI SDK uses httpx2, whereas Groq uses httpx.
import httpx2
original_send2 = httpx2.Client.send
def observed_send2(self, request, *args, **kwargs):
    provider = provider_for(request)
    start = time.perf_counter()
    response = None
    error = None
    try:
        response = original_send2(self, request, *args, **kwargs)
        return response
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        if provider:
            emit("audit.provider.attempt", provider=provider,
                 duration_ms=round((time.perf_counter()-start)*1000, 2),
                 status_code=response.status_code if response is not None else None,
                 error_type=error, sdk_retry=request.headers.get("x-stainless-retry-count"))
httpx2.Client.send = observed_send2

from app.graph.final_response_composer import MultilingualFinalResponseComposer
original_compose = MultilingualFinalResponseComposer.compose
def observed_compose(self, *args, **kwargs):
    try:
        return original_compose(self, *args, **kwargs)
    finally:
        emit("audit.composer.validation", attempts=[{
            "attempt": a.get("attempt"), "accepted": a.get("accepted"),
            "reasons": a.get("reasons"),
            "error_type": a.get("diagnostics", {}).get("exception_type"),
        } for a in self.validation_attempts])
MultilingualFinalResponseComposer.compose = observed_compose

def observe_method(cls, name, event):
    original = getattr(cls, name)
    def observed(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        finally:
            emit(event, duration_ms=round((time.perf_counter()-started)*1000, 2))
    setattr(cls, name, observed)

from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.memory.shared_context import SharedMemoryRuntime
from app.memory.embeddings import LocalBGEEmbedder
observe_method(SqlAlchemyConversationHistoryStore, "append_turn", "audit.history.sql")
observe_method(SharedMemoryRuntime, "index_canonical_messages", "audit.memory.index")
observe_method(LocalBGEEmbedder, "embed_texts", "audit.memory.embedding_passages")
observe_method(LocalBGEEmbedder, "embed_query", "audit.memory.embedding_query")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080)
