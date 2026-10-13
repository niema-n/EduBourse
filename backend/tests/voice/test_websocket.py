from __future__ import annotations

import importlib.util
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import voice as voice_api
from app.graph.core import build_graph
from app.main import app
from app.voice.errors import (
    TranscriptionFailed,
    TranscriptionTimeout,
    TTSFailed,
    VoiceProviderUnavailable,
)
from app.voice.models import SpeechSynthesisResult
from app.voice.providers.live import GeminiLiveSTTProvider, GeminiLiveTranscriptionSession

_CLIENT_SPEC = importlib.util.spec_from_file_location(
    "test_voice_websocket_client",
    Path(__file__).parents[3] / "scripts" / "test_voice_websocket.py",
)
assert _CLIENT_SPEC and _CLIENT_SPEC.loader
_CLIENT_MODULE = importlib.util.module_from_spec(_CLIENT_SPEC)
_CLIENT_SPEC.loader.exec_module(_CLIENT_MODULE)
pcm_duration_seconds = _CLIENT_MODULE.pcm_duration_seconds


@pytest.fixture(autouse=True)
def disable_live_final_composer(monkeypatch):
    import app.api.chat as chat_api

    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: None)


@dataclass
class FakeLiveSession:
    events: list[object]
    sent_audio: list[bytes]
    finished: bool = False
    finished_turns: int = 0
    closed: bool = False
    started_turns: int = 0
    send_times: list[float] = field(default_factory=list)

    async def start_turn(self) -> None:
        self.started_turns += 1

    async def send_audio(self, audio: bytes) -> None:
        self.sent_audio.append(audio)
        self.send_times.append(time.monotonic())

    async def finish_turn(self) -> None:
        self.finished = True
        self.finished_turns += 1

    async def receive_events(self):
        for event in self.events:
            yield event

    async def close(self) -> None:
        self.closed = True


class FakeLiveProvider:
    def __init__(self, session: FakeLiveSession):
        self.session = session
        self.connected = False

    async def connect(self):
        self.connected = True
        return self.session


class FakeTTS:
    provider_name = "fake-tts"

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []

    def synthesize(self, text: str, *, language: str, script: str):
        self.calls.append((text, language, script))
        return SpeechSynthesisResult(
            audio=b"\x01\x00" * 4,
            mime_type="audio/l16",
            provider=self.provider_name,
            model="fake-model",
            voice="Kore",
            sample_rate=24000,
            channels=1,
            sample_width_bytes=2,
        )


class FakeSupervisor:
    def invoke_structured(self, request):
        return {"domain_status": "in_domain", "route": "pedagogie"}


def make_client(
    session, tts=None, *, max_chunk=65536, max_seconds=300, supervisor=None, debug_dump_dir=""
):
    tts = tts or FakeTTS()
    provider = FakeLiveProvider(session)
    graph = build_graph(supervisor_provider=supervisor or FakeSupervisor())
    app.dependency_overrides[voice_api.get_live_stt_provider] = lambda: provider
    app.dependency_overrides[voice_api.get_voice_tts_provider] = lambda: tts
    app.dependency_overrides[voice_api.get_chat_graph] = lambda: graph
    old_settings = voice_api.get_settings
    voice_api.get_settings = lambda: SimpleNamespace(
        voice_ws_max_chunk_bytes=max_chunk,
        voice_ws_output_chunk_bytes=min(4096, max_chunk),
        voice_ws_max_session_seconds=max_seconds,
        voice_debug_dump_dir=debug_dump_dir,
    )
    return TestClient(app), provider, tts, old_settings


def cleanup(old_settings):
    app.dependency_overrides.clear()
    voice_api.get_settings = old_settings


def start_message():
    return {
        "type": "session.start",
        "session_id": "session-1",
        "thread_id": "thread-1",
        "audio": {
            "mime_type": "audio/pcm",
            "sample_rate": 16000,
            "channels": 1,
            "sample_width_bytes": 2,
        },
    }


@pytest.mark.parametrize("tts_fails", [False, True])
def test_tts_and_audio_complete_without_waiting_for_semantic_indexing(monkeypatch, tts_fails):
    from app.api import chat

    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def index(thread_id, ids):
        entered.set()
        assert release.wait(5)
        finished.set()

    monkeypatch.setattr(chat, "get_conversation_history_store", lambda: SimpleNamespace(
        append_turn=lambda *args, **kwargs: [SimpleNamespace(id=1), SimpleNamespace(id=2)],
    ))
    monkeypatch.setattr(chat, "get_memory_runtime", lambda: SimpleNamespace(
        index_canonical_messages=index,
    ))
    session = FakeLiveSession([SimpleNamespace(kind="final", text="Une action ?")], [])

    class ObservedTTS(FakeTTS):
        def synthesize(self, text, *, language, script):
            result = super().synthesize(text, language=language, script=script)
            if tts_fails:
                raise TTSFailed("controlled test failure")
            return result

    client, _, tts, old_settings = make_client(session, tts=ObservedTTS())
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            while True:
                message = websocket.receive_json()
                if message["type"] == "response.text":
                    break
            assert message["status"] == "ok"
            assert entered.wait(2)
            messages = _finish_messages(websocket)
            expected = "error" if tts_fails else "response.complete"
            assert any(item["type"] == expected for item in messages)
            assert not release.is_set()
            assert not finished.is_set()
            assert tts.calls == [(message["answer"], message["language"], message["script"])]
            # Closing the socket must drain enrichment even after audio completes.
            timer = threading.Timer(0.1, release.set)
            timer.start()
        timer.join()
        assert finished.is_set()
    finally:
        release.set()
        cleanup(old_settings)


def test_live_websocket_full_turn_uses_final_transcript_and_safe_j4_answer():
    session = FakeLiveSession(
        events=[
            SimpleNamespace(kind="partial", text="C'est quoi"),
            SimpleNamespace(kind="partial", text="C'est quoi une action"),
            SimpleNamespace(kind="final", text="C'est quoi une action en Bourse ?"),
        ],
        sent_audio=[],
    )
    client, provider, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = []
            audio = b""
            while True:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    audio += message["bytes"]
                    continue
                payload = message["text"]
                messages.append(json.loads(payload))
                if messages[-1]["type"] == "response.complete":
                    break
        assert provider.connected is True
        assert session.started_turns == 1
        assert session.sent_audio == [b"\x00\x00"]
        assert session.finished is True
        assert session.closed is True
        assert [m["type"] for m in messages] == [
            "processing.started",
            "transcript.partial",
            "transcript.partial",
            "transcript.final",
            "response.text",
            "response.audio.start",
            "response.audio.end",
            "response.complete",
        ]
        assert messages[4]["answer"]
        assert audio == b"\x01\x00" * 4
        assert len(tts.calls) == 1
        assert tts.calls[0][0] == messages[4]["answer"]
    finally:
        cleanup(old_settings)


def test_live_websocket_sends_composed_answer_to_tts_and_response(monkeypatch):
    import app.api.chat as chat_api

    class FakeComposer:
        validation_attempts = []

        def compose(self, *args, **kwargs):
            return "FINAL_AZURE_TEXT"

    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="What is a stock?")],
        sent_audio=[],
    )
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: FakeComposer())
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        response = next(message for message in messages if message["type"] == "response.text")
        assert response["answer"] == "FINAL_AZURE_TEXT"
        assert tts.calls[0][0] == "FINAL_AZURE_TEXT"
        assert response["answer"] == tts.calls[0][0]
    finally:
        cleanup(old_settings)


def test_live_websocket_rejects_audio_before_start_without_connecting():
    session = FakeLiveSession([], [])
    client, provider, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_bytes(b"\x00\x00")
            error = websocket.receive_json()
            assert error["code"] == "INVALID_SESSION"
        assert provider.connected is False
    finally:
        cleanup(old_settings)


def test_live_websocket_rejects_invalid_audio_metadata():
    session = FakeLiveSession([], [])
    client, provider, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            message = start_message()
            message["audio"]["sample_rate"] = 44100
            websocket.send_json(message)
            assert websocket.receive_json()["code"] == "INVALID_AUDIO_FORMAT"
        assert provider.connected is False
    finally:
        cleanup(old_settings)


def test_live_websocket_rejects_oversized_chunk():
    session = FakeLiveSession([], [])
    client, provider, _, old_settings = make_client(session, max_chunk=2)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_bytes(b"123")
            assert websocket.receive_json()["code"] == "AUDIO_CHUNK_TOO_LARGE"
        assert provider.connected is True
        assert session.sent_audio == []
    finally:
        cleanup(old_settings)


def test_live_websocket_rejects_malformed_event_json():
    session = FakeLiveSession([], [])
    client, provider, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_text("not-json")
            assert websocket.receive_json()["code"] == "INVALID_STATE"
        assert provider.connected is True
    finally:
        cleanup(old_settings)


def test_voice_error_payloads_expose_fatality_context():
    busy = voice_api._busy_payload("request-1")
    assert busy["fatal"] is False
    fatal = voice_api._error_payload(
        VoiceProviderUnavailable("private"), "request-2", fatal=True
    )
    assert fatal["fatal"] is True
    assert "private" not in fatal["message"]


def test_audio_pacing_uses_cumulative_target():
    rate = voice_api._audio_bytes_per_second(24000, 1, 2)
    assert voice_api._audio_pacing_delay(4096, rate, 0.0, 0.0) == pytest.approx(
        4096 / 48000
    )
    assert voice_api._audio_pacing_delay(48000, rate, 0.0, 0.5) == pytest.approx(0.5)
    assert voice_api._audio_duration_seconds(48000, 24000, 1, 2) == pytest.approx(1.0)
    assert voice_api._audio_duration_seconds(209280, 24000, 1, 2) == pytest.approx(4.36)


def test_duplicate_audio_start_is_non_fatal_and_socket_reusable():
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "audio.start"})
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.start"})
            duplicate = websocket.receive_json()
            assert duplicate["code"] == "INVALID_STATE"
            assert duplicate["fatal"] is False
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert messages[-1]["type"] == "response.complete"
        assert session.started_turns == 1
        assert session.finished_turns == 1
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


@dataclass
class ExpiringLiveSession(FakeLiveSession):
    """Gemini Live closes idle sessions (1008): start_turn then fails."""

    expired: bool = False

    async def start_turn(self) -> None:
        if self.expired:
            raise TranscriptionFailed("Gemini Live turn start failed")
        await super().start_turn()


class SequenceLiveProvider:
    def __init__(self, sessions):
        self.sessions = list(sessions)
        self.connections = 0

    async def connect(self):
        self.connections += 1
        return self.sessions.pop(0)


@pytest.mark.parametrize("second_turn_opener", ["audio.start", "binary"])
def test_idle_expired_live_session_is_reopened_once_for_next_turn(second_turn_opener):
    final = [SimpleNamespace(kind="final", text="What is a stock?")]
    first = ExpiringLiveSession(list(final), [])
    fresh = ExpiringLiveSession(list(final), [])
    client, _, tts, old_settings = make_client(first)
    provider = SequenceLiveProvider([first, fresh])
    app.dependency_overrides[voice_api.get_live_stt_provider] = lambda: provider
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            assert websocket.receive_json()["type"] == "session.ready"
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            assert _finish_messages(websocket)[-1]["type"] == "response.complete"

            first.expired = True  # idle time between turns closed the Live session
            if second_turn_opener == "audio.start":
                websocket.send_json({"type": "audio.start"})
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert messages[-1]["type"] == "response.complete"
        assert not any(message.get("type") == "error" for message in messages)
        assert provider.connections == 2
        assert first.closed is True
        assert fresh.started_turns == 1
        assert fresh.sent_audio == [b"\x01\x00"]
        assert len(tts.calls) == 2
    finally:
        cleanup(old_settings)


def test_live_session_that_cannot_be_reopened_still_fails_closed():
    final = [SimpleNamespace(kind="final", text="What is a stock?")]
    first = ExpiringLiveSession(list(final), [])
    dead = ExpiringLiveSession(list(final), [], expired=True)
    client, _, _, old_settings = make_client(first)
    provider = SequenceLiveProvider([first, dead])
    app.dependency_overrides[voice_api.get_live_stt_provider] = lambda: provider
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            _finish_messages(websocket)
            first.expired = True
            websocket.send_json({"type": "audio.start"})
            error = websocket.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "TRANSCRIPTION_FAILED"
        assert error["fatal"] is True
        assert provider.connections == 2
    finally:
        cleanup(old_settings)


def test_empty_utterance_is_non_fatal_balanced_and_reusable():
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "audio.start"})
            websocket.send_json({"type": "audio.end"})
            empty = websocket.receive_json()
            assert empty["code"] == "INVALID_AUDIO_FORMAT"
            assert empty["fatal"] is False
            websocket.send_json({"type": "audio.start"})
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert messages[-1]["type"] == "response.complete"
        assert session.started_turns == 2
        assert session.finished_turns == 2
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


def test_live_websocket_ignores_model_text_and_requires_final_for_j4():
    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="What is a stock?")], sent_audio=[]
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            seen = []
            while True:
                message = websocket.receive()
                if message.get("text"):
                    payload = json.loads(message["text"])
                    seen.append(payload)
                    if payload["type"] == "response.complete":
                        break
        texts = [payload.get("text", "") for payload in seen]
        assert "You should buy XYZ." not in texts
        assert tts.calls[0][0] == next(p["answer"] for p in seen if p["type"] == "response.text")
    finally:
        cleanup(old_settings)


def test_live_websocket_keeps_cumulative_partials_out_of_j4():
    final_text = "C'est quoi une action en bourse ?"
    session = FakeLiveSession(
        [
            SimpleNamespace(kind="partial", text="C'est quoi une"),
            SimpleNamespace(kind="partial", text="C'est quoi une action"),
            SimpleNamespace(kind="partial", text="C'est quoi une action en"),
            SimpleNamespace(kind="partial", text=final_text),
            SimpleNamespace(kind="final", text=final_text),
        ],
        [],
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        partials = [
            message["text"]
            for message in messages
            if message["type"] == "transcript.partial"
        ]
        assert partials == [
            "C'est quoi une",
            "C'est quoi une action",
            "C'est quoi une action en",
            final_text,
        ]
        assert tts.calls[0][0]
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


def test_live_websocket_uses_authoritative_final_over_last_partial():
    session = FakeLiveSession(
        [
            SimpleNamespace(kind="partial", text="C'est quoi une action en bourse"),
            SimpleNamespace(kind="final", text="C'est quoi une action en Bourse ?"),
        ],
        [],
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert any(
            message.get("type") == "transcript.final"
            and message["text"] == "C'est quoi une action en Bourse ?"
            for message in messages
        )
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


def test_real_observed_live_sequence_commits_only_input_transcription():
    final_text = "C'est quoi une action en bourse ?"
    session = FakeLiveSession(
        [
            SimpleNamespace(kind="partial", text="C'est quoi une"),
            SimpleNamespace(kind="partial", text="C'est quoi une action"),
            SimpleNamespace(kind="partial", text="C'est quoi une action en"),
            SimpleNamespace(kind="partial", text=final_text),
            SimpleNamespace(kind="final", text=final_text),
        ],
        [],
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert [m["type"] for m in messages].count("transcript.partial") == 4
        assert [m["type"] for m in messages].count("transcript.final") == 1
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


def test_pcm_timing_calculation_uses_canonical_format():
    assert pcm_duration_seconds(3200) == 0.1
    assert pcm_duration_seconds(85120) == 2.66


def test_live_websocket_session_close_cleans_up():
    session = FakeLiveSession([], [])
    client, provider, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "session.close"})
        assert provider.connected is True
        assert session.closed is True
    finally:
        cleanup(old_settings)


def test_live_websocket_session_close_balances_open_activity():
    session = FakeLiveSession([], [])
    client, _, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "audio.start"})
            websocket.send_json({"type": "session.close"})
        assert session.finished_turns == 1
        assert session.closed is True
    finally:
        cleanup(old_settings)


def test_live_websocket_disconnect_balances_open_activity():
    session = FakeLiveSession([], [])
    client, _, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "audio.start"})
        assert session.finished_turns == 1
        assert session.closed is True
    finally:
        cleanup(old_settings)


def test_gemini_live_provider_uses_transcription_only_config():
    class Context:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class Live:
        def __init__(self):
            self.model = None
            self.config = None

        def connect(self, *, model, config):
            self.model = model
            self.config = config
            return Context()

    live = Live()
    client = SimpleNamespace(aio=SimpleNamespace(live=live))
    provider = GeminiLiveSTTProvider(
        api_key="test-key", client_factory=lambda key: client
    )

    session = __import__("asyncio").run(provider.connect())

    assert isinstance(session, GeminiLiveTranscriptionSession)
    assert live.model == "gemini-3.5-transcribe-live"
    assert live.config.response_modalities == ["TEXT"]
    assert live.config.input_audio_transcription.language_codes == ["fr", "en", "ar"]
    assert live.config.input_audio_transcription.mode == "VERBATIM"
    assert live.config.output_audio_transcription is None
    assert live.config.realtime_input_config.automatic_activity_detection.disabled is True
    __import__("asyncio").run(session.close())


def test_gemini_live_session_sends_canonical_pcm_and_ignores_model_text():
    class Session:
        def __init__(self):
            self.audio = None
            self.activity_started = 0
            self.activity_ended = 0
            self.stream_ended = False

        async def send_realtime_input(self, **kwargs):
            if "audio" in kwargs:
                self.audio = kwargs["audio"]
            if "activity_start" in kwargs:
                self.activity_started += 1
            if "activity_end" in kwargs:
                self.activity_ended += 1
            if kwargs.get("audio_stream_end"):
                self.stream_ended = True

        async def receive(self):
            yield SimpleNamespace(
                server_content=SimpleNamespace(
                    model_turn=SimpleNamespace(parts=[SimpleNamespace(text="buy XYZ")]),
                    interim_input_transcription=SimpleNamespace(
                        text="C'est quoi", language_code="fr"
                    ),
                    input_transcription=None,
                )
            )
            yield SimpleNamespace(
                server_content=SimpleNamespace(
                    model_turn=None,
                    interim_input_transcription=None,
                    input_transcription=SimpleNamespace(
                        text="C'est quoi une action ?", finished=True, language_code="fr"
                    ),
                )
            )

    import asyncio

    raw_session = Session()
    session = GeminiLiveTranscriptionSession(SimpleNamespace(), raw_session)
    asyncio.run(session.start_turn())
    asyncio.run(session.send_audio(b"\x00\x00"))
    asyncio.run(session.finish_turn())
    events = asyncio.run(_collect_events(session))

    assert raw_session.audio.mime_type == "audio/pcm;rate=16000"
    assert raw_session.audio.data == b"\x00\x00"
    assert raw_session.activity_started == 1
    assert raw_session.activity_ended == 1
    assert raw_session.stream_ended is False
    assert [(event.kind, event.text) for event in events] == [
        ("partial", "C'est quoi"),
        ("final", "C'est quoi une action ?"),
    ]
    assert [event.source for event in events] == [
        "interim_input_transcription",
        "input_transcription",
    ]
    assert [event.language_code for event in events] == ["fr", "fr"]


async def _collect_events(session):
    return [event async for event in session.receive_events()]


@pytest.mark.parametrize("finished", [None, False, True])
def test_input_transcription_is_final_regardless_of_finished(finished):
    class Session:
        async def receive(self):
            yield SimpleNamespace(
                server_content=SimpleNamespace(
                    interim_input_transcription=None,
                    input_transcription=SimpleNamespace(
                        text="authoritative", finished=finished, language_code="ar"
                    ),
                )
            )

    events = __import__("asyncio").run(
        _collect_events(GeminiLiveTranscriptionSession(SimpleNamespace(), Session()))
    )
    assert [(event.kind, event.source) for event in events] == [
        ("final", "input_transcription")
    ]
    assert events[0].language_code == "ar"


@pytest.mark.parametrize("finished", [None, False, True])
def test_interim_transcription_is_always_partial(finished):
    class Session:
        async def receive(self):
            yield SimpleNamespace(
                server_content=SimpleNamespace(
                    interim_input_transcription=SimpleNamespace(
                        text="hypothesis", finished=finished, language_code="ar"
                    ),
                    input_transcription=None,
                )
            )

    events = __import__("asyncio").run(
        _collect_events(GeminiLiveTranscriptionSession(SimpleNamespace(), Session()))
    )
    assert [(event.kind, event.source) for event in events] == [
        ("partial", "interim_input_transcription")
    ]
    assert events[0].language_code == "ar"


class BlockingTTS(FakeTTS):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def synthesize(self, text: str, *, language: str, script: str):
        self.entered.set()
        self.release.wait(timeout=5)
        return super().synthesize(text, language=language, script=script)


def _finish_messages(websocket):
    messages = []
    while True:
        message = websocket.receive()
        if message.get("bytes") is not None:
            continue
        payload = json.loads(message["text"])
        messages.append(payload)
        if payload["type"] in {"response.complete", "error"}:
            return messages


def _receive_busy(websocket, expected: int):
    messages = []
    while sum(message.get("code") == "BUSY" for message in messages) < expected:
        message = websocket.receive_json()
        messages.append(message)
    return messages


def test_live_websocket_drops_processing_audio_and_next_turn_is_clean():
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    tts = BlockingTTS()
    client, provider, _, old_settings = make_client(session, tts)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            assert websocket.receive_json()["type"] == "processing.started"
            assert tts.entered.wait(timeout=5)
            websocket.send_json(start_message())
            session_start_error = None
            while session_start_error is None:
                candidate = websocket.receive_json()
                if candidate.get("code") == "INVALID_STATE":
                    session_start_error = candidate
            assert session_start_error["code"] == "INVALID_STATE"
            assert session_start_error["fatal"] is False
            for _ in range(5):
                websocket.send_bytes(b"busy")
            busy = _receive_busy(websocket, 5)
            assert sum(message.get("code") == "BUSY" for message in busy) == 5
            assert all(message["fatal"] is False for message in busy)
            assert session.sent_audio == [b"\x00\x00"]
            tts.release.set()
            messages = _finish_messages(websocket)
            assert messages[-1]["type"] == "response.complete"
            websocket.send_bytes(b"\x02\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert session.started_turns == 2
        assert session.sent_audio == [b"\x00\x00", b"\x02\x00"]
    finally:
        cleanup(old_settings)


def test_live_websocket_drops_speaking_audio():
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    tts = BlockingTTS()
    client, _, _, old_settings = make_client(session, tts)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            assert websocket.receive_json()["type"] == "processing.started"
            assert tts.entered.wait(timeout=5)
            websocket.send_bytes(b"speaking")
            busy = _receive_busy(websocket, 1)
            assert busy[-1]["code"] == "BUSY"
            assert session.sent_audio == [b"\x00\x00"]
            tts.release.set()
            _finish_messages(websocket)
    finally:
        cleanup(old_settings)


def test_live_websocket_reports_provider_failure():
    class FailingProvider:
        async def connect(self):
            raise VoiceProviderUnavailable("unavailable")

    session = FakeLiveSession([], [])
    client, _, _, old_settings = make_client(session)
    app.dependency_overrides[voice_api.get_live_stt_provider] = lambda: FailingProvider()
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            error = websocket.receive_json()
            assert error["code"] == "VOICE_PROVIDER_UNAVAILABLE"
            assert error["fatal"] is True
    finally:
        cleanup(old_settings)


def test_live_websocket_reports_tts_failure_without_detail_leak():
    class FailingTTS(FakeTTS):
        def synthesize(self, text: str, *, language: str, script: str):
            raise TTSFailed("provider detail must stay private")

    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    client, _, _, old_settings = make_client(session, FailingTTS())
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert messages[-1]["code"] == "TTS_FAILED"
        assert "provider detail" not in messages[-1]["message"]
    finally:
        cleanup(old_settings)


def test_tts_failure_preserves_text_and_allows_next_turn():
    class FailOnceTTS(FakeTTS):
        def __init__(self):
            super().__init__()
            self.failed = False

        def synthesize(self, text: str, *, language: str, script: str):
            if not self.failed:
                self.failed = True
                raise TTSFailed("private provider detail")
            return super().synthesize(text, language=language, script=script)

    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    tts = FailOnceTTS()
    client, _, _, old_settings = make_client(session, tts)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            first = _finish_messages(websocket)
            assert any(message["type"] == "response.text" for message in first)
            assert first[-1]["code"] == "TTS_FAILED"
            assert first[-1]["fatal"] is False
            assert not any(message["type"] == "response.audio.start" for message in first)
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            second = _finish_messages(websocket)
        assert second[-1]["type"] == "response.complete"
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


class FailOnceReceiveSession(FakeLiveSession):
    def __init__(self, events, sent_audio, error):
        super().__init__(events, sent_audio)
        self.error = error
        self.failed = False

    async def receive_events(self):
        if not self.failed:
            self.failed = True
            raise self.error
        async for event in super().receive_events():
            yield event


def test_unpaced_inbound_audio_forwards_all_chunks_without_playback_delay():
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    chunks = [bytes([index % 256]) * 3200 for index in range(30)]
    client, _, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_json({"type": "audio.start"})
            started = time.monotonic()
            for chunk in chunks:
                websocket.send_bytes(chunk)
            forwarded = time.monotonic()
            websocket.send_json({"type": "audio.end"})
            _finish_messages(websocket)
        assert session.sent_audio == chunks
        assert len(session.send_times) == 30
        assert session.send_times[-1] - session.send_times[0] < 0.5
        assert forwarded - started < 0.5
    finally:
        cleanup(old_settings)


def test_unexpected_turn_exception_is_fatal_and_terminates_session():
    class MalformedTTS(FakeTTS):
        def synthesize(self, text: str, *, language: str, script: str):
            self.calls.append((text, language, script))
            return SpeechSynthesisResult(
                audio=None,
                mime_type="audio/l16",
                provider=self.provider_name,
                model="fake-model",
                voice="Kore",
                sample_rate=24000,
                channels=1,
                sample_width_bytes=2,
            )

    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    client, _, _, old_settings = make_client(session, MalformedTTS())
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = []
            while True:
                message = websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("text"):
                    payload = json.loads(message["text"])
                    messages.append(payload)
                    if payload["type"] == "error":
                        assert payload["code"] == "BUSINESS_PIPELINE_ERROR"
                        assert payload["fatal"] is True
                        break
            assert messages[-1]["fatal"] is True
            assert websocket.receive()["type"] == "websocket.close"
        assert session.closed is True
    finally:
        cleanup(old_settings)


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (TranscriptionFailed("turn failed"), "TRANSCRIPTION_FAILED"),
        (TranscriptionTimeout("turn timed out"), "TRANSCRIPTION_TIMEOUT"),
    ],
)
def test_turn_transcription_errors_are_non_fatal_and_reusable(error, expected_code):
    session = FailOnceReceiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], [], error
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            first = _finish_messages(websocket)
            assert first[-1]["code"] == expected_code
            assert first[-1]["fatal"] is False
            assert tts.calls == []
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            second = _finish_messages(websocket)
        assert second[-1]["type"] == "response.complete"
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


def test_business_pipeline_error_is_non_fatal_and_reusable(monkeypatch):
    session = FakeLiveSession(
        [SimpleNamespace(kind="final", text="What is a stock?")], []
    )
    original = voice_api.process_text_message
    failed = False

    def fail_once(payload, graph, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("private business failure")
        return original(payload, graph, **kwargs)

    monkeypatch.setattr(voice_api, "process_text_message", fail_once)
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            first = _finish_messages(websocket)
            assert first[-1]["code"] == "BUSINESS_PIPELINE_ERROR"
            assert first[-1]["fatal"] is False
            assert tts.calls == []
            websocket.send_bytes(b"\x01\x00")
            websocket.send_json({"type": "audio.end"})
            second = _finish_messages(websocket)
        assert second[-1]["type"] == "response.complete"
        assert len(tts.calls) == 1
    finally:
        cleanup(old_settings)


class RoutedSupervisor:
    def __init__(self, route: str):
        self.route = route
        self.calls = 0

    def invoke_structured(self, request):
        self.calls += 1
        domain = "out_of_domain" if self.route == "out_of_domain" else "in_domain"
        return {"domain_status": domain, "route": self.route}


class SlowLiveSession(FakeLiveSession):
    def __init__(self, events, sent_audio, delay: float):
        super().__init__(events, sent_audio)
        self.delay = delay

    async def receive_events(self):
        import asyncio

        await asyncio.sleep(self.delay)
        for event in self.events:
            yield event


def _run_single_turn(session, *, transcript_events=None, **kwargs):
    """Drive one complete utterance and return the collected JSON events."""
    if transcript_events is not None:
        session.events = transcript_events
    client, provider, tts, old_settings = make_client(session, **kwargs)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        return messages, tts, provider
    finally:
        cleanup(old_settings)


def test_live_websocket_sends_one_activity_start_for_many_audio_chunks():
    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="C'est quoi une action en bourse ?")],
        sent_audio=[],
    )
    client, _, _, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            for _ in range(27):
                websocket.send_bytes(b"\x00" * 640)
            websocket.send_json({"type": "audio.end"})
            _finish_messages(websocket)
    finally:
        cleanup(old_settings)

    assert len(session.sent_audio) == 27
    assert session.started_turns == 1
    assert session.finished is True


def test_live_websocket_sensitive_transcript_is_blocked_by_j4():
    supervisor = RoutedSupervisor("pedagogie")
    session = FakeLiveSession(events=[], sent_audio=[])
    messages, tts, _ = _run_single_turn(
        session,
        transcript_events=[
            SimpleNamespace(
                kind="final",
                text="Quelle action dois-je acheter demain pour gagner rapidement ?",
            )
        ],
        supervisor=supervisor,
    )

    response = next(m for m in messages if m["type"] == "response.text")
    assert response["route"] == "securite"
    assert response["blocked"] is True
    assert response["status"] == "blocked"
    assert supervisor.calls == 0
    assert tts.calls[0][0] == response["answer"]


def test_live_websocket_out_of_domain_is_not_answered_as_pedagogie():
    session = FakeLiveSession(events=[], sent_audio=[])
    messages, _, _ = _run_single_turn(
        session,
        transcript_events=[SimpleNamespace(kind="final", text="What is the capital of Japan?")],
        supervisor=RoutedSupervisor("out_of_domain"),
    )

    response = next(m for m in messages if m["type"] == "response.text")
    assert response["route"] == "out_of_domain"
    assert response["status"] == "ok"


def test_live_websocket_preserves_darija_language_and_script():
    for transcript, language, script in (
        ("chno hiya action f lborsa?", "ary", "latin"),
        ("\u0634\u0646\u0648 \u0647\u064a \u0627\u0644\u0623\u0643\u0633\u064a\u0648\u0646"
         " \u0641\u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f", "ary", "arabic"),
    ):
        session = FakeLiveSession(events=[], sent_audio=[])
        messages, tts, _ = _run_single_turn(
            session, transcript_events=[SimpleNamespace(kind="final", text=transcript)]
        )
        response = next(m for m in messages if m["type"] == "response.text")
        assert response["language"] == language, transcript
        assert response["script"] == script, transcript
        assert tts.calls[0][1:] == (language, script)


def test_live_websocket_finalization_timeout_never_promotes_a_partial():
    session = SlowLiveSession(
        events=[SimpleNamespace(kind="final", text="never delivered")],
        sent_audio=[],
        delay=30,
    )
    client, _, tts, old_settings = make_client(session, max_seconds=1)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
    finally:
        cleanup(old_settings)

    error = messages[-1]
    assert error["type"] == "error"
    assert error["code"] in {"TRANSCRIPTION_TIMEOUT", "SESSION_TIMEOUT"}
    assert error["fatal"] is False
    assert tts.calls == []
    assert session.finished_turns == 1
    assert session.closed is True


def test_live_websocket_disconnect_during_processing_runs_no_business_turn():
    session = SlowLiveSession(
        events=[SimpleNamespace(kind="final", text="C'est quoi une action ?")],
        sent_audio=[],
        delay=1.5,
    )
    client, _, tts, old_settings = make_client(session)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            websocket.receive_json()
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            assert websocket.receive_json()["type"] == "processing.started"
    finally:
        cleanup(old_settings)

    assert session.closed is True
    assert tts.calls == []


class BargeLiveSession(FakeLiveSession):
    def __init__(self, turn_events):
        super().__init__(events=[], sent_audio=[])
        self.turn_events = turn_events
        self.current_turn = -1

    async def start_turn(self):
        self.started_turns += 1
        self.current_turn += 1

    async def receive_events(self):
        for event in self.turn_events[self.current_turn]:
            yield event


class LargeTTS(FakeTTS):
    def synthesize(self, text: str, *, language: str, script: str):
        self.calls.append((text, language, script))
        return SpeechSynthesisResult(
            audio=b"\x01\x00" * 20,
            mime_type="audio/l16",
            provider=self.provider_name,
            model="fake-model",
            voice="Kore",
            sample_rate=24000,
            channels=1,
            sample_width_bytes=2,
        )


def test_live_websocket_barge_in_cancels_old_output_and_reuses_live_session(monkeypatch):
    session = BargeLiveSession(
        [
            [SimpleNamespace(kind="final", text="What is a stock?")],
            [SimpleNamespace(kind="final", text="How do I save money?")],
        ]
    )
    tts = LargeTTS()
    release_output = threading.Event()
    original_send_bytes = voice_api._send_bytes
    sends = 0

    async def paused_send_bytes(websocket, lock, audio):
        nonlocal sends
        sends += 1
        if sends == 3:
            await __import__("asyncio").to_thread(release_output.wait, 5)
        await original_send_bytes(websocket, lock, audio)

    monkeypatch.setattr(voice_api, "_send_bytes", paused_send_bytes)
    client, provider, _, old_settings = make_client(session, tts, max_chunk=4)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            ready = websocket.receive_json()
            old_request_id = ready["request_id"]
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            while websocket.receive_json()["type"] != "response.audio.start":
                pass
            websocket.send_json({"type": "audio.start"})
            while True:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    continue
                interrupted = json.loads(message["text"])
                if interrupted["type"] == "response.interrupted":
                    break
            assert interrupted == {
                "type": "response.interrupted",
                "request_id": old_request_id,
                "reason": "barge_in",
            }
            release_output.set()
            websocket.send_bytes(b"\x02\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        new_response = next(m for m in messages if m["type"] == "response.text")
        assert new_response["request_id"] != old_request_id
        assert new_response["thread_id"] == "thread-1"
        assert [m["type"] for m in messages].count("response.complete") == 1
        assert session.started_turns == 2
        assert provider.session is session
        assert len(tts.calls) == 2
    finally:
        cleanup(old_settings)


def test_audio_timing_helpers_use_output_metadata():
    assert voice_api._audio_bytes_per_second(24000, 1, 2) == 48000
    assert voice_api._audio_duration_seconds(4096, 24000, 1, 2) == pytest.approx(
        0.0853333333
    )
    assert voice_api._audio_duration_seconds(209280, 24000, 1, 2) == pytest.approx(4.36)


def test_live_websocket_realistic_barge_in_after_first_frame(monkeypatch):
    session = BargeLiveSession(
        [
            [SimpleNamespace(kind="final", text="What is a stock?")],
            [SimpleNamespace(kind="final", text="How do I save money?")],
        ]
    )
    tts = LargeTTS()
    client, provider, _, old_settings = make_client(session, tts, max_chunk=4)
    try:
        with client.websocket_connect("/api/v1/voice/live") as websocket:
            websocket.send_json(start_message())
            ready = websocket.receive_json()
            old_request_id = ready["request_id"]
            websocket.send_bytes(b"\x00\x00")
            websocket.send_json({"type": "audio.end"})
            first_audio_seen = False
            interrupted = None
            while interrupted is None:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    if not first_audio_seen:
                        first_audio_seen = True
                        websocket.send_json({"type": "audio.start"})
                    continue
                payload = json.loads(message["text"])
                if payload["type"] == "response.interrupted":
                    interrupted = payload
            assert first_audio_seen is True
            assert interrupted == {
                "type": "response.interrupted",
                "request_id": old_request_id,
                "reason": "barge_in",
            }
            websocket.send_bytes(b"\x02\x00")
            websocket.send_json({"type": "audio.end"})
            messages = _finish_messages(websocket)
        assert provider.session is session
        assert session.started_turns == 2
        assert [m["type"] for m in messages].count("response.complete") == 1
    finally:
        cleanup(old_settings)


def _run_turn_with_chunks(client, chunks):
    with client.websocket_connect("/api/v1/voice/live") as websocket:
        websocket.send_json(start_message())
        assert websocket.receive_json()["type"] == "session.ready"
        websocket.send_json({"type": "audio.start"})
        for chunk in chunks:
            websocket.send_bytes(chunk)
        websocket.send_json({"type": "audio.end"})
        types = []
        while True:
            message = websocket.receive()
            if message.get("bytes") is not None:
                continue
            types.append(json.loads(message["text"])["type"])
            if types[-1] in {"response.complete", "error"}:
                return types


def test_debug_dump_writes_exact_received_pcm_without_changing_the_turn(tmp_path):
    import wave

    chunks = [b"\x10\x00\xf0\xff" * 400, b"\x00\x40\x00\xc0" * 400]
    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="C'est quoi une action ?")], sent_audio=[]
    )
    client, _, tts, old_settings = make_client(session, debug_dump_dir=str(tmp_path))
    try:
        types = _run_turn_with_chunks(client, chunks)
    finally:
        cleanup(old_settings)
    assert types[-1] == "response.complete"
    assert session.sent_audio == chunks  # STT receives exactly the same bytes
    assert len(tts.calls) == 1
    dumps = list(tmp_path.glob("*_input.wav"))
    assert len(dumps) == 1
    with wave.open(str(dumps[0]), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 16000)
        assert wav.readframes(wav.getnframes()) == b"".join(chunks)


def test_debug_dump_disabled_by_default_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="C'est quoi une action ?")], sent_audio=[]
    )
    client, _, _, old_settings = make_client(session)
    try:
        types = _run_turn_with_chunks(client, [b"\x01\x00" * 800])
    finally:
        cleanup(old_settings)
    assert types[-1] == "response.complete"
    assert list(tmp_path.rglob("*.wav")) == []


def test_active_socket_counter_returns_to_baseline():
    baseline = voice_api._active_voice_sockets
    session = FakeLiveSession(
        events=[SimpleNamespace(kind="final", text="C'est quoi une action ?")], sent_audio=[]
    )
    client, _, _, old_settings = make_client(session)
    try:
        _run_turn_with_chunks(client, [b"\x01\x00" * 800])
    finally:
        cleanup(old_settings)
    assert voice_api._active_voice_sockets == baseline
