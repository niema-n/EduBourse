from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from anyio import CancelScope
from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect

from app.api.chat import get_chat_graph, process_text_message
from app.config import Settings, get_settings
from app.observability.context import bind_context, new_id
from app.observability.logging import emit
from app.observability.timing import elapsed_ms, start_timer
from app.schemas.chat import ChatRequest
from app.voice.debug_audio import analyze_pcm16, dump_turn_wav
from app.voice.errors import (
    AudioChunkTooLarge,
    BusinessPipelineFailed,
    BusyVoiceInput,
    InvalidAudio,
    InvalidVoiceSession,
    InvalidVoiceState,
    SessionTimeout,
    TranscriptionFailed,
    TranscriptionTimeout,
    TTSFailed,
    VoiceError,
)
from app.voice.providers.factory import create_live_provider, create_voice_provider
from app.voice.providers.live import LiveSpeechToTextProvider, receive_final_event

router = APIRouter(tags=["Voice"])

logger = logging.getLogger(__name__)

# Diagnostic only: number of live voice WebSockets currently open in this process.
_active_voice_sockets = 0


def _elapsed_ms(since: float) -> float:
    return round((time.monotonic() - since) * 1000, 1)


async def _log_turn_audio(
    pcm: bytes, *, request_id: str, socket_id: str, elapsed: float, dump_dir: str
) -> None:
    """Diagnostic only: measure (and optionally dump) the exact PCM of one turn.

    Never raises into the voice turn and never changes what is sent to STT.
    """
    try:
        metrics = analyze_pcm16(pcm)
        logger.info(
            "voice_ws_audio_metrics socket_id=%s request_id=%s elapsed_ms=%s audio_bytes=%d "
            "audio_duration_ms=%s pcm_rms=%s pcm_peak=%s zero_sample_ratio=%s "
            "classification=%s",
            socket_id,
            request_id,
            elapsed,
            metrics.audio_bytes,
            metrics.audio_duration_ms,
            metrics.pcm_rms,
            metrics.pcm_peak,
            metrics.zero_sample_ratio,
            metrics.classification,
        )
        if dump_dir.strip():
            path = await asyncio.to_thread(dump_turn_wav, dump_dir, request_id, pcm)
            logger.info("voice_ws_audio_dump request_id=%s path=%s", request_id, path)
    except Exception as exc:
        logger.warning(
            "voice_ws_audio_diagnostics_failed request_id=%s error_class=%s",
            request_id,
            type(exc).__name__,
        )

def get_live_stt_provider() -> LiveSpeechToTextProvider:
    return create_live_provider()


def get_voice_tts_provider():
    return create_voice_provider()


def _error_payload(
    error: VoiceError, request_id: str, *, fatal: bool, message: str | None = None
) -> dict[str, Any]:
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
        "message": message or messages.get(code, "Voice request failed."),
        "request_id": request_id,
        "fatal": fatal,
    }


def _busy_payload(request_id: str) -> dict[str, Any]:
    return _error_payload(BusyVoiceInput("busy"), request_id, fatal=False)


def _audio_bytes_per_second(sample_rate: int, channels: int, sample_width_bytes: int) -> int:
    if sample_rate <= 0 or channels <= 0 or sample_width_bytes <= 0:
        raise ValueError("audio metadata must contain positive values")
    return sample_rate * channels * sample_width_bytes


def _audio_duration_seconds(
    audio_bytes: int, sample_rate: int, channels: int, sample_width_bytes: int
) -> float:
    return audio_bytes / _audio_bytes_per_second(sample_rate, channels, sample_width_bytes)


def _audio_pacing_delay(
    bytes_sent: int, bytes_per_second: int, pace_started: float, now: float
) -> float:
    target_elapsed = bytes_sent / bytes_per_second
    return max(0.0, target_elapsed - (now - pace_started))


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
    indexing_tasks: list[asyncio.Task[None]] = []
    turn_generation = 0
    state = "NEW"
    session_id = None
    thread_id = None
    had_audio = False
    turn_started = False
    live_activity_open = False
    session_log_id = request_id
    turns = 0
    audio_chunks = 0
    audio_bytes = 0
    assistant_audio_chunks_sent = 0
    assistant_audio_bytes_sent = 0
    started = time.monotonic()
    # Diagnostic only: the exact PCM of the current turn, measured (and optionally
    # dumped) at audio.end. It is never altered or used to accept/reject a turn.
    turn_audio = bytearray()
    socket_id = uuid.uuid4().hex[:8]
    global _active_voice_sockets
    _active_voice_sockets += 1
    logger.info(
        "voice_ws_open socket_id=%s request_id=%s active_sockets=%d",
        socket_id,
        request_id,
        _active_voice_sockets,
    )

    async def send_error(
        error: VoiceError,
        current_request_id: str,
        *,
        fatal: bool,
        message: str | None = None,
    ) -> None:
        try:
            await _send(
                websocket,
                send_lock,
                _error_payload(error, current_request_id, fatal=fatal, message=message),
            )
        except Exception:
            pass

    async def begin_live_turn() -> None:
        """Open a Gemini Live activity, reopening the Live session once if it died.

        Gemini Live closes an idle session (close 1008) after roughly a minute,
        which the business pipeline and audio playback of the previous turn can
        easily exceed. No audio has been sent yet for this turn, so reconnecting
        loses nothing; a second failure is reported as before.
        """
        nonlocal live_session, turn_started, live_activity_open, turn_audio
        turn_audio = bytearray()
        logger.info(
            "voice_ws_recording_start socket_id=%s request_id=%s elapsed_ms=%s",
            socket_id,
            request_id,
            _elapsed_ms(started),
        )
        try:
            await live_session.start_turn()
        except TranscriptionFailed:
            logger.info("voice_ws_live_session_reopen session_log_id=%s", session_log_id)
            try:
                await live_session.close()
            except Exception:
                pass
            live_session = await live_provider.connect()
            await live_session.start_turn()
        turn_started = True
        live_activity_open = True

    async def finish_open_activity() -> None:
        nonlocal live_activity_open
        if not live_activity_open or live_session is None:
            return
        try:
            await live_session.finish_turn()
        except Exception as exc:
            logger.warning(
                "voice_ws_activity_end_cleanup_failed session_log_id=%s error_class=%s",
                session_log_id,
                type(exc).__name__,
            )
        finally:
            live_activity_open = False

    async def process_turn(current_request_id: str, generation: int, audio_end_at: float) -> None:
        nonlocal state, had_audio, request_id, turn_started, live_activity_open
        nonlocal assistant_audio_chunks_sent, assistant_audio_bytes_sent
        turn_started_at = time.monotonic()
        turn_trace_id = new_id()
        stt_started = start_timer()
        final_text = None
        latest_interim_text = None
        saw_input_transcription = False
        speech_end_at: float | None = None
        gemini_events = 0

        def owns_turn() -> bool:
            return generation == turn_generation

        try:
            remaining = settings.voice_ws_max_session_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise SessionTimeout("voice session timed out")
            await live_session.finish_turn()
            live_activity_open = False
            speech_end_at = time.monotonic()
            finalization_timeout = min(30, remaining)
            logger.info(
                "voice_ws_speech_end socket_id=%s request_id=%s elapsed_ms=%s "
                "finalization_timeout_s=%s",
                socket_id,
                current_request_id,
                _elapsed_ms(started),
                round(finalization_timeout, 1),
            )
            async for event in receive_final_event(live_session, finalization_timeout):
                if not owns_turn():
                    return
                gemini_events += 1
                if gemini_events == 1:
                    logger.info(
                        "voice_ws_gemini_first_event request_id=%s after_speech_end_ms=%s "
                        "kind=%s source=%s",
                        current_request_id,
                        _elapsed_ms(speech_end_at),
                        event.kind,
                        getattr(event, "source", ""),
                    )
                if getattr(event, "source", "") == "input_transcription":
                    saw_input_transcription = True
                if event.kind == "partial":
                    if latest_interim_text is None:
                        logger.info(
                            "voice_ws_first_interim request_id=%s after_speech_end_ms=%s "
                            "text_length=%d",
                            current_request_id,
                            _elapsed_ms(speech_end_at),
                            len(event.text),
                        )
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
                    logger.info(
                        "voice_ws_final_transcript request_id=%s after_speech_end_ms=%s "
                        "text_length=%d",
                        current_request_id,
                        _elapsed_ms(speech_end_at),
                        len(final_text),
                    )
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
                logger.info(
                    "voice_ws_gemini_stream_ended_without_final request_id=%s "
                    "after_speech_end_ms=%s gemini_events=%d",
                    current_request_id,
                    _elapsed_ms(speech_end_at),
                    gemini_events,
                )
                raise TranscriptionFailed("live transcription was empty")
            with bind_context(
                request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
            ):
                emit(
                    "voice.stt.completed",
                    duration_ms=elapsed_ms(stt_started),
                    audio_end_to_final_transcript_ms=_elapsed_ms(audio_end_at),
                    status="ok",
                )
            remaining = settings.voice_ws_max_session_seconds - (
                time.monotonic() - started
            )
            if remaining <= 0:
                raise SessionTimeout("voice session timed out")
            post_response_tasks = BackgroundTasks()
            try:
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    response = await asyncio.to_thread(
                        process_text_message,
                        ChatRequest(message=final_text, thread_id=thread_id),
                        graph,
                        apply_final_response_composer=True,
                        post_response_tasks=post_response_tasks,
                    )
            except Exception as exc:
                raise BusinessPipelineFailed("business pipeline failed") from exc
            # The connection owns enrichment independently of the cancellable
            # voice turn and drains it on close. It must not delay TTS.
            try:
                if not owns_turn():
                    return
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
                text_sent_at = time.monotonic()
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    emit("voice.text.sent", duration_ms=_elapsed_ms(audio_end_at))
            finally:
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    indexing_tasks.append(asyncio.create_task(post_response_tasks()))
            if not owns_turn():
                return
            state = "SPEAKING"
            try:
                tts_started = start_timer()
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    def synthesize_response():
                        emit(
                            "voice.tts.started",
                            delay_after_text_ms=_elapsed_ms(text_sent_at),
                        )
                        return tts_provider.synthesize(
                            response.answer,
                            language=response.language,
                            script=response.script,
                        )

                    synthesis = await asyncio.to_thread(synthesize_response)
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    emit(
                        "voice.tts.completed",
                        duration_ms=elapsed_ms(tts_started),
                        audio_end_to_tts_ready_ms=_elapsed_ms(audio_end_at),
                        status="ok",
                        language=response.language,
                        script=response.script,
                    )
            except Exception as exc:
                with bind_context(
                    request_id=current_request_id, trace_id=turn_trace_id, modality="voice"
                ):
                    emit(
                        "voice.tts.failed",
                        level=logging.ERROR,
                        duration_ms=elapsed_ms(tts_started),
                        error_type=type(exc).__name__,
                        stage="tts",
                    )
                raise TTSFailed("voice response audio failed") from exc
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
                delay = _audio_pacing_delay(
                    bytes_sent, bytes_per_second, pace_started, time.monotonic()
                )
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
            fatal = not isinstance(
                exc, (TTSFailed, TranscriptionFailed, TranscriptionTimeout, BusinessPipelineFailed)
            )
            code = getattr(exc, "code", "VOICE_PROVIDER_UNAVAILABLE")
            if code == "TRANSCRIPTION_TIMEOUT":
                # Diagnostics only: never log or forward the partial hypothesis itself.
                logger.warning(
                    "voice_ws_finalization_timeout request_id=%s "
                    "latest_interim_present=%s latest_interim_length=%d "
                    "saw_input_transcription=%s gemini_events=%d after_speech_end_ms=%s",
                    current_request_id,
                    latest_interim_text is not None,
                    len(latest_interim_text or ""),
                    saw_input_transcription,
                    gemini_events,
                    _elapsed_ms(speech_end_at) if speech_end_at is not None else None,
                )
            else:
                cause = exc.__cause__
                logger.warning(
                    "voice_ws_turn_error request_id=%s code=%s cause=%s gemini_events=%d "
                    "after_speech_end_ms=%s",
                    current_request_id,
                    code,
                    type(cause).__name__ if cause is not None else None,
                    gemini_events,
                    _elapsed_ms(speech_end_at) if speech_end_at is not None else None,
                )
            await send_error(exc, current_request_id, fatal=fatal)
        except Exception as exc:
            if not owns_turn():
                return
            state = "ERROR"
            had_audio = False
            turn_started = False
            logger.warning(
                "voice_ws_turn_error request_id=%s code=%s detail=%s",
                current_request_id,
                "BUSINESS_PIPELINE_ERROR",
                type(exc).__name__,
            )
            await send_error(
                BusinessPipelineFailed("turn failed"), current_request_id, fatal=True
            )
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

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
        connect_started = time.monotonic()
        live_session = await live_provider.connect()
        state = "READY"
        session_log_id = request_id
        logger.info(
            "voice_ws_session_start request_id=%s socket_id=%s gemini_connect_ms=%s "
            "elapsed_ms=%s active_sockets=%d",
            session_log_id,
            socket_id,
            _elapsed_ms(connect_started),
            _elapsed_ms(started),
            _active_voice_sockets,
        )
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
            packet_received_at = time.monotonic()
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
                    await begin_live_turn()
                await live_session.send_audio(audio)
                turn_audio.extend(audio)
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
                await finish_open_activity()
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
                    await begin_live_turn()
                    continue
                if state == "READY":
                    await begin_live_turn()
                    state = "RECEIVING_AUDIO"
                    had_audio = False
                    continue
                if state == "RECEIVING_AUDIO":
                    await send_error(
                        InvalidVoiceState("audio.start is already active"),
                        request_id,
                        fatal=False,
                    )
                    continue
                raise InvalidVoiceState("audio.start is not allowed in the current state")
            if busy:
                if event_type == "session.start":
                    await send_error(
                        InvalidVoiceState("session.start is not allowed while busy"),
                        request_id,
                        fatal=False,
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
            if state != "RECEIVING_AUDIO":
                raise InvalidVoiceState("audio.end requires audio chunks")
            if not had_audio:
                await finish_open_activity()
                state = "READY"
                turn_started = False
                await send_error(
                    InvalidAudio("no audio data was received"),
                    request_id,
                    fatal=False,
                    message="No audio data was received for the current utterance.",
                )
                continue
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
            await _log_turn_audio(
                bytes(turn_audio),
                request_id=request_id,
                socket_id=socket_id,
                elapsed=_elapsed_ms(started),
                dump_dir=getattr(settings, "voice_debug_dump_dir", "") or "",
            )
            turn_audio = bytearray()
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
            active_task = asyncio.create_task(
                process_turn(request_id, generation, packet_received_at)
            )
    except WebSocketDisconnect:
        return
    except TimeoutError:
        await send_error(
            SessionTimeout("voice session timed out"), request_id, fatal=True
        )
    except VoiceError as exc:
        await send_error(exc, request_id, fatal=True)
    finally:
        if active_task is not None and not active_task.done():
            active_task.cancel()
            await asyncio.gather(active_task, return_exceptions=True)
        # Barge-in, TTS failure and normal disconnect never cancel enrichment.
        # Shield the drain from the surrounding ASGI cancellation scope.
        with CancelScope(shield=True):
            await asyncio.gather(*indexing_tasks)
        if live_session is not None:
            await finish_open_activity()
            await live_session.close()
        if session_id is not None:
            logger.info(
                "voice_ws_session_end request_id=%s duration_ms=%s turns=%d",
                session_log_id,
                round((time.monotonic() - started) * 1000, 2),
                turns,
            )
        _active_voice_sockets -= 1
        logger.info(
            "voice_ws_close socket_id=%s request_id=%s elapsed_ms=%s active_sockets=%d",
            socket_id,
            session_log_id,
            _elapsed_ms(started),
            _active_voice_sockets,
        )
