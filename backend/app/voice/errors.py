class VoiceError(Exception):
    """Base class for controlled voice application errors."""


class VoiceProviderUnavailable(VoiceError):
    code = "VOICE_PROVIDER_UNAVAILABLE"


class InvalidAudio(VoiceError):
    code = "INVALID_AUDIO"


class TranscriptionFailed(VoiceError):
    code = "TRANSCRIPTION_FAILED"


class TTSFailed(VoiceError):
    code = "TTS_FAILED"


class VoiceSessionError(VoiceError):
    code = "VOICE_SESSION_ERROR"


class VoiceConfigurationError(VoiceError):
    code = "VOICE_CONFIGURATION_ERROR"
