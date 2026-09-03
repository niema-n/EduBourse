"""Validate and split the curated, versioned J3 contract corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from app.graph.intent import normalize_text

LANGUAGES = {"fr", "en", "ar", "ary"}
SCRIPTS = {"latin", "arabic"}
VALID_LANGUAGE_SCRIPTS = {
    ("fr", "latin"),
    ("en", "latin"),
    ("ar", "arabic"),
    ("ary", "latin"),
    ("ary", "arabic"),
}
SECURITY_LABELS = {"safe", "sensitive_personalized_financial_advice"}
ROUTING_LABELS = {
    "pedagogie",
    "formation_elearning",
    "cisi",
    "quiz",
    "championnat",
    "orientation",
    "support_ecole",
    "out_of_domain",
}
FORBIDDEN_TEXT = {
    "personalized financial advice",
    "general educational explanation",
    "formation_elearning",
    "support_ecole",
    "out_of_domain",
    "ary-latin",
    "ary-arabic",
}


def load_rows(path: Path) -> list[dict[str, str]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    required = {
        "id",
        "task",
        "text",
        "language",
        "label",
        "semantic_family",
        "group_id",
        "source",
        "script",
    }
    for row in rows:
        missing = required - row.keys()
        valid_label = row["label"] in (
            SECURITY_LABELS if row["task"] == "security" else ROUTING_LABELS
        )
        if (
            missing
            or row["language"] not in LANGUAGES
            or row["script"] not in SCRIPTS
            or (row["language"], row["script"]) not in VALID_LANGUAGE_SCRIPTS
            or row["source"] != "internal_manual_contract"
            or not valid_label
        ):
            raise ValueError(f"invalid J3 record: {row.get('id', 'unknown')}")
        text = normalize_text(row["text"])
        if not text or any(marker in text for marker in FORBIDDEN_TEXT):
            raise ValueError(f"artificial or empty training text: {row['id']}")
    return rows


def split_rows(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    groups = sorted({row["group_id"] for row in rows})
    first, rest = next(
        GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42).split(
            groups, groups=groups
        )
    )
    train_groups = {groups[index] for index in first}
    remaining = [groups[index] for index in rest]
    second, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42).split(
            remaining, groups=remaining
        )
    )
    validation_groups = {remaining[index] for index in second}
    test_groups = {remaining[index] for index in test}
    return tuple(
        [row for row in rows if row["group_id"] in selected]
        for selected in (train_groups, validation_groups, test_groups)
    )


def audit(rows: list[dict[str, str]]) -> dict[str, object]:
    normalized = [normalize_text(row["text"]) for row in rows]
    if len(normalized) != len(set(normalized)):
        raise ValueError("exact or normalized duplicate in J3 corpus")
    train, validation, test = split_rows(rows)
    sets = [
        {normalize_text(row["text"]) for row in part}
        for part in (train, validation, test)
    ]
    overlaps = [len(sets[0] & sets[1]), len(sets[0] & sets[2]), len(sets[1] & sets[2])]
    if any(overlaps):
        raise ValueError(f"split overlap detected: {overlaps}")
    return {
        "total": len(rows),
        "per_task": Counter(row["task"] for row in rows),
        "per_language": Counter(row["language"] for row in rows),
        "per_label": Counter(row["label"] for row in rows),
        "train": len(train),
        "validation": len(validation),
        "test": len(test),
        "train_validation_exact_overlap": 0,
        "train_validation_normalized_overlap": 0,
        "train_test_exact_overlap": 0,
        "train_test_normalized_overlap": 0,
        "group_leakage": 0,
        "top_prefixes_by_label": {},
        "top_suffixes_by_label": {},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/j3/contract_examples.jsonl")
    )
    args = parser.parse_args()
    print(json.dumps(audit(load_rows(args.dataset)), indent=2, default=dict))


if __name__ == "__main__":
    main()
