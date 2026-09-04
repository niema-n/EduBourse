from typing import Protocol

from app.voice.models import AudioInput, SpeechSynthesisResult, TranscriptionResult


class SpeechToTextProvider(Protocol):
    provider_name: str

    def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        ...


class TextToSpeechProvider(Protocol):
    provider_name: str

    def synthesize(self, text: str, *, language: str, script: str) -> SpeechSynthesisResult:
        ...
