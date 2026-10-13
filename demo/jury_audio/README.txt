EduBourse jury audio questions

Playback from the repository root:
powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 fr
powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 en
powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 ar
powershell -ExecutionPolicy Bypass -File demo/jury_audio/play_demo.ps1 darija

Generation (uses the existing environment and Gemini speech profiles):
.\backend\.venv\Scripts\python.exe demo/jury_audio/generate_audio.py --verify-transcripts
Optional content/pronunciation audit of existing WAVs:
.\backend\.venv\Scripts\python.exe demo/jury_audio/generate_audio.py --audit-audio
Existing WAV files are preserved unless --overwrite is supplied.
WAV edges are trimmed conservatively, volume normalized without clipping,
then 0.4 seconds of silence added before and 0.7 seconds after.
Validation evidence is recorded in validation.json.

Validation uses automated transcription and an audio-model audit; it is not
a human listening review. Darija loanword spellings can differ in transcription.
The requested text is passed to TTS exactly, including the Darija wording.

LANGUAGE: French
EXACT QUESTION: Quelle est la différence entre une action et une obligation, notamment en termes de propriété, de rendement et de risque ?
FILENAME: jury_fr_action_vs_obligation.wav
DURATION: 8.414 seconds
AUDIO FORMAT: WAV, PCM signed 16-bit little-endian, mono, 24000 Hz
TTS PROVIDER: gemini
TTS MODEL: gemini-2.5-flash-preview-tts
TTS VOICE: Kore

LANGUAGE: English
EXACT QUESTION: How does an IPO work, and why does a company choose to go public?
FILENAME: jury_en_ipo.wav
DURATION: 5.789 seconds
AUDIO FORMAT: WAV, PCM signed 16-bit little-endian, mono, 24000 Hz
TTS PROVIDER: gemini
TTS MODEL: gemini-2.5-flash-preview-tts
TTS VOICE: Kore

LANGUAGE: Modern Standard Arabic
EXACT QUESTION: ما هي أهم مخاطر الاستثمار في البورصة وكيف يمكن للمستثمر فهمها؟
FILENAME: jury_ar_investment_risks.wav
DURATION: 6.631 seconds
AUDIO FORMAT: WAV, PCM signed 16-bit little-endian, mono, 24000 Hz
TTS PROVIDER: gemini
TTS MODEL: gemini-2.5-flash-preview-tts
TTS VOICE: Kore

LANGUAGE: Moroccan Darija
EXACT QUESTION: شنو هو الديفيدوند وكيفاش كيستافد منو المستثمر؟
FILENAME: jury_darija_dividend.wav
DURATION: 4.284 seconds
AUDIO FORMAT: WAV, PCM signed 16-bit little-endian, mono, 24000 Hz
TTS PROVIDER: gemini
TTS MODEL: gemini-2.5-flash-preview-tts
TTS VOICE: Kore
