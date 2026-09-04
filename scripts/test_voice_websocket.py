"""Development client for the backend voice WebSocket."""

from __future__ import annotations

import argparse
import json
import time
import wave
from pathlib import Path

from websockets.sync.client import connect


def pcm_duration_seconds(
    pcm_bytes: int, *, sample_rate: int = 16000, channels: int = 1, sample_width_bytes: int = 2
) -> float:
    return pcm_bytes / (sample_rate * channels * sample_width_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send raw 16 kHz mono PCM to EduBourse.")
    parser.add_argument("--url", default="ws://127.0.0.1:8000/api/v1/voice/live")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--session-id", default="voice-demo")
    parser.add_argument(
        "--output", type=Path, help="Optional raw assistant audio output outside the repo."
    )
    parser.add_argument("--chunk-bytes", type=int, default=3200)
    parser.add_argument(
        "--no-realtime",
        action="store_true",
        help="Disable microphone-style pacing for stress tests.",
    )
    args = parser.parse_args()

    path = args.file.expanduser().resolve()
    if not path.is_file() or args.chunk_bytes <= 0:
        print("ERROR: invalid input file or chunk size")
        return 2
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav:
                if (
                    wav.getnchannels() != 1
                    or wav.getsampwidth() != 2
                    or wav.getframerate() != 16000
                ):
                    print("ERROR: WAV must be mono, 16-bit, 16000 Hz")
                    return 2
                pcm = wav.readframes(wav.getnframes())
        except (wave.Error, OSError):
            print("ERROR: invalid WAV input")
            return 2
    else:
        pcm = path.read_bytes()
    if not pcm or len(pcm) % 2:
        print("ERROR: input must be non-empty complete 16-bit PCM")
        return 2

    received = bytearray()
    with connect(args.url) as websocket:
        websocket.send(
            json.dumps(
                {
                    "type": "session.start",
                    "session_id": args.session_id,
                    "thread_id": args.thread_id,
                    "audio": {
                        "mime_type": "audio/pcm",
                        "sample_rate": 16000,
                        "channels": 1,
                        "sample_width_bytes": 2,
                    },
                }
            )
        )
        print(websocket.recv())
        pace_started = time.monotonic()
        bytes_sent = 0
        bytes_per_second = pcm_duration_seconds(1) ** -1
        for offset in range(0, len(pcm), args.chunk_bytes):
            chunk = pcm[offset : offset + args.chunk_bytes]
            websocket.send(chunk)
            if not args.no_realtime:
                bytes_sent += len(chunk)
                target_elapsed = bytes_sent / bytes_per_second
                delay = target_elapsed - (time.monotonic() - pace_started)
                if delay > 0:
                    time.sleep(delay)
        websocket.send(json.dumps({"type": "audio.end"}))
        while True:
            message = websocket.recv()
            if isinstance(message, bytes):
                received.extend(message)
                continue
            print(message)
            payload = json.loads(message)
            if payload.get("type") == "error":
                # Missing fatal on older servers is conservatively fatal.
                if payload.get("fatal", True) is False:
                    continue
                break
            if payload.get("type") in {"response.complete", "error"}:
                break
        websocket.send(json.dumps({"type": "session.close"}))

    if args.output and received:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(received)
        print(json.dumps({"assistant_audio_bytes": len(received), "output_path": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
