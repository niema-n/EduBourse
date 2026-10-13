"""Bounded, process-local operational metrics derived from observability events."""

from __future__ import annotations

from collections import Counter
from threading import RLock
from typing import Any

HISTOGRAM_BUCKETS = (1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
ROUTES = (
    "pedagogie", "formation_elearning", "cisi", "quiz", "championnat",
    "orientation", "support_ecole", "out_of_domain", "securite", "fallback",
)
LANGUAGES = ("fr", "en", "ar", "ary")
SCRIPTS = ("latin", "arabic")
PROVENANCES = (
    "rag", "llm_general_financial_knowledge", "llm_web_grounded_financial_knowledge",
    "none",
)


class _Histogram:
    def __init__(self) -> None:
        self.count = 0
        self.total = 0.0
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.buckets = Counter({str(bucket): 0 for bucket in HISTOGRAM_BUCKETS})
        self.buckets["+Inf"] = 0

    def observe(self, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return
        duration = max(0.0, float(value))
        self.count += 1
        self.total += duration
        self.minimum = duration if self.minimum is None else min(self.minimum, duration)
        self.maximum = duration if self.maximum is None else max(self.maximum, duration)
        for bucket in HISTOGRAM_BUCKETS:
            if duration <= bucket:
                self.buckets[str(bucket)] += 1
        self.buckets["+Inf"] += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "average_ms": round(self.total / self.count, 2) if self.count else 0.0,
            "min_ms": self.minimum,
            "max_ms": self.maximum,
            "bucket_counts": dict(self.buckets),
        }


def _finite(value: Any, allowed: tuple[str, ...], default: str = "unknown") -> str:
    return value if isinstance(value, str) and value in allowed else default


class MetricsRegistry:
    """A bounded registry with finite labels and no content-bearing fields."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", RLock()):
            self._counters: dict[str, int] = Counter()
            self._labeled: dict[str, Counter[str]] = {}
            self._histograms: dict[str, _Histogram] = {}

    def _inc(self, name: str, label: str | None = None) -> None:
        self._counters[name] += 1
        if label is not None:
            self._labeled.setdefault(name, Counter())[label] += 1

    def observe_event(self, event: str, fields: dict[str, Any]) -> None:
        with self._lock:
            route = _finite(fields.get("route"), ROUTES)
            status = _finite(fields.get("response_status"), ("ok", "blocked", "error", "fallback"))
            modality = _finite(fields.get("modality"), ("text", "voice"))
            language = _finite(fields.get("language"), LANGUAGES)
            script = _finite(fields.get("script"), SCRIPTS)
            provenance = _finite(fields.get("knowledge_source"), PROVENANCES)

            if event == "request.completed":
                self._inc("requests_total")
                for name, value in (("by_modality", modality), ("by_status", status),
                                    ("by_route", route), ("by_language", language),
                                    ("by_script", script), ("by_provenance", provenance)):
                    self._inc(f"requests_total.{name}", value)
            elif event == "request.failed":
                self._inc("request_failures_total")

            if event.startswith("security."):
                self._inc("security_decisions_total")
                self._inc("security_decisions_total.by_status", _finite(
                    fields.get("security_status"), ("clear", "sensitive", "unknown")
                ))
                self._inc("security_risk_total")
                self._inc("security_risk_total.by_risk", _finite(
                    fields.get("risk_level"), ("none", "low", "medium", "high", "unknown")
                ))
            if event == "agent.completed":
                self._inc("agent_calls_total")
                self._inc("agent_calls_total.by_route", route)
            if event.startswith("rag."):
                self._inc("rag_calls_total")
                if event == "rag.completed":
                    if fields.get("grounded") is True:
                        self._inc("rag_grounded_total")
                    if fields.get("insufficient_evidence") is True:
                        self._inc("rag_insufficient_evidence_total")
                else:
                    self._inc("rag_failure_total")
            if event.startswith("financial_expert."):
                self._inc("financial_expert_calls_total")
                if event == "financial_expert.completed":
                    mode = _finite(fields.get("mode"), ("general", "web_grounded"))
                    self._inc(f"financial_expert_{mode}_total")
                else:
                    self._inc("financial_expert_failure_total")
            if event == "persistence.history.failed":
                self._inc("history_persistence_failures_total")
            if event.startswith("voice.stt."):
                self._inc("voice_stt_calls_total")
                if event.endswith("failed"):
                    self._inc("voice_stt_failures_total")
            if event.startswith("voice.tts."):
                self._inc("voice_tts_calls_total")
                if event.endswith("failed"):
                    self._inc("voice_tts_failures_total")

            stage = {
                "request.completed": "request",
                "graph.completed": "graph",
                "security.completed": "security",
                "routing.completed": "routing",
                "agent.completed": "agent",
                "rag.completed": "rag",
                "rag.failed": "rag",
                "financial_expert.completed": "financial_expert",
                "financial_expert.failed": "financial_expert",
                "persistence.history.completed": "history_persistence",
                "persistence.history.failed": "history_persistence",
                "voice.stt.completed": "voice_stt",
                "voice.stt.failed": "voice_stt",
                "voice.tts.completed": "voice_tts",
                "voice.tts.failed": "voice_tts",
            }.get(event)
            if stage:
                self._histograms.setdefault(stage, _Histogram()).observe(fields.get("duration_ms"))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            for name, values in self._labeled.items():
                counters[name] = dict(values)
            return {
                "counters": counters,
                "latency": {name: histogram.snapshot()
                             for name, histogram in self._histograms.items()},
                "histogram_buckets_ms": list(HISTOGRAM_BUCKETS),
            }


REGISTRY = MetricsRegistry()


def observe_event(event: str, fields: dict[str, Any]) -> None:
    try:
        REGISTRY.observe_event(event, fields)
    except Exception:
        # Diagnostics must never alter request execution.
        return


def get_metrics_snapshot() -> dict[str, Any]:
    return REGISTRY.snapshot()


def reset_metrics() -> None:
    REGISTRY.reset()
