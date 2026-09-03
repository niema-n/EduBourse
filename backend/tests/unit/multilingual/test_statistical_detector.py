from __future__ import annotations

import socket

import pytest

from app.multilingual.detector import detect_language
from app.multilingual.statistical_detector import (
    ARTIFACT_PATH,
    StatisticalDetectorUnavailable,
    load_artifact,
    predict_latin,
)


def test_model_artifact_loads_with_expected_schema() -> None:
    artifact = load_artifact(ARTIFACT_PATH)

    assert {"latin_model", "arabic_model", "metadata"}.issubset(artifact)
    assert artifact["metadata"]["model_type"] == "character TF-IDF + Logistic Regression"


def test_statistical_inference_is_deterministic() -> None:
    first = predict_latin("Sorry, one more question if you do not mind.")
    second = predict_latin("Sorry, one more question if you do not mind.")

    assert first == second
    assert first.language == "en"


def test_missing_artifact_raises_controlled_error(tmp_path) -> None:
    missing_path = tmp_path / "missing.joblib"

    with pytest.raises(StatisticalDetectorUnavailable):
        load_artifact(missing_path)


def test_invalid_artifact_raises_controlled_error(tmp_path) -> None:
    invalid_path = tmp_path / "invalid.joblib"
    invalid_path.write_text("not a joblib artifact", encoding="utf-8")

    with pytest.raises(StatisticalDetectorUnavailable):
        load_artifact(invalid_path)


def test_inference_does_not_require_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args, **kwargs):
        raise AssertionError("network access attempted during inference")

    monkeypatch.setattr(socket, "socket", fail_socket)

    assert detect_language("Could you say that differently?").language == "en"
    assert detect_language("بغيت نفهم stock market مزيان").language == "ary-arabic"


def test_hybrid_keeps_high_precision_rule_for_clear_darija() -> None:
    result = detect_language("wach OPCVM fih risk?")

    assert result.language == "ary-latin"
    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0


def test_classifier_handles_lower_evidence_english() -> None:
    result = detect_language("Alright, go ahead.")

    assert result.language == "en"
    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0
