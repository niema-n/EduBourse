"""Speak the exact saved HTTP answers with EduBourse's configured Gemini TTS."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
sys.path.insert(0, str(PROJECT / "backend"))
from app.config import Settings  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402

spec = importlib.util.spec_from_file_location("jury_audio_helper", PROJECT / "demo/jury_audio/generate_audio.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def first_sentences(answer, count=3):
    """Return an unchanged prefix ending at the third sentence, if present."""
    ends = list(re.finditer(r"(?<!\d)[.!?؟](?:[\]*\"»”]*)(?=\s|$)", answer))
    if len(ends) < count:
        return None
    end = ends[count - 1].end()
    return answer[:end] if end < len(answer) else None


def split_exact_text(text, max_chars=650):
    """Split at sentence/paragraph boundaries without deleting a single character."""
    chunks = []
    remaining = text
    while len(remaining) > max_chars:
        boundaries = [m.end() for m in re.finditer(r"\n\n|(?<!\d)[.!?؟](?=\s)", remaining[:max_chars])]
        end = max(boundaries) if boundaries else remaining.rfind(" ", 0, max_chars)
        if end <= 0:
            end = max_chars
        chunks.append(remaining[:end])
        remaining = remaining[end:]
    if remaining:
        chunks.append(remaining)
    assert "".join(chunks) == text
    return chunks


def synthesize(provider, text, record, path):
    chunks = split_exact_text(text)
    cache = OUTPUT / "chunks"
    cache.mkdir(exist_ok=True)
    pieces = []
    rates = []
    request_segments = []

    def get_segment(chunk):
        identity = json.dumps([provider.tts_model, provider.tts_voice, record["language"], record["script"], chunk], ensure_ascii=False)
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        pcm_path, metadata_path = cache / f"{digest}.pcm", cache / f"{digest}.json"
        if pcm_path.exists() and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            pcm, rate = pcm_path.read_bytes(), metadata["sample_rate_hz"]
            actual_segments = metadata.get("request_segments", [chunk])
        else:
            actual_segments = [chunk]
            for attempt in range(2):
                try:
                    result = provider.synthesize(chunk, language=record["language"], script=record["script"])
                    padded, rate = helper.prepare_audio(result)
                    pcm = padded[round(rate * 0.4) * 2:-round(rate * 0.7) * 2]
                    break
                except Exception as exc:
                    if attempt:
                        if "no audio chunks" in str(exc).lower():
                            # Gemini can report rate limits as stream error events;
                            # the existing adapter exposes these as missing audio.
                            # Do not multiply requests by splitting a quota failure.
                            raise
                        if len(chunk) <= 250:
                            raise
                        print(f"  Splitting unavailable {len(chunk)}-character segment into shorter exact spans", flush=True)
                        smaller = split_exact_text(chunk, max_chars=len(chunk) // 2)
                        results = [get_segment(part) for part in smaller]
                        rate = results[0][1]
                        if any(item[1] != rate for item in results):
                            raise ValueError("Inconsistent sample rate")
                        pcm = (b"\x00\x00" * round(rate * 0.25)).join(item[0] for item in results)
                        actual_segments = [span for item in results for span in item[2]]
                        break
                    print(f"  Retrying segment after {type(exc).__name__}", flush=True)
                    time.sleep(30 if "no audio chunks" in str(exc).lower() else 2)
            pcm_path.write_bytes(pcm)
            metadata_path.write_text(json.dumps({"exact_tts_input": chunk, "request_segments": actual_segments, "sample_rate_hz": rate, "tts_model": provider.tts_model, "tts_voice": provider.tts_voice}, ensure_ascii=False, indent=2), encoding="utf-8")
        return pcm, rate, actual_segments

    for index, chunk in enumerate(chunks):
        print(f"  {path.stem}: speech segment {index + 1}/{len(chunks)} ({len(chunk)} characters)", flush=True)
        pcm, rate, actual_segments = get_segment(chunk)
        pieces.append(pcm)
        rates.append(rate)
        request_segments.extend(actual_segments)
    if len(set(rates)) != 1:
        raise ValueError("TTS returned inconsistent sample rates")
    rate = rates[0]
    pause = b"\x00\x00" * round(rate * 0.25)
    audio = b"\x00\x00" * round(rate * 0.4) + pause.join(pieces) + b"\x00\x00" * round(rate * 0.7)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(audio)
    with wave.open(str(path), "rb") as wav:
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        duration = wav.getnframes() / wav.getframerate()
        assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
    assert len(samples) and np.max(np.abs(samples.astype(np.int32))) > 100
    assert not np.any(samples[:round(rate * 0.4)])
    assert not np.any(samples[-round(rate * 0.7):])
    return {
        "filename": path.name, "duration_seconds": round(duration, 3),
        "sample_rate_hz": rate, "channels": 1, "bits_per_sample": 16,
        "tts_provider": provider.provider_name, "tts_model": provider.tts_model, "tts_voice": provider.tts_voice,
        "speech_segments": len(request_segments), "exact_tts_segments": request_segments,
        "exact_tts_input": text,
        "tts_input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "wav_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "wav_validation_passed": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=["fr", "en", "ar", "darija"])
    args = parser.parse_args()
    records = json.loads((PROJECT / "demo/jury_answers/jury_answers.json").read_text(encoding="utf-8"))
    settings = Settings(_env_file=PROJECT / ".env")
    provider = create_voice_provider(settings)
    manifest_path = OUTPUT / "audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    def save():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for language, record in records.items():
        if args.language and language != args.language:
            continue
        answer = record["answer"]
        assert answer == record["backend_result"]["answer"]
        assert answer == (PROJECT / "demo/jury_answers" / f"{language}_answer.txt").read_text(encoding="utf-8")
        entry = manifest.setdefault(language, {})
        path = OUTPUT / f"{language}_response.wav"
        if not entry.get("full") or not path.exists():
            print(f"Synthesizing full {language} response ({len(answer)} characters)", flush=True)
            entry["full"] = synthesize(provider, answer, record, path)
            save()
        if entry["full"]["tts_input_sha256"] != record["answer_sha256"]:
            raise ValueError("Audio manifest belongs to a different saved answer")
        print(f"{language} full: {entry['full']['duration_seconds']}s", flush=True)
        if entry["full"]["duration_seconds"] > 45:
            excerpt = first_sentences(answer)
            if excerpt is not None and not entry.get("demo_excerpt"):
                print(f"Synthesizing shortened {language} playback: first three complete sentences", flush=True)
                entry["demo_excerpt"] = synthesize(provider, excerpt, record, OUTPUT / f"{language}_response_demo.wav")
                entry["demo_excerpt"]["shortened_playback_version"] = True
                entry["demo_excerpt"]["selection"] = "Exact prefix through the first three complete sentences; not a rewritten answer"
                (OUTPUT / f"{language}_response_demo.txt").write_text(excerpt, encoding="utf-8")
                save()
    lines = [
        "EduBourse real response audio", "",
        "*_response.wav speaks the complete, unchanged answer saved in jury_answers.",
        "*_response_demo.wav is a SHORTENED PLAYBACK VERSION when a full recording exceeds 45 seconds.",
        "Demo excerpts contain only an unchanged prefix ending after three complete sentences.",
        "The corresponding *_response_demo.txt preserves the exact excerpt sent to TTS.",
        "No standalone LLM generates or rewrites the answer text.",
        "Long answers are spoken in ordered segments with unchanged text; joined with 0.25-second pauses.",
        "Provider, model, voice, exact TTS inputs, hashes and durations: audio_manifest.json.", "",
        "Playback: powershell -ExecutionPolicy Bypass -File demo/jury_answers_audio/play_response.ps1 fr",
        "Short excerpt: append -Demo (only where an excerpt exists).", "",
    ]
    for language, entry in manifest.items():
        for kind, item in entry.items():
            lines.append(f"{language} {kind}: {item['filename']} ({item['duration_seconds']} seconds)")
    (OUTPUT / "README.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
