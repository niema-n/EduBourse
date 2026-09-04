from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.voice.errors import TranscriptionFailed, TranscriptionTimeout, VoiceProviderUnavailable


@dataclass(frozen=True)
class LiveTranscriptEvent:
    kind: str
    text: str
    # Which Gemini field produced this event. Only "input_transcription" is
    # authoritative; "interim_input_transcription" carries cumulative hypotheses.
    source: str = ""


class LiveTranscriptionSession(Protocol):
    async def start_turn(self) -> None: ...

    async def send_audio(self, audio: bytes) -> None: ...

    async def finish_turn(self) -> None: ...

    def receive_events(self) -> AsyncIterator[LiveTranscriptEvent]: ...

    async def close(self) -> None: ...


class LiveSpeechToTextProvider(Protocol):
    async def connect(self) -> LiveTranscriptionSession: ...


class GeminiLiveSTTProvider:
    provider_name = "gemini-live"

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-3.5-transcribe-live",
        http_timeout_ms: int = 60_000,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.http_timeout_ms = http_timeout_ms
        self._client_factory = client_factory
        self._client: Any | None = None

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

    async def connect(self) -> GeminiLiveTranscriptionSession:
        client = self._get_client()
        try:
            from google.genai import types

            config = types.LiveConnectConfig(
                response_modalities=["TEXT"],
                input_audio_transcription=types.AudioTranscriptionConfig(
                    language_codes=[], mode="VERBATIM"
                ),
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(
                        disabled=True
                    )
                ),
            )
            context = client.aio.live.connect(model=self.model, config=config)
            session = await context.__aenter__()
            return GeminiLiveTranscriptionSession(context, session)
        except (VoiceProviderUnavailable, TranscriptionFailed):
            raise
        except Exception as exc:
            raise VoiceProviderUnavailable("Gemini Live connection failed") from exc


class GeminiLiveTranscriptionSession:
    def __init__(self, context: Any, session: Any) -> None:
        self._context = context
        self._session = session

    async def start_turn(self) -> None:
        try:
            from google.genai import types

            await self._session.send_realtime_input(activity_start=types.ActivityStart())
        except Exception as exc:
            raise TranscriptionFailed("Gemini Live turn start failed") from exc

    async def send_audio(self, audio: bytes) -> None:
        try:
            from google.genai import types

            await self._session.send_realtime_input(
                audio=types.Blob(data=audio, mime_type="audio/pcm;rate=16000")
            )
        except Exception as exc:
            raise TranscriptionFailed("Gemini Live audio send failed") from exc

    async def finish_turn(self) -> None:
        try:
            from google.genai import types

            await self._session.send_realtime_input(activity_end=types.ActivityEnd())
        except Exception as exc:
            raise TranscriptionFailed("Gemini Live turn completion failed") from exc

    async def receive_events(self) -> AsyncIterator[LiveTranscriptEvent]:
        try:
            async for message in self._session.receive():
                content = getattr(message, "server_content", None)
                if content is None:
                    continue
                interim = getattr(content, "interim_input_transcription", None)
                if interim is not None and getattr(interim, "text", None):
                    yield LiveTranscriptEvent(
                        "partial", interim.text, "interim_input_transcription"
                    )
                transcription = getattr(content, "input_transcription", None)
                if transcription is not None and getattr(transcription, "text", None):
                    yield LiveTranscriptEvent(
                        "final", transcription.text, "input_transcription"
                    )
        except (TranscriptionFailed, VoiceProviderUnavailable):
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise TranscriptionFailed("Gemini Live receive failed") from exc

    async def close(self) -> None:
        try:
            await self._context.__aexit__(None, None, None)
        except Exception:
            pass


async def receive_final_event(
    session: LiveTranscriptionSession, timeout_seconds: float
) -> AsyncIterator[LiveTranscriptEvent]:
    try:
        async with asyncio.timeout(timeout_seconds):
            async for event in session.receive_events():
                yield event
                if event.kind == "final":
                    return
    except TimeoutError as exc:
        raise TranscriptionTimeout("live transcription timed out") from exc
