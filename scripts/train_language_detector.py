from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data" / "multilingual"
ARABIC_LID_DIR = PROJECT_ROOT / "data" / "arabic_lid"
ARTIFACT_PATH = BACKEND_ROOT / "app" / "multilingual" / "artifacts" / "language_detector.joblib"
METRICS_PATH = (
    BACKEND_ROOT / "app" / "multilingual" / "artifacts" / "language_detector_metrics.json"
)
LATIN_LABELS = ["fr", "en", "ary-latin"]
ARABIC_LABELS = ["ar", "ary-arabic"]
ALL_LABELS = ["fr", "en", "ar", "ary-latin", "ary-arabic"]
SEED = 42


def load_jsonl(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as input_file:
        return [json.loads(line) for line in input_file if line.strip()]


def build_model() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=SEED,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def records_for_labels(
    records: list[dict[str, str]],
    labels: list[str],
) -> tuple[list[str], list[str]]:
    selected = [record for record in records if record["expected_language"] in labels]
    return (
        [record["text"] for record in selected],
        [record["expected_language"] for record in selected],
    )


def predict(models: dict[str, Any], text: str, expected: str) -> str:
    model = models["arabic"] if expected in ARABIC_LABELS else models["latin"]
    return str(model.predict([text])[0])


def predict_with_confidence(models: dict[str, Any], text: str, expected: str) -> tuple[str, float]:
    model = models["arabic"] if expected in ARABIC_LABELS else models["latin"]
    labels = list(model.classes_)
    probabilities = model.predict_proba([text])[0]
    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return str(labels[best_index]), float(probabilities[best_index])


def evaluate(
    records: list[dict[str, str]],
    models: dict[str, Any],
    labels: list[str] = ALL_LABELS,
) -> dict[str, object]:
    expected = [record["expected_language"] for record in records]
    predictions = [
        predict_with_confidence(models, record["text"], record["expected_language"])
        for record in records
    ]
    predicted = [prediction for prediction, _ in predictions]
    confidences = [confidence for _, confidence in predictions]
    report = classification_report(
        expected,
        predicted,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(expected, predicted, labels=labels)
    per_language_accuracy = {
        label: report[label]["recall"]
        for label in labels
    }
    correct_confidences = [
        confidence
        for confidence, expected_label, predicted_label in zip(
            confidences,
            expected,
            predicted,
            strict=True,
        )
        if expected_label == predicted_label
    ]
    error_confidences = [
        confidence
        for confidence, expected_label, predicted_label in zip(
            confidences,
            expected,
            predicted,
            strict=True,
        )
        if expected_label != predicted_label
    ]
    return {
        "overall_accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, labels=labels, average="macro"),
        "per_language_accuracy": per_language_accuracy,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "labels": labels,
        "mean_confidence_correct": (
            sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
        ),
        "mean_confidence_error": (
            sum(error_confidences) / len(error_confidences) if error_confidences else 0.0
        ),
        "max_confidence_on_error": max(error_confidences) if error_confidences else 0.0,
    }


def exact_overlap(
    train_records: list[dict[str, str]],
    test_records: list[dict[str, str]],
) -> tuple[int, int, int]:
    train_texts = {record["text"] for record in train_records}
    test_texts = {record["text"] for record in test_records}
    train_normalized = {" ".join(record["text"].lower().split()) for record in train_records}
    test_normalized = {" ".join(record["text"].lower().split()) for record in test_records}
    train_indices = {record["source_index"] for record in train_records}
    test_indices = {record["source_index"] for record in test_records}
    return (
        len(train_texts & test_texts),
        len(train_normalized & test_normalized),
        len(train_indices & test_indices),
    )


def normalized_overlap(
    left_records: list[dict[str, str]],
    right_records: list[dict[str, str]],
) -> int:
    left_normalized = {" ".join(record["text"].lower().split()) for record in left_records}
    right_normalized = {" ".join(record["text"].lower().split()) for record in right_records}
    return len(left_normalized & right_normalized)


def exact_text_overlap(
    left_records: list[dict[str, str]],
    right_records: list[dict[str, str]],
) -> int:
    left_texts = {record["text"] for record in left_records}
    right_texts = {record["text"] for record in right_records}
    return len(left_texts & right_texts)


def load_existing_latin_model(artifact_path: Path) -> Any | None:
    if not artifact_path.exists():
        return None
    artifact = joblib.load(artifact_path)
    if isinstance(artifact, dict) and "latin_model" in artifact:
        return artifact["latin_model"]
    return None


def arabic_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    return [record for record in records if record["expected_language"] in ARABIC_LABELS]


def train_model(records: list[dict[str, str]], labels: list[str]) -> Pipeline:
    model = build_model()
    x, y = records_for_labels(records, labels)
    model.fit(x, y)
    return model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the local multilingual language detector.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--arabic-lid-dir", type=Path, default=ARABIC_LID_DIR)
    parser.add_argument("--artifact-path", type=Path, default=ARTIFACT_PATH)
    parser.add_argument(
        "--doda-arabic-weight",
        type=int,
        default=8,
        help="Repeat DODa Arabic records in model C to preserve the existing internal domain.",
    )
    parser.add_argument(
        "--retrain-latin",
        action="store_true",
        help="Retrain the Latin model instead of reusing it from the existing artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir if args.data_dir.is_absolute() else PROJECT_ROOT / args.data_dir
    artifact_path = (
        args.artifact_path
        if args.artifact_path.is_absolute()
        else PROJECT_ROOT / args.artifact_path
    )
    train_records = load_jsonl(data_dir / "train.jsonl")
    validation_records = load_jsonl(data_dir / "validation.jsonl")
    test_records = load_jsonl(data_dir / "test.jsonl")
    arabic_lid_dir = (
        args.arabic_lid_dir
        if args.arabic_lid_dir.is_absolute()
        else PROJECT_ROOT / args.arabic_lid_dir
    )
    lid_train_records = load_jsonl(arabic_lid_dir / "train.jsonl")
    lid_validation_records = load_jsonl(arabic_lid_dir / "validation.jsonl")
    lid_test_records = load_jsonl(arabic_lid_dir / "test.jsonl")
    lid_source_disjoint_records = load_jsonl(arabic_lid_dir / "source_disjoint.jsonl")
    lid_metadata = json.loads((arabic_lid_dir / "metadata.json").read_text(encoding="utf-8"))

    started = time.perf_counter()
    latin_model = None if args.retrain_latin else load_existing_latin_model(artifact_path)
    latin_source = "existing artifact"
    if latin_model is None:
        latin_model = train_model(train_records, LATIN_LABELS)
        latin_source = "retrained from DODa"

    doda_arabic_records = arabic_records(train_records)
    arabic_model_a = train_model(doda_arabic_records, ARABIC_LABELS)
    arabic_model_b = train_model(lid_train_records, ARABIC_LABELS)
    weighted_doda_arabic_records = doda_arabic_records * args.doda_arabic_weight
    arabic_model_c = train_model(weighted_doda_arabic_records + lid_train_records, ARABIC_LABELS)
    arabic_model = arabic_model_c
    duration_ms = (time.perf_counter() - started) * 1000

    models = {"latin": latin_model, "arabic": arabic_model}
    arabic_models = {
        "model_a_doda_only": {"latin": latin_model, "arabic": arabic_model_a},
        "model_b_darija_lid_only": {"latin": latin_model, "arabic": arabic_model_b},
        "model_c_doda_plus_darija_lid": models,
    }
    train_test_exact, train_test_normalized, parallel_leakage = exact_overlap(
        train_records,
        test_records,
    )
    final_arabic_train_records = doda_arabic_records + lid_train_records
    final_effective_arabic_train_records = weighted_doda_arabic_records + lid_train_records
    metadata = {
        "model_type": "character TF-IDF + Logistic Regression",
        "model_parameters": {
            "analyzer": "char_wb",
            "ngram_range": [2, 5],
            "class_weight": "balanced",
            "solver": "lbfgs",
            "random_state": SEED,
        },
        "seed": SEED,
        "latin_model_source": latin_source,
        "arabic_model_strategy": (
            "model C: DODa Arabic branch + Darija-LID ary/MSA Arabic-script subset"
        ),
        "train_size": len(train_records) + len(lid_train_records),
        "validation_size": len(validation_records) + len(lid_validation_records),
        "test_size": len(test_records) + len(lid_test_records),
        "doda_train_size": len(train_records),
        "darija_lid_train_size": len(lid_train_records),
        "darija_lid_validation_size": len(lid_validation_records),
        "darija_lid_test_size": len(lid_test_records),
        "darija_lid_source_disjoint_size": len(lid_source_disjoint_records),
        "doda_arabic_weight": args.doda_arabic_weight,
        "effective_arabic_train_size": len(final_effective_arabic_train_records),
        "class_distribution": dict(
            Counter(record["expected_language"] for record in train_records + lid_train_records)
        ),
        "effective_arabic_class_distribution": dict(
            Counter(record["expected_language"] for record in final_effective_arabic_train_records)
        ),
        "training_duration_ms": round(duration_ms, 2),
        "train_test_exact_overlap": train_test_exact,
        "train_test_normalized_overlap": train_test_normalized,
        "parallel_index_leakage": parallel_leakage,
        "lid_train_test_exact_overlap": exact_text_overlap(lid_train_records, lid_test_records),
        "lid_train_test_normalized_overlap": normalized_overlap(
            lid_train_records,
            lid_test_records,
        ),
        "lid_validation_test_overlap": normalized_overlap(
            lid_validation_records,
            lid_test_records,
        ),
        "doda_overlap": normalized_overlap(
            final_arabic_train_records,
            arabic_records(test_records),
        ),
        "train_sources": {
            "doda": ["MBZUAI-Paris/DODa-10K"],
            "darija_lid": lid_metadata["train_sources"],
        },
        "validation_sources": {
            "doda": ["MBZUAI-Paris/DODa-10K"],
            "darija_lid": lid_metadata["validation_sources"],
        },
        "test_sources": {
            "doda": ["MBZUAI-Paris/DODa-10K"],
            "darija_lid": lid_metadata["test_sources"],
            "source_disjoint": lid_metadata["source_disjoint_sources"],
        },
        "darija_lid_total_rows": lid_metadata["total_rows"],
        "darija_lid_used_rows": (
            len(lid_train_records)
            + len(lid_validation_records)
            + len(lid_test_records)
            + len(lid_source_disjoint_records)
        ),
        "darija_lid_metadata": lid_metadata,
    }

    artifact = {
        "latin_model": latin_model,
        "arabic_model": arabic_model,
        "metadata": metadata,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path, compress=3)
    artifact_size = artifact_path.stat().st_size

    metrics = {
        "metadata": metadata
        | {
            "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
            "artifact_size": artifact_size,
        },
        "validation": evaluate(validation_records, models),
        "test": evaluate(test_records, models),
        "doda_arabic_test": evaluate(arabic_records(test_records), models, ARABIC_LABELS),
        "darija_lid_validation": evaluate(lid_validation_records, models, ARABIC_LABELS),
        "darija_lid_test": evaluate(lid_test_records, models, ARABIC_LABELS),
        "darija_lid_source_disjoint": evaluate(
            lid_source_disjoint_records,
            models,
            ARABIC_LABELS,
        ),
        "model_selection": {
            name: {
                "doda_arabic_test": evaluate(
                    arabic_records(test_records),
                    candidate_models,
                    ARABIC_LABELS,
                ),
                "darija_lid_validation": evaluate(
                    lid_validation_records,
                    candidate_models,
                    ARABIC_LABELS,
                ),
            }
            for name, candidate_models in arabic_models.items()
        },
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
