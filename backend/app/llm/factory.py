"""Environment-driven provider factory."""

from __future__ import annotations

import os

from app.llm.base import LLMProvider, ProviderUnavailable
from app.llm.groq_provider import from_environment


def create_provider(model: str | None = None) -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider != "groq":
        raise ProviderUnavailable(f"Unsupported LLM_PROVIDER: {provider}")
    return from_environment(model=model)
