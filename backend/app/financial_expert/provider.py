"""Dependency-injected provider interface and lazy Gemini text adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.llm.base import ProviderUnavailable

DEFAULT_GEMINI_FINANCIAL_EXPERT_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class FinancialExpertGeneration:
    text: str
    web_grounded: bool = False
    web_sources: tuple[dict[str, str | None], ...] = ()
    web_search_entry_point: str | None = None


class FinancialExpertProvider(Protocol):
    provider_name: str
    model: str

    def generate(
        self,
        question: str,
        system_prompt: str,
        *,
        use_web_grounding: bool = False,
    ) -> FinancialExpertGeneration:
        """Generate one answer from the supplied policy and question."""


class GeminiFinancialExpertProvider:
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_FINANCIAL_EXPERT_MODEL,
        http_timeout_ms: int = 60_000,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.http_timeout_ms = http_timeout_ms
        self._client = client

    def _get_client(self) -> Any:
        if not self.api_key.strip() and self._client is None:
            raise ProviderUnavailable("Gemini API key is not configured")
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise ProviderUnavailable("google-genai is not installed") from exc
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.http_timeout_ms),
            )
        return self._client

    def generate(
        self,
        question: str,
        system_prompt: str,
        *,
        use_web_grounding: bool = False,
    ) -> FinancialExpertGeneration:
        try:
            config: dict[str, Any] = {
                "system_instruction": system_prompt,
                "temperature": 0,
            }
            if use_web_grounding:
                from google.genai import types

                config["tools"] = [
                    types.Tool(google_search=types.GoogleSearch()),
                ]
            response = self._get_client().models.generate_content(
                model=self.model,
                contents=question,
                config=config,
            )
            answer = getattr(response, "text", None)
            if not isinstance(answer, str) or not answer.strip():
                raise ProviderUnavailable("Gemini returned an empty financial-expert answer")
            if not use_web_grounding:
                return FinancialExpertGeneration(text=answer.strip())
            metadata = _grounding_metadata(response)
            sources = []
            for chunk in getattr(metadata, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                if web is None:
                    continue
                title = getattr(web, "title", None)
                uri = getattr(web, "uri", None)
                domain = getattr(web, "domain", None)
                if isinstance(title, str) or isinstance(uri, str) or isinstance(domain, str):
                    source = {
                        "title": title if isinstance(title, str) else None,
                        "uri": uri if isinstance(uri, str) else None,
                    }
                    if isinstance(domain, str):
                        source["domain"] = domain
                    sources.append(source)
            entry_point = getattr(
                getattr(metadata, "search_entry_point", None),
                "rendered_content",
                None,
            )
            return FinancialExpertGeneration(
                text=answer.strip(),
                web_grounded=bool(sources),
                web_sources=tuple(sources),
                web_search_entry_point=entry_point if isinstance(entry_point, str) else None,
            )
        except ProviderUnavailable:
            raise
        except Exception as exc:
            raise ProviderUnavailable("Gemini financial-expert generation failed") from exc


def _grounding_metadata(response: Any) -> Any | None:
    metadata = getattr(response, "grounding_metadata", None)
    if metadata is not None:
        return metadata
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        return getattr(candidates[0], "grounding_metadata", None)
    return None
