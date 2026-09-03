import importlib.util
from pathlib import Path


def evaluator():
    path = Path(__file__).parents[3] / "scripts" / "evaluate_j3_llm_supervisor.py"
    spec = importlib.util.spec_from_file_location("fix3f7_evaluator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retry_after_and_unknown_limit_are_not_guessed() -> None:
    module = evaluator()
    assert module.retry_delay("PROVIDER_RATE_LIMIT", "161", 1, 1) == 162
    assert module.rate_limit_type({"x-ratelimit-remaining-tokens": "7662"}) == "UNKNOWN"


def test_fallback_rate_limit_cooldowns_are_bounded() -> None:
    module = evaluator()
    assert module.retry_delay("PROVIDER_RATE_LIMIT", None, 1, 1) == 60
    assert module.retry_delay("PROVIDER_RATE_LIMIT", None, 2, 1) == 90


def test_reset_header_duration_formats_are_parsed_without_guessing() -> None:
    module = evaluator()
    assert module.parse_reset_seconds("2.535s") == 2.535
    assert module.parse_reset_seconds("1ms") == 0.001
    assert module.parse_reset_seconds("5h9m36s") == 18576
    assert module.token_reset_delay(
        {"x-ratelimit-remaining-tokens": "100", "x-ratelimit-reset-tokens": "2.535s"}
    ) == 3.535


def test_attempt_counter_invariant_and_terminal_categories() -> None:
    module = evaluator()
    records = [
        {"provider_result_type": "PROVIDER_RATE_LIMIT"},
        {"provider_result_type": "PROVIDER_RATE_LIMIT"},
        {"provider_result_type": "TIMEOUT"},
        {"provider_result_type": "OTHER_PROVIDER_FAILURE"},
        {"provider_result_type": "SUCCESS"},
    ]
    counts = module.summarize_attempts(records)
    assert counts == {
        "attempts": 5,
        "successes": 1,
        "rate_limits": 2,
        "timeouts": 1,
        "other_failures": 1,
    }
    assert module.attempt_counter_invariant(counts)


def test_checkpoint_is_deduplicated_and_rate_limits_are_not_results() -> None:
    module = evaluator()
    results = [
        {"validation_id": "v1", "parse_success": True},
        {"validation_id": "v2", "parse_success": True},
        {"validation_id": "v2", "parse_success": True},
    ]
    attempts = [{"validation_id": "v3", "provider_result_type": "PROVIDER_RATE_LIMIT"}]
    assert len({item["validation_id"] for item in results}) == 2
    assert all(item["parse_success"] for item in results)
    assert all(item.get("provider_result_type") != "PROVIDER_RATE_LIMIT" for item in results)
    assert module.summarize_attempts(attempts)["rate_limits"] == 1
