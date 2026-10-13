from __future__ import annotations

import math
import struct
import wave

import pytest

from app.config import Settings
from app.voice.debug_audio import analyze_pcm16, dump_turn_wav


def _pcm(samples: list[int]) -> bytes:
    return struct.pack(f"<{len(samples)}h", *samples)


def test_debug_dump_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("VOICE_DEBUG_DUMP_DIR", raising=False)
    assert Settings(_env_file=None).voice_debug_dump_dir == ""
    assert dump_turn_wav("", "req-1", _pcm([1, 2, 3])) is None
    assert dump_turn_wav("   ", "req-1", _pcm([1, 2, 3])) is None
    assert list(tmp_path.iterdir()) == []


def test_dump_writes_valid_pcm16_16khz_mono_wav_with_exact_samples(tmp_path):
    pcm = _pcm([0, 1000, -1000, 32767, -32768, 12345])
    path = dump_turn_wav(str(tmp_path / "voice_debug"), "0ce22780-fa8a-42be", pcm)
    assert path is not None
    assert path.name == "0ce22780-fa8a-42be_input.wav"
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.getcomptype() == "NONE"
        assert wav.getnframes() == 6
        assert wav.readframes(wav.getnframes()) == pcm


def test_dump_file_name_cannot_escape_the_directory(tmp_path):
    path = dump_turn_wav(str(tmp_path), "../../etc/passwd", _pcm([1]))
    assert path is not None
    assert path.parent == tmp_path
    assert "/" not in path.name and "\\" not in path.name


def test_rms_peak_and_zero_ratio_are_exact():
    metrics = analyze_pcm16(_pcm([0, 16384, -16384, 0]))
    assert metrics.audio_bytes == 8
    assert metrics.audio_duration_ms == pytest.approx(0.2, abs=0.05)
    expected_rms = math.sqrt((2 * 16384**2) / 4) / 32768
    assert metrics.pcm_rms == pytest.approx(expected_rms, abs=1e-5)
    assert metrics.pcm_peak == pytest.approx(0.5)
    assert metrics.zero_sample_ratio == 0.5
    assert metrics.classification == "NORMAL"


def test_duration_uses_16khz_pcm16():
    metrics = analyze_pcm16(b"\x00\x00" * 16000)
    assert metrics.audio_duration_ms == 1000.0
    assert metrics.audio_bytes == 32000


@pytest.mark.parametrize(
    ("samples", "classification"),
    [
        ([0] * 1600, "SILENT"),
        ([20, -20] * 800, "SILENT"),
        ([100, -100] * 800, "VERY_LOW"),
        ([4000, -4000] * 800, "NORMAL"),
    ],
)
def test_conservative_classification(samples, classification):
    assert analyze_pcm16(_pcm(samples)).classification == classification


def test_empty_and_odd_length_input_do_not_raise():
    assert analyze_pcm16(b"").classification == "EMPTY"
    metrics = analyze_pcm16(_pcm([100]) + b"\x01")
    assert metrics.audio_bytes == 3
    assert metrics.pcm_peak == pytest.approx(100 / 32768, abs=1e-5)
