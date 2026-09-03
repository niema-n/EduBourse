from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_DATASET_PATH = PROJECT_ROOT / "evaluation" / "multilingual" / "golden_dataset.jsonl"
LANGUAGES = ["fr", "en", "ar", "ary-latin", "ary-arabic"]
THRESHOLD_PROFILES = {
    "none": {},
    "golden": {"overall": 0.95},
    "challenge": {
        "overall": 0.95,
        "fr": 0.95,
        "en": 0.95,
        "ar": 0.95,
        "ary-latin": 0.90,
        "ary-arabic": 0.90,
    },
}

sys.path.insert(0, str(BACKEND_ROOT))


def load_dataset(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as dataset_file:
        return [json.loads(line) for line in dataset_file if line.strip()]


def format_accuracy(correct: int, total: int) -> str:
    if total == 0:
        return "0.00%"
    return f"{(correct / total) * 100:.2f}%"


def ratio(correct: int, total: int) -> float:
    if total == 0:
        return 0.0
    return correct / total


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def minimums_for(profile: str) -> dict[str, float]:
    return THRESHOLD_PROFILES[profile]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic multilingual detection.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="JSONL dataset with text and expected_language fields.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(THRESHOLD_PROFILES),
        default="golden",
        help="Explicit threshold profile to enforce.",
    )
    return parser.parse_args()


def main() -> int:
    from app.multilingual.detector import detect_language

    args = parse_args()
    dataset_path = args.dataset
    if not dataset_path.is_absolute():
        dataset_path = PROJECT_ROOT / dataset_path

    rows = load_dataset(dataset_path)
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
    print(f"Dataset: {display_path(dataset_path)}")
    print(f"Profile: {args.profile}")
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {format_accuracy(correct, total)}")
    print()
    print("Accuracy per language:")
    for language in LANGUAGES:
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

    minimums = minimums_for(args.profile)
    failures: list[str] = []
    overall_accuracy = ratio(correct, total)
    overall_minimum = minimums.get("overall")
    if overall_minimum is not None and overall_accuracy < overall_minimum:
        failures.append(f"overall<{overall_minimum:.0%}")
    for language in LANGUAGES:
        minimum = minimums.get(language)
        if minimum is None:
            continue
        language_accuracy = ratio(per_language_correct[language], per_language_total[language])
        if language_accuracy < minimum:
            failures.append(f"{language}<{minimum:.0%}")

    if failures:
        print()
        print("Threshold failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
