from app.config import get_settings
from app.voice.errors import InvalidAudio
from app.voice.models import AudioInput


def validate_audio(audio: AudioInput, *, max_bytes: int | None = None) -> AudioInput:
    if not audio.data or not audio.mime_type.strip():
        raise InvalidAudio("audio data and MIME type are required")
    if not audio.mime_type.lower().startswith("audio/"):
        raise InvalidAudio("MIME type must represent audio")
    configured_max = get_settings().voice_max_audio_bytes if max_bytes is None else max_bytes
    if configured_max <= 0:
        raise InvalidAudio("maximum audio size must be positive")
    if len(audio.data) > configured_max:
        raise InvalidAudio("audio exceeds the maximum allowed size")
    if audio.sample_rate is not None and audio.sample_rate <= 0:
        raise InvalidAudio("sample rate must be positive")
    if audio.channels is not None and audio.channels <= 0:
        raise InvalidAudio("channel count must be positive")
    return audio
