"""Development-only one-shot Gemini audio transcription smoke tool."""

from __future__ import annotations

import argparse
import mimetypes
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.voice.errors import VoiceError  # noqa: E402
from app.voice.models import AudioInput  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe one audio file with Gemini STT.")
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to an explicitly selected audio file.",
    )
    args = parser.parse_args()
    path = args.file.expanduser().resolve()
    if not path.is_file():
        print("ERROR: audio file not found")
        return 2
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime_type.startswith("audio/"):
        print("ERROR: file MIME type is not audio")
        return 2

    settings = get_settings()
    print(f"GEMINI_API_KEY_PRESENT={'YES' if settings.gemini_api_key.strip() else 'NO'}")
    if not settings.gemini_api_key.strip():
        print("ERROR: Gemini API key is not configured")
        return 2
    try:
        provider = create_voice_provider(settings)
        started = time.perf_counter()
        result = provider.transcribe(
            AudioInput(data=path.read_bytes(), mime_type=mime_type, filename=path.name)
        )
    except VoiceError as exc:
        print(f"ERROR: {exc.__class__.__name__}")
        return 1
    print(f"provider={result.provider}")
    print(f"model={result.model}")
    print(f"mime_type={mime_type}")
    print(f"latency_ms={round((time.perf_counter() - started) * 1000, 2)}")
    print(f"transcript={result.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
