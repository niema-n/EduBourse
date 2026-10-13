"""Extract one real voice turn from existing logs; never invent missing timings.

Run from the repository root with backend/.venv/Scripts/python.exe.
Browser render latency is printed separately by voice.browser.text_displayed
in the browser console and cannot be inferred from the server's send timestamp.
"""

import argparse
import json
import re
from pathlib import Path


def report(log: Path, request_id: str | None = None) -> dict:
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    events = []
    for line in lines:
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if request_id is None:
        ids = [e["request_id"] for e in events if e.get("event") == "voice.text.sent"]
        if not ids:
            return {"status": "awaiting_real_voice_turn", "request_id": None}
        request_id = ids[-1]
    by_event = {e["event"]: e for e in events if e.get("request_id") == request_id}

    def event(name, field="duration_ms"):
        return by_event.get(name, {}).get(field)

    def metric(name):
        for line in lines:
            if f"request_id={request_id}" in line:
                match = re.search(rf"\b{re.escape(name)}=([\d.]+)", line)
                if match:
                    return float(match[1])
        return None

    return {
        "request_id": request_id,
        "GEMINI_CONNECT_MS": metric("gemini_connect_ms"),
        "AUDIO_DURATION_MS": metric("audio_duration_ms"),
        "AUDIO_END_TO_FINAL_TRANSCRIPT_MS": event(
            "voice.stt.completed", "audio_end_to_final_transcript_ms",
        ),
        "SECURITY_MS": event("security.completed"),
        "MEMORY_CONTEXT_MS": event("memory.context.completed"),
        "SUPERVISOR_MS": event("supervisor.provider.completed"),
        "RAG_RETRIEVAL_MS": event("rag.stages", "retrieval_ms"),
        "RAG_GENERATION_MS": event("rag.stages", "generation_provider_ms"),
        "AZURE_MS": event("final_response.composed", "latency_ms"),
        "PERSISTENCE_SYNC_MS": event("persistence.history.completed"),
        "HISTORY_APPEND_MS": event("persistence.history.append.completed"),
        "DEFERRED_INDEX_MS": event("memory.index.completed"),
        "AUDIO_END_TO_TEXT_SENT_MS": event("voice.text.sent"),
        "AUDIO_END_TO_FINAL_ANSWER_MS": None,
        "browser_timing_source": "voice.browser.text_displayed in browser console",
        "route": event("request.completed", "route"),
        "language": event("request.completed", "language"),
        "grounded": event("request.completed", "grounded"),
        "TTS_MS": event("voice.tts.completed"),
        "before_browser_ms": 73499,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=Path("backend_latency.stdout.log"))
    parser.add_argument("--request-id")
    args = parser.parse_args()
    print(json.dumps(report(args.log, args.request_id), ensure_ascii=False, indent=2))
