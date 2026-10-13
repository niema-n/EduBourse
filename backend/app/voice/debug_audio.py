"""Diagnostic-only measurements of the PCM a voice turn actually received.

Nothing here changes, rejects or filters audio: the metrics are logged and, when
VOICE_DEBUG_DUMP_DIR is set, the exact received bytes are written as a WAV file.
"""

from __future__ import annotations

import array
import math
import re
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
INT16_FULL_SCALE = 32768.0

# Conservative diagnostic thresholds on normalized amplitude (1.0 = full scale).
# Conversational speech from a working microphone is typically well above an RMS
# of 0.01 (-40 dBFS); a peak below 0.002 (about -54 dBFS) carries no usable speech.
SILENT_PEAK = 0.002
SILENT_RMS = 0.001
VERY_LOW_RMS = 0.01

AudioClassification = Literal["EMPTY", "SILENT", "VERY_LOW", "NORMAL"]
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class PcmMetrics:
    audio_bytes: int
    audio_duration_ms: float
    pcm_rms: float
    pcm_peak: float
    zero_sample_ratio: float
    classification: AudioClassification


def analyze_pcm16(pcm: bytes) -> PcmMetrics:
    """Measure little-endian mono PCM16 at 16 kHz; a trailing odd byte is ignored."""
    count = len(pcm) // SAMPLE_WIDTH_BYTES
    if count == 0:
        return PcmMetrics(len(pcm), 0.0, 0.0, 0.0, 1.0, "EMPTY")
    samples = array.array("h")
    samples.frombytes(pcm[: count * SAMPLE_WIDTH_BYTES])
    if sys.byteorder == "big":
        samples.byteswap()  # the wire format is little-endian PCM16
    square_sum = 0
    peak = 0
    zeros = 0
    for sample in samples:
        square_sum += sample * sample
        magnitude = -sample if sample < 0 else sample
        if magnitude > peak:
            peak = magnitude
        if sample == 0:
            zeros += 1
    rms = math.sqrt(square_sum / count) / INT16_FULL_SCALE
    normalized_peak = peak / INT16_FULL_SCALE
    if normalized_peak < SILENT_PEAK or rms < SILENT_RMS:
        classification: AudioClassification = "SILENT"
    elif rms < VERY_LOW_RMS:
        classification = "VERY_LOW"
    else:
        classification = "NORMAL"
    return PcmMetrics(
        audio_bytes=len(pcm),
        audio_duration_ms=round(count / SAMPLE_RATE * 1000, 1),
        pcm_rms=round(rms, 5),
        pcm_peak=round(normalized_peak, 5),
        zero_sample_ratio=round(zeros / count, 4),
        classification=classification,
    )


def dump_turn_wav(directory: str, request_id: str, pcm: bytes) -> Path | None:
    """Write the exact received PCM as a 16 kHz mono PCM16 WAV; no-op when disabled."""
    if not directory or not directory.strip():
        return None
    target_dir = Path(directory.strip())
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _SAFE_NAME.sub("_", request_id)[:80] or "turn"
    path = target_dir / f"{safe_id}_input.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return path
