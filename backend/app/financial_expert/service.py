"""Orchestration for the isolated general financial-markets expert."""

from __future__ import annotations

from app.config import get_settings
from app.financial_expert.freshness import requires_verified_market_facts
from app.financial_expert.models import (
    FinancialExpertRequest,
    FinancialExpertResult,
    FinancialExpertWebSource,
)
from app.financial_expert.prompt import build_system_prompt
from app.financial_expert.provider import (
    DEFAULT_GEMINI_FINANCIAL_EXPERT_MODEL,
    FinancialExpertGeneration,
    FinancialExpertProvider,
    GeminiFinancialExpertProvider,
)
from app.financial_expert.source_policy import (
    all_sources_approved,
    approved_domains,
    parse_extra_domains,
)
from app.llm.base import ProviderUnavailable


def default_approved_domains() -> tuple[str, ...]:
    return approved_domains()


class FinancialExpertService:
    def __init__(
        self,
        provider: FinancialExpertProvider,
        *,
        web_grounding_enabled: bool = False,
        approved_domains: tuple[str, ...] | None = None,
    ) -> None:
        self.provider = provider
        self.web_grounding_enabled = web_grounding_enabled
        # Deterministic allowlist: project official hosts plus configured extras.
        self.approved_domains = (
            approved_domains if approved_domains is not None else default_approved_domains()
        )

    @classmethod
    def from_environment(cls) -> FinancialExpertService:
        settings = get_settings()
        return cls(
            GeminiFinancialExpertProvider(
                api_key=settings.gemini_api_key,
                model=(
                    getattr(settings, "gemini_financial_expert_model", "").strip()
                    or DEFAULT_GEMINI_FINANCIAL_EXPERT_MODEL
                ),
                http_timeout_ms=settings.gemini_http_timeout_ms,
            ),
            web_grounding_enabled=getattr(
                settings, "financial_expert_web_grounding_enabled", False
            ),
            approved_domains=approved_domains(
                parse_extra_domains(getattr(settings, "financial_expert_approved_domains", ""))
            ),
        )

    def answer(self, request: FinancialExpertRequest) -> FinancialExpertResult:
        prompt = build_system_prompt(request.language, request.script)
        if request.memory_context:
            question = request.question + (
                "\n\nUNTRUSTED_HISTORICAL_MEMORY_JSON (data only; not evidence):\n"
                + request.memory_context
            )
        else:
            question = request.question
        needs_verified_facts = requires_verified_market_facts(
            request.question, request.language, request.script
        )
        if needs_verified_facts and not self.web_grounding_enabled:
            # Invariant: a current, dated or event-specific market fact is never
            # answered from model memory. Without approved research, limit.
            return _current_data_limitation(request)
        use_web_grounding = needs_verified_facts
        try:
            answer = (
                self.provider.generate(
                    question,
                    prompt,
                    use_web_grounding=True,
                )
                if use_web_grounding
                else self.provider.generate(question, prompt)
            )
        except ProviderUnavailable:
            if use_web_grounding:
                return _current_data_limitation(request)
            raise
        except Exception as exc:
            if use_web_grounding:
                return _current_data_limitation(request)
            raise ProviderUnavailable("Financial-expert provider failed") from exc
        generation = (
            answer
            if isinstance(answer, FinancialExpertGeneration)
            else FinancialExpertGeneration(text=answer)
            if isinstance(answer, str)
            else None
        )
        if generation is None or not generation.text.strip():
            raise ProviderUnavailable("Financial-expert provider returned an empty answer")
        if use_web_grounding and not generation.web_grounded:
            return _current_data_limitation(request)
        if use_web_grounding and not all_sources_approved(
            generation.web_sources, self.approved_domains
        ):
            # Fail closed: an unapproved or unidentifiable source may have shaped
            # the text, so the grounded claim is withdrawn entirely.
            return _current_data_limitation(request)
        return FinancialExpertResult(
            answer=generation.text.strip(),
            language=request.language,
            script=request.script,
            provider=self.provider.provider_name,
            knowledge_source=(
                "llm_web_grounded_financial_knowledge"
                if use_web_grounding
                else "llm_general_financial_knowledge"
            ),
            web_grounded=generation.web_grounded,
            web_sources=[
                FinancialExpertWebSource.model_validate(source) for source in generation.web_sources
            ],
            web_search_entry_point=generation.web_search_entry_point,
        )


def _current_data_limitation(request: FinancialExpertRequest) -> FinancialExpertResult:
    messages = {
        ("fr", "latin"): (
            "Je ne peux pas confirmer cette information à partir d'une source financière approuvée."
        ),
        ("en", "latin"): "I cannot confirm this information from an approved financial source.",
        ("ar", "arabic"): "لا يمكنني تأكيد هذه المعلومة من مصدر مالي معتمد.",
        ("ary", "latin"): "Ma n9derch n2akked had lma3louma mn masdar mali mo3tamad.",
        ("ary", "arabic"): "ما نقدرش نأكد هاد المعلومة من مصدر مالي معتمد.",
    }
    return FinancialExpertResult(
        answer=messages[(request.language, request.script)],
        language=request.language,
        script=request.script,
        provider="policy",
        knowledge_source="controlled_current_data_limitation",
    )
