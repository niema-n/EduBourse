from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATASET_PATH = PROJECT_ROOT / "evaluation" / "multilingual" / "golden_dataset.jsonl"
MINIMUM_ACCEPTABLE_ACCURACY = 0.95

sys.path.insert(0, str(BACKEND_ROOT))

from app.multilingual.detector import detect_language  # noqa: E402


def load_dataset(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as dataset_file:
        return [json.loads(line) for line in dataset_file if line.strip()]


def format_accuracy(correct: int, total: int) -> str:
    if total == 0:
        return "0.00%"
    return f"{(correct / total) * 100:.2f}%"


def main() -> int:
    rows = load_dataset(DATASET_PATH)
    total = len(rows)
    correct = 0
    per_language_total: Counter[str] = Counter()
    per_language_correct: Counter[str] = Counter()
    confusion: Counter[tuple[str, str]] = Counter()
    errors: list[tuple[str, str, str]] = []

    for row in rows:
        expected = row["expected_language"]
        detected = detect_language(row["text"]).language
        per_language_total[expected] += 1
        if detected == expected:
            correct += 1
            per_language_correct[expected] += 1
        else:
            confusion[(expected, detected)] += 1
            errors.append((row["text"], expected, detected))

    print("MULTILINGUAL EVALUATION")
    print()
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {format_accuracy(correct, total)}")
    print()
    print("Accuracy per language:")
    for language in ["fr", "en", "ar", "ary-latin", "ary-arabic"]:
        print(
            f"{language}: "
            f"{format_accuracy(per_language_correct[language], per_language_total[language])}"
        )

    print()
    print("Confusion counts:")
    if confusion:
        for (expected, detected), count in sorted(confusion.items()):
            print(f"{expected} -> {detected}: {count}")
    else:
        print("none")

    print()
    print("Errors:")
    if errors:
        for text, expected, detected in errors:
            print(f"- expected={expected} detected={detected} text={text}")
    else:
        print("none")

    accuracy = correct / total if total else 0.0
    return 0 if accuracy >= MINIMUM_ACCEPTABLE_ACCURACY else 1


if __name__ == "__main__":
    raise SystemExit(main())
