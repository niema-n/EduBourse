FINAL JURY RESPONSE AUDIO — PARTIAL, STOPPED ON GEMINI QUOTA

AVAILABLE
darija_response_demo.wav — 24.282 seconds.
This is the exact first three complete sentences, with the original leading
headings retained, from ../jury_answers_final/darija_answer.txt.
Format: WAV, mono, 24000 Hz, 16-bit PCM, normal volume.

UNAVAILABLE
darija_response_full.wav
fr_response_demo.wav / fr_response_full.wav
en_response_demo.wav / en_response_full.wav
ar_response_demo.wav / ar_response_full.wav

The latest authorized run generated the Darija demo, then Gemini returned
rate_limit_exceeded on the Darija full version. It reports a Free Tier limit
of 10 requests per day. Generation stopped immediately; no further provider
request was sent. Existing WAVs are preserved. A previous connection failure
and previous campaign stops remain archived as generation_status_before_*.json.

Provider: Gemini
Model: gemini-2.5-flash-preview-tts
Voice: Kore
Latest run: 2 TTS requests; no retry after the quota error.
Sequential order: Darija, French, English, Arabic; demo then full per language.

SOURCE OF TRUTH
Only the four existing *_answer.txt files in ../jury_answers_final/ were read
for response content. No chat endpoint, Groq or Azure OpenAI call was made.
No answer was regenerated, rewritten, summarized or translated.
The authoritative files and production source/configuration hashes are unchanged.

VALIDATION
validation.json records WAV integrity, non-zero samples, silence padding,
Windows decoding and exact correspondence between TTS input and source text.
The Darija demo was also played through play_response.ps1 successfully.
Independent spoken-word and pronunciation review was not performed.
Silence/payload checks alone are not a semantic proof of every spoken word.

PLAYBACK — DEFAULT IS THE DEMO VERSION
From the repository root:
powershell -ExecutionPolicy Bypass -File demo/jury_answers_audio_final/play_response.ps1 darija

From any directory:
powershell -ExecutionPolicy Bypass -File "C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant\demo\jury_answers_audio_final\play_response.ps1" darija

The player supports fr, en, ar, darija and fr-full, en-full, ar-full, darija-full.
Missing recordings print an explicit message and exit with code 2.
No external audio player is required.

EVIDENCE AND RESUMPTION
generation_status.json: actual latest service error and immediate stop.
audio_plan.json: exact excerpt texts and planned filenames.
audio_manifest.json: generated WAV metadata and exact TTS input spans.
final_report.txt: requested output fields and blocked verdict.

The generator will not retry a recorded stop automatically. A later explicitly
authorized run can use --new-run; completed files are retained and source hashes
must match. This does not regenerate any EduBourse answer.
