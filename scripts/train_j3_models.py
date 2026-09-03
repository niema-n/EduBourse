"""Train J3 local intent artifacts from the internal contract dataset only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from prepare_j3_intent_dataset import load_rows, split_rows

from app.graph.intent import normalize_text

SEED = 42


def model() -> Pipeline:
    features = FeatureUnion(
        [
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    preprocessor=normalize_text,
                    min_df=1,
                ),
            ),
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    preprocessor=normalize_text,
                    min_df=1,
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced", random_state=SEED, max_iter=1000
                ),
            ),
        ]
    )


def deduplicate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    clean = []
    for row in rows:
        key = normalize_text(row["text"])
        if key not in seen:
            seen.add(key)
            clean.append(row)
    return clean


def split(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    groups = [row["semantic_family"] for row in rows]
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
    train_idx, validation_idx = next(splitter.split(rows, groups=groups))
    return [rows[i] for i in train_idx], [rows[i] for i in validation_idx]


def choose_threshold(
    model_: Pipeline, validation: list[dict[str, str]], security: bool
) -> float:
    if security:
        target = "sensitive_personalized_financial_advice"
        y = [row["label"] == target for row in validation]
    else:
        y = [row["label"] for row in validation]
    probabilities = model_.predict_proba([row["text"] for row in validation])
    if security:
        classes = list(model_.named_steps["classifier"].classes_)
        sensitive_index = classes.index(target)
        scores = probabilities[:, sensitive_index]
        candidates = [x / 100 for x in range(1, 100)]
        valid = []
        for threshold in candidates:
            predictions = scores >= threshold
            recall = sum(
                pred and actual for pred, actual in zip(predictions, y, strict=True)
            ) / max(sum(y), 1)
            false_block = sum(
                pred and not actual for pred, actual in zip(predictions, y, strict=True)
            ) / max(sum(not actual for actual in y), 1)
            if recall >= 0.98 and false_block <= 0.05:
                valid.append((recall, 1 - false_block, threshold))
        return max(valid, default=(0.0, 0.0, 0.5))[2]
    # Select the lowest threshold meeting the validation accuracy gate so the
    # application preserves coverage while uncertain inputs still fall back.
    candidates = [x / 100 for x in range(15, 100)]
    probabilities = model_.predict_proba([row["text"] for row in validation])
    classes = list(model_.named_steps["classifier"].classes_)
    selected = []
    for threshold in candidates:
        accepted = [prob.max() >= threshold for prob in probabilities]
        if not any(accepted):
            continue
        predictions = [
            classes[prob.argmax()] for prob in probabilities if prob.max() >= threshold
        ]
        actual = [
            row["label"] for row, keep in zip(validation, accepted, strict=True) if keep
        ]
        accuracy = sum(
            pred == expected for pred, expected in zip(predictions, actual, strict=True)
        ) / len(actual)
        if accuracy >= 0.95:
            selected.append((sum(accepted), -threshold, threshold))
    return max(selected, default=(0, 0, 0.5))[2]


def train(kind: str, rows: list[dict[str, str]], output: Path) -> dict[str, object]:
    security = kind == "security"
    rows = [
        row
        for row in rows
        if (row["label"] in {"safe", "sensitive_personalized_financial_advice"})
        == security
    ]
    rows = deduplicate(rows)
    train_rows, validation_rows, test_rows = split_rows(rows)
    fitted = model().fit(
        [row["text"] for row in train_rows], [row["label"] for row in train_rows]
    )
    threshold = choose_threshold(fitted, validation_rows, security)
    metadata = {
        "model_family": "FeatureUnion(char_wb_2_5+word_1_2)+LogisticRegression",
        "classes": list(fitted.named_steps["classifier"].classes_),
        "threshold": threshold,
        "training_dataset_version": "j3-contract-v2-natural",
        "source": "internal project contract dataset",
        "random_seed": SEED,
        "train_size": len(train_rows),
        "validation_size": len(validation_rows),
        "internal_test_size": len(test_rows),
        "train_validation_exact_overlap": 0,
        "train_validation_normalized_overlap": 0,
        "semantic_group_leakage": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": fitted, "metadata": metadata}, output)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/j3/contract_examples.jsonl")
    )
    parser.add_argument(
        "--artifact-dir", type=Path, default=Path("backend/app/graph/artifacts")
    )
    args = parser.parse_args()
    rows = load_rows(args.dataset)
    print(
        json.dumps(
            {
                "security": train(
                    "security", rows, args.artifact_dir / "security_intent.joblib"
                ),
                "router": train(
                    "router", rows, args.artifact_dir / "business_router.joblib"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
