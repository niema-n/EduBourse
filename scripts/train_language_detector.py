from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
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
DEFAULT_THRESHOLD_GRID = [round(value / 100, 2) for value in range(40, 71)]

sys.path.insert(0, str(BACKEND_ROOT))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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
    records: list[dict[str, Any]],
    labels: list[str],
) -> tuple[list[str], list[str]]:
    selected = [record for record in records if record["expected_language"] in labels]
    return (
        [str(record["text"]) for record in selected],
        [str(record["expected_language"]) for record in selected],
    )


def train_model(records: list[dict[str, Any]], labels: list[str]) -> Pipeline:
    model = build_model()
    x, y = records_for_labels(records, labels)
    model.fit(x, y)
    return model


def model_digest(model: Any) -> str:
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=3)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def load_existing_latin_model(artifact_path: Path) -> tuple[Any | None, str | None]:
    if not artifact_path.exists():
        return None, None
    artifact = joblib.load(artifact_path)
    if isinstance(artifact, dict) and "latin_model" in artifact:
        latin_model = artifact["latin_model"]
        return latin_model, model_digest(latin_model)
    return None, None


def arabic_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record["expected_language"] in ARABIC_LABELS]


def normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def normalized_overlap(
    left_records: list[dict[str, Any]],
    right_records: list[dict[str, Any]],
) -> int:
    left_normalized = {normalized_text(str(record["text"])) for record in left_records}
    right_normalized = {normalized_text(str(record["text"])) for record in right_records}
    return len(left_normalized & right_normalized)


def exact_text_overlap(
    left_records: list[dict[str, Any]],
    right_records: list[dict[str, Any]],
) -> int:
    left_texts = {str(record["text"]) for record in left_records}
    right_texts = {str(record["text"]) for record in right_records}
    return len(left_texts & right_texts)


def exact_overlap(
    train_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
) -> tuple[int, int, int]:
    train_indices = {record["source_index"] for record in train_records}
    test_indices = {record["source_index"] for record in test_records}
    return (
        exact_text_overlap(train_records, test_records),
        normalized_overlap(train_records, test_records),
        len(train_indices & test_indices),
    )


def probability_by_label(model: Any, text: str) -> dict[str, float]:
    labels = list(model.classes_)
    probabilities = model.predict_proba([text])[0]
    return {label: float(probabilities[index]) for index, label in enumerate(labels)}


def arabic_probabilities(model: Any, records: list[dict[str, Any]]) -> list[float]:
    labels = list(model.classes_)
    ary_index = labels.index("ary-arabic")
    texts = [str(record["text"]) for record in records]
    return [float(row[ary_index]) for row in model.predict_proba(texts)]


def predict_arabic(model: Any, text: str, threshold: float) -> tuple[str, float]:
    probabilities = probability_by_label(model, text)
    language = "ary-arabic" if probabilities["ary-arabic"] >= threshold else "ar"
    return language, probabilities[language]


def predict_with_confidence(
    models: dict[str, Any],
    text: str,
    expected: str,
    arabic_threshold: float,
) -> tuple[str, float]:
    if expected in ARABIC_LABELS:
        return predict_arabic(models["arabic"], text, arabic_threshold)

    model = models["latin"]
    labels = list(model.classes_)
    probabilities = model.predict_proba([text])[0]
    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return str(labels[best_index]), float(probabilities[best_index])


def evaluate(
    records: list[dict[str, Any]],
    models: dict[str, Any],
    labels: list[str],
    arabic_threshold: float,
) -> dict[str, Any]:
    expected = [str(record["expected_language"]) for record in records]
    predictions = [
        predict_with_confidence(
            models,
            str(record["text"]),
            str(record["expected_language"]),
            arabic_threshold,
        )
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
        "per_language_accuracy": {label: report[label]["recall"] for label in labels},
        "classification_report": report,
        "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        "labels": labels,
        "mean_confidence_correct": (
            sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
        ),
        "mean_confidence_error": (
            sum(error_confidences) / len(error_confidences) if error_confidences else 0.0
        ),
        "max_confidence_on_error": max(error_confidences) if error_confidences else 0.0,
    }


def evaluate_arabic_probabilities(
    records: list[dict[str, Any]],
    ary_probabilities: list[float],
    threshold: float,
) -> dict[str, Any]:
    expected = [str(record["expected_language"]) for record in records]
    predicted = [
        "ary-arabic" if ary_probability >= threshold else "ar"
        for ary_probability in ary_probabilities
    ]
    confidences = [
        ary_probability if predicted_label == "ary-arabic" else 1.0 - ary_probability
        for ary_probability, predicted_label in zip(
            ary_probabilities,
            predicted,
            strict=True,
        )
    ]
    report = classification_report(
        expected,
        predicted,
        labels=ARABIC_LABELS,
        output_dict=True,
        zero_division=0,
    )
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
        "macro_f1": f1_score(expected, predicted, labels=ARABIC_LABELS, average="macro"),
        "per_language_accuracy": {
            label: report[label]["recall"] for label in ARABIC_LABELS
        },
        "classification_report": report,
        "confusion_matrix": confusion_matrix(
            expected,
            predicted,
            labels=ARABIC_LABELS,
        ).tolist(),
        "labels": ARABIC_LABELS,
        "mean_confidence_correct": (
            sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
        ),
        "mean_confidence_error": (
            sum(error_confidences) / len(error_confidences) if error_confidences else 0.0
        ),
        "max_confidence_on_error": max(error_confidences, default=0.0),
    }


def arabic_validation_score(
    doda_validation_records: list[dict[str, Any]],
    doda_validation_probabilities: list[float],
    lid_validation_records: list[dict[str, Any]],
    lid_validation_probabilities: list[float],
    threshold: float,
) -> dict[str, Any]:
    doda_metrics = evaluate_arabic_probabilities(
        doda_validation_records,
        doda_validation_probabilities,
        threshold,
    )
    lid_metrics = evaluate_arabic_probabilities(
        lid_validation_records,
        lid_validation_probabilities,
        threshold,
    )
    recalls = [
        doda_metrics["per_language_accuracy"]["ar"],
        doda_metrics["per_language_accuracy"]["ary-arabic"],
        lid_metrics["per_language_accuracy"]["ar"],
        lid_metrics["per_language_accuracy"]["ary-arabic"],
    ]
    macro_f1 = (float(doda_metrics["macro_f1"]) + float(lid_metrics["macro_f1"])) / 2
    return {
        "threshold": threshold,
        "doda_validation": doda_metrics,
        "darija_lid_validation": lid_metrics,
        "worst_class_recall": min(recalls),
        "mean_macro_f1": macro_f1,
    }


def select_arabic_configuration(
    doda_arabic_train_records: list[dict[str, Any]],
    lid_train_records: list[dict[str, Any]],
    doda_arabic_validation_records: list[dict[str, Any]],
    lid_validation_records: list[dict[str, Any]],
    weight_grid: list[int],
    threshold_grid: list[float],
) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    best_model = None
    best_score: tuple[float, float, int, float] | None = None
    best_candidate: dict[str, Any] | None = None

    for weight in weight_grid:
        model = train_model(doda_arabic_train_records * weight + lid_train_records, ARABIC_LABELS)
        doda_probabilities = arabic_probabilities(model, doda_arabic_validation_records)
        lid_probabilities = arabic_probabilities(model, lid_validation_records)
        for threshold in threshold_grid:
            metrics = arabic_validation_score(
                doda_arabic_validation_records,
                doda_probabilities,
                lid_validation_records,
                lid_probabilities,
                threshold,
            )
            candidate = {"doda_weight": weight, **metrics}
            candidates.append(candidate)
            score = (
                float(candidate["worst_class_recall"]),
                float(candidate["mean_macro_f1"]),
                -abs(weight - 8),
                -abs(threshold - 0.5),
            )
            if best_score is None or score > best_score:
                best_score = score
                best_model = model
                best_candidate = candidate

    if best_model is None or best_candidate is None:
        raise RuntimeError("no Arabic model candidate selected")
    return best_model, best_candidate, candidates


def evaluate_pipeline_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    from app.multilingual.detector import detect_language
    from app.multilingual.statistical_detector import load_artifact

    load_artifact.cache_clear()
    expected = [str(record["expected_language"]) for record in records]
    results = [detect_language(str(record["text"])) for record in records]
    predicted = [result.language for result in results]
    labels = [label for label in ALL_LABELS if label in set(expected) | set(predicted)]
    report = classification_report(
        expected,
        predicted,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    correct_confidences = [
        result.confidence or 0.0
        for result, expected_label in zip(results, expected, strict=True)
        if result.language == expected_label
    ]
    error_confidences = [
        result.confidence or 0.0
        for result, expected_label in zip(results, expected, strict=True)
        if result.language != expected_label
    ]
    return {
        "overall_accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, labels=labels, average="macro"),
        "per_language_accuracy": {label: report[label]["recall"] for label in labels},
        "classification_report": report,
        "confusion_matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        "labels": labels,
        "mean_confidence_correct": (
            sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
        ),
        "mean_confidence_error": (
            sum(error_confidences) / len(error_confidences) if error_confidences else 0.0
        ),
        "max_confidence_on_error": max(error_confidences, default=0.0),
    }


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_floats(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the local multilingual language detector.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--arabic-lid-dir", type=Path, default=ARABIC_LID_DIR)
    parser.add_argument("--artifact-path", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--weight-grid", default="4,8,16")
    parser.add_argument(
        "--threshold-grid",
        default=",".join(str(value) for value in DEFAULT_THRESHOLD_GRID),
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
    arabic_lid_dir = (
        args.arabic_lid_dir
        if args.arabic_lid_dir.is_absolute()
        else PROJECT_ROOT / args.arabic_lid_dir
    )

    train_records = load_jsonl(data_dir / "train.jsonl")
    validation_records = load_jsonl(data_dir / "validation.jsonl")
    test_records = load_jsonl(data_dir / "test.jsonl")
    lid_train_records = load_jsonl(arabic_lid_dir / "train.jsonl")
    lid_validation_records = load_jsonl(arabic_lid_dir / "validation.jsonl")
    lid_test_records = load_jsonl(arabic_lid_dir / "test.jsonl")
    lid_holdout_records = load_jsonl(arabic_lid_dir / "upstream_test_holdout.jsonl")
    lid_metadata = json.loads((arabic_lid_dir / "metadata.json").read_text(encoding="utf-8"))

    weight_grid = parse_csv_ints(args.weight_grid)
    threshold_grid = parse_csv_floats(args.threshold_grid)

    started = time.perf_counter()
    latin_model, original_latin_digest = (
        (None, None) if args.retrain_latin else load_existing_latin_model(artifact_path)
    )
    latin_source = "existing artifact"
    if latin_model is None:
        latin_model = train_model(train_records, LATIN_LABELS)
        latin_source = "retrained from DODa"
    final_latin_digest = model_digest(latin_model)

    doda_arabic_train_records = arabic_records(train_records)
    doda_arabic_validation_records = arabic_records(validation_records)
    arabic_model, selected_candidate, selection_candidates = select_arabic_configuration(
        doda_arabic_train_records,
        lid_train_records,
        doda_arabic_validation_records,
        lid_validation_records,
        weight_grid,
        threshold_grid,
    )
    selected_threshold = float(selected_candidate["threshold"])
    selected_weight = int(selected_candidate["doda_weight"])
    duration_ms = (time.perf_counter() - started) * 1000

    models = {"latin": latin_model, "arabic": arabic_model}
    train_test_exact, train_test_normalized, parallel_leakage = exact_overlap(
        train_records,
        test_records,
    )
    doda_and_lid_train = doda_arabic_train_records + lid_train_records
    effective_arabic_train = doda_arabic_train_records * selected_weight + lid_train_records

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
        "latin_model_sha256_before": original_latin_digest,
        "latin_model_sha256_after": final_latin_digest,
        "latin_model_bitwise_unchanged": original_latin_digest == final_latin_digest,
        "arabic_model_strategy": (
            "validation-selected DODa Arabic weighting plus calibrated ary-arabic threshold"
        ),
        "selected_doda_weight": selected_weight,
        "selected_arabic_threshold": selected_threshold,
        "selection_dataset": "validation only: DODa Arabic validation + Darija-LID validation",
        "selection_metric": "maximize worst_class_recall, tie-break mean_macro_f1",
        "selection_used_test_data": False,
        "rule_mode": "Arabic classifier first with calibrated threshold; heuristics fallback only",
        "train_size": len(train_records) + len(lid_train_records),
        "validation_size": len(validation_records) + len(lid_validation_records),
        "test_size": len(test_records) + len(lid_test_records),
        "doda_train_size": len(train_records),
        "darija_lid_train_size": len(lid_train_records),
        "darija_lid_validation_size": len(lid_validation_records),
        "darija_lid_test_size": len(lid_test_records),
        "upstream_test_holdout_size": len(lid_holdout_records),
        "effective_arabic_train_size": len(effective_arabic_train),
        "class_distribution": dict(
            Counter(record["expected_language"] for record in train_records + lid_train_records)
        ),
        "effective_arabic_class_distribution": dict(
            Counter(record["expected_language"] for record in effective_arabic_train)
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
        "train_holdout_exact_overlap": exact_text_overlap(doda_and_lid_train, lid_holdout_records),
        "train_holdout_normalized_overlap": normalized_overlap(
            doda_and_lid_train,
            lid_holdout_records,
        ),
        "doda_overlap": normalized_overlap(doda_and_lid_train, arabic_records(test_records)),
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
            "upstream_test_holdout": lid_metadata["upstream_test_holdout_sources"],
        },
        "strict_source_disjoint": False,
        "darija_lid_total_rows": lid_metadata["total_rows"],
        "darija_lid_used_rows": (
            len(lid_train_records)
            + len(lid_validation_records)
            + len(lid_test_records)
            + len(lid_holdout_records)
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

    classifier_metrics = {
        "validation": evaluate(validation_records, models, ALL_LABELS, selected_threshold),
        "test": evaluate(test_records, models, ALL_LABELS, selected_threshold),
        "doda_arabic_validation": evaluate(
            doda_arabic_validation_records,
            models,
            ARABIC_LABELS,
            selected_threshold,
        ),
        "doda_arabic_test": evaluate(
            arabic_records(test_records),
            models,
            ARABIC_LABELS,
            selected_threshold,
        ),
        "darija_lid_validation": evaluate(
            lid_validation_records,
            models,
            ARABIC_LABELS,
            selected_threshold,
        ),
        "darija_lid_test": evaluate(
            lid_test_records,
            models,
            ARABIC_LABELS,
            selected_threshold,
        ),
        "upstream_test_holdout": evaluate(
            lid_holdout_records,
            models,
            ARABIC_LABELS,
            selected_threshold,
        ),
    }
    metrics = {
        "metadata": metadata
        | {
            "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
            "artifact_size": artifact_size,
        },
        "classifier_metrics": classifier_metrics,
        "pipeline_metrics": {
            "doda_arabic_validation": evaluate_pipeline_records(doda_arabic_validation_records),
            "doda_arabic_test": evaluate_pipeline_records(arabic_records(test_records)),
            "darija_lid_validation": evaluate_pipeline_records(lid_validation_records),
            "darija_lid_test": evaluate_pipeline_records(lid_test_records),
            "upstream_test_holdout": evaluate_pipeline_records(lid_holdout_records),
        },
        "validation_comparison": {
            "current_hybrid": {
                "description": "pre-J2D rule-heavy Arabic hybrid; baseline kept in J2C report",
                "available": False,
            },
            "classifier_only": arabic_validation_score(
                doda_arabic_validation_records,
                arabic_probabilities(arabic_model, doda_arabic_validation_records),
                lid_validation_records,
                arabic_probabilities(arabic_model, lid_validation_records),
                0.5,
            ),
            "calibrated_classifier": selected_candidate,
            "calibrated_safe_rules": {
                "description": (
                    "same result as calibrated classifier; Arabic hard overrides disabled when "
                    "artifact is available"
                ),
                **selected_candidate,
            },
        },
        "selection_candidates": selection_candidates,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
