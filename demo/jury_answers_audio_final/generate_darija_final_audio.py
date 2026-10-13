"""Darija jury audio from the validated final answer only.

Reuses the existing generator's Gemini TTS path (same provider, model, voice, profile,
chunking and WAV assembly). Demo first, then full. Stops on the first TTS error and never
retries, so a quota response cannot trigger further requests.
"""

import hashlib
import importlib.util
import json
import re
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
ANSWER = PROJECT / "demo/jury_answers_final/darija_answer_final.txt"
RECORD = {"language": "ary", "script": "arabic"}

spec = importlib.util.spec_from_file_location("jury_final_audio", OUTPUT / "generate_audio.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

sys.path.insert(0, str(PROJECT / "backend"))
from app.config import Settings  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def first_sentence(paragraph):
    match = re.search(r"(?<!\d)[.!?؟]", paragraph)
    return paragraph[: match.end()] if match else paragraph


def demo_text(answer):
    """Verbatim sentences: the distinction, the stock, the bond, the synthesis.

    One sentence per instrument keeps the spoken demo inside its target duration; the
    unabridged answer is the full WAV.
    """
    paragraphs = [block.strip() for block in answer.split("\n\n") if block.strip()]
    opening = first_sentence(paragraphs[0])
    stock = first_sentence(next(p for p in paragraphs[1:] if p.startswith("السهم هو")))
    bond = first_sentence(next(p for p in paragraphs[1:] if p.startswith("السند هو")))
    synthesis = paragraphs[-1]
    selected = [opening, stock, bond, synthesis]
    for piece in selected:
        assert piece in answer, "demo sentence is not verbatim"
    return "\n\n".join(selected)


def write_wav(path, pieces, rate):
    gap = b"\x00\x00" * round(rate * 0.25)
    pcm = b"\x00\x00" * round(rate * 0.4) + gap.join(pieces) + b"\x00\x00" * round(rate * 0.7)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return round(len(pcm) / (rate * 2), 3)


def main():
    answer = ANSWER.read_text(encoding="utf-8")
    assert answer.strip(), "empty authoritative answer file"
    demo = demo_text(answer)
    (OUTPUT / "darija_response_demo.txt").write_text(demo, encoding="utf-8")

    settings = Settings(_env_file=PROJECT / ".env")
    assert settings.gemini_tts_model == "gemini-2.5-flash-preview-tts"
    assert settings.gemini_tts_voice == "Kore"
    provider = create_voice_provider(settings)

    manifest_path = OUTPUT / "audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    status_path = OUTPUT / "darija_final_generation_status.json"
    requests = 0
    # The demo has priority: the full answer is only attempted once it succeeded.
    for name, text in (("darija_response_demo.wav", demo), ("darija_response_full.wav", answer)):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if (OUTPUT / name).exists() and manifest.get(name, {}).get("tts_input_sha256") == digest:
            print(f"{name} already matches its source text; no request sent", flush=True)
            continue
        spans = base.chunks(text)
        assert "".join(spans) == text, "chunking altered the text"
        pieces, rates = [], []
        try:
            for span in spans:
                requests += 1
                print(f"TTS request {requests}: {name} ({len(span)} characters)", flush=True)
                padded, rate = base.synthesize(provider, span, RECORD)
                pieces.append(padded[round(rate * 0.4) * 2 : -round(rate * 0.7) * 2])
                rates.append(rate)
        except Exception as exc:
            detail = exc.detail if isinstance(exc, base.StreamFailure) else {"code": type(exc).__name__}
            save(
                status_path,
                {
                    "status": "blocked",
                    "stopped": True,
                    "stopped_at": datetime.now(timezone.utc).isoformat(),
                    "requests_sent": requests,
                    "failed_file": name,
                    "error": detail,
                    "retry_performed": False,
                    "provider_changed": False,
                    "model_changed": False,
                    "voice_changed": False,
                    "production_configuration_changed": False,
                    "source": "demo/jury_answers_final/darija_answer_final.txt",
                },
            )
            print(f"TTS stopped: {json.dumps(detail, ensure_ascii=False)}", flush=True)
            return
        assert len(set(rates)) == 1, "inconsistent sample rates"
        duration = write_wav(OUTPUT / name, pieces, rates[0])
        manifest[name] = {
            "duration_seconds": duration,
            "sample_rate_hz": rates[0],
            "channels": 1,
            "bits_per_sample": 16,
            "exact_tts_segments": spans,
            "tts_input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "tts_provider": "gemini",
            "tts_model": provider.tts_model,
            "tts_voice": provider.tts_voice,
            "shortened_playback_version": name.endswith("demo.wav"),
            "source_answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        }
        save(manifest_path, manifest)
        print(f"wrote {name}: {duration}s", flush=True)
    save(
        status_path,
        {
            "status": "complete",
            "stopped": False,
            "requests_sent": requests,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "source": "demo/jury_answers_final/darija_answer_final.txt",
        },
    )


if __name__ == "__main__":
    main()
