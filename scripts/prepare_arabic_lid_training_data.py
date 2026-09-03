from __future__ import annotations

import argparse
import json
import random
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "arabic_lid"
DATASET = "atlasia/Darija-LID"
REVISION = "main"
LICENSE = "MIT"
SEED = 42
ARABIC_RE = re.compile(r"[\u0621-\u064a]")
LATIN_RE = re.compile(r"[A-Za-z]")


def normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def count_arabic_letters(text: str) -> int:
    return len(ARABIC_RE.findall(text))


def count_latin_letters(text: str) -> int:
    return len(LATIN_RE.findall(text))


def is_arabic_script(text: str) -> bool:
    arabic_count = count_arabic_letters(text)
    latin_count = count_latin_letters(text)
    return arabic_count >= 3 and arabic_count >= latin_count * 2


def mapped_label(row: dict[str, object]) -> str | None:
    dialect = str(row.get("dialect", "")).strip().lower()
    label = str(row.get("label", "")).strip().lower()
    if label == "ary" or dialect in {"ary", "moroccan darija", "moroccan_arabic"}:
        return "ary-arabic"
    if dialect in {"msa", "modern standard arabic"}:
        return "ar"
    return None


def fetch_json(url: str) -> dict[str, object]:
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
    if not isinstance(payload, dict):
        raise RuntimeError(f"failed to fetch {url}")
    return payload


def dataset_size() -> dict[str, int]:
    encoded = urllib.parse.quote(DATASET, safe="")
    payload = fetch_json(f"https://datasets-server.huggingface.co/size?dataset={encoded}")
    splits = payload["size"]["splits"]  # type: ignore[index]
    return {str(split["split"]): int(split["num_rows"]) for split in splits}  # type: ignore[index]


def parquet_urls() -> dict[str, str]:
    encoded = urllib.parse.quote(DATASET, safe="")
    payload = fetch_json(f"https://datasets-server.huggingface.co/parquet?dataset={encoded}")
    return {
        str(file_info["split"]): str(file_info["url"])
        for file_info in payload["parquet_files"]  # type: ignore[index]
    }


def download_parquet(url: str, split: str) -> Path:
    cache_dir = PROJECT_ROOT / "data" / "arabic_lid" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{split}.parquet"
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    return path


def fetch_rows_from_parquet(split: str, limit: int) -> list[dict[str, object]] | None:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return None

    urls = parquet_urls()
    table = pq.read_table(download_parquet(urls[split], split))
    all_rows = table.to_pylist()
    if limit >= len(all_rows):
        row_indices = list(range(len(all_rows)))
    elif limit <= 1:
        row_indices = [0]
    else:
        max_index = len(all_rows) - 1
        row_indices = [
            round(index * max_index / (limit - 1))
            for index in range(limit)
        ]
    return [
        all_rows[index] | {"hf_split": split, "source_index": index}
        for index in row_indices
    ]


def fetch_rows(split: str, limit: int, total_rows: int) -> list[dict[str, object]]:
    parquet_rows = fetch_rows_from_parquet(split, min(limit, total_rows))
    if parquet_rows is not None:
        return parquet_rows

    rows: list[dict[str, object]] = []
    page_size = 100
    encoded = urllib.parse.quote(DATASET, safe="")
    page_count = max(1, min(limit, total_rows) // page_size)
    if page_count == 1:
        offsets = [0]
    else:
        max_offset = max(0, total_rows - page_size)
        offsets = sorted(
            {round(index * max_offset / (page_count - 1)) for index in range(page_count)}
        )
    for offset in offsets:
        length = min(page_size, total_rows - offset)
        url = (
            "https://datasets-server.huggingface.co/rows"
            f"?dataset={encoded}&config=default&split={split}"
            f"&offset={offset}&length={length}"
        )
        payload = fetch_json(url)
        rows.extend(
            item["row"] | {"hf_split": split, "source_index": item["row_idx"]}
            for item in payload["rows"]  # type: ignore[index]
        )
    return rows


def to_record(row: dict[str, object]) -> dict[str, object] | None:
    text = str(row.get("text", "")).strip()
    label = mapped_label(row)
    if not text or label is None or not is_arabic_script(text):
        return None
    return {
        "text": text,
        "expected_language": label,
        "dialect": str(row.get("dialect", "")),
        "source": str(row.get("source", "")),
        "original_label": str(row.get("label", "")),
        "hf_split": str(row.get("hf_split", "")),
        "source_index": int(row.get("source_index", -1)),
        "normalized_text": normalized_text(text),
        "nwords": int(row.get("nwords", 0) or 0),
    }


def deduplicate(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique_records: list[dict[str, object]] = []
    for record in records:
        key = str(record["normalized_text"])
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)
    return unique_records


def balanced_sample(
    records: list[dict[str, object]],
    per_label_limit: int,
    seed: int,
) -> list[dict[str, object]]:
    rng = random.Random(seed)
    by_label: dict[str, list[dict[str, object]]] = {"ar": [], "ary-arabic": []}
    for record in records:
        by_label[str(record["expected_language"])].append(record)
    selected: list[dict[str, object]] = []
    for label_records in by_label.values():
        rng.shuffle(label_records)
        selected.extend(label_records[:per_label_limit])
    rng.shuffle(selected)
    return selected


def split_records(
    train_source_records: list[dict[str, object]],
    test_source_records: list[dict[str, object]],
    seed: int,
) -> dict[str, list[dict[str, object]]]:
    rng = random.Random(seed)
    train_pool = list(train_source_records)
    rng.shuffle(train_pool)
    by_label: dict[str, list[dict[str, object]]] = {"ar": [], "ary-arabic": []}
    for record in train_pool:
        by_label[str(record["expected_language"])].append(record)

    splits = {
        "train": [],
        "validation": [],
        "test": [],
        "source_disjoint": list(test_source_records),
    }
    for records in by_label.values():
        validation_end = int(len(records) * 0.15)
        test_end = int(len(records) * 0.30)
        splits["validation"].extend(records[:validation_end])
        splits["test"].extend(records[validation_end:test_end])
        splits["train"].extend(records[test_end:])
    for records in splits.values():
        rng.shuffle(records)
    return splits


def overlap(left: list[dict[str, object]], right: list[dict[str, object]]) -> tuple[int, int]:
    left_exact = {str(record["text"]) for record in left}
    right_exact = {str(record["text"]) for record in right}
    left_normalized = {str(record["normalized_text"]) for record in left}
    right_normalized = {str(record["normalized_text"]) for record in right}
    return len(left_exact & right_exact), len(left_normalized & right_normalized)


def doda_overlap(records: list[dict[str, object]], doda_dir: Path) -> int:
    doda_test = doda_dir / "test.jsonl"
    if not doda_test.exists():
        return -1
    doda_texts = set()
    with doda_test.open(encoding="utf-8") as input_file:
        for line in input_file:
            row = json.loads(line)
            if row.get("expected_language") in {"ar", "ary-arabic"}:
                doda_texts.add(normalized_text(str(row["text"])))
    train_texts = {str(record["normalized_text"]) for record in records}
    return len(train_texts & doda_texts)


def analysis_for_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    lengths = [
        int(row.get("nwords", 0) or len(str(row.get("text", "")).split()))
        for row in rows
    ]
    script_counts = Counter(
        "arabic" if is_arabic_script(str(row.get("text", ""))) else "latin_or_mixed"
        for row in rows
    )
    normalized_counts = Counter(normalized_text(str(row.get("text", ""))) for row in rows)
    duplicates = sum(count - 1 for count in normalized_counts.values() if count > 1)
    label_field = "expected_language" if rows and "expected_language" in rows[0] else "label"
    return {
        "rows": len(rows),
        "label_distribution": dict(Counter(str(row.get(label_field, "")) for row in rows)),
        "dialect_distribution": dict(Counter(str(row.get("dialect", "")) for row in rows)),
        "source_distribution": dict(Counter(str(row.get("source", "")) for row in rows)),
        "script_distribution": dict(script_counts),
        "min_words": min(lengths) if lengths else 0,
        "max_words": max(lengths) if lengths else 0,
        "mean_words": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "normalized_duplicates": duplicates,
    }


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            payload = dict(record)
            payload.pop("normalized_text", None)
            output_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Arabic branch data from atlasia/Darija-LID."
    )
    parser.add_argument("--train-fetch-limit", type=int, default=60000)
    parser.add_argument("--test-fetch-limit", type=int, default=20000)
    parser.add_argument("--per-label-limit", type=int, default=20000)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--doda-dir", type=Path, default=PROJECT_ROOT / "data" / "multilingual")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sizes = dataset_size()
    raw_train_rows = fetch_rows("train", args.train_fetch_limit, sizes["train"])
    raw_test_rows = fetch_rows("test", args.test_fetch_limit, sizes["test"])

    train_candidates = deduplicate(record for row in raw_train_rows if (record := to_record(row)))
    test_candidates = deduplicate(record for row in raw_test_rows if (record := to_record(row)))
    selected_train_candidates = balanced_sample(train_candidates, args.per_label_limit, SEED)
    selected_test_candidates = balanced_sample(test_candidates, args.per_label_limit // 4, SEED + 1)
    splits = split_records(selected_train_candidates, selected_test_candidates, SEED)

    train_test_exact, train_test_normalized = overlap(splits["train"], splits["test"])
    validation_test_exact, validation_test_normalized = overlap(
        splits["validation"],
        splits["test"],
    )
    metadata = {
        "dataset_source": DATASET,
        "dataset_revision": REVISION,
        "license": LICENSE,
        "total_rows": sum(sizes.values()),
        "split_rows": sizes,
        "seed": SEED,
        "phase": "ary Arabic-script vs MSA only; other dialects excluded from training",
        "selection": {
            "train_fetch_limit": args.train_fetch_limit,
            "test_fetch_limit": args.test_fetch_limit,
            "per_label_limit": args.per_label_limit,
        },
        "analysis": {
            "train_fetched": analysis_for_rows(raw_train_rows),
            "test_fetched": analysis_for_rows(raw_test_rows),
            "train_candidates": analysis_for_rows(train_candidates),
            "test_candidates": analysis_for_rows(test_candidates),
        },
        "train_size": len(splits["train"]),
        "validation_size": len(splits["validation"]),
        "test_size": len(splits["test"]),
        "source_disjoint_size": len(splits["source_disjoint"]),
        "train_sources": sorted({str(record["source"]) for record in splits["train"]}),
        "validation_sources": sorted({str(record["source"]) for record in splits["validation"]}),
        "test_sources": sorted({str(record["source"]) for record in splits["test"]}),
        "source_disjoint_sources": sorted(
            {str(record["source"]) for record in splits["source_disjoint"]}
        ),
        "train_test_exact_overlap": train_test_exact,
        "train_test_normalized_overlap": train_test_normalized,
        "validation_test_exact_overlap": validation_test_exact,
        "validation_test_normalized_overlap": validation_test_normalized,
        "doda_train_overlap_with_doda_test": doda_overlap(
            splits["train"],
            args.doda_dir if args.doda_dir.is_absolute() else PROJECT_ROOT / args.doda_dir,
        ),
        "source_disjoint_note": (
            "Darija-LID train/test splits are used as the hardest held-out diagnostic boundary. "
            "This is not a strict upstream-source-disjoint split: within the selected ary/MSA "
            "phase, each class is dominated by one upstream source, so a stricter by-source "
            "split would remove a class from training."
        ),
    }

    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for split, records in splits.items():
        write_jsonl(output_dir / f"{split}.jsonl", records)
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
