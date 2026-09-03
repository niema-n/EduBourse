"""Evaluate J3 artifacts on the grouped internal validation split."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from prepare_j3_intent_dataset import load_rows, split_rows
from train_j3_models import deduplicate


def evaluate(
    path: Path, rows: list[dict[str, str]], security: bool
) -> dict[str, object]:
    bundle = joblib.load(path)
    model = bundle["model"]
    threshold = bundle["metadata"]["threshold"]
    rows = [
        row
        for row in rows
        if (row["label"] in {"safe", "sensitive_personalized_financial_advice"})
        == security
    ]
    _, validation, _ = split_rows(deduplicate(rows))
    probabilities = model.predict_proba([row["text"] for row in validation])
    classes = list(model.classes_)
    if security:
        target = "sensitive_personalized_financial_advice"
        index = classes.index(target)
        predicted = [target if p[index] >= threshold else "safe" for p in probabilities]
    else:
        predicted = [
            classes[p.argmax()] if p.max() >= threshold else "fallback"
            for p in probabilities
        ]
    expected = [row["label"] for row in validation]
    accepted = [x != "fallback" for x in predicted]
    if not security:
        expected = [x for x, keep in zip(expected, accepted, strict=True) if keep]
        predicted = [x for x in predicted if x != "fallback"]
    return {
        "total": len(validation),
        "accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, average="macro"),
        "precision": precision_score(
            expected,
            predicted,
            pos_label="sensitive_personalized_financial_advice",
            zero_division=0,
        )
        if security
        else None,
        "recall": recall_score(
            expected,
            predicted,
            pos_label="sensitive_personalized_financial_advice",
            zero_division=0,
        )
        if security
        else None,
        "coverage": sum(accepted) / len(accepted) if not security else 1.0,
        "threshold": threshold,
        "metadata": bundle["metadata"],
    }


def main() -> None:
    rows = load_rows(Path("data/j3/contract_examples.jsonl"))
    print(
        json.dumps(
            {
                "security": evaluate(
                    Path("backend/app/graph/artifacts/security_intent.joblib"),
                    rows,
                    True,
                ),
                "router": evaluate(
                    Path("backend/app/graph/artifacts/business_router.joblib"),
                    rows,
                    False,
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
