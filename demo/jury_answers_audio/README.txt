EDUBOURSE — AUDIO OF REAL CAPTURED RESPONSES

AVAILABLE

fr_response.wav: complete French answer, 104.687 seconds.
fr_response_demo.wav: SHORTENED PLAYBACK VERSION, 24.554 seconds.
fr_response_demo.txt: exact unchanged prefix used for shortened playback,
ending after the first three complete sentences; leading headings are retained.

UNAVAILABLE

en_response.wav, ar_response.wav and darija_response.wav were not completed.
Gemini returned rate_limit_exceeded; its actual message reports a Free Tier
limit of 10 requests per day. See tts_service_status.json for the returned error.
Repeated attempts, including waiting before retrying, did not complete these files.
The chunks directory contains cached speech segments, not substitute full answers.

SOURCE AND FIDELITY

All answer text originates exclusively from the normal EduBourse chat endpoint.
The generator reads ../jury_answers/jury_answers.json and checks its answer
against both the complete HTTP result and the corresponding TXT file.
No standalone LLM generates, summarizes, translates or rewrites the responses.
Each long answer is split into exact consecutive text spans. Concatenating those
spans reproduces the original text character for character. Speech segments are
assembled with 0.25-second pauses, 0.4 seconds before and 0.7 seconds after.

Provider: gemini
Model: gemini-2.5-flash-preview-tts
Voice: Kore
Format: WAV, mono, 24000 Hz, signed 16-bit PCM.
audio_manifest.json records exact inputs, hashes, durations and provider metadata.
audio_validation.json records available and blocked outputs.

The saved Darija business response is itself a controlled error caused by the
grounded-generation provider rate limit. If later synthesized, the audio generator
will speak that exact error response; it will not replace it with a new answer.

PLAYBACK FROM ANY DIRECTORY

powershell -ExecutionPolicy Bypass -File "C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant\demo\jury_answers_audio\play_response.ps1" fr
powershell -ExecutionPolicy Bypass -File "C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant\demo\jury_answers_audio\play_response.ps1" fr -Demo

RESUME OPTIONAL AUDIO WHEN GEMINI QUOTA IS AVAILABLE

From the repository root:
.\backend\.venv\Scripts\python.exe demo/jury_answers_audio/generate_responses.py

Existing answers and completed audio segments are preserved. No chat request is
resent, and production configuration and code remain unchanged.
