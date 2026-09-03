from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SOURCE_URL = "https://huggingface.co/datasets/samihyounes/Moroccan-Codeswitching/resolve/main/test.tsv"

sys.path.insert(0, str(BACKEND_ROOT))


def count_arabic_letters(text: str) -> int:
    return sum(1 for character in text if "\u0621" <= character <= "\u064a")


def count_latin_letters(text: str) -> int:
    return sum(1 for character in text if character.isalpha() and character.isascii())


def fetch_tsv(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def grouped_sentences(tsv_text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    rows_by_sentence: dict[str, list[tuple[str, str]]] = defaultdict(list)
    reader = csv.DictReader(tsv_text.splitlines())
    for row in reader:
        rows_by_sentence[row["sentence_id"]].append((row["words"], row["labels"]))
    return list(rows_by_sentence.items())


def candidate_darija_arabic_sentences(tsv_text: str, limit: int) -> list[str]:
    candidates: list[str] = []
    for _, tokens in grouped_sentences(tsv_text):
        words = [word for word, _ in tokens]
        labels = [label for _, label in tokens]
        text = " ".join(words).strip()
        arabic_letters = count_arabic_letters(text)
        latin_letters = count_latin_letters(text)
        lang2_tokens = sum(1 for label in labels if label == "lang2")
        if lang2_tokens >= 3 and arabic_letters >= max(8, latin_letters * 2):
            candidates.append(text)
        if len(candidates) >= limit:
            break
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate external Moroccan code-switching data.")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    from app.multilingual.detector import detect_language

    args = parse_args()
    texts = candidate_darija_arabic_sentences(fetch_tsv(SOURCE_URL), args.limit)
    correct = sum(1 for text in texts if detect_language(text).language == "ary-arabic")
    total = len(texts)
    accuracy = correct / total if total else 0.0
    print("EXTERNAL MOROCCAN CODESWITCHING EVALUATION")
    print(f"Source: {SOURCE_URL}")
    print("Expected label: ary-arabic")
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
