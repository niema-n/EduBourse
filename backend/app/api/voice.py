from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.chat import get_chat_graph, process_text_message
from app.config import Settings, get_settings
from app.schemas.chat import ChatRequest
from app.voice.errors import (
    AudioChunkTooLarge,
    BusinessPipelineFailed,
    BusyVoiceInput,
    InvalidAudio,
    InvalidVoiceSession,
    InvalidVoiceState,
    SessionTimeout,
    TranscriptionFailed,
    TTSFailed,
    VoiceError,
)
from app.voice.providers.factory import create_live_provider, create_voice_provider
from app.voice.providers.live import LiveSpeechToTextProvider, receive_final_event

router = APIRouter(tags=["Voice"])

logger = logging.getLogger(__name__)


def get_live_stt_provider() -> LiveSpeechToTextProvider:
    return create_live_provider()


def get_voice_tts_provider():
    return create_voice_provider()


def _error_payload(error: VoiceError, request_id: str) -> dict[str, str]:
    messages = {
        "INVALID_SESSION": "Invalid voice session.",
        "INVALID_STATE": "The voice session is not ready for this event.",
        "INVALID_AUDIO_FORMAT": "Only 16-bit mono PCM audio at 16000 Hz is supported.",
        "AUDIO_CHUNK_TOO_LARGE": "The audio chunk is too large.",
        "TRANSCRIPTION_TIMEOUT": "Audio transcription timed out.",
        "TRANSCRIPTION_FAILED": "Unable to transcribe audio.",
        "VOICE_PROVIDER_UNAVAILABLE": "Voice provider unavailable.",
        "TTS_FAILED": "Unable to synthesize the response.",
        "SESSION_TIMEOUT": "Voice session timed out.",
        "BUSINESS_PIPELINE_ERROR": "Unable to process the voice request.",
        "BUSY": "The assistant is still processing the previous utterance.",
    }
    code = getattr(error, "code", "VOICE_PROVIDER_UNAVAILABLE")
    if code == "INVALID_AUDIO":
        code = "INVALID_AUDIO_FORMAT"
    return {
        "type": "error",
        "code": code,
        "message": messages.get(code, "Voice request failed."),
        "request_id": request_id,
    }


def _busy_payload(request_id: str) -> dict[str, str]:
    return _error_payload(BusyVoiceInput("busy"), request_id)


def _audio_bytes_per_second(sample_rate: int, channels: int, sample_width_bytes: int) -> int:
    if sample_rate <= 0 or channels <= 0 or sample_width_bytes <= 0:
        raise ValueError("audio metadata must contain positive values")
    return sample_rate * channels * sample_width_bytes


def _audio_duration_seconds(
    audio_bytes: int, sample_rate: int, channels: int, sample_width_bytes: int
) -> float:
    return audio_bytes / _audio_bytes_per_second(sample_rate, channels, sample_width_bytes)


def _validate_start(message: dict[str, Any]) -> tuple[str, str]:
    if message.get("type") != "session.start":
        raise InvalidVoiceSession("session.start is required")
    session_id = message.get("session_id")
    thread_id = message.get("thread_id")
    audio = message.get("audio")
    if not isinstance(session_id, str) or not session_id.strip():
        raise InvalidVoiceSession("session_id is required")
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise InvalidVoiceSession("thread_id is required")
    if not isinstance(audio, dict):
        raise InvalidAudio("audio metadata is required")
    if (
        audio.get("mime_type") != "audio/pcm"
        or audio.get("sample_rate") != 16000
        or audio.get("channels") != 1
        or audio.get("sample_width_bytes") != 2
    ):
        raise InvalidAudio("only canonical PCM audio is supported")
    return session_id.strip(), thread_id.strip()


async def _send(websocket: WebSocket, lock: asyncio.Lock, payload: dict[str, Any]) -> None:
    async with lock:
        await websocket.send_json(payload)


async def _send_bytes(websocket: WebSocket, lock: asyncio.Lock, audio: bytes) -> None:
    async with lock:
        await websocket.send_bytes(audio)


@router.websocket("/voice/live")
async def live_voice(
    websocket: WebSocket,
    live_provider: LiveSpeechToTextProvider = Depends(get_live_stt_provider),  # noqa: B008
    tts_provider=Depends(get_voice_tts_provider),  # noqa: B008
    graph=Depends(get_chat_graph),  # noqa: B008
) -> None:
    await websocket.accept()
    settings: Settings = get_settings()
    send_lock = asyncio.Lock()
    request_id = str(uuid.uuid4())
    live_session = None
    active_task: asyncio.Task[None] | None = None
    turn_generation = 0
    state = "NEW"
    session_id = None
    thread_id = None
    had_audio = False
    turn_started = False
    session_log_id = request_id
    turns = 0
    audio_chunks = 0
    audio_bytes = 0
    assistant_audio_chunks_sent = 0
    assistant_audio_bytes_sent = 0
    started = time.monotonic()

    async def send_error(error: VoiceError, current_request_id: str) -> None:
        try:
            await _send(websocket, send_lock, _error_payload(error, current_request_id))
        except Exception:
            pass

    async def process_turn(current_request_id: str, generation: int) -> None:
        nonlocal state, had_audio, request_id, turn_started
        nonlocal assistant_audio_chunks_sent, assistant_audio_bytes_sent
        turn_started_at = time.monotonic()
        final_text = None
        latest_interim_text = None
        saw_input_transcription = False

        def owns_turn() -> bool:
            return generation == turn_generation

        try:
            remaining = settings.voice_ws_max_session_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise SessionTimeout("voice session timed out")
            await live_session.finish_turn()
            async for event in receive_final_event(live_session, min(30, remaining)):
                if not owns_turn():
                    return
                if getattr(event, "source", "") == "input_transcription":
                    saw_input_transcription = True
                if event.kind == "partial":
                    latest_interim_text = event.text
                    await _send(
                        websocket,
                        send_lock,
                        {
                            "type": "transcript.partial",
                            "text": latest_interim_text,
                            "request_id": current_request_id,
                        },
                    )
                elif event.kind == "final" and event.text.strip():
                    final_text = event.text.strip()
                    await _send(
                        websocket,
                        send_lock,
                        {
                            "type": "transcript.final",
                            "text": final_text,
                            "request_id": current_request_id,
                        },
                    )
            if not final_text:
                raise TranscriptionFailed("live transcription was empty")
            remaining = settings.voice_ws_max_session_seconds - (
                time.monotonic() - started
            )
            if remaining <= 0:
                raise SessionTimeout("voice session timed out")
            try:
                response = await asyncio.to_thread(
                    process_text_message,
                    ChatRequest(message=final_text, thread_id=thread_id),
                    graph,
                )
            except Exception as exc:
                raise BusinessPipelineFailed("business pipeline failed") from exc
            if not owns_turn():
                return
            state = "SPEAKING"
            await _send(
                websocket,
                send_lock,
                {
                    "type": "response.text",
                    "request_id": current_request_id,
                    "thread_id": thread_id,
                    **response.model_dump(),
                },
            )
            synthesis = await asyncio.to_thread(
                tts_provider.synthesize,
                response.answer,
                language=response.language,
                script=response.script,
            )
            if not owns_turn():
                return
            try:
                bytes_per_second = _audio_bytes_per_second(
                    synthesis.sample_rate,
                    synthesis.channels,
                    synthesis.sample_width_bytes,
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise TTSFailed("invalid synthesized audio metadata") from exc
            output_chunk_bytes = settings.voice_ws_output_chunk_bytes
            if output_chunk_bytes <= 0 or output_chunk_bytes > settings.voice_ws_max_chunk_bytes:
                raise TTSFailed("invalid output audio chunk configuration")
            await _send(
                websocket,
                send_lock,
                {
                    "type": "response.audio.start",
                    "request_id": current_request_id,
                    "mime_type": synthesis.mime_type,
                    "sample_rate": synthesis.sample_rate,
                    "channels": synthesis.channels,
                    "sample_width_bytes": synthesis.sample_width_bytes,
                },
            )
            pace_started = time.monotonic()
            bytes_sent = 0
            assistant_audio_chunks_sent = 0
            assistant_audio_bytes_sent = 0
            for offset in range(0, len(synthesis.audio), output_chunk_bytes):
                if not owns_turn():
                    return
                chunk = synthesis.audio[offset : offset + output_chunk_bytes]
                await _send_bytes(
                    websocket,
                    send_lock,
                    chunk,
                )
                bytes_sent += len(chunk)
                assistant_audio_chunks_sent += 1
                assistant_audio_bytes_sent += len(chunk)
                delay = bytes_sent / bytes_per_second - (time.monotonic() - pace_started)
                if delay > 0:
                    await asyncio.sleep(delay)
                if not owns_turn():
                    return
            if not owns_turn():
                return
            await _send(
                websocket,
                send_lock,
                {"type": "response.audio.end", "request_id": current_request_id},
            )
            if not owns_turn():
                return
            await _send(
                websocket,
                send_lock,
                {
                    "type": "response.complete",
                    "request_id": current_request_id,
                    "thread_id": thread_id,
                },
            )
            if not owns_turn():
                return
            state = "READY"
            had_audio = False
            turn_started = False
            request_id = str(uuid.uuid4())
            logger.info(
                "voice_ws_turn_complete request_id=%s duration_ms=%s route=%s "
                "blocked=%s status=%s",
                current_request_id,
                round((time.monotonic() - turn_started_at) * 1000, 2),
                response.route,
                response.blocked,
                response.status,
            )
        except asyncio.CancelledError:
            raise
        except VoiceError as exc:
            if not owns_turn():
                return
            state = "READY"
            had_audio = False
            turn_started = False
            code = getattr(exc, "code", "VOICE_PROVIDER_UNAVAILABLE")
            if code == "TRANSCRIPTION_TIMEOUT":
                # Diagnostics only: never log or forward the partial hypothesis itself.
                logger.warning(
                    "voice_ws_finalization_timeout request_id=%s "
                    "latest_interim_present=%s latest_interim_length=%d "
                    "saw_input_transcription=%s",
                    current_request_id,
                    latest_interim_text is not None,
                    len(latest_interim_text or ""),
                    saw_input_transcription,
                )
            else:
                logger.warning(
                    "voice_ws_turn_error request_id=%s code=%s", current_request_id, code
                )
            await send_error(exc, current_request_id)
        except Exception as exc:
            if not owns_turn():
                return
            state = "READY"
            had_audio = False
            turn_started = False
            logger.warning(
                "voice_ws_turn_error request_id=%s code=%s detail=%s",
                current_request_id,
                "BUSINESS_PIPELINE_ERROR",
                type(exc).__name__,
            )
            await send_error(BusinessPipelineFailed("turn failed"), current_request_id)

    try:
        first_packet = await asyncio.wait_for(websocket.receive(), timeout=10)
        if first_packet.get("bytes") is not None or first_packet.get("text") is None:
            raise InvalidVoiceSession("session.start must be JSON")
        try:
            first = json.loads(first_packet["text"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidVoiceSession("session.start must be valid JSON") from exc
        if not isinstance(first, dict):
            raise InvalidVoiceSession("session.start must be a JSON object")
        session_id, thread_id = _validate_start(first)
        live_session = await live_provider.connect()
        state = "READY"
        session_log_id = request_id
        logger.info("voice_ws_session_start request_id=%s", session_log_id)
        await _send(
            websocket,
            send_lock,
            {
                "type": "session.ready",
                "session_id": session_id,
                "thread_id": thread_id,
                "request_id": request_id,
            },
        )
        while True:
            remaining = settings.voice_ws_max_session_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise SessionTimeout("voice session timed out")
            packet = await asyncio.wait_for(websocket.receive(), timeout=remaining)
            if packet.get("type") == "websocket.disconnect":
                return
            busy = state in {"PROCESSING", "SPEAKING"}
            if packet.get("bytes") is not None:
                if busy:
                    logger.info(
                        "voice_ws_busy_input request_id=%s state=%s kind=audio bytes=%d",
                        request_id,
                        state,
                        len(packet["bytes"]),
                    )
                    await _send(websocket, send_lock, _busy_payload(request_id))
                    continue
                if state not in {"READY", "RECEIVING_AUDIO"}:
                    raise InvalidVoiceState("audio is not accepted in the current state")
                audio = packet["bytes"]
                if len(audio) > settings.voice_ws_max_chunk_bytes:
                    raise AudioChunkTooLarge("audio chunk exceeds limit")
                if not turn_started:
                    await live_session.start_turn()
                    turn_started = True
                await live_session.send_audio(audio)
                had_audio = True
                audio_chunks += 1
                audio_bytes += len(audio)
                state = "RECEIVING_AUDIO"
                continue
            if packet.get("text") is None:
                raise InvalidVoiceState("unsupported websocket frame")
            try:
                message = json.loads(packet["text"])
            except json.JSONDecodeError as exc:
                raise InvalidVoiceState("voice event must be valid JSON") from exc
            if not isinstance(message, dict):
                raise InvalidVoiceState("voice event must be a JSON object")
            event_type = message.get("type")
            if event_type == "session.close":
                if active_task is not None:
                    active_task.cancel()
                    await asyncio.gather(active_task, return_exceptions=True)
                state = "CLOSED"
                return
            if event_type == "audio.start":
                if state == "PROCESSING":
                    await _send(websocket, send_lock, _busy_payload(request_id))
                    continue
                if state == "SPEAKING":
                    old_request_id = request_id
                    turn_generation += 1
                    if active_task is not None and not active_task.done():
                        active_task.cancel()
                        await asyncio.gather(active_task, return_exceptions=True)
                    active_task = None
                    request_id = str(uuid.uuid4())
                    state = "RECEIVING_AUDIO"
                    had_audio = False
                    logger.info(
                        "voice_ws_barge_in session_log_id=%s old_request_id=%s "
                        "new_generation=%s state=%s old_audio_chunks_sent=%s "
                        "old_audio_bytes_sent=%s",
                        session_log_id,
                        old_request_id,
                        turn_generation,
                        "SPEAKING",
                        assistant_audio_chunks_sent,
                        assistant_audio_bytes_sent,
                    )
                    await _send(
                        websocket,
                        send_lock,
                        {
                            "type": "response.interrupted",
                            "request_id": old_request_id,
                            "reason": "barge_in",
                        },
                    )
                    await live_session.start_turn()
                    turn_started = True
                    continue
                if state == "READY":
                    await live_session.start_turn()
                    state = "RECEIVING_AUDIO"
                    had_audio = False
                    turn_started = True
                    continue
                raise InvalidVoiceState("audio.start is not allowed in the current state")
            if busy:
                if event_type == "session.start":
                    await send_error(
                        InvalidVoiceState("session.start is not allowed while busy"),
                        request_id,
                    )
                else:
                    logger.info(
                        "voice_ws_busy_input request_id=%s state=%s kind=event",
                        request_id,
                        state,
                    )
                    await _send(websocket, send_lock, _busy_payload(request_id))
                continue
            if event_type != "audio.end":
                raise InvalidVoiceState("unsupported voice event")
            if state != "RECEIVING_AUDIO" or not had_audio:
                raise InvalidVoiceState("audio.end requires audio chunks")
            state = "PROCESSING"
            turn_generation += 1
            generation = turn_generation
            turns += 1
            logger.info(
                "voice_ws_turn_start request_id=%s audio_chunks=%d audio_bytes=%d",
                request_id,
                audio_chunks,
                audio_bytes,
            )
            audio_chunks = 0
            audio_bytes = 0
            await _send(
                websocket,
                send_lock,
                {
                    "type": "processing.started",
                    "request_id": request_id,
                    "thread_id": thread_id,
                },
            )
            active_task = asyncio.create_task(process_turn(request_id, generation))
    except WebSocketDisconnect:
        return
    except TimeoutError:
        await send_error(SessionTimeout("voice session timed out"), request_id)
    except VoiceError as exc:
        await send_error(exc, request_id)
    finally:
        if active_task is not None and not active_task.done():
            active_task.cancel()
            await asyncio.gather(active_task, return_exceptions=True)
        if live_session is not None:
            await live_session.close()
        if session_id is not None:
            logger.info(
                "voice_ws_session_end request_id=%s duration_ms=%s turns=%d",
                session_log_id,
                round((time.monotonic() - started) * 1000, 2),
                turns,
            )
