"""Resumable, interleaved FIX3F6 Groq evaluation on validation only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).parent))
from prepare_j3_intent_dataset import load_rows, split_rows

from app.graph.supervisor import (
    SUPERVISOR_INSTRUCTION,
    SupervisorRequest,
    parse_route_decision,
)
from app.llm.base import ProviderUnavailable
from app.llm.factory import create_provider

BATCH_SIZE = 20
MAX_RETRIES = 2
MIN_REQUEST_INTERVAL_SECONDS = 10.0
ROUTES = [
    "pedagogie",
    "formation_elearning",
    "orientation",
    "cisi",
    "quiz",
    "championnat",
    "support_ecole",
    "out_of_domain",
]


def validation_rows(dataset: Path) -> list[dict[str, str]]:
    routing = [row for row in load_rows(dataset) if row["task"] == "routing"]
    return interleaved_rows(split_rows(routing)[1])


def manifest_rows(dataset: Path, manifest: Path) -> list[dict[str, str]]:
    rows = {row["id"]: row for row in validation_rows(dataset)}
    manifest_ids = json.loads(manifest.read_text(encoding="utf-8"))["validation_ids"]
    if len(manifest_ids) != len(set(manifest_ids)) or set(manifest_ids) != set(rows):
        raise ValueError("FIX3F6 manifest does not match the frozen validation set")
    return [rows[row_id] for row_id in manifest_ids]


def interleaved_rows(rows: list[dict[str, str]], seed: int = 42) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {route: [] for route in ROUTES}
    for row in rows:
        grouped[row["label"]].append(row)
    rng = random.Random(seed)
    for values in grouped.values():
        rng.shuffle(values)
    output = []
    while any(grouped.values()):
        for route in ROUTES:
            if grouped[route]:
                output.append(grouped[route].pop())
    return output


def fingerprint(model: str) -> str:
    schema = {"version": "SupervisorRouteDecision-v1", "routes": ROUTES}
    value = json.dumps(
        {"model": model, "mode": "JSON_OBJECT", "prompt": SUPERVISOR_INSTRUCTION, "schema": schema},
        sort_keys=True,
    )
    return hashlib.sha256(value.encode()).hexdigest()


def load_jsonl(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            result[item["validation_id"]] = item
    return result


def append_jsonl(path: Path, item: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        handle.flush()


def error_kind(exc: Exception) -> tuple[str, str | None, dict[str, str]]:
    name = type(exc).__name__.lower()
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    safe_headers = {
        key: str(headers[key])
        for key in (
            "x-ratelimit-limit-requests",
            "x-ratelimit-remaining-requests",
            "x-ratelimit-reset-requests",
            "x-ratelimit-limit-tokens",
            "x-ratelimit-remaining-tokens",
            "x-ratelimit-reset-tokens",
            "retry-after",
        )
        if headers.get(key) is not None
    }
    retry_after = safe_headers.get("retry-after")
    if "rate" in name or "429" in str(exc) or "rate" in str(exc).lower():
        return "PROVIDER_RATE_LIMIT", retry_after, safe_headers
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return "TIMEOUT", retry_after, safe_headers
    return "OTHER_PROVIDER_FAILURE", retry_after, safe_headers


def rate_limit_type(headers: dict[str, str]) -> str:
    """Classify only when a remaining counter proves which limit is exhausted."""

    if headers.get("x-ratelimit-remaining-tokens") == "0":
        return "TPM_OR_TPD"
    if headers.get("x-ratelimit-remaining-requests") == "0":
        return "RPM_OR_RPD"
    return "UNKNOWN"


def parse_reset_seconds(value: str | None) -> float | None:
    if not value:
        return None
    if str(value).replace(".", "", 1).isdigit():
        return float(value)
    matches = re.findall(r"(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h)", value)
    if not matches:
        return None
    multipliers = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
    return sum(float(number) * multipliers[unit] for number, unit in matches)


def token_reset_delay(headers: dict[str, str], threshold: int = 1000) -> float:
    remaining = headers.get("x-ratelimit-remaining-tokens")
    reset = parse_reset_seconds(headers.get("x-ratelimit-reset-tokens"))
    if remaining is None or reset is None or int(remaining) > threshold:
        return 0.0
    return reset + 1.0


def retry_delay(kind: str, retry_after: str | None, consecutive_rates: int, attempt: int) -> float:
    if retry_after and str(retry_after).replace(".", "", 1).isdigit():
        return float(retry_after) + 1.0
    if kind == "PROVIDER_RATE_LIMIT":
        return 60.0 if consecutive_rates == 1 else 90.0
    return float(15 * (2 ** (attempt - 1)))


def attempt_category(provider_result_type: str) -> str:
    categories = {
        "SUCCESS": "success",
        "PROVIDER_RATE_LIMIT": "rate_limit",
        "TIMEOUT": "timeout",
        "OTHER_PROVIDER_FAILURE": "other_failure",
    }
    try:
        return categories[provider_result_type]
    except KeyError as exc:
        raise ValueError(f"unknown provider result type: {provider_result_type}") from exc


def summarize_attempts(records: list[dict[str, object]]) -> dict[str, int]:
    counts = {"successes": 0, "rate_limits": 0, "timeouts": 0, "other_failures": 0}
    for record in records:
        category = attempt_category(str(record["provider_result_type"]))
        key = {
            "success": "successes",
            "rate_limit": "rate_limits",
            "timeout": "timeouts",
            "other_failure": "other_failures",
        }[category]
        counts[key] += 1
    counts["attempts"] = sum(counts.values())
    return counts


def attempt_counter_invariant(counts: dict[str, int]) -> bool:
    return counts["attempts"] == sum(
        counts[key] for key in ("successes", "rate_limits", "timeouts", "other_failures")
    )


def make_manifest(path: Path, rows: list[dict[str, str]], model: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "validation_ids": [row["id"] for row in rows],
                "seed": 42,
                "model": model,
                "prompt_fingerprint": fingerprint(model),
                "schema_version": "SupervisorRouteDecision-v1",
                "structured_output_mode": "JSON_OBJECT",
                "dataset_sha256": (
                    "04b2065b0271647d26d74d8dd6311fa6e2c9ad174e2a6b6ed45a5811ceb74d3f"
                ),
                "started_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def run_batch(
    provider: object, rows: list[dict[str, str]], results_path: Path, attempts_path: Path
) -> dict[str, int]:
    counts = {
        "attempts": 0,
        "successful": 0,
        "rate_limits": 0,
        "timeouts": 0,
        "other_failures": 0,
        "circuit_breaker": 0,
    }
    last_request = 0.0
    consecutive_rates = 0
    for row in rows:
        for attempt in range(1, MAX_RETRIES + 2):
            wait = MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - last_request)
            if wait > 0:
                time.sleep(wait)
            last_request = time.monotonic()
            start = time.perf_counter()
            counts["attempts"] += 1
            try:
                request = SupervisorRequest(
                    user_message=row["text"],
                    business_language=row["language"],
                    script=row["script"],
                )
                decision = parse_route_decision(provider.invoke_structured(request))
                metadata = getattr(provider, "last_metadata", {}) or {}
                append_jsonl(
                    results_path,
                    {
                        "validation_id": row["id"],
                        "expected_route": row["label"],
                        "predicted_route": decision.route,
                        "expected_domain": "out_of_domain"
                        if row["label"] == "out_of_domain"
                        else "in_domain",
                        "predicted_domain": decision.domain_status,
                        "language": row["language"],
                        "script": row["script"],
                        "parse_success": True,
                        "fallback": decision.route == "fallback",
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                        "token_usage": metadata.get("token_usage"),
                        "rate_limit_headers": metadata.get("rate_limit_headers", {}),
                    },
                )
                header_wait = token_reset_delay(metadata.get("rate_limit_headers", {}))
                if header_wait:
                    time.sleep(header_wait)
                counts["successful"] += 1
                consecutive_rates = 0
                break
            except Exception as exc:
                kind, retry_after, headers = error_kind(exc)
                counts["rate_limits"] += kind == "PROVIDER_RATE_LIMIT"
                counts["timeouts"] += kind == "TIMEOUT"
                counts["other_failures"] += kind == "OTHER_PROVIDER_FAILURE"
                append_jsonl(
                    attempts_path,
                    {
                        "validation_id": row["id"],
                        "attempt_number": attempt,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "provider_result_type": kind,
                        "rate_limit_type": (
                            rate_limit_type(headers) if kind == "PROVIDER_RATE_LIMIT" else None
                        ),
                        "retry_after": retry_after,
                        "rate_limit_headers": headers,
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                        "token_usage": None,
                    },
                )
                if kind == "PROVIDER_RATE_LIMIT":
                    consecutive_rates += 1
                    if consecutive_rates >= 3:
                        counts["circuit_breaker"] = 1
                        return counts
                if attempt <= MAX_RETRIES:
                    time.sleep(retry_delay(kind, retry_after, consecutive_rates, attempt))
                else:
                    break
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/j3/contract_examples.jsonl"))
    parser.add_argument("--run-dir", type=Path, default=Path("results/j3_fix3f6"))
    parser.add_argument("--max-new-rows", type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    try:
        provider = create_provider()
    except ProviderUnavailable as exc:
        print(json.dumps({"provider": "unavailable", "reason": str(exc)}))
        return 2
    model = os.getenv("GROQ_MODEL", "")
    manifest_path = args.run_dir / "run1_manifest.json"
    rows = (
        manifest_rows(args.dataset, manifest_path)
        if manifest_path.exists()
        else validation_rows(args.dataset)
    )
    results_path = args.run_dir / "run1_results.jsonl"
    attempts_path = args.run_dir / "run1_attempts.jsonl"
    make_manifest(manifest_path, rows, model)
    completed = load_jsonl(results_path)
    missing = [row for row in rows if row["id"] not in completed][: args.max_new_rows]
    counts = run_batch(provider, missing, results_path, attempts_path)
    completed = load_jsonl(results_path)
    print(
        json.dumps(
            {
                "model": model,
                "prompt_fingerprint": fingerprint(model),
                "batch_size": BATCH_SIZE,
                "completed_rows": len(completed),
                "remaining_rows": len(rows) - len(completed),
                "counts": counts,
                "circuit_open": bool(counts["circuit_breaker"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
