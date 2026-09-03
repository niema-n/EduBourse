from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

DATASET = Path(__file__).resolve().parents[3] / "data" / "j3" / "contract_examples.jsonl"

SECURITY_LABELS = {"safe", "sensitive_personalized_financial_advice"}
R1_LABELS = {"pedagogie", "formation_elearning", "cisi", "quiz"}
R2_LABELS = {"championnat", "orientation", "support_ecole", "out_of_domain"}
ROUTING_LABELS = R1_LABELS | R2_LABELS
BUSINESS_LANGUAGES = {"fr", "en", "ar", "ary"}
VALID_LANGUAGE_SCRIPTS = {
    ("fr", "latin"),
    ("en", "latin"),
    ("ar", "arabic"),
    ("ary", "latin"),
    ("ary", "arabic"),
}
REQUIRED_FIELDS = {
    "id",
    "task",
    "text",
    "language",
    "script",
    "label",
    "semantic_family",
    "group_id",
    "source",
}
FORBIDDEN_IN_TEXT = (
    "support_ecole",
    "out_of_domain",
    "formation_elearning",
    "ary-latin",
    "ary-arabic",
    "route:",
    "intent:",
    "label:",
    "class:",
    "personalized financial advice",
    "general educational explanation",
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w\s]", " ", stripped).split())


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    with DATASET.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def routing_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["task"] == "routing"]


def security_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["task"] == "security"]


def test_dataset_totals(rows: list[dict[str, str]]) -> None:
    assert len(rows) == 1800
    assert len(security_rows(rows)) == 600
    assert len(routing_rows(rows)) == 1200


def test_routing_labels_have_150_rows_each(rows: list[dict[str, str]]) -> None:
    counts = Counter(row["label"] for row in routing_rows(rows))
    assert set(counts) == ROUTING_LABELS
    assert all(counts[label] == 150 for label in ROUTING_LABELS), counts


def test_each_routing_route_has_30_rows_per_language_script(rows: list[dict[str, str]]) -> None:
    for label in ROUTING_LABELS:
        variants = Counter(
            (row["language"], row["script"])
            for row in routing_rows(rows)
            if row["label"] == label
        )
        assert set(variants) == VALID_LANGUAGE_SCRIPTS, label
        assert all(count == 30 for count in variants.values()), (label, variants)


def test_group_counts(rows: list[dict[str, str]]) -> None:
    assert len({row["group_id"] for row in security_rows(rows)}) == 120
    assert len({row["group_id"] for row in routing_rows(rows)}) == 240
    assert len({row["group_id"] for row in rows}) == 360


def test_every_group_holds_the_five_language_script_variants(rows: list[dict[str, str]]) -> None:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["group_id"], []).append(row)
    for group_id, members in groups.items():
        assert len(members) == 5, group_id
        assert sorted((m["language"], m["script"]) for m in members) == sorted(
            VALID_LANGUAGE_SCRIPTS
        ), group_id
        assert len({m["label"] for m in members}) == 1, group_id
        assert len({m["semantic_family"] for m in members}) == 1, group_id
        assert len({m["task"] for m in members}) == 1, group_id


def test_schema_and_business_languages(rows: list[dict[str, str]]) -> None:
    for row in rows:
        assert REQUIRED_FIELDS <= set(row), row.get("id")
        assert row["language"] in BUSINESS_LANGUAGES, row["id"]
        assert (row["language"], row["script"]) in VALID_LANGUAGE_SCRIPTS, row["id"]
        assert row["task"] in {"security", "routing"}, row["id"]


def test_darija_covers_both_scripts(rows: list[dict[str, str]]) -> None:
    darija_scripts = {row["script"] for row in rows if row["language"] == "ary"}
    assert darija_scripts == {"latin", "arabic"}
    assert sum(1 for row in rows if row["language"] == "ary") == 720


def test_no_target_leakage_in_text(rows: list[dict[str, str]]) -> None:
    offenders = [
        (row["id"], marker)
        for row in rows
        for marker in FORBIDDEN_IN_TEXT
        if marker in row["text"].casefold()
    ]
    assert offenders == []


def test_no_normalized_duplicates(rows: list[dict[str, str]]) -> None:
    normalized = [normalize(row["text"]) for row in rows]
    assert len(normalized) == len(set(normalized))


def test_ids_are_unique(rows: list[dict[str, str]]) -> None:
    identifiers = [row["id"] for row in rows]
    assert len(identifiers) == len(set(identifiers))
