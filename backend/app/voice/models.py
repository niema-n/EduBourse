from dataclasses import dataclass, field
from typing import Any, Literal

VoiceState = Literal["idle", "listening", "processing", "speaking", "interrupted", "error"]


@dataclass(frozen=True)
class AudioInput:
    data: bytes
    mime_type: str
    sample_rate: int | None = None
    channels: int | None = None
    duration_ms: int | None = None
    filename: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    provider: str
    model: str | None = None
    detected_language: str | None = None
    confidence: float | None = None
    duration_ms: int | None = None
    degraded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpeechSynthesisResult:
    audio: bytes
    mime_type: str
    provider: str
    model: str | None = None
    voice: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    sample_width_bytes: int | None = None
    duration_ms: int | None = None
    degraded: bool = False


@dataclass(frozen=True)
class VoiceSession:
    session_id: str
    thread_id: str
    state: VoiceState = "idle"


@dataclass(frozen=True)
class VoiceTurnResult:
    session: VoiceSession
    transcription: TranscriptionResult | None = None
    text_response: Any | None = None
    synthesis: SpeechSynthesisResult | None = None
    error: str | None = None
    error_stage: str | None = None
    answer: str | None = None
    language: str | None = None
    script: str | None = None
    route: str | None = None
    blocked: bool | None = None
    status: str | None = None
    stt_provider: str | None = None
    stt_model: str | None = None
    tts_provider: str | None = None
    tts_model: str | None = None
    tts_voice: str | None = None
    audio: bytes | None = None
    audio_mime_type: str | None = None
    audio_sample_rate: int | None = None
    stt_latency_ms: float | None = None
    business_latency_ms: float | None = None
    tts_latency_ms: float | None = None
    total_latency_ms: float | None = None


@dataclass(frozen=True)
class VoiceTextResult:
    session_id: str
    thread_id: str
    transcript: str
    language: str
    script: str
    route: str
    blocked: bool
    status: str
    answer: str
    stt_provider: str
    transcription_result: TranscriptionResult | None = None
    stt_model: str | None = None
    stt_latency_ms: float | None = None
    business_latency_ms: float | None = None
    total_latency_ms: float | None = None
    degraded: bool = False
