"""Small monotonic timing helpers."""

import time


def start_timer() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
