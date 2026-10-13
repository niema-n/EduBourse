import json
from types import SimpleNamespace

from app.graph.response_localizer import (
    FallbackResponseLocalizationProvider,
    GeminiDarijaLocalizationProvider,
    localize_business_answer,
)

LATIN_DARIJA = (
    "Saham howa wara9a maliya li kat3ni joz2 mn ras lmal dyal charika. "
    "Li 3ndo saham kayweli cherik f charika."
)
ARABIC_DARIJA = (
    "السهم هو ورقة مالية اللي كتعني جزء من راس المال ديال الشركة. "
    "اللي عندو سهم كيولي شريك فالشركة."
)


class GeminiModels:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({"answer": self.answer}))


def test_gemini_plain_text_is_checked_by_the_darija_guard_not_fallen_back() -> None:
    class PlainTextModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=LATIN_DARIJA)

    provider = GeminiDarijaLocalizationProvider(
        api_key="test",
        model="gemini-3.6-flash",
        timeout_ms=1000,
        client=SimpleNamespace(models=PlainTextModels()),
    )

    outcome = localize_business_answer(
        "Une action represente une part du capital.", "ary", "latin", provider
    )

    assert outcome.status == "localized"
    assert outcome.answer == LATIN_DARIJA


def test_gemini_localizer_sends_only_the_business_answer_and_json_contract() -> None:
    models = GeminiModels(LATIN_DARIJA)
    provider = GeminiDarijaLocalizationProvider(
        api_key="test", model="gemini-3.6-flash", timeout_ms=1000,
        client=SimpleNamespace(models=models),
    )

    outcome = localize_business_answer(
        "Une action represente une part du capital.", "ary", "latin", provider
    )

    assert outcome.status == "localized"
    assert outcome.answer == LATIN_DARIJA
    assert outcome.provider == "gemini"
    assert len(models.calls) == 1
    call = models.calls[0]
    assert call["model"] == "gemini-3.6-flash"
    assert set(json.loads(call["contents"])) == {"target_language", "answer"}
    assert "citation" not in call["contents"].lower()
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["max_output_tokens"] == 4096


def test_gemini_localizer_unwraps_fenced_and_nested_json_before_validation() -> None:
    nested = json.dumps({"answer": json.dumps({"answer": LATIN_DARIJA})})

    class NestedModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=f"```json\n{nested}\n```")

    provider = GeminiDarijaLocalizationProvider(
        api_key="test",
        model="gemini-3.6-flash",
        timeout_ms=1000,
        client=SimpleNamespace(models=NestedModels()),
    )

    outcome = localize_business_answer("Une reponse metier complete.", "ary", "latin", provider)

    assert outcome.status == "localized"
    assert outcome.answer == LATIN_DARIJA


def test_truncated_provider_output_retries_from_the_original_business_answer() -> None:
    class SequencedProvider:
        provider_name = "gemini"

        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def localize(self, system_prompt, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {"answer": LATIN_DARIJA, "_metadata": {"finish_reason": "max_tokens"}}
            return {"answer": LATIN_DARIJA, "_metadata": {"finish_reason": "stop"}}

    provider = SequencedProvider()
    source = "Une reponse metier complete qui doit etre localisee entierement."

    outcome = localize_business_answer(source, "ary", "latin", provider)

    assert outcome.status == "localized"
    assert outcome.retry_count == 1
    assert provider.calls[1]["answer"] == source


def test_malformed_structured_output_retries_gemini_without_fallback() -> None:
    class MalformedThenValidModels:
        def __init__(self) -> None:
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            text = (
                '{"unexpected": "wrapper"}'
                if self.calls == 1
                else json.dumps({"answer": LATIN_DARIJA})
            )
            return SimpleNamespace(text=text)

    models = MalformedThenValidModels()
    provider = GeminiDarijaLocalizationProvider(
        api_key="test",
        model="gemini-3.6-flash",
        timeout_ms=1000,
        client=SimpleNamespace(models=models),
    )

    outcome = localize_business_answer("Une reponse metier complete.", "ary", "latin", provider)

    assert outcome.status == "localized"
    assert outcome.retry_count == 1
    assert models.calls == 2


def test_gemini_localizer_respects_arabic_script() -> None:
    models = GeminiModels(ARABIC_DARIJA)
    provider = GeminiDarijaLocalizationProvider(
        api_key="test", model="gemini-3.6-flash", timeout_ms=1000,
        client=SimpleNamespace(models=models),
    )

    outcome = localize_business_answer(
        "يمكن للمستثمر شراء السهم في البورصة.", "ary", "arabic", provider
    )

    assert outcome.status == "localized"
    assert outcome.answer == ARABIC_DARIJA
    payload = json.loads(models.calls[0]["contents"])
    assert "Arabic script" in payload["target_language"]


def test_non_darija_languages_never_call_gemini() -> None:
    models = GeminiModels(LATIN_DARIJA)
    provider = GeminiDarijaLocalizationProvider(
        api_key="test", model="gemini-3.6-flash", timeout_ms=1000,
        client=SimpleNamespace(models=models),
    )

    for language, script in (("fr", "latin"), ("en", "latin"), ("ar", "arabic")):
        outcome = localize_business_answer("Source answer.", language, script, provider)
        assert outcome.status == "not_needed"
    assert models.calls == []


class FailingProvider:
    provider_name = "gemini"

    def __init__(self) -> None:
        self.calls = 0

    def localize(self, system_prompt, payload):
        self.calls += 1
        raise TimeoutError("provider unavailable")


class FixedProvider:
    provider_name = "groq_fallback"

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = 0

    def localize(self, system_prompt, payload):
        self.calls += 1
        return {"answer": self.answer}


def test_technical_gemini_failure_uses_controlled_groq_fallback() -> None:
    gemini = FailingProvider()
    groq = FixedProvider(LATIN_DARIJA)
    provider = FallbackResponseLocalizationProvider(gemini, groq)

    outcome = localize_business_answer("Une action represente une part.", "ary", "latin", provider)

    assert outcome.status == "localized"
    assert outcome.provider == "groq_fallback"
    assert gemini.calls == 2
    assert groq.calls == 1


def test_transient_gemini_failure_retries_primary_without_calling_groq() -> None:
    class TransientGemini:
        provider_name = "gemini"

        def __init__(self) -> None:
            self.calls = 0

        def localize(self, system_prompt, payload):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("temporary provider failure")
            return {"answer": LATIN_DARIJA}

    gemini = TransientGemini()
    groq = FixedProvider(LATIN_DARIJA)
    provider = FallbackResponseLocalizationProvider(gemini, groq)

    outcome = localize_business_answer("Une action represente une part.", "ary", "latin", provider)

    assert outcome.status == "localized"
    assert outcome.provider == "gemini"
    assert gemini.calls == 2
    assert groq.calls == 0


def test_structured_answer_does_not_use_groq_after_two_gemini_failures() -> None:
    gemini = FailingProvider()
    groq = FixedProvider(LATIN_DARIJA)
    provider = FallbackResponseLocalizationProvider(gemini, groq)
    source = "\n".join(f"{index}. Une etape importante." for index in range(1, 6))

    outcome = localize_business_answer(source, "ary", "latin", provider)

    assert outcome.status == "failed"
    assert gemini.calls == 2
    assert groq.calls == 0


def test_guard_rejection_retries_gemini_without_calling_fallback() -> None:
    class RejectedGemini:
        provider_name = "gemini"

        def __init__(self) -> None:
            self.calls = 0

        def localize(self, system_prompt, payload):
            self.calls += 1
            return {"answer": "Cette phrase reste entierement francaise et ne devient pas Darija."}

    gemini = RejectedGemini()
    groq = FixedProvider(LATIN_DARIJA)
    provider = FallbackResponseLocalizationProvider(gemini, groq)

    outcome = localize_business_answer("Une action represente une part.", "ary", "latin", provider)

    assert outcome.status == "failed"
    assert outcome.retry_count == 1
    assert gemini.calls == 2
    assert groq.calls == 0
