"""One-off jury audio generation using the project's existing Gemini configuration."""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from app.config import Settings  # noqa: E402
from app.voice.models import AudioInput  # noqa: E402
from app.voice.providers.factory import create_voice_provider  # noqa: E402

QUESTIONS = (
    ("fr", "French", "fr", "latin", "jury_fr_action_vs_obligation.wav",
     "Quelle est la différence entre une action et une obligation, notamment en termes de propriété, de rendement et de risque ?"),
    ("en", "English", "en", "latin", "jury_en_ipo.wav",
     "How does an IPO work, and why does a company choose to go public?"),
    ("ar", "Modern Standard Arabic", "ar", "arabic", "jury_ar_investment_risks.wav",
     "ما هي أهم مخاطر الاستثمار في البورصة وكيف يمكن للمستثمر فهمها؟"),
    ("darija", "Moroccan Darija", "ary", "arabic", "jury_darija_dividend.wav",
     "شنو هو الديفيدوند وكيفاش كيستافد منو المستثمر؟"),
)


def prepare_audio(result):
    if result.mime_type.split(";", 1)[0].lower() in {"audio/pcm", "audio/l16"}:
        raw, rate, channels, width = (
            result.audio, result.sample_rate, result.channels, result.sample_width_bytes
        )
    else:
        with wave.open(io.BytesIO(result.audio), "rb") as source:
            rate, channels, width = (
                source.getframerate(), source.getnchannels(), source.getsampwidth()
            )
            raw = source.readframes(source.getnframes())
    if not rate or not channels or width != 2 or len(raw) % (2 * channels):
        raise ValueError("Expected complete signed 16-bit PCM audio")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64)
    samples = samples.reshape(-1, channels).mean(axis=1)
    if not samples.size or np.max(np.abs(samples)) < 100:
        raise ValueError("Provider returned empty or nearly silent audio")

    # Trim only the quiet outer edges, retaining 20 ms around detected activity.
    threshold = max(12.0, float(np.max(np.abs(samples))) * 0.002)
    activity = np.flatnonzero(np.abs(samples) > threshold)
    margin = round(rate * 0.02)
    samples = samples[max(0, activity[0] - margin):min(len(samples), activity[-1] + margin + 1)]
    rms = float(np.sqrt(np.mean(samples ** 2)))
    gain = min(32767 * 0.10 / rms, 32767 * 10 ** (-1 / 20) / np.max(np.abs(samples)))
    samples = np.rint(samples * gain).astype("<i2")
    padded = np.concatenate((
        np.zeros(round(rate * 0.4), dtype="<i2"),
        samples,
        np.zeros(round(rate * 0.7), dtype="<i2"),
    ))
    return padded.tobytes(), rate


def validate(path):
    header = path.read_bytes()[:12]
    if header[:4] != b"RIFF" or header[8:] != b"WAVE":
        raise ValueError("Invalid RIFF/WAVE header")
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
            raise ValueError("Expected uncompressed mono 16-bit WAV")
        rate, frames = wav.getframerate(), wav.getnframes()
        data = wav.readframes(frames)
    if len(data) != frames * 2:
        raise ValueError("Truncated WAV data")
    samples = np.frombuffer(data, dtype="<i2").astype(np.float64)
    duration = frames / rate
    peak = float(np.max(np.abs(samples)))
    if not 2 <= duration <= 30 or peak < 100 or peak >= 32767:
        raise ValueError("Unreasonable duration, silent audio, or clipping")
    if np.any(samples[:round(rate * 0.4)]) or np.any(samples[-round(rate * 0.7):]):
        raise ValueError("Missing required silence padding")
    return {
        "file_exists": True, "valid_wav_header": True, "complete_pcm_data": True,
        "duration_seconds": round(duration, 3), "nonzero_audio": True,
        "sample_rate_hz": rate, "channels": 1, "bits_per_sample": 16,
        "peak_dbfs": round(20 * math.log10(peak / 32768), 2),
        "leading_silence_added_seconds": 0.4, "trailing_silence_added_seconds": 0.7,
    }


def normalized(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c))


def write_readme(records):
    lines = [
        "EduBourse jury audio questions", "",
        "Playback from the repository root:",
        "powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 fr",
        "powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 en",
        "powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 ar",
        "powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 darija", "",
        "Generation (uses the existing environment and Gemini speech profiles):",
        r".\backend\.venv\Scripts\python.exe demo/jury_audio/generate_audio.py --verify-transcripts",
        "Optional content/pronunciation audit of existing WAVs:",
        r".\backend\.venv\Scripts\python.exe demo/jury_audio/generate_audio.py --audit-audio",
        "Existing WAV files are preserved unless --overwrite is supplied.",
        "WAV edges are trimmed conservatively, volume normalized without clipping,",
        "then 0.4 seconds of silence added before and 0.7 seconds after.",
        "Validation evidence is recorded in validation.json.", "",
        "Validation uses automated transcription and an audio-model audit; it is not",
        "a human listening review. Darija loanword spellings can differ in transcription.",
        "The requested text is passed to TTS exactly, including the Darija wording.", "",
    ]
    for record in records:
        lines.extend([
            f"LANGUAGE: {record['language']}",
            f"EXACT QUESTION: {record['question']}",
            f"FILENAME: {record['filename']}",
            f"DURATION: {record['duration_seconds']:.3f} seconds",
            f"AUDIO FORMAT: WAV, PCM signed 16-bit little-endian, mono, {record['sample_rate_hz']} Hz",
            f"TTS PROVIDER: {record['tts_provider']}",
            f"TTS MODEL: {record['tts_model']}",
            f"TTS VOICE: {record['tts_voice']}", "",
        ])
    (OUTPUT / "README.txt").write_text("\n".join(lines), encoding="utf-8-sig")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verify-transcripts", action="store_true")
    parser.add_argument("--audit-audio", action="store_true", help="Check speech content and delivery with the configured Gemini analysis model")
    parser.add_argument("--language", choices=[q[0] for q in QUESTIONS])
    args = parser.parse_args()
    settings = Settings(_env_file=PROJECT / ".env")
    provider = create_voice_provider(settings)
    report_path = OUTPUT / "validation.json"
    previous = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
    by_file = {r["filename"]: r for r in previous}
    for key, label, language, script, filename, question in QUESTIONS:
        if args.language and key != args.language:
            continue
        path = OUTPUT / filename
        generated = args.overwrite or not path.exists()
        if generated:
            print(f"Generating {key} with {settings.gemini_tts_model}/{settings.gemini_tts_voice}", flush=True)
            result = provider.synthesize(question, language=language, script=script)
            data, rate = prepare_audio(result)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(data)
        record = {} if generated else by_file.get(filename, {}).copy()
        if not generated and not record:
            raise ValueError("Existing WAV has no provenance; explicitly regenerate with --overwrite")
        record.update(validate(path))
        record.update({"language": label, "question": question, "filename": filename})
        if generated:
            record.update({"tts_provider": result.provider, "tts_model": result.model, "tts_voice": result.voice})
        by_file[filename] = record
        report_path.write_text(json.dumps(list(by_file.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        if args.verify_transcripts:
            transcript = provider.transcribe(AudioInput(
                data=path.read_bytes(), mime_type="audio/wav", filename=filename,
                duration_ms=round(record["duration_seconds"] * 1000),
            ))
            record["verification_stt_model"] = transcript.model
            record["transcript"] = transcript.text
            record["transcript_matches_ignoring_punctuation_case_spacing"] = normalized(question) == normalized(transcript.text)
            print(f"{key} transcript: {transcript.text}", flush=True)
        if args.audit_audio:
            from google.genai import types

            prompt = (
                "Audit the attached speech recording by listening to it. Return only JSON. "
                f"Expected language/dialect: {label}. Expected exact question: {question}\n"
                "Check that the audio contains this question only, with no introduction, answer, "
                "extra words, music, or effects. Check that neither beginning nor ending is cut off, "
                "and speech is clear and naturally paced. For English, IPO should be spoken as "
                "the letters I P O. For Darija, verify authentic Moroccan wording and pronunciation, "
                "not Modern Standard Arabic. The financial loanword الديفيدوند may be transcribed "
                "with alternative spellings; judge the spoken word and explain any difference. "
                "Do not assume the recording is correct. Use boolean fields question_only, "
                "wording_matches, language_and_dialect_match, clear_natural_speech, "
                "no_music_or_effects, beginning_complete, ending_complete, "
                "plus string fields heard_transcript and notes."
            )
            response = provider._get_client().models.generate_content(
                model=settings.gemini_localizer_model,
                contents=[prompt, types.Part.from_bytes(data=path.read_bytes(), mime_type="audio/wav")],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
            record["audio_audit_model"] = settings.gemini_localizer_model
            record["audio_audit"] = json.loads(response.text)
            checks = (
                "question_only", "wording_matches", "language_and_dialect_match",
                "clear_natural_speech", "no_music_or_effects", "beginning_complete", "ending_complete",
            )
            record["audio_audit_status"] = (
                "passed" if all(record["audio_audit"].get(check) is True for check in checks)
                else "needs_review"
            )
            print(f"{key} audio audit: {json.dumps(record['audio_audit'], ensure_ascii=False)}", flush=True)
        report_path.write_text(json.dumps(list(by_file.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{key}: {record['duration_seconds']:.3f}s; WAV validation passed", flush=True)
    records = [by_file[q[4]] for q in QUESTIONS if q[4] in by_file]
    write_readme(records)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid exposing provider credentials, HTTP headers or request URLs.
        print(f"Generation/validation failed: {type(exc).__name__}", file=sys.stderr)
        if hasattr(exc, "message"):
            secret = Settings(_env_file=PROJECT / ".env").gemini_api_key
            message = str(exc.message)
            if secret:
                message = message.replace(secret, "[REDACTED]")
            print(message, file=sys.stderr)
        cause = exc.__cause__
        if cause is not None:
            print(f"Cause type: {type(cause).__name__}", file=sys.stderr)
        raise SystemExit(1)
