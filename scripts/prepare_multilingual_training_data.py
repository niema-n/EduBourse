from __future__ import annotations

import argparse
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "multilingual"
SOURCE_DATASET = "MBZUAI-Paris/DODa-10K"
SOURCE_REVISION = "main"
SEED = 42
LABEL_COLUMNS = {
    "fr": "French",
    "en": "English",
    "ar": "MSA",
    "ary-latin": "Darija_latin",
    "ary-arabic": "Darija_arabic",
}


class DisjointSet:
    def __init__(self, values: list[int]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def fetch_rows(limit: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    page_size = 100
    encoded_dataset = urllib.parse.quote(SOURCE_DATASET, safe="")
    for offset in range(0, limit, page_size):
        length = min(page_size, limit - offset)
        url = (
            "https://datasets-server.huggingface.co/rows"
            f"?dataset={encoded_dataset}&config=default&split=train"
            f"&offset={offset}&length={length}"
        )
        payload = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(1.0 + attempt)
        if payload is None:
            raise RuntimeError(f"failed to fetch rows at offset {offset}")
        rows.extend(item["row"] for item in payload["rows"])
    return rows


def split_indices(rows: list[dict[str, str]]) -> dict[str, set[int]]:
    indices = [int(row["index"]) for row in rows]
    disjoint_set = DisjointSet(indices)
    first_index_by_text: dict[str, int] = {}
    for row in rows:
        row_index = int(row["index"])
        for column in LABEL_COLUMNS.values():
            text_key = normalized_text(str(row[column]))
            if not text_key:
                continue
            if text_key in first_index_by_text:
                disjoint_set.union(first_index_by_text[text_key], row_index)
            else:
                first_index_by_text[text_key] = row_index

    groups_by_root: dict[int, set[int]] = {}
    for index in indices:
        groups_by_root.setdefault(disjoint_set.find(index), set()).add(index)

    groups = list(groups_by_root.values())
    random.Random(SEED).shuffle(groups)
    train_end = int(len(groups) * 0.70)
    validation_end = int(len(groups) * 0.85)
    train_groups = groups[:train_end]
    validation_groups = groups[train_end:validation_end]
    test_groups = groups[validation_end:]
    return {
        "train": set().union(*train_groups),
        "validation": set().union(*validation_groups),
        "test": set().union(*test_groups),
    }


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def expand_rows(
    rows: list[dict[str, str]],
    split_by_index: dict[str, set[int]],
) -> dict[str, list[dict[str, str]]]:
    expanded = {"train": [], "validation": [], "test": []}
    for row in rows:
        source_index = int(row["index"])
        split = next(name for name, indices in split_by_index.items() if source_index in indices)
        for label, column in LABEL_COLUMNS.items():
            text = str(row[column]).strip()
            if text:
                expanded[split].append(
                    {"source_index": source_index, "text": text, "expected_language": label}
                )
    return expanded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare multilingual training data from DODa-10K."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Number of parallel DODa rows to fetch.",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = fetch_rows(args.limit)
    split_by_index = split_indices(rows)
    expanded = expand_rows(rows, split_by_index)

    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for split, records in expanded.items():
        write_jsonl(output_dir / f"{split}.jsonl", records)

    metadata = {
        "dataset_source": SOURCE_DATASET,
        "dataset_revision": SOURCE_REVISION,
        "license": "cc-by-nc-4.0",
        "seed": SEED,
        "parallel_rows": len(rows),
        "train_size": len(expanded["train"]),
        "validation_size": len(expanded["validation"]),
        "test_size": len(expanded["test"]),
        "split_strategy": "split parallel source indices before expanding language columns",
        "duplicate_strategy": "keep duplicate normalized texts in the same split",
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
