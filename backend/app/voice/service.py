import time
from collections.abc import Callable

from app.schemas.chat import ChatRequest, ChatResponse
from app.voice.audio import validate_audio
from app.voice.errors import (
    TranscriptionFailed,
    TTSFailed,
    VoiceError,
    VoiceSessionError,
)
from app.voice.models import AudioInput, VoiceSession, VoiceTextResult, VoiceTurnResult
from app.voice.providers.base import SpeechToTextProvider, TextToSpeechProvider


class VoiceService:
    """Wraps the single J4 text pipeline with future STT/TTS provider boundaries."""

    def __init__(
        self,
        stt_provider: SpeechToTextProvider,
        tts_provider: TextToSpeechProvider,
        text_pipeline: Callable[[ChatRequest], ChatResponse],
        max_audio_bytes: int | None = None,
    ) -> None:
        self.stt_provider = stt_provider
        self.tts_provider = tts_provider
        self.text_pipeline = text_pipeline
        self.max_audio_bytes = max_audio_bytes

    def process(
        self,
        audio: AudioInput,
        *,
        session_id: str,
        thread_id: str,
    ) -> VoiceTurnResult:
        started = time.perf_counter()
        text_result = self.process_to_text(
            audio,
            session_id=session_id,
            thread_id=thread_id,
        )
        tts_started = time.perf_counter()
        try:
            synthesis = self.tts_provider.synthesize(
                text_result.answer,
                language=text_result.language,
                script=text_result.script,
            )
        except VoiceError:
            raise
        except Exception as exc:
            raise TTSFailed("voice synthesis failed") from exc
        tts_latency_ms = round((time.perf_counter() - tts_started) * 1000, 2)
        return VoiceTurnResult(
            session=VoiceSession(session_id=session_id, thread_id=thread_id, state="speaking"),
            transcription=text_result.transcription_result,
            text_response=text_result,
            synthesis=synthesis,
            answer=text_result.answer,
            language=text_result.language,
            script=text_result.script,
            route=text_result.route,
            blocked=text_result.blocked,
            status=text_result.status,
            stt_provider=text_result.stt_provider,
            stt_model=text_result.stt_model,
            tts_provider=synthesis.provider,
            tts_model=synthesis.model,
            tts_voice=synthesis.voice,
            audio=synthesis.audio,
            audio_mime_type=synthesis.mime_type,
            audio_sample_rate=synthesis.sample_rate,
            stt_latency_ms=text_result.stt_latency_ms,
            business_latency_ms=text_result.business_latency_ms,
            tts_latency_ms=tts_latency_ms,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def process_to_text(
        self,
        audio: AudioInput,
        *,
        session_id: str,
        thread_id: str,
    ) -> VoiceTextResult:
        started = time.perf_counter()
        try:
            transcription = self.stt_provider.transcribe(
                validate_audio(audio, max_bytes=self.max_audio_bytes)
            )
        except VoiceError:
            raise
        except Exception as exc:
            raise TranscriptionFailed("voice transcription failed") from exc
        if not transcription.text.strip():
            raise TranscriptionFailed("transcription is empty")
        stt_latency_ms = round((time.perf_counter() - started) * 1000, 2)

        business_started = time.perf_counter()
        try:
            response = self.text_pipeline(
                ChatRequest(message=transcription.text, thread_id=thread_id)
            )
        except Exception as exc:
            raise VoiceSessionError("shared text pipeline failed") from exc
        business_latency_ms = round((time.perf_counter() - business_started) * 1000, 2)
        return VoiceTextResult(
            session_id=session_id,
            thread_id=thread_id,
            transcript=transcription.text,
            language=response.language,
            script=response.script,
            route=response.route,
            blocked=response.blocked,
            status=response.status,
            answer=response.answer,
            stt_provider=transcription.provider,
            transcription_result=transcription,
            stt_model=transcription.model,
            stt_latency_ms=stt_latency_ms,
            business_latency_ms=business_latency_ms,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
            degraded=transcription.degraded,
        )
