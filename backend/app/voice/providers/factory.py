from app.config import Settings, get_settings
from app.voice.errors import VoiceConfigurationError
from app.voice.providers.gemini import GeminiVoiceProvider, UnavailableGeminiVoiceProvider


def create_voice_provider(settings: Settings | None = None) -> GeminiVoiceProvider:
    settings = settings or get_settings()
    if settings.voice_provider != "gemini":
        raise VoiceConfigurationError(f"unsupported voice provider: {settings.voice_provider}")
    provider_type = (
        GeminiVoiceProvider if settings.gemini_api_key.strip() else UnavailableGeminiVoiceProvider
    )
    return provider_type(
        api_key=settings.gemini_api_key,
        stt_model=settings.gemini_stt_model,
        tts_model=settings.gemini_tts_model,
        tts_voice=settings.gemini_tts_voice,
        http_timeout_ms=settings.gemini_http_timeout_ms,
    )


def create_live_provider(settings: Settings | None = None):
    from app.voice.providers.live import GeminiLiveSTTProvider

    settings = settings or get_settings()
    if settings.voice_provider != "gemini":
        raise VoiceConfigurationError(f"unsupported voice provider: {settings.voice_provider}")
    return GeminiLiveSTTProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_live_stt_model,
        http_timeout_ms=settings.gemini_http_timeout_ms,
    )
