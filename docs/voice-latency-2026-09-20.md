# Voice text latency — implementation and validation

## Scope and result

Implemented the three requested low-risk changes. Azure composition, RAG, language handling, security decisions, STT model/timeout, PCM capture format and TTS implementation are unchanged.

The previous successful French voice trace is `ad2e0640-c786-43f7-9dcb-3bf6db214b96` in `backend_runtime.stdout.log`. The supplied browser baseline is **73,499 ms** from audio end to final text. No post-change audio turn has been observed yet, so no end-to-end improvement is claimed.

## Capture lifecycle

`useVoiceSession` now connects/reuses the socket and awaits Gemini `session.ready` before constructing or starting microphone capture. Connecting displays “Connexion au service vocal…”; successful capture displays “Prêt à parler”. Audio chunks stream as they arrive. The short queue is retained only for the final microphone flush during stop, not for connection-time recording. PCM16, 16 kHz, mono, 100 ms chunks and silence detection remain unchanged.

Repeated clicks are guarded synchronously. Reset/unmount invalidates pending starts, closes the old socket and stops late microphone acquisition. A stale connection completion cannot overwrite a replacement socket.

## Persistence breakdown and deferral

A temporary, isolated diagnostic thread used the actual PostgreSQL history store and semantic-memory runtime; its rows and semantic vectors were removed afterward. Model loading occurred before the timings below. These are component measurements, not a replacement for the live voice benchmark.

| Component | First sample | Second sample |
|---|---:|---:|
| history_store.append_turn | 98.32 ms | 48.08 ms |
| memory_runtime.index_canonical_messages | 17,980.95 ms | 3,941.18 ms |

For voice, canonical user/assistant history still commits synchronously before `response.text`. Only semantic indexing is registered in Starlette `BackgroundTasks` and awaited after sending text. It runs in a worker thread, remains owned by the voice turn and completes before TTS starts. It is not an untracked task. A send failure also drains the registered work. Canonical continuity does not depend on the semantic index, and index failures remain logged and nonfatal. Ordinary HTTP chat keeps its existing synchronous indexing behavior.

New events separate `persistence.history.append.completed`, `persistence.history.completed` (the synchronous voice persistence stage), and `memory.index.completed`/`memory.index.failed` (deferred enrichment).

## Security warmup

Startup launches a single background thread that loads and primes the existing local security classifier. A lock prevents duplicate model loading if a request arrives during warmup. No thresholds, rules or classifier artifacts changed. Failure is logged and normal fail-closed handling remains intact.

Measured warmup: **2,235.08 ms**, outside the application startup wait. `Application startup complete` and Uvicorn readiness were logged normally. Backend PID **27892** owns 8080; Vite PID **7680** remains on 5173. Health is `ok`; PostgreSQL is reachable; the active persistent RAG index contains 353 documents. Gemini `session.ready` was verified with a zero-audio readiness probe.

## Tests and build

- **264 backend tests passed**, two dependency warnings: voice, canonical history, recent/relevant/shared memory, security, chat and final composer integration, shared-memory end-to-end tests.
- **4 frontend lifecycle tests passed** using the real hook bundled by the existing esbuild and Node's built-in test runner. Controlled media/socket adapters cover delayed readiness, progressive chunks, final PCM flush, socket reuse, connection failure, reset during connection and reset during permission acquisition.
- New backend tests verify committed next-turn history before enrichment, continuity after enrichment failure, synchronous commit failure, text delivery before a blocked indexer finishes, unchanged security decisions, one-time nonblocking warmup and concurrent model loading.
- Ruff and Python compilation passed for all changed Python files.
- TypeScript and Vite production build passed; only the existing bundle-size advisory remains.
- Vitest remains unavailable in the existing node_modules; no dependency-tree rebuild was needed. The new lifecycle tests execute without Vitest.
- No regression detected by these checks. Live latency and browser behavior remain to be measured.

## Before/after benchmark

| Requested metric | Before (ms) | After (ms) |
|---|---:|---:|
| GEMINI_CONNECT_MS | approximately 3,800 | Pending browser turn |
| AUDIO_DURATION_MS | See baseline trace | Pending |
| AUDIO_END_TO_FINAL_TRANSCRIPT_MS | approximately 18,300 | Pending |
| SECURITY_MS | 3,296.36 | Pending; startup warmup completed |
| MEMORY_CONTEXT_MS | 3,811.27 | Pending |
| SUPERVISOR_MS | 1,176.67 | Pending |
| RAG_RETRIEVAL_MS | 2,034.55 | Pending |
| RAG_GENERATION_MS | 7,893.35 | Pending |
| AZURE_MS | 27,378.01 | Pending |
| PERSISTENCE_SYNC_MS | 7,463.96, formerly including indexing | Pending voice measurement |
| AUDIO_END_TO_FINAL_ANSWER_MS | **73,499** | **Not measured** |

Server event `voice.text.sent.duration_ms` now measures from receipt of `audio.end` to sending the final text, including audio diagnostics and STT finalization. `voice.stt.completed.audio_end_to_final_transcript_ms` uses the same starting point. These server timings must not be mislabeled as browser display latency.

The browser emits `voice.browser.text_displayed` after React commits the response. Its `audio_end_to_final_answer_ms` is the browser metric to compare with 73,499 ms. Preserve this console value and request_id for the single French test.

Extract the latest completed server text trace from the project root:

```powershell
.\backend\.venv\Scripts\python.exe scripts/voice_latency_report.py
```

Missing stages remain `null`; the tool does not infer success or synthesize timings. Current logs are `backend_latency.stdout.log` and `backend_latency.stderr.log`.

## Files changed in this phase

- `frontend/src/components/voice/useVoiceSession.ts`
- `frontend/src/components/voice/VoiceControl.tsx`
- `frontend/tests/voice-lifecycle.test.mjs`
- `backend/app/api/chat.py`
- `backend/app/api/voice.py`
- `backend/app/graph/intent.py`
- `backend/app/graph/security_warmup.py`
- `backend/app/main.py`
- `backend/tests/unit/test_voice_latency_memory.py`
- `backend/tests/unit/test_security_warmup.py`
- `backend/tests/voice/test_websocket.py`
- `scripts/voice_latency_report.py`
- This report.

Frontend build artifacts and runtime logs were also generated. Pre-existing user edits were retained.

## Pending live step

Refresh http://localhost:5173, open Voice, click the microphone and wait for “Prêt à parler”. Say “C'est quoi une action ?”, then stop. Keep services running. Only one real audio benchmark is requested. This agent session has no browser-control tool; user participation is needed for physical microphone input and the browser-console timing.

Verdict until that measurement is available: **VOICE_TEXT_LATENCY_OPTIMIZATION_INCOMPLETE**.
