from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.multilingual.models import LanguageCode

ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "language_detector.joblib"


@dataclass(frozen=True)
class StatisticalPrediction:
    language: LanguageCode
    confidence: float
    source: str


class StatisticalDetectorUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_artifact(path: Path = ARTIFACT_PATH) -> dict[str, Any]:
    try:
        import joblib
    except ImportError as exc:  # pragma: no cover - covered when dependency is absent
        raise StatisticalDetectorUnavailable("joblib is not installed") from exc

    if not path.exists():
        raise StatisticalDetectorUnavailable(f"language detector artifact not found: {path}")
    try:
        artifact = joblib.load(path)
    except Exception as exc:
        message = "language detector artifact could not be loaded"
        raise StatisticalDetectorUnavailable(message) from exc

    required_keys = {"latin_model", "arabic_model", "metadata"}
    if not isinstance(artifact, dict) or not required_keys.issubset(artifact):
        raise StatisticalDetectorUnavailable("language detector artifact has an invalid schema")
    return artifact


def _predict_with_model(model: Any, text: str) -> StatisticalPrediction:
    labels = list(model.classes_)
    probabilities = model.predict_proba([text])[0]
    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return StatisticalPrediction(
        language=labels[best_index],
        confidence=round(float(probabilities[best_index]), 2),
        source="classifier",
    )


def _predict_arabic_with_threshold(
    model: Any,
    text: str,
    threshold: float,
) -> StatisticalPrediction:
    labels = list(model.classes_)
    probabilities = model.predict_proba([text])[0]
    probability_by_label = {
        label: float(probabilities[index])
        for index, label in enumerate(labels)
    }
    ary_probability = probability_by_label["ary-arabic"]
    language: LanguageCode = "ary-arabic" if ary_probability >= threshold else "ar"
    return StatisticalPrediction(
        language=language,
        confidence=round(probability_by_label[language], 2),
        source="classifier",
    )


def predict_latin(text: str) -> StatisticalPrediction:
    artifact = load_artifact()
    return _predict_with_model(artifact["latin_model"], text)


def predict_arabic(text: str) -> StatisticalPrediction:
    artifact = load_artifact()
    threshold = artifact["metadata"].get("selected_arabic_threshold", 0.5)
    if not isinstance(threshold, int | float) or not 0.0 <= threshold <= 1.0:
        raise StatisticalDetectorUnavailable("language detector artifact has invalid threshold")
    return _predict_arabic_with_threshold(artifact["arabic_model"], text, float(threshold))
