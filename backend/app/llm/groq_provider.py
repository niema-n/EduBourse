"""Small Groq adapter for the J3 supervisor experiment."""

from __future__ import annotations

import json
import os
from typing import Any

from app.graph.supervisor import SUPERVISOR_INSTRUCTION, SupervisorRequest
from app.llm.base import ProviderUnavailable


class GroqProvider:
    def __init__(self, api_key: str, model: str, timeout: float = 60.0) -> None:
        try:
            from groq import Groq
        except ImportError as exc:
            raise ProviderUnavailable("Groq SDK is not installed") from exc
        self._client = Groq(api_key=api_key, timeout=timeout, max_retries=2)
        self.model = model
        self.last_metadata: dict[str, object] = {}

    def invoke_structured(self, request: SupervisorRequest) -> object:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            reasoning_effort="none",
            max_completion_tokens=100,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SUPERVISOR_INSTRUCTION},
                {"role": "user", "content": self._request_text(request)},
            ],
        )
        headers = getattr(response, "headers", {}) or {}
        usage = getattr(response, "usage", None)
        self.last_metadata = {
            "rate_limit_headers": {
                key: headers.get(key)
                for key in (
                    "x-ratelimit-limit-requests",
                    "x-ratelimit-remaining-requests",
                    "x-ratelimit-reset-requests",
                    "x-ratelimit-limit-tokens",
                    "x-ratelimit-remaining-tokens",
                    "x-ratelimit-reset-tokens",
                    "retry-after",
                )
                if headers.get(key) is not None
            },
            "token_usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }
            if usage is not None
            else None,
        }
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty structured response")
        return json.loads(content)

    @staticmethod
    def _request_text(request: SupervisorRequest) -> str:
        payload: dict[str, Any] = {
            "user_message": request.user_message,
            "business_language": request.business_language,
            "script": request.script,
        }
        if request.workflow_context:
            payload["workflow_context"] = request.workflow_context
        return json.dumps(payload, ensure_ascii=False)


def from_environment() -> GroqProvider:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "").strip()
    if not api_key:
        raise ProviderUnavailable("GROQ_API_KEY is not configured")
    if not model:
        raise ProviderUnavailable("GROQ_MODEL is not configured")
    return GroqProvider(api_key=api_key, model=model)
