import base64
import wave
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.api.chat import process_text_message
from app.config import Settings
from app.graph.core import build_graph
from app.schemas.chat import ChatResponse
from app.voice.audio import validate_audio
from app.voice.errors import InvalidAudio, TranscriptionFailed, TTSFailed, VoiceProviderUnavailable
from app.voice.models import AudioInput, SpeechSynthesisResult, TranscriptionResult
from app.voice.providers.factory import create_voice_provider
from app.voice.providers.gemini import (
    GeminiVoiceProvider,
    UnavailableGeminiVoiceProvider,
    _extract_audio,
    _extract_audio_stream,
    _extract_transcript,
)
from app.voice.service import VoiceService
from app.voice.wav import write_pcm_wav


@dataclass
class FakeSTT:
    text: str
    provider_name: str = "fake-stt"

    def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        assert audio.data
        return TranscriptionResult(text=self.text, provider=self.provider_name)


@dataclass
class FakeTTS:
    calls: list[tuple[str, str, str]]
    provider_name: str = "fake-tts"

    def synthesize(self, text: str, *, language: str, script: str) -> SpeechSynthesisResult:
        self.calls.append((text, language, script))
        return SpeechSynthesisResult(
            audio=b"audio", mime_type="audio/wav", provider=self.provider_name
        )


def make_service(transcript: str, tts: FakeTTS | None = None) -> tuple[VoiceService, FakeTTS]:
    tts = tts or FakeTTS([])
    graph = build_graph(supervisor_provider=FakeSupervisor())

    def text_pipeline(payload):
        return process_text_message(payload, graph)

    return VoiceService(FakeSTT(transcript), tts, text_pipeline), tts


class FakeSupervisor:
    def invoke_structured(self, request: object) -> object:
        return {"domain_status": "in_domain", "route": "pedagogie"}


@pytest.mark.parametrize(
    ("transcript", "language", "script"),
    [
        ("C'est quoi une action en Bourse ?", "fr", "latin"),
        ("What is a stock?", "en", "latin"),
        ("ما هو السهم؟", "ar", "arabic"),
        ("chno hiya action f lborsa?", "ary", "latin"),
        ("شنو هي الأكسيون فالبورصة؟", "ary", "arabic"),
    ],
)
def test_fake_stt_uses_real_j4_pipeline_and_final_metadata(transcript, language, script):
    service, tts = make_service(transcript)

    result = service.process(
        AudioInput(data=b"audio", mime_type="audio/webm"),
        session_id="voice-session",
        thread_id="j4-thread",
    )

    assert result.text_response.language == language
    assert result.text_response.script == script
    assert tts.calls == [(result.text_response.answer, language, script)]
    assert result.synthesis.audio == b"audio"
    assert result.session.thread_id == "j4-thread"


def test_process_to_text_reuses_j4_and_does_not_call_tts():
    service, tts = make_service("What is a stock?")

    result = service.process_to_text(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id="voice-session",
        thread_id="j4-thread",
    )

    assert result.transcript == "What is a stock?"
    assert result.language == "en"
    assert result.script == "latin"
    assert result.answer
    assert result.stt_provider == "fake-stt"
    assert tts.calls == []


def test_voice_does_not_call_final_response_composer_or_send_its_output(monkeypatch):
    import app.api.chat as chat_api

    composer = type(
        "FakeComposer",
        (),
        {
            "calls": 0,
            "compose": lambda self, *args, **kwargs: setattr(self, "calls", self.calls + 1)
            or "AZURE_VOICE_FINAL",
        },
    )()
    monkeypatch.setattr(chat_api, "get_final_response_composer", lambda: composer)

    service, tts = make_service("What is a stock?")
    result = service.process(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id="voice-composer-isolation",
        thread_id="voice-composer-isolation",
    )

    assert composer.calls == 0
    assert "AZURE_VOICE_FINAL" not in result.text_response.answer
    assert "AZURE_VOICE_FINAL" not in tts.calls[0][0]


def test_voice_turns_preserve_thread_and_isolate_other_thread():
    provider = FakeSupervisor()
    graph = build_graph(supervisor_provider=provider)

    def pipeline(payload):
        return process_text_message(payload, graph)

    service = VoiceService(FakeSTT("I want a quiz"), FakeTTS([]), pipeline)
    first = service.process_to_text(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id="session-a",
        thread_id="thread-a",
    )
    second = service.process_to_text(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id="session-a",
        thread_id="thread-a",
    )
    other = service.process_to_text(
        AudioInput(data=b"audio", mime_type="audio/wav"),
        session_id="session-b",
        thread_id="thread-b",
    )

    assert first.thread_id == second.thread_id == "thread-a"
    assert other.thread_id == "thread-b"
    assert graph.get_state({"configurable": {"thread_id": "thread-a"}}).values
    assert graph.get_state({"configurable": {"thread_id": "thread-b"}}).values


def test_security_reuses_j4_and_tts_receives_only_safe_refusal():
    service, tts = make_service("Quelle action dois-je acheter demain pour gagner rapidement ?")

    result = service.process(
        AudioInput(data=b"audio", mime_type="audio/webm"),
        session_id="secure-session",
        thread_id="secure-thread",
    )

    assert result.text_response.blocked is True
    assert result.text_response.route == "securite"
    assert len(tts.calls) == 1
    assert tts.calls[0][0] == result.text_response.answer
    assert "business_answer" not in tts.calls[0][0]


def test_missing_gemini_key_returns_controlled_unavailable_provider():
    provider = create_voice_provider(Settings(gemini_api_key=""))

    assert isinstance(provider, UnavailableGeminiVoiceProvider)
    with pytest.raises(VoiceProviderUnavailable):
        provider.transcribe(AudioInput(data=b"audio", mime_type="audio/webm"))


def test_stt_failure_does_not_invoke_text_pipeline():
    class BrokenSTT:
        provider_name = "broken"

        def transcribe(self, audio):
            raise RuntimeError("no transcript")

    calls = 0

    def pipeline(payload: object) -> ChatResponse:
        nonlocal calls
        calls += 1
        raise AssertionError("pipeline must not run")

    service = VoiceService(BrokenSTT(), FakeTTS([]), pipeline)
    with pytest.raises(TranscriptionFailed):
        service.process(
            AudioInput(data=b"audio", mime_type="audio/webm"),
            session_id="session",
            thread_id="thread",
        )
    assert calls == 0


def test_tts_failure_is_controlled():
    class BrokenTTS:
        provider_name = "broken"

        def synthesize(self, text, *, language, script):
            raise RuntimeError("no audio")

    service, _ = make_service("What is a stock?")
    service.tts_provider = BrokenTTS()

    with pytest.raises(TTSFailed):
        service.process(
            AudioInput(data=b"audio", mime_type="audio/webm"),
            session_id="session",
            thread_id="thread",
        )


@pytest.mark.parametrize(
    ("audio", "error_type"),
    [
        (AudioInput(data=b"", mime_type="audio/wav"), InvalidAudio),
        (AudioInput(data=b"x", mime_type="text/plain"), InvalidAudio),
    ],
)
def test_voice_service_preserves_invalid_audio(audio, error_type):
    service = VoiceService(FakeSTT("unused"), FakeTTS([]), lambda payload: None)

    with pytest.raises(error_type):
        service.process(audio, session_id="session", thread_id="thread")


@pytest.mark.parametrize("error_type", [VoiceProviderUnavailable, TranscriptionFailed])
def test_voice_service_preserves_known_stt_errors(error_type):
    class TypedFailure:
        def transcribe(self, audio):
            raise error_type("typed failure")

    service = VoiceService(TypedFailure(), FakeTTS([]), lambda payload: None)

    with pytest.raises(error_type):
        service.process(
            AudioInput(data=b"audio", mime_type="audio/wav"),
            session_id="session",
            thread_id="thread",
        )


def test_voice_service_maps_unexpected_stt_error():
    class UnexpectedFailure:
        def transcribe(self, audio):
            raise RuntimeError("internal detail")

    service = VoiceService(UnexpectedFailure(), FakeTTS([]), lambda payload: None)

    with pytest.raises(TranscriptionFailed, match="voice transcription failed"):
        service.process(
            AudioInput(data=b"audio", mime_type="audio/wav"),
            session_id="session",
            thread_id="thread",
        )


def test_audio_size_boundaries():
    assert validate_audio(AudioInput(data=b"x", mime_type="audio/wav"), max_bytes=16)
    assert validate_audio(AudioInput(data=b"x" * 16, mime_type="audio/wav"), max_bytes=16)
    with pytest.raises(InvalidAudio):
        validate_audio(AudioInput(data=b"x" * 17, mime_type="audio/wav"), max_bytes=16)


def test_gemini_provider_uploads_audio_uses_model_and_cleans_remote_file():
    class Uploaded:
        name = "files/test-audio"

    class Files:
        def __init__(self):
            self.uploaded_path = None
            self.deleted_name = None

        def upload(self, *, file):
            self.uploaded_path = file
            assert Path(file).suffix == ".wav"
            return Uploaded()

        def delete(self, *, name):
            self.deleted_name = name

    class Models:
        def __init__(self):
            self.model = None
            self.contents = None

        def generate_content(self, *, model, contents):
            self.model = model
            self.contents = contents
            return type("Response", (), {"text": "transcript"})()

    class Client:
        def __init__(self):
            self.files = Files()
            self.models = Models()

    client = Client()
    provider = GeminiVoiceProvider(
        api_key="test-gemini-key",
        stt_model="gemini-3.5-transcribe",
        client_factory=lambda key: client,
    )

    result = provider.transcribe(AudioInput(data=b"wav", mime_type="audio/wav"))

    assert result.text == "transcript"
    assert result.model == "gemini-3.5-transcribe"
    assert client.models.model == "gemini-3.5-transcribe"
    assert client.files.deleted_name == "files/test-audio"
    assert not Path(client.files.uploaded_path).exists()


def test_gemini_provider_empty_response_is_controlled():
    class Client:
        class files:
            @staticmethod
            def upload(*, file):
                return object()

        class models:
            @staticmethod
            def generate_content(*, model, contents):
                return type("Response", (), {"text": "  "})()

    provider = GeminiVoiceProvider(api_key="test-gemini-key", client_factory=lambda key: Client())
    with pytest.raises(TranscriptionFailed):
        provider.transcribe(AudioInput(data=b"wav", mime_type="audio/wav"))


def test_extract_transcript_from_response_text():
    assert _extract_transcript(SimpleNamespace(text="response transcript")) == "response transcript"


def test_extract_transcript_from_audio_transcription_parts():
    response = SimpleNamespace(
        text="",
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(audio_transcription=SimpleNamespace(text="first segment")),
                        SimpleNamespace(audio_transcription=SimpleNamespace(text="second segment")),
                    ]
                )
            )
        ],
    )
    assert _extract_transcript(response) == "first segment second segment"


def test_extract_transcript_prefers_interaction_output_text():
    response = SimpleNamespace(output_text="interaction transcript", text="other text")
    assert _extract_transcript(response) == "interaction transcript"


def test_extract_transcript_prefers_explicit_audio_parts_over_unrelated_text():
    response = SimpleNamespace(
        text="unrelated generated text",
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            audio_transcription=SimpleNamespace(text="actual speech")
                        )
                    ]
                )
            )
        ],
    )
    assert _extract_transcript(response) == "actual speech"


def test_extract_transcript_empty_is_empty():
    assert _extract_transcript(SimpleNamespace(text="", candidates=[])) == ""


def test_gemini_provider_uses_interactions_api_when_available():
    class Uploaded:
        name = "files/audio"
        uri = "https://example.invalid/audio"
        mime_type = "audio/wav"

    class Files:
        def upload(self, *, file):
            return Uploaded()

        def delete(self, *, name):
            pass

    class Interactions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(output_text="interaction transcript")

    class Client:
        def __init__(self):
            self.files = Files()
            self.interactions = Interactions()

    client = Client()
    provider = GeminiVoiceProvider(
        api_key="test-gemini-key", client_factory=lambda key: client
    )
    result = provider.transcribe(AudioInput(data=b"wav", mime_type="audio/wav"))

    assert result.text == "interaction transcript"
    assert client.interactions.kwargs["model"] == "gemini-3.5-transcribe"
    assert client.interactions.kwargs["input"][0]["mime_type"] == "audio/wav"


def test_gemini_tts_uses_interactions_audio_contract_and_pcm_metadata():
    class Interactions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                output_audio=SimpleNamespace(
                    type="audio",
                    data=b"pcm-bytes",
                    mime_type="audio/pcm",
                    sample_rate=24000,
                    channels=1,
                )
            )

    client = SimpleNamespace(interactions=Interactions())
    provider = GeminiVoiceProvider(
        api_key="test-gemini-key",
        tts_model="gemini-3.1-flash-tts-preview",
        tts_voice="Kore",
        client_factory=lambda key: client,
    )

    result = provider.synthesize("final safe answer", language="fr", script="latin")

    assert result.audio == b"pcm-bytes"
    assert result.mime_type == "audio/pcm"
    assert result.model == "gemini-3.1-flash-tts-preview"
    assert result.voice == "Kore"
    assert result.sample_rate == 24000
    assert result.channels == 1
    assert result.sample_width_bytes == 2
    assert client.interactions.kwargs == {
        "model": "gemini-3.1-flash-tts-preview",
        "input": (
            "### DIRECTOR'S NOTES\n"
            "Speak naturally in clear contemporary French. Use a warm, professional "
            "educational tone and a moderate conversational pace. Use natural French "
            "pronunciation and prosody. Read the supplied transcript faithfully. Do not "
            "translate, summarize, paraphrase, add, or remove any content."
            "\n\n#### TRANSCRIPT\nfinal safe answer"
        ),
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": [{"language": "French", "voice": "Kore"}]
        },
        "stream": True,
    }


def test_gemini_tts_decodes_base64_audio_once():
    encoded = base64.b64encode(b"encoded-audio").decode("ascii")
    response = SimpleNamespace(
        output_audio=SimpleNamespace(type="audio", data=encoded, mime_type="audio/wav")
    )

    audio, mime_type, sample_rate, channels = _extract_audio(response)

    assert (audio, mime_type, sample_rate, channels) == (b"encoded-audio", "audio/wav", None, None)


@pytest.mark.parametrize("text", [None, "", "  "])
def test_gemini_tts_rejects_empty_input(text):
    provider = GeminiVoiceProvider(api_key="test", tts_model="model", tts_voice="Kore")
    with pytest.raises(TTSFailed):
        provider.synthesize(text, language="fr", script="latin")


def test_gemini_tts_empty_audio_is_controlled():
    client = SimpleNamespace(
        interactions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                output_audio=SimpleNamespace(type="audio", data="", mime_type="audio/pcm")
            )
        )
    )
    provider = GeminiVoiceProvider(
        api_key="test", tts_model="model", tts_voice="Kore", client_factory=lambda key: client
    )
    with pytest.raises(TTSFailed):
        provider.synthesize("safe answer", language="fr", script="latin")


def test_gemini_tts_missing_key_is_controlled_and_lazy():
    called = False

    def factory(key):
        nonlocal called
        called = True
        return object()

    provider = GeminiVoiceProvider(
        api_key="", tts_model="model", tts_voice="Kore", client_factory=factory
    )
    with pytest.raises(VoiceProviderUnavailable):
        provider.synthesize("safe answer", language="fr", script="latin")
    assert called is False


def test_extract_audio_stream_concatenates_audio_deltas_and_ignores_text():
    stream = [
        SimpleNamespace(event_type="step.delta", delta=SimpleNamespace(type="text", text="ignore")),
        SimpleNamespace(event_type="step.delta", delta=SimpleNamespace(type="audio", data=b"one")),
        SimpleNamespace(event_type="step.delta", delta=SimpleNamespace(type="audio", data=b"two")),
    ]

    audio, mime_type, sample_rate, channels = _extract_audio_stream(stream)

    assert (audio, mime_type, sample_rate, channels) == (b"onetwo", "audio/pcm", 24000, 1)


def test_extract_audio_stream_decodes_base64_delta_once():
    stream = [
        SimpleNamespace(
            event_type="step.delta",
            delta=SimpleNamespace(type="audio", data=base64.b64encode(b"chunk" ).decode("ascii")),
        )
    ]

    audio, *_ = _extract_audio_stream(stream)

    assert audio == b"chunk"


def test_l16_audio_is_treated_as_raw_pcm_for_metadata():
    client = SimpleNamespace(
        interactions=SimpleNamespace(
            create=lambda **kwargs: [
                SimpleNamespace(
                    event_type="step.delta",
                    delta=SimpleNamespace(
                        type="audio",
                        data=b"pcm",
                        mime_type="audio/l16",
                        sample_rate=24000,
                        channels=1,
                    ),
                )
            ]
        )
    )
    provider = GeminiVoiceProvider(
        api_key="test", tts_model="model", tts_voice="Kore", client_factory=lambda key: client
    )

    result = provider.synthesize("safe answer", language="fr", script="latin")

    assert result.mime_type == "audio/l16"
    assert result.sample_width_bytes == 2


def test_extract_audio_stream_empty_and_failure_are_controlled():
    with pytest.raises(TTSFailed):
        _extract_audio_stream([])

    def broken_stream():
        yield SimpleNamespace(
            event_type="step.delta",
            delta=SimpleNamespace(type="audio", data=b"one"),
        )
        raise TimeoutError("timed out")

    with pytest.raises(TTSFailed):
        _extract_audio_stream(broken_stream())


def test_pcm_wav_helper_roundtrips_complete_samples(tmp_path):
    pcm = b"\x01\x00\x02\x00" * 1200
    output = tmp_path / "roundtrip.wav"

    write_pcm_wav(pcm, output)

    assert output.read_bytes()[:4] == b"RIFF"
    with wave.open(str(output), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24000
        assert wav.getnframes() == len(pcm) // 2
        assert wav.readframes(wav.getnframes()) == pcm


def test_pcm_wav_helper_rejects_empty_and_incomplete_samples(tmp_path):
    with pytest.raises(ValueError):
        write_pcm_wav(b"", tmp_path / "empty.wav")
    with pytest.raises(ValueError):
        write_pcm_wav(b"\x00", tmp_path / "odd.wav")


@pytest.mark.parametrize("mime_type", ["audio/l16", "audio/l16;rate=24000"])
def test_l16_mime_variants_are_raw_pcm(mime_type, tmp_path):
    pcm = b"\x00\x00" * 94080
    output = tmp_path / "l16.wav"

    write_pcm_wav(pcm, output)

    with wave.open(str(output), "rb") as wav:
        assert mime_type.startswith("audio/l16")
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24000
        assert wav.getnframes() == 94080


def test_real_length_shape_188160_bytes_is_valid_wav(tmp_path):
    pcm = b"\x00\x00" * (188160 // 2)
    output = tmp_path / "shape.wav"

    write_pcm_wav(pcm, output)

    assert output.stat().st_size > len(pcm)
    with wave.open(str(output), "rb") as wav:
        assert wav.getnframes() == 94080
