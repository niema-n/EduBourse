from app.rag.embedding_benchmark import GoldCase
from app.rag.en_ar_diagnostic import (
    classify_failure,
    diagnostic_projection,
    pair_target_cases,
    reason_counts,
    recall5,
)


def case(case_id, language, topic="topic", source="source"):
    return GoldCase(
        id=case_id,
        query=case_id,
        language=language,
        script="arabic" if language == "ar" else "latin",
        topic=topic,
        expected_source_ids=[source],
    )


def test_pairing_is_deterministic_and_does_not_use_ranks():
    cases = [case("en-1", "en"), case("fr-1", "fr"), case("ar-1", "ar")]
    first = pair_target_cases(cases)
    second = pair_target_cases(cases)
    assert first == second
    assert first[0]["FR_COUNTERPART"].id == "fr-1"
    assert first[0]["AR_COUNTERPART"].id == "ar-1"


def test_missing_counterpart_is_none_not_fabricated():
    paired = pair_target_cases([case("en-1", "en")])
    assert paired[0]["FR_COUNTERPART"] is None
    assert paired[0]["ARY_ARABIC_COUNTERPART"] is None


def test_failure_classification_requires_actual_hits():
    base = {
        "original_language": "en",
        "variants": {
            "ORIGINAL": {"available": True, "hit_at_5": False},
            "FR_COUNTERPART": {"available": True, "hit_at_5": True},
            "ARY_ARABIC_COUNTERPART": {"available": True, "hit_at_5": False},
        },
    }
    assert classify_failure(base) == "FRENCH_REPRESENTATION_RECOVERY"
    base["variants"]["FR_COUNTERPART"]["hit_at_5"] = False
    assert classify_failure(base) == "CORPUS_GAP_SUSPECTED"


def test_arabic_variant_recovery_is_not_cross_script_gap():
    result = {
        "original_language": "ar",
        "variants": {
            "ORIGINAL": {"available": True, "hit_at_5": False},
            "FR_COUNTERPART": {"available": True, "hit_at_5": False},
            "ARY_ARABIC_COUNTERPART": {"available": True, "hit_at_5": True},
        },
    }
    assert classify_failure(result) == "ARABIC_VARIANT_RECOVERY"


def test_recall_uses_available_denominator():
    assert recall5(
        [
            {"available": True, "hit_at_5": True},
            {"available": True, "hit_at_5": False},
            {"available": False},
        ]
    ) == 0.5


def test_projection_arithmetic_is_diagnostic_only():
    results = [
        {
            "variants": {
                "ORIGINAL": {"hit_at_5": False},
                "FR_COUNTERPART": {"available": True, "hit_at_5": True},
            }
        },
        {"variants": {"ORIGINAL": {"hit_at_5": True}}},
    ]
    projection = diagnostic_projection("en", results, {"en": 0.75, "ar": 0.75})
    assert projection["recoverable_recall5"] == 1.0
    assert projection["diagnostic_only"] is True


def test_reason_counts_are_derived():
    results = [
        {"failure_reason": "FRENCH_REPRESENTATION_RECOVERY"},
        {"failure_reason": "CORPUS_GAP_SUSPECTED"},
        {"failure_reason": "NOT_A_FAILURE"},
    ]
    assert reason_counts(results) == {
        "CORPUS_GAP_SUSPECTED": 1,
        "FRENCH_REPRESENTATION_RECOVERY": 1,
    }


def test_module_is_isolated_from_providers_and_chroma():
    import app.rag.en_ar_diagnostic as module

    source = open(module.__file__, encoding="utf-8").read()
    assert not any(name in source for name in ("groq", "openai", "google", "anthropic", "chromadb"))
