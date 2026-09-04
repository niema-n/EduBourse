"""Local-only helpers for wrapping raw Gemini PCM audio in WAV."""

from __future__ import annotations

import wave
from pathlib import Path


def write_pcm_wav(
    pcm_bytes: bytes,
    output_path: Path,
    *,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width_bytes: int = 2,
) -> None:
    """Write complete raw PCM samples into a standard WAV container."""
    if not isinstance(pcm_bytes, bytes) or not pcm_bytes:
        raise ValueError("PCM audio must be non-empty bytes")
    if sample_width_bytes <= 0 or len(pcm_bytes) % sample_width_bytes:
        raise ValueError("PCM audio contains an incomplete sample")
    if sample_rate <= 0 or channels <= 0:
        raise ValueError("WAV parameters must be positive")
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width_bytes)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
