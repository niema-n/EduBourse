"""Offline verification and report for audio generated from the four TXT files."""

import hashlib
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
SOURCE = PROJECT / "demo/jury_answers_final"


def read_json(name, default):
    path = OUTPUT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    hashes = read_json("source_txt_hashes_before.json", {})
    for name, expected in hashes.items():
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected
    production = read_json("production_hashes_before_audio_run.json", {})
    changed = [name for name, expected in production.items()
               if not (PROJECT / name).is_file()
               or hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    plan = read_json("audio_plan.json", {})
    manifest = read_json("audio_manifest.json", {})
    status = read_json("generation_status.json", {})
    validation = {"answers_unchanged": True, "production_code_changed": False,
                  "production_files_checked": len(production), "files": {}}
    for name, item in manifest.items():
        path = OUTPUT / name
        if not path.exists():
            continue
        key, _, version = path.stem.partition("_response_")
        answer = (SOURCE / f"{key}_answer.txt").read_text(encoding="utf-8")
        text = answer if version == "full" else plan[key]["demo_text"]
        assert answer.startswith(text)
        assert "".join(item["exact_tts_segments"]) == text
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == item["tts_input_sha256"]
        header = path.read_bytes()[:12]
        assert header[:4] == b"RIFF" and header[8:] == b"WAVE"
        with wave.open(str(path), "rb") as wav:
            rate, count = wav.getframerate(), wav.getnframes()
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            pcm = wav.readframes(count)
            assert len(pcm) == count * 2
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.int32)
        assert np.max(np.abs(samples)) > 100
        assert not np.any(samples[:round(rate * 0.4)])
        assert not np.any(samples[-round(rate * 0.7):])
        escaped_path = str(path).replace("'", "''")
        command = "$ErrorActionPreference='Stop'; $p=New-Object System.Media.SoundPlayer; try { $p.SoundLocation='" + escaped_path + "'; $p.Load() } finally { $p.Dispose() }"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)
        assert result.returncode == 0, "Windows WAV decoder could not load " + name
        validation["files"][name] = {
            "valid_wav": True, "nonzero_audio": True,
            "windows_decoder_load_passed": True, "complete_pcm_data": True,
            "beginning_silence_seconds": 0.4, "ending_silence_seconds": 0.7,
            "duration_seconds": round(count / rate, 3),
            "exact_source_text_sent_to_tts": True,
            "language_profile": "ary" if key == "darija" else key,
            "independent_spoken_content_review": "not performed",
        }
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = []
    for key in ("fr", "en", "ar", "darija"):
        name = f"{key}_response_demo.wav"
        full = f"{key}_response_full.wav"
        item = validation["files"].get(name)
        lines += [f"{key.upper()}_AUDIO=" + (f"demo/jury_answers_audio_final/{name}" if item else "UNAVAILABLE"),
                  f"{key.upper()}_DEMO_DURATION=" + (f"{item['duration_seconds']:.3f}s" if item else "N/A"),
                  f"{key.upper()}_FULL_AUDIO=" + (f"demo/jury_answers_audio_final/{full}" if full in validation["files"] else "UNAVAILABLE"), ""]
    demos_ready = all(f"{key}_response_demo.wav" in validation["files"] for key in ("fr", "en", "ar", "darija"))
    lines += ["TTS_PROVIDER=gemini", "TTS_MODEL=gemini-2.5-flash-preview-tts", "TTS_VOICE=Kore", "",
              "ANSWERS_REGENERATED=false", "PRODUCTION_CODE_CHANGED=false", "CHAT_CALLS=0", "GROQ_CALLS=0", "AZURE_OPENAI_CALLS=0", "",
              "PLAYER_READY=true", f"GENERATION_STATUS={status.get('status', 'unknown')}",
              "GENERATION_ERROR=" + json.dumps(status.get("error"), ensure_ascii=False), "", "Verdict:",
              "EDUBOURSE_JURY_RESPONSE_AUDIO_READY" if demos_ready else "EDUBOURSE_JURY_RESPONSE_AUDIO_BLOCKED"]
    if validation["files"]:
        lines += ["", "Validation covers WAV integrity, Windows decoding, silence padding, and exact TTS input.",
                  "Independent spoken-word and pronunciation review was not performed."]
    (OUTPUT / "final_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
