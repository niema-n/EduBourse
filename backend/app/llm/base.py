"""Provider-neutral interfaces used by the J3 supervisor."""

from __future__ import annotations

from typing import Protocol

from app.graph.supervisor import SupervisorRequest


class ProviderUnavailable(RuntimeError):
    """Raised when no configured provider can serve a request."""


class LLMProvider(Protocol):
    def invoke_structured(self, request: SupervisorRequest) -> object:
        """Return structured routing data, never a user-facing answer."""
