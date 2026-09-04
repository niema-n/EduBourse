"""Development-only real STT to shared J4 text pipeline smoke tool."""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.api.chat import get_chat_graph, process_text_message  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.voice.errors import VoiceError  # noqa: E402
from app.voice.models import AudioInput  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402
from app.voice.service import VoiceService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run real Gemini STT through the J4 text pipeline."
    )
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--session-id", default="voice-cli")
    args = parser.parse_args()
    path = args.file.expanduser().resolve()
    if not path.is_file():
        print("ERROR: audio file not found")
        return 2
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        print("ERROR: Gemini provider unavailable")
        return 2
    graph = get_chat_graph()
    service = VoiceService(
        create_voice_provider(settings),
        tts_provider=UnavailableTTS(),
        text_pipeline=lambda payload: process_text_message(payload, graph),
    )
    try:
        result = service.process_to_text(
            AudioInput(data=path.read_bytes(), mime_type=mime_type, filename=path.name),
            session_id=args.session_id,
            thread_id=args.thread_id,
        )
    except VoiceError as exc:
        print(f"ERROR: {exc.__class__.__name__}")
        return 1
    print(f"transcript={result.transcript}")
    print(f"language={result.language}")
    print(f"script={result.script}")
    print(f"route={result.route}")
    print(f"blocked={result.blocked}")
    print(f"status={result.status}")
    print(f"answer={result.answer}")
    print(f"stt_provider={result.stt_provider}")
    print(f"stt_model={result.stt_model}")
    print(f"stt_latency_ms={result.stt_latency_ms}")
    print(f"total_latency_ms={result.total_latency_ms}")
    return 0


class UnavailableTTS:
    """Explicitly disables synthesis for this text-only development command."""

    def synthesize(self, text, *, language, script):
        raise RuntimeError("TTS is disabled in J5-03")


if __name__ == "__main__":
    raise SystemExit(main())
