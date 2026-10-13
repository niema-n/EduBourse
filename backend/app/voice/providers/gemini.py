import base64
import binascii
import logging
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.voice.audio import validate_audio
from app.voice.errors import TranscriptionFailed, TTSFailed, VoiceProviderUnavailable
from app.voice.models import AudioInput, SpeechSynthesisResult, TranscriptionResult

logger = logging.getLogger(__name__)

MIME_SUFFIXES = {
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/mp3": ".mp3",
    "audio/mpeg": ".mpeg",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
}


@dataclass(frozen=True)
class TTSSpeechProfile:
    speech_language: str
    instruction: str


TTS_SPEECH_PROFILES: dict[tuple[str, str], TTSSpeechProfile] = {
    ("fr", "latin"): TTSSpeechProfile(
        speech_language="French",
        instruction=(
            "Speak naturally in clear contemporary French. Use a warm, professional "
            "educational tone and a moderate conversational pace. Use natural French "
            "pronunciation and prosody. Read the supplied transcript faithfully. Do not "
            "translate, summarize, paraphrase, add, or remove any content."
        ),
    ),
    ("en", "latin"): TTSSpeechProfile(
        speech_language="English",
        instruction=(
            "Speak naturally in clear fluent English with a neutral, internationally "
            "understandable accent. Use a warm professional educational tone and a "
            "moderate conversational pace. Read the supplied transcript faithfully. Do "
            "not translate, summarize, paraphrase, add, or remove any content."
        ),
    ),
    ("ar", "arabic"): TTSSpeechProfile(
        speech_language="Arabic",
        instruction=(
            "Speak in natural, clear Modern Standard Arabic (MSA / العربية الفصحى). "
            "Use professional educational pronunciation and a calm conversational pace. "
            "Do not switch to Moroccan Darija or another regional Arabic dialect. Read "
            "the transcript faithfully without translating or rewriting it."
        ),
    ),
    ("ary", "arabic"): TTSSpeechProfile(
        speech_language="Arabic",
        instruction=(
            "Speak this transcript in authentic contemporary Moroccan Darija as naturally "
            "spoken in Morocco. Use a clearly Moroccan accent and Moroccan rhythm, "
            "pronunciation and intonation. Do not pronounce it as Modern Standard Arabic. "
            "Do not use an Egyptian, Levantine or Gulf accent. The delivery should sound "
            "like a friendly Moroccan financial-education assistant speaking naturally to "
            "another Moroccan person. Keep technical financial terminology intelligible, "
            "but preserve Moroccan Darija prosody around it. Read the supplied transcript "
            "faithfully. Do not translate it. Do not paraphrase it. Do not add or remove "
            "information."
        ),
    ),
    ("ary", "latin"): TTSSpeechProfile(
        speech_language="Arabic",
        instruction=(
            "Speak this transcript as authentic contemporary Moroccan Darija. The transcript "
            "is Moroccan Darija written in Latin/Arabizi script. Interpret it as spoken "
            "Moroccan Darija. Digits such as 3, 7 and 9 are Arabizi phonetic symbols where "
            "applicable. Do not read them as literal numbers or spell the Latin characters. "
            "Use a clearly Moroccan accent, rhythm, pronunciation and intonation. Do not "
            "pronounce it as Modern Standard Arabic or another regional Arabic dialect. "
            "Read the supplied transcript faithfully. Do not translate, paraphrase, add, "
            "or remove any information."
        ),
    ),
}


def _get_tts_profile(language: str, script: str) -> TTSSpeechProfile:
    try:
        return TTS_SPEECH_PROFILES[(language, script)]
    except KeyError as exc:
        raise TTSFailed(f"Unsupported TTS language/script: {language}/{script}") from exc


def _tts_input(profile: TTSSpeechProfile, text: str) -> str:
    """Speaking profile as director's notes, followed by the exact transcript.

    Gemini TTS models reject ``system_instruction`` ("Developer instruction is not
    enabled for this model"), so the style guidance travels in the input using the
    documented notes/transcript structure. Only the transcript is spoken.
    """
    return f"### DIRECTOR'S NOTES\n{profile.instruction}\n\n#### TRANSCRIPT\n{text}"


class GeminiVoiceProvider:
    """Gemini audio adapter with lazy shared STT and TTS client access."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str = "",
        stt_model: str = "gemini-3.5-transcribe",
        tts_model: str = "",
        tts_voice: str = "",
        http_timeout_ms: int = 60_000,
        client_factory: Callable[[str], Any] | None = None,
        max_audio_bytes: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.stt_model = stt_model or "gemini-3.5-transcribe"
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self.http_timeout_ms = http_timeout_ms
        self._client_factory = client_factory
        self._client: Any | None = None
        self.max_audio_bytes = max_audio_bytes

    def _get_client(self) -> Any:
        if not self.api_key.strip():
            raise VoiceProviderUnavailable("Gemini API key is not configured")
        if self._client is None:
            factory = self._client_factory
            if factory is None:
                try:
                    from google import genai
                    from google.genai import types
                except ImportError as exc:
                    raise VoiceProviderUnavailable("google-genai is not installed") from exc

                def factory(key: str) -> Any:
                    return genai.Client(
                        api_key=key,
                        http_options=types.HttpOptions(timeout=self.http_timeout_ms),
                    )

            self._client = factory(self.api_key)
        return self._client

    def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        audio = validate_audio(audio, max_bytes=self.max_audio_bytes)
        client = self._get_client()
        suffix = MIME_SUFFIXES.get(audio.mime_type.split(";", 1)[0].lower(), ".audio")
        fd, temp_name = tempfile.mkstemp(prefix="edubourse-audio-", suffix=suffix)
        os.close(fd)
        uploaded_file = None
        started = time.perf_counter()
        try:
            Path(temp_name).write_bytes(audio.data)
            uploaded_file = client.files.upload(file=temp_name)
            interactions = getattr(client, "interactions", None)
            if interactions is not None and hasattr(interactions, "create"):
                response = interactions.create(
                    model=self.stt_model,
                    input=[
                        {
                            "type": "audio",
                            "uri": uploaded_file.uri,
                            "mime_type": audio.mime_type,
                        }
                    ],
                )
            else:
                response = client.models.generate_content(
                    model=self.stt_model,
                    contents=[uploaded_file],
                )
            text = _extract_transcript(response)
            if not text:
                raise TranscriptionFailed("Gemini returned an empty transcription")
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "gemini_stt_success provider=gemini model=%s mime_type=%s bytes=%d latency_ms=%s",
                self.stt_model,
                audio.mime_type,
                len(audio.data),
                latency_ms,
            )
            return TranscriptionResult(
                text=text,
                provider=self.provider_name,
                model=self.stt_model,
                confidence=None,
                duration_ms=audio.duration_ms,
                degraded=False,
                metadata={"mime_type": audio.mime_type, "latency_ms": latency_ms},
            )
        except (TranscriptionFailed, VoiceProviderUnavailable):
            raise
        except Exception as exc:
            category = _error_category(exc)
            logger.warning("gemini_stt_failure provider=gemini category=%s", category)
            raise VoiceProviderUnavailable("Gemini transcription failed") from exc
        finally:
            if uploaded_file is not None:
                self._delete_remote_file(client, uploaded_file)
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                logger.warning("gemini_stt_temp_cleanup_failed")

    @staticmethod
    def _delete_remote_file(client: Any, uploaded_file: Any) -> None:
        delete = getattr(client.files, "delete", None)
        name = getattr(uploaded_file, "name", None)
        if delete is None or not name:
            return
        try:
            delete(name=name)
        except Exception:
            logger.warning("gemini_stt_remote_cleanup_failed")

    def synthesize(self, text: str, *, language: str, script: str) -> SpeechSynthesisResult:
        if not isinstance(text, str) or not text.strip():
            raise TTSFailed("TTS input is empty")
        if not self.tts_model.strip() or not self.tts_voice.strip():
            raise VoiceProviderUnavailable("Gemini TTS configuration is incomplete")
        profile = _get_tts_profile(language, script)

        started = time.perf_counter()
        try:
            client = self._get_client()
            interactions = getattr(client, "interactions", None)
            create = getattr(interactions, "create", None)
            if create is None:
                raise VoiceProviderUnavailable("Gemini Interactions API is unavailable")
            response = create(
                model=self.tts_model,
                input=_tts_input(profile, text),
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"language": profile.speech_language, "voice": self.tts_voice}
                    ]
                },
                stream=True,
            )
            audio, mime_type, sample_rate, channels = _extract_audio_stream(response)
            duration_ms = None
            base_mime_type = mime_type.split(";", 1)[0].lower()
            if base_mime_type in {"audio/pcm", "audio/l16"} and sample_rate and channels:
                duration_ms = round(len(audio) / (sample_rate * channels * 2) * 1000)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "gemini_tts_success provider=gemini model=%s voice=%s chars=%d "
                "bytes=%d latency_ms=%s",
                self.tts_model,
                self.tts_voice,
                len(text),
                len(audio),
                latency_ms,
            )
            return SpeechSynthesisResult(
                audio=audio,
                mime_type=mime_type,
                provider=self.provider_name,
                model=self.tts_model,
                voice=self.tts_voice,
                sample_rate=sample_rate,
                channels=channels,
                sample_width_bytes=2 if base_mime_type in {"audio/pcm", "audio/l16"} else None,
                duration_ms=duration_ms,
            )
        except (TTSFailed, VoiceProviderUnavailable):
            raise
        except Exception as exc:
            logger.warning("gemini_tts_failure provider=gemini category=%s", _error_category(exc))
            raise TTSFailed("Gemini synthesis failed") from exc


class UnavailableGeminiVoiceProvider(GeminiVoiceProvider):
    """Explicit unavailable state used when no Gemini key is configured."""

    reason = "GEMINI_API_KEY is not configured"


def _error_category(error: Exception) -> str:
    status = getattr(error, "status_code", None)
    if status == 429 or "quota" in str(error).lower() or "rate" in str(error).lower():
        return "rate_limited"
    if status in {401, 403} or "auth" in str(error).lower():
        return "authentication"
    return "provider_unavailable"


def _extract_transcript(response: Any) -> str:
    """Extract only transcription text from the SDK's supported response shapes."""
    segments: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            transcription = getattr(part, "audio_transcription", None)
            text = str(getattr(transcription, "text", "") or "").strip()
            if text:
                segments.append(text)
    if segments:
        return " ".join(segments)

    output_text = str(getattr(response, "output_text", "") or "").strip()
    if output_text:
        return output_text

    return str(getattr(response, "text", "") or "").strip()


def _extract_audio(response: Any) -> tuple[bytes, str, int | None, int | None]:
    """Extract only the typed Interactions audio output, decoding data once."""
    audio_content = getattr(response, "output_audio", None)
    if audio_content is None:
        for step in getattr(response, "steps", []) or []:
            if getattr(step, "type", None) != "model_output":
                continue
            for content in getattr(step, "content", []) or []:
                if getattr(content, "type", None) == "audio":
                    audio_content = content
                    break
            if audio_content is not None:
                break
    if audio_content is None:
        raise TTSFailed("Gemini returned no audio")

    raw_data = getattr(audio_content, "data", None)
    if isinstance(raw_data, bytes):
        audio = raw_data
    elif isinstance(raw_data, str) and raw_data:
        try:
            audio = base64.b64decode(raw_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise TTSFailed("Gemini returned invalid audio data") from exc
    else:
        raise TTSFailed("Gemini returned empty audio")
    if not audio:
        raise TTSFailed("Gemini returned empty audio")

    mime_type = str(getattr(audio_content, "mime_type", None) or "audio/pcm")
    sample_rate = getattr(audio_content, "sample_rate", None)
    channels = getattr(audio_content, "channels", None)
    if mime_type.split(";", 1)[0].lower() in {"audio/pcm", "audio/l16"}:
        sample_rate = sample_rate or 24000
        channels = channels or 1
    return audio, mime_type, sample_rate, channels


def _extract_audio_stream(stream: Any) -> tuple[bytes, str, int | None, int | None]:
    """Collect ordered audio deltas from an Interactions TTS stream."""
    if not hasattr(stream, "__iter__"):
        return _extract_audio(stream)

    chunks: list[bytes] = []
    mime_type = "audio/pcm"
    sample_rate = 24000
    channels = 1
    try:
        for event in stream:
            if getattr(event, "event_type", None) != "step.delta":
                continue
            delta = getattr(event, "delta", None)
            if getattr(delta, "type", None) != "audio":
                continue
            raw_data = getattr(delta, "data", None)
            if isinstance(raw_data, bytes):
                chunk = raw_data
            elif isinstance(raw_data, str) and raw_data:
                try:
                    chunk = base64.b64decode(raw_data, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise TTSFailed("Gemini returned invalid audio data") from exc
            else:
                continue
            if chunk:
                chunks.append(chunk)
            mime_type = str(getattr(delta, "mime_type", None) or mime_type)
            sample_rate = getattr(delta, "sample_rate", None) or sample_rate
            channels = getattr(delta, "channels", None) or channels
    except (TTSFailed, VoiceProviderUnavailable):
        raise
    except Exception as exc:
        raise TTSFailed("Gemini TTS stream failed") from exc
    audio = b"".join(chunks)
    if not audio:
        raise TTSFailed("Gemini returned no audio chunks")
    return audio, mime_type, sample_rate, channels
