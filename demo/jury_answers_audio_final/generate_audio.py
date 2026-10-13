"""Final response audio only. Stop on the first TTS quota error; never retry."""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import wave
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
sys.path.insert(0, str(PROJECT / "backend"))
from app.config import Settings
from app.voice.errors import TTSFailed
from app.voice.models import SpeechSynthesisResult
from app.voice.providers.factory import create_voice_provider
from app.voice.providers.gemini import _extract_audio_stream, _get_tts_profile, _tts_input

spec = importlib.util.spec_from_file_location("jury_audio_helper", PROJECT / "demo/jury_audio/generate_audio.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class StreamFailure(TTSFailed):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(str(detail.get("code", "tts_stream_error")))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def excerpt(answer):
    boundaries = list(re.finditer(r'(?<!\d)[.!?؟][*\]"»”]*(?=\s|$)', answer))
    choices = [(n, answer[:boundaries[n - 1].end()]) for n in (2, 3) if len(boundaries) >= n]
    if not choices:
        raise ValueError("Answer has fewer than two complete sentences")
    # Approximate moderate speech; retain the closest 2/3-sentence exact prefix.
    count, text = min(choices, key=lambda item: abs(len(item[1].split()) / 2.5 - 22.5))
    assert answer.startswith(text)
    return text, count


def chunks(text):
    result = []
    while len(text) > 650:
        ends = [m.end() for m in re.finditer(r"\n\n|(?<!\d)[.!?؟](?=\s)", text[:650])]
        end = max(ends) if ends else text.rfind(" ", 0, 650)
        end = end if end > 0 else 650
        result.append(text[:end])
        text = text[end:]
    if text:
        result.append(text)
    return result


def synthesize(provider, text, record):
    profile = _get_tts_profile(record["language"], record["script"])
    # Same configured model, voice, profile, request and stream extraction as
    # the existing adapter. Observe stream errors so quota cannot be hidden as
    # "no audio chunks" and accidentally trigger further requests.
    stream = provider._get_client().interactions.create(
        model=provider.tts_model, input=_tts_input(profile, text),
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"language": profile.speech_language, "voice": provider.tts_voice}]},
        stream=True,
    )

    def observed():
        for event in stream:
            if getattr(event, "event_type", None) == "error":
                error = getattr(event, "error", None)
                detail = error.model_dump(exclude_none=True) if hasattr(error, "model_dump") else {"code": "tts_stream_error", "message": str(error)}
                raise StreamFailure(detail)
            yield event

    audio, mime, rate, channels = _extract_audio_stream(observed())
    result = SpeechSynthesisResult(audio=audio, mime_type=mime, provider="gemini", model=provider.tts_model, voice=provider.tts_voice, sample_rate=rate, channels=channels, sample_width_bytes=2)
    return helper.prepare_audio(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-run", action="store_true", help="Explicitly start a newly authorized campaign, preserving prior stop evidence")
    args = parser.parse_args()
    status_path = OUTPUT / "generation_status.json"
    if status_path.exists() and json.loads(status_path.read_text(encoding="utf-8")).get("stopped"):
        if not args.new_run:
            print("This campaign already stopped after a TTS error; no additional request sent.", flush=True)
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        (OUTPUT / f"generation_status_before_{stamp}.json").write_bytes(status_path.read_bytes())
    # Darija is a frozen, already validated pack.  It is deliberately excluded
    # from this campaign so a historical metadata mismatch cannot block other
    # languages and no Darija TTS request can be made accidentally.
    order = ("fr", "en", "ar")
    records = {}
    source_hashes = {}
    for key in order:
        source = PROJECT / "demo/jury_answers_final" / f"{key}_answer_final.txt"
        if not source.exists():
            # No accepted live response means this language is not part of the
            # run; never fall back to an older non-authoritative answer.
            continue
        # These four TXT files are the only authority for response content.
        answer = source.read_text(encoding="utf-8")
        if not answer.strip():
            raise ValueError(f"Empty authoritative answer file: {source.name}")
        records[key] = {"answer": answer, "language": "ary" if key == "darija" else key,
                        "script": "arabic" if key in ("darija", "ar") else "latin",
                        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest()}
        source_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    save(OUTPUT / "source_txt_hashes_before.json", source_hashes)
    settings = Settings(_env_file=PROJECT / ".env")
    assert settings.gemini_tts_model == "gemini-2.5-flash-preview-tts" and settings.gemini_tts_voice == "Kore"
    provider = create_voice_provider(settings)
    plan = {}
    for key, record in records.items():
        text, count = excerpt(record["answer"])
        (OUTPUT / f"{key}_response_demo.txt").write_text(text, encoding="utf-8")
        plan[key] = {"demo_text": text, "sentence_count": count, "full_text_sha256": record["answer_sha256"], "shortened_playback_version": text != record["answer"], "demo_audio_file": f"{key}_response_demo.wav", "full_audio_file": f"{key}_response_full.wav"}
    save(OUTPUT / "audio_plan.json", plan)
    manifest_path = OUTPUT / "audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    requests = 0
    # Complete each language sequentially in the user's explicit priority order.
    for version in ("demo", "full"):
        for key in order:
            if key not in records:
                continue
            name = f"{key}_response_{version}.wav"
            text = plan[key]["demo_text"] if version == "demo" else records[key]["answer"]
            if name in manifest and (OUTPUT / name).exists():
                if manifest[name]["tts_input_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest():
                    raise ValueError(f"Existing WAV has different source text: {name}")
                continue
            spans = chunks(text)
            assert "".join(spans) == text
            pieces, rates = [], []
            try:
                for span in spans:
                    requests += 1
                    print(f"TTS request {requests}: {name} ({len(span)} characters)", flush=True)
                    padded, rate = synthesize(provider, span, records[key])
                    pieces.append(padded[round(rate * 0.4) * 2:-round(rate * 0.7) * 2])
                    rates.append(rate)
            except Exception as exc:
                detail = exc.detail if isinstance(exc, StreamFailure) else {"code": type(exc).__name__}
                save(status_path, {"status": "blocked", "stopped": True, "requests_sent": requests, "failed_file": name, "error": detail, "retry_performed": False, "provider_changed": False, "production_configuration_changed": False, "language_order": order, "source": "validated TXT files only", "answers_regenerated": False})
                print(f"TTS stopped: {json.dumps(detail, ensure_ascii=False)}", flush=True)
                return
            assert len(set(rates)) == 1
            rate = rates[0]
            pcm = b"\x00\x00" * round(rate * 0.4) + (b"\x00\x00" * round(rate * 0.25)).join(pieces) + b"\x00\x00" * round(rate * 0.7)
            with wave.open(str(OUTPUT / name), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(pcm)
            manifest[name] = {"duration_seconds": round(len(pcm) / (rate * 2), 3), "sample_rate_hz": rate, "channels": 1, "bits_per_sample": 16, "exact_tts_segments": spans, "tts_input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "tts_provider": "gemini", "tts_model": provider.tts_model, "tts_voice": provider.tts_voice, "shortened_playback_version": version == "demo" and plan[key]["shortened_playback_version"]}
            save(manifest_path, manifest)
    save(status_path, {"status": "complete", "stopped": False, "requests_sent": requests})


if __name__ == "__main__":
    main()
