"""Development-only one-shot Gemini TTS smoke tool."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.voice.errors import VoiceError  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402
from app.voice.wav import write_pcm_wav  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one real Gemini TTS synthesis.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    settings = get_settings()
    print(f"gemini_api_key_present={'YES' if settings.gemini_api_key.strip() else 'NO'}")
    provider = create_voice_provider(settings)
    started = time.perf_counter()
    try:
        result = provider.synthesize(args.text, language="fr", script="latin")
    except VoiceError as exc:
        print(f"ERROR: {exc.__class__.__name__}")
        return 1

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if result.mime_type.split(";", 1)[0].lower() in {"audio/pcm", "audio/l16"}:
        if not result.sample_rate or result.channels != 1 or result.sample_width_bytes != 2:
            print("ERROR: unsupported PCM metadata")
            return 1
        write_pcm_wav(
            result.audio,
            output,
            sample_rate=result.sample_rate,
            channels=result.channels,
            sample_width_bytes=result.sample_width_bytes,
        )
    else:
        output.write_bytes(result.audio)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    print(f"provider={result.provider}")
    print(f"model={result.model}")
    print(f"voice={result.voice}")
    print(f"mime={result.mime_type}")
    print(f"byte_count={len(result.audio)}")
    print(f"output_path={output}")
    print(f"latency_ms={latency_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
