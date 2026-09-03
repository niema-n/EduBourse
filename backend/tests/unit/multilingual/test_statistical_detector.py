from __future__ import annotations

import importlib.util
import socket
from pathlib import Path

import pytest

from app.multilingual.detector import detect_language
from app.multilingual.statistical_detector import (
    ARTIFACT_PATH,
    StatisticalDetectorUnavailable,
    load_artifact,
    predict_arabic,
    predict_latin,
)


def _load_arabic_lid_module():
    script_path = (
        Path(__file__).resolve().parents[4]
        / "scripts"
        / "prepare_arabic_lid_training_data.py"
    )
    spec = importlib.util.spec_from_file_location("prepare_arabic_lid_training_data", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_artifact_loads_with_expected_schema() -> None:
    artifact = load_artifact(ARTIFACT_PATH)

    assert {"latin_model", "arabic_model", "metadata"}.issubset(artifact)
    assert artifact["metadata"]["model_type"] == "character TF-IDF + Logistic Regression"
    assert sorted(artifact["arabic_model"].classes_.tolist()) == ["ar", "ary-arabic"]


def test_statistical_inference_is_deterministic() -> None:
    first = predict_latin("Sorry, one more question if you do not mind.")
    second = predict_latin("Sorry, one more question if you do not mind.")

    assert first == second
    assert first.language == "en"


def test_arabic_statistical_inference_is_deterministic() -> None:
    first = predict_arabic("شنو هي البورصة؟")
    second = predict_arabic("شنو هي البورصة؟")

    assert first == second
    assert first.language in {"ar", "ary-arabic"}


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


def test_darija_lid_preprocessing_maps_only_phase_one_labels() -> None:
    preparer = _load_arabic_lid_module()

    assert preparer.mapped_label({"label": "ary", "dialect": "ary"}) == "ary-arabic"
    assert preparer.mapped_label({"label": "other", "dialect": "msa"}) == "ar"
    assert preparer.mapped_label({"label": "other", "dialect": "Jordan"}) is None


def test_darija_lid_preprocessing_filters_arabizi_from_arabic_branch() -> None:
    preparer = _load_arabic_lid_module()

    assert preparer.is_arabic_script("شنو هي البورصة؟")
    assert not preparer.is_arabic_script("chno hiya lborsa?")


def test_source_split_keeps_source_disjoint_records_separate() -> None:
    preparer = _load_arabic_lid_module()

    train_records = [
        {
            "text": "شنو هي البورصة؟",
            "normalized_text": preparer.normalized_text("شنو هي البورصة؟"),
            "expected_language": "ary-arabic",
            "source": "train-source",
        },
        {
            "text": "ما هي البورصة؟",
            "normalized_text": preparer.normalized_text("ما هي البورصة؟"),
            "expected_language": "ar",
            "source": "train-source",
        },
    ] * 10
    source_disjoint_records = [
        {
            "text": "كيف يعمل السوق؟",
            "normalized_text": preparer.normalized_text("كيف يعمل السوق؟"),
            "expected_language": "ar",
            "source": "held-out-source",
        }
    ]

    splits = preparer.split_records(train_records, source_disjoint_records, seed=42)

    assert {record["source"] for record in splits["source_disjoint"]} == {"held-out-source"}
    assert not any(record["source"] == "held-out-source" for record in splits["train"])


def test_deduplication_prevents_normalized_overlap() -> None:
    preparer = _load_arabic_lid_module()

    records = [
        {
            "text": "شنو هي البورصة؟",
            "normalized_text": preparer.normalized_text("شنو هي البورصة؟"),
            "expected_language": "ary-arabic",
        },
        {
            "text": "شنو   هي   البورصة؟",
            "normalized_text": preparer.normalized_text("شنو   هي   البورصة؟"),
            "expected_language": "ary-arabic",
        },
    ]

    unique_records = preparer.deduplicate(records)
    exact, normalized = preparer.overlap(unique_records, [])

    assert len(unique_records) == 1
    assert exact == 0
    assert normalized == 0


def test_artifact_metadata_documents_dataset_provenance() -> None:
    artifact = load_artifact(Path(ARTIFACT_PATH))
    metadata = artifact["metadata"]

    assert metadata["model_parameters"]["analyzer"] == "char_wb"
    assert "model_type" in metadata
