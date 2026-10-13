"""Bounded selection of actual HTTP responses; never changes application logic."""

import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
PREVIOUS = PROJECT / "demo/jury_answers"
ENDPOINT = "http://127.0.0.1:8080/api/v1/chat"
QUESTIONS = {
    "fr": "Quelle est la différence entre une action et une obligation ?",
    "darija_primary": "شنو الفرق بين السهم والسند؟",
    "darija_alternative": "شنو هي المخاطر ديال الاستثمار فالبورصة؟",
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def trace_for(request_id):
    events = []
    for line in (PREVIOUS / "backend.stdout.log").read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("request_id") == request_id:
            events.append(event)
    return events


def accepted(record, language):
    return (
        record.get("status") == "ok" and record.get("route") == "pedagogie"
        and record.get("grounded") is True and record.get("citations_count", 0) >= 1
        and record.get("language") == language
        and record.get("script") == ("arabic" if language == "ary" else "latin")
        and bool(record.get("answer"))
    )


def main():
    attempts_path = OUT / "attempts.json"
    attempts = json.loads(attempts_path.read_text(encoding="utf-8")) if attempts_path.exists() else []
    selected_path = OUT / "jury_answers_final.json"
    selected = json.loads(selected_path.read_text(encoding="utf-8")) if selected_path.exists() else {}
    previous = json.loads((PREVIOUS / "jury_answers.json").read_text(encoding="utf-8"))
    for key in ("en", "ar"):
        assert previous[key]["status"] == "ok" and previous[key]["grounded"] is True
        assert previous[key]["citations_count"] >= 1
        selected[key] = previous[key]
        shutil.copyfile(PREVIOUS / f"{key}_answer.txt", OUT / f"{key}_answer.txt")
    write_json(selected_path, selected)

    snapshot_path = OUT / "production_hashes_before.json"
    if not snapshot_path.exists():
        paths = [p for base in ("backend/app", "frontend/src") for p in (PROJECT / base).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        paths += [PROJECT / name for name in (".env", "docker-compose.yml", "backend/pyproject.toml")]
        write_json(snapshot_path, {p.relative_to(PROJECT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        old_files = [p for p in PREVIOUS.iterdir() if p.is_file() and p.suffix in (".json", ".txt")]
        write_json(OUT / "previous_capture_hashes.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in old_files})

    with httpx.Client(timeout=httpx.Timeout(900, connect=10), trust_env=False) as client:
        client.get(ENDPOINT.replace("/chat", "/health/live")).raise_for_status()

        def execute(key, number):
            existing = next((r for r in attempts if r["case"] == key and r["attempt_number"] == number), None)
            if existing is not None:
                return existing
            language = "fr" if key == "fr" else "ary"
            request_id = str(uuid.uuid4())
            payload = {"message": QUESTIONS[key], "thread_id": f"jury-final-{key.replace('_', '-')}-{uuid.uuid4().hex}"}
            record = {"case": key, "attempt_number": number, "question": payload["message"], "thread_id": payload["thread_id"], "request_id": request_id, "execution_state": "submitted", "endpoint": ENDPOINT, "submitted_at_utc": datetime.now(timezone.utc).isoformat()}
            # Reserve the attempt before sending: rerunning cannot exceed the limits.
            attempts.append(record)
            write_json(attempts_path, attempts)
            stem = f"{key}_{number}"
            write_json(OUT / f"{stem}_request.json", payload)
            print(f"Executing {key} attempt {number}", flush=True)
            started = time.perf_counter()
            try:
                response = client.post(ENDPOINT, json=payload, headers={"x-request-id": request_id})
                record["latency_seconds"] = round(time.perf_counter() - started, 3)
                record["http_status"] = response.status_code
                (OUT / f"{stem}_backend_result.json").write_bytes(response.content)
                result = response.json()
                record["backend_result"] = result
                for field in ("answer", "language", "script", "route", "status", "grounded", "citations"):
                    record[field] = result.get(field)
                record["citations"] = record["citations"] or []
                record["citations_count"] = len(record["citations"])
                record["execution_state"] = "completed"
                if isinstance(record["answer"], str):
                    record["answer_sha256"] = hashlib.sha256(record["answer"].encode("utf-8")).hexdigest()
            except Exception as exc:
                record["execution_state"] = "transport_error"
                record["error_type"] = type(exc).__name__
                record["latency_seconds"] = round(time.perf_counter() - started, 3)
            events = trace_for(request_id)
            record["pipeline_trace"] = events
            composed = next((e for e in reversed(events) if e.get("event") == "final_response.composed"), None)
            record["final_composer_metadata"] = composed
            record["final_composer_status"] = composed.get("composer_status") if composed else None
            record["accepted"] = accepted(record, language)
            record["external_provider_error"] = any(
                e.get("generation_status") in ("generation_provider_error", "generation_provider_unavailable")
                or e.get("event") in ("supervisor.provider_init_failed", "final_response.composer_failed")
                or e.get("error_type") in ("RateLimitError", "APITimeoutError", "APIConnectionError")
                for e in events
            ) and not record["accepted"]
            write_json(attempts_path, attempts)
            print(f"{key}/{number}: status={record.get('status')} language={record.get('language')} route={record.get('route')} grounded={record.get('grounded')} citations={record.get('citations_count')} latency={record['latency_seconds']}s accepted={record['accepted']} external_provider_error={record['external_provider_error']}", flush=True)
            return record

        def select(key, record):
            if record.get("accepted"):
                selected[key] = record
                (OUT / f"{key}_answer.txt").write_text(record["answer"], encoding="utf-8")
                write_json(selected_path, {k: selected[k] for k in ("fr", "en", "ar", "darija") if k in selected})

        if "fr" not in selected:
            select("fr", execute("fr", 1))
        if "darija" not in selected:
            record = execute("darija_primary", 1)
            if not record.get("accepted") and record.get("external_provider_error"):
                print("External provider failure: waiting 20 seconds before the single controlled retry", flush=True)
                time.sleep(20)
                record = execute("darija_primary", 2)
            if not record.get("accepted"):
                record = execute("darija_alternative", 1)
            select("darija", record)
    print(f"Selected languages: {', '.join(selected)}", flush=True)


if __name__ == "__main__":
    main()
