"""Capture real responses through EduBourse's normal HTTP chat endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
QUESTIONS = {
    "fr": "Quelle est la différence entre une action et une obligation, notamment en termes de propriété, de rendement et de risque ?",
    "en": "How does an IPO work, and why does a company choose to go public?",
    "ar": "ما هي أهم مخاطر الاستثمار في البورصة وكيف يمكن للمستثمر فهمها؟",
    "darija": "شنو هو الديفيدوند وكيفاش كيستافد منو المستثمر؟",
}


def save(records):
    (OUTPUT / "jury_answers.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def attach_traces(records):
    log = OUTPUT / "backend.stdout.log"
    events = []
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
                if isinstance(item, dict) and item.get("request_id"):
                    events.append(item)
            except json.JSONDecodeError:
                continue
    for record in records.values():
        trace = [e for e in events if e["request_id"] == record["request_id"]]
        record["pipeline_trace"] = trace
        composed = next((e for e in reversed(trace) if e.get("event") == "final_response.composed"), None)
        record["final_composer_status"] = composed.get("composer_status") if composed else None
        record["final_composer_metadata"] = composed
        record["degraded"] = (
            record.get("status") != "ok" or record.get("language") != {"darija": "ary"}.get(record["demo_language"], record["demo_language"])
            or bool(composed and (composed.get("fallback_used") or composed.get("language_degraded")))
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--refresh-metadata", action="store_true")
    args = parser.parse_args()
    result_path = OUTPUT / "jury_answers.json"
    records = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    if args.refresh_metadata:
        attach_traces(records)
        save(records)
        return
    with httpx.Client(timeout=httpx.Timeout(900, connect=10), trust_env=False) as client:
        live = client.get(args.base_url + "/api/v1/health/live")
        live.raise_for_status()
        (OUTPUT / "backend_liveness.json").write_text(live.text, encoding="utf-8")
        for language, question in QUESTIONS.items():
            if language in records:
                print(f"Preserving previously captured {language} response", flush=True)
                continue
            thread_id = f"jury-{language}-{uuid.uuid4().hex}"
            request_id = str(uuid.uuid4())
            payload = {"message": question, "thread_id": thread_id}
            (OUTPUT / f"{language}_request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Requesting {language}: thread_id={thread_id}", flush=True)
            started = time.perf_counter()
            response = client.post(args.base_url + "/api/v1/chat", json=payload, headers={"x-request-id": request_id})
            latency = time.perf_counter() - started
            # Preserve complete response bytes even for an HTTP error.
            (OUTPUT / f"{language}_backend_result.json").write_bytes(response.content)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result.get("answer"), str) or not result["answer"]:
                raise ValueError("Backend returned no answer")
            (OUTPUT / f"{language}_answer.txt").write_text(result["answer"], encoding="utf-8")
            records[language] = {
                "question": question, "answer": result["answer"],
                "language": result.get("language"), "script": result.get("script"),
                "route": result.get("route"), "status": result.get("status"),
                "grounded": result.get("grounded"),
                "citations_count": len(result.get("citations", [])),
                "citations": result.get("citations", []),
                "latency_seconds": round(latency, 3),
                "thread_id": result.get("thread_id"), "request_id": response.headers.get("x-request-id", request_id),
                "demo_language": language, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "endpoint": args.base_url + "/api/v1/chat", "http_status": response.status_code,
                "backend_result": result,
                "answer_sha256": hashlib.sha256(result["answer"].encode("utf-8")).hexdigest(),
            }
            attach_traces(records)
            save(records)
            print(f"{language}: route={result.get('route')}, language={result.get('language')}, status={result.get('status')}, grounded={result.get('grounded')}, citations={len(result.get('citations', []))}, latency={latency:.3f}s", flush=True)
    attach_traces(records)
    save(records)


if __name__ == "__main__":
    main()
