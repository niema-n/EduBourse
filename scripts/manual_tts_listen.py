"""Play the current production Gemini TTS profiles locally on Windows."""

# ruff: noqa: I001

from __future__ import annotations

import re
import sys
import wave
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
OUTPUT_ROOT = REPOSITORY_ROOT / "tmp_tts_listen"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402


TEST_CASES = (
    (
        "FR",
        "fr",
        "latin",
        "Je peux vous expliquer simplement la différence entre une action et une obligation.",
    ),
    (
        "EN",
        "en",
        "latin",
        "I can explain the difference between a stock and a bond in simple terms.",
    ),
    (
        "AR",
        "ar",
        "arabic",
        "يمكنني شرح الفرق بين السهم والسند بطريقة واضحة وبسيطة.",
    ),
    (
        "ARY",
        "ary",
        "arabic",
        "نقدر نشرح ليك ببساطة شنو الفرق بين السهم والسند.",
    ),
)


def _write_wav(
    path: Path, audio: bytes, sample_rate: int, channels: int, sample_width: int
) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio)


def _safe_error_message(error: Exception, api_key: str) -> str:
    message = str(error)
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(r"(?i)(api[_-]?key|authorization|bearer)[^\s,;]*", "[REDACTED]", message)
    return message or "provider call failed"


def main() -> None:
    settings = Settings()
    provider = create_voice_provider(settings)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    import winsound

    listened: list[str] = []
    for label, language, script, text in TEST_CASES:
        print("================================")
        print(label)
        print(f"language={language}")
        print(f"script={script}")
        try:
            result = provider.synthesize(text, language=language, script=script)
            output_path = OUTPUT_ROOT / f"{language}.wav"
            if (
                result.sample_rate is None
                or result.channels is None
                or result.sample_width_bytes is None
            ):
                raise RuntimeError("provider returned incomplete audio metadata")
            _write_wav(
                output_path,
                result.audio,
                result.sample_rate,
                result.channels,
                result.sample_width_bytes,
            )
            winsound.PlaySound(str(output_path), winsound.SND_FILENAME)
            listened.append(label)
        except Exception as error:  # noqa: BLE001
            safe_message = _safe_error_message(error, settings.gemini_api_key)
            print(f"{label} -> TTS_FAILED: {type(error).__name__}: {safe_message}")

    for label in listened:
        print(f"{label}  -> LISTENED")


if __name__ == "__main__":
    main()
