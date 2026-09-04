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


class InvalidVoiceSession(VoiceError):
    code = "INVALID_SESSION"


class InvalidVoiceState(VoiceError):
    code = "INVALID_STATE"


class AudioChunkTooLarge(VoiceError):
    code = "AUDIO_CHUNK_TOO_LARGE"


class TranscriptionTimeout(VoiceError):
    code = "TRANSCRIPTION_TIMEOUT"


class SessionTimeout(VoiceError):
    code = "SESSION_TIMEOUT"


class BusinessPipelineFailed(VoiceError):
    code = "BUSINESS_PIPELINE_ERROR"


class BusyVoiceInput(VoiceError):
    code = "BUSY"
