"""Prime the existing local classifier without delaying application startup."""

import logging
from threading import Lock, Thread

from app.graph.intent import security_model
from app.observability.logging import emit
from app.observability.timing import elapsed_ms, start_timer

_lock = Lock()
_thread: Thread | None = None


def run_security_warmup() -> bool:
    started = start_timer()
    try:
        security_model.predict("Bonjour")
    except Exception as exc:
        # Normal requests retain the existing fail-closed handling.
        emit(
            "security.warmup.failed", level=logging.WARNING,
            duration_ms=elapsed_ms(started), error_type=type(exc).__name__,
        )
        return False
    emit("security.warmup.completed", duration_ms=elapsed_ms(started))
    return True


def start_security_warmup() -> bool:
    global _thread
    with _lock:
        if _thread is not None:
            return False
        _thread = Thread(target=run_security_warmup, name="security-warmup", daemon=True)
        _thread.start()
    return True
