# Voice runtime recovery — 20 September 2026

## Runtime repair

- `OLD_PID=23296`, `OLD_PROCESS=python.exe / Uvicorn`, started 00:08:11 local time. Parent 1832 was the `backend/.venv` Python launcher, not a second server.
- Verified working directory: `C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant\backend`.
- The original listener was the correct host backend. Starting another backend caused error 10048.
- Direct PostgreSQL `SELECT 1` took 0.032 seconds at `127.0.0.1`. With `localhost`, it took 5.172 seconds even with a five-second connection timeout; the original unbounded health connection hung.
- Changed only `POSTGRES_HOST` in the local `.env` from `localhost` to `127.0.0.1`.
- `ACTION=Stopped PID 23296 and restarted the host backend with corrected configuration and python -u`. New listener: PID 29672, launcher 27172. No Docker backend was started and no image was rebuilt.
- Vite PID 7680, started 00:10:12, retained. Verified working directory: the project's `frontend` directory. Exactly one frontend listener.
- PostgreSQL container `financial-education-assistant-postgres-1` retained; no database restart or data changes needed.

## Checks

| Item | Result |
|---|---|
| Backend | Running at 127.0.0.1:8080 |
| Liveness | HTTP 200 |
| Dependency health | HTTP 200, overall `ok` |
| PostgreSQL | `ok`; direct SELECT 1 passed |
| Active RAG index | `available`, 353 documents, `j6_bge_m3_content_v1` |
| Legacy Chroma HTTP service | Unavailable from host; marked legacy infrastructure, not the active persistent RAG index |
| Frontend | HTTP 200 at http://localhost:5173 |
| Actual Vite API target | http://localhost:8080, confirmed in served JavaScript |
| WebSocket | ws://localhost:8080/api/v1/voice/live; real Gemini `session.ready` received |
| Handshake request_id | `ba561f30-ad9f-4645-a0cb-b3680ab0e375` — readiness only, zero audio turns |
| Gemini connection | 7421 ms; first connection including model initialization took 35.39 seconds |
| Microphone | Previous user-provided result NORMAL: RMS 0.02264, peak 0.32883, zero ratio 0.0237; not remeasured yet |
| STT | Previous user-provided transcript: “C'est quoi une action ?”; no new audio turn yet |
| Language / route / grounding / citations | Awaiting real browser turn |
| Final answer / TTS / audible playback | Awaiting real browser turn; no quota failure established |

The microphone code remains unchanged: PCM16, 16 kHz, mono, 100 ms chunks, silence detection and signal UI. The existing error handler retains response text when TTS fails.

## Validation

- Voice, chat integration, security encoding, conversation/relevant memory and quiz: **218 passed**, two warnings.
- Additional health, final-response composer integration and shared-memory end-to-end regressions: **48 passed**, two warnings. Total: **266 passed**.
- TypeScript and Vite production build: **passed**. Fixed one missing closing brace at the end of `frontend/src/styles.css`; the subsequent build no longer emits the CSS syntax warning. The existing bundle-size advisory remains.
- Vitest: blocked because its executable is missing from the current node_modules; dependencies were not rebuilt.
- Ruff / Python compile for modified backend files: not applicable; no backend Python file changed.
- Files changed by this recovery: `.env`, `frontend/src/styles.css`, this report. Runtime logs were created; frontend `dist` was rebuilt. All pre-existing repository edits were preserved.

## Clean startup tomorrow (PowerShell)

The services are currently running. Reuse them; do not launch duplicates. The guards below stop a second launch if a port is already occupied. For an intentional restart, use Ctrl+C in the owning terminal, or inspect the listener command line before stopping its exact PID.

Terminal 1:

```powershell
Set-Location 'C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant'
if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) { throw '8080 already has a listener; reuse or inspect it before restarting.' }
docker compose up -d --no-deps --no-build postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
Set-Location backend
$env:POSTGRES_HOST = '127.0.0.1'
$env:RAG_WARMUP_ENABLED = 'true'
.\.venv\Scripts\python.exe -u -m uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8080 2>&1 | Tee-Object -FilePath ..\backend_demo.log
```

Wait for `Application startup complete` and `rag.retrieval_service.created` before the microphone demo; the first model load can take tens of seconds.

Terminal 2:

```powershell
Set-Location 'C:\Users\hp\OneDrive\Desktop\V2\financial-education-assistant\frontend'
if (Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue) { throw '5173 already has a listener; reuse or inspect it before restarting.' }
npm.cmd run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open http://localhost:5173. In the Voice page, record “C'est quoi une action ?”, stop recording, and wait for the text and audio response. The current backend logs are `backend_runtime.stdout.log` and `backend_runtime.stderr.log` at the project root. The startup command above writes future logs to `backend_demo.log`.

## Remaining validation

A real microphone/browser playback test requires the user: this session has no browser-control tool. A WebSocket readiness probe is not an end-to-end voice test. Until a real turn is observed, the requested trace stages have no fresh audio request to measure, and the verdict is `VOICE_TO_VOICE_RUNTIME_INCOMPLETE`.

The following presence values describe the fresh readiness-only request above. They do not indicate failures of stages that were never invoked.

| Stage | PRESENT | Duration |
|---|---|---|
| voice.stt.completed | false | N/A — no audio turn |
| request.started | false | N/A |
| language.completed | false | N/A |
| security.completed | false | N/A |
| memory.context.completed | false | N/A |
| supervisor.provider.completed | false | N/A |
| routing.completed | false | N/A |
| rag.completed | false | N/A |
| graph.completed | false | N/A |
| final_response.composed | false | N/A |
| request.completed | false | N/A |
| voice.tts.completed | false | N/A |

Final service state: `BACKEND_8080=RUNNING`, `FRONTEND_5173=RUNNING`, `POSTGRES=RUNNING`, `VOICE_WEBSOCKET=READY`.
