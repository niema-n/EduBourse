from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data" / "multilingual"
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


def predict(models: dict[str, Pipeline], text: str, expected: str) -> str:
    model = models["arabic"] if expected in ARABIC_LABELS else models["latin"]
    return str(model.predict([text])[0])


def evaluate(records: list[dict[str, str]], models: dict[str, Pipeline]) -> dict[str, object]:
    expected = [record["expected_language"] for record in records]
    predicted = [predict(models, record["text"], record["expected_language"]) for record in records]
    report = classification_report(
        expected,
        predicted,
        labels=ALL_LABELS,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(expected, predicted, labels=ALL_LABELS)
    per_language_accuracy = {
        label: report[label]["recall"]
        for label in ALL_LABELS
    }
    return {
        "overall_accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, labels=ALL_LABELS, average="macro"),
        "per_language_accuracy": per_language_accuracy,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "labels": ALL_LABELS,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the local multilingual language detector.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--artifact-path", type=Path, default=ARTIFACT_PATH)
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

    latin_model = build_model()
    arabic_model = build_model()
    latin_x, latin_y = records_for_labels(train_records, LATIN_LABELS)
    arabic_x, arabic_y = records_for_labels(train_records, ARABIC_LABELS)

    started = time.perf_counter()
    latin_model.fit(latin_x, latin_y)
    arabic_model.fit(arabic_x, arabic_y)
    duration_ms = (time.perf_counter() - started) * 1000

    models = {"latin": latin_model, "arabic": arabic_model}
    train_test_exact, train_test_normalized, parallel_leakage = exact_overlap(
        train_records,
        test_records,
    )
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
        "train_size": len(train_records),
        "validation_size": len(validation_records),
        "test_size": len(test_records),
        "class_distribution": dict(
            Counter(record["expected_language"] for record in train_records)
        ),
        "training_duration_ms": round(duration_ms, 2),
        "train_test_exact_overlap": train_test_exact,
        "train_test_normalized_overlap": train_test_normalized,
        "parallel_index_leakage": parallel_leakage,
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
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
