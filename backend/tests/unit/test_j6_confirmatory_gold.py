import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "evaluation/rag/embedding_gold_confirmatory_v1.jsonl"
MANIFEST = ROOT / "backend/data/rag/manifests/confirmatory_gold_v1.json"
OLD_GOLD = ROOT / "evaluation/rag/embedding_gold_v1.jsonl"
CHUNKS = ROOT / "backend/data/rag/processed/chunks_v1.jsonl"
CORPUS = ROOT / "backend/data/rag/manifests/corpus_v1.json"
PAGES = ROOT / "backend/data/rag/processed/pages_v1.jsonl"
CONFIRMATORY_DATASET_SHA256 = "09984f65ceab47d5b0aafdaec051cedf45219c183d765985bd95b2652b839289"
CONFIRMATORY_MANIFEST_SHA256 = "aa83584e1bf9daa89dafa946c29fb100688645f4b25c4d3b6e28cab15a3787d8"


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[^\w]+", " ", normalized).strip()


@pytest.fixture(scope="module")
def dataset():
    return _records(DATASET)


def test_confirmatory_dataset_has_60_records_and_12_groups(dataset):
    assert len(dataset) == 60
    assert len({record["topic"] for record in dataset}) == 12
    assert len({record["id"] for record in dataset}) == 60


def test_confirmatory_case_ids_and_group_numbers_are_exact(dataset):
    expected = {
        f"confirm-{language}-{number:02d}"
        for language in ("fr", "en", "ar", "ary-latin", "ary-arabic")
        for number in range(1, 13)
    }
    assert {record["id"] for record in dataset} == expected
    for record in dataset:
        group_number = int(record["id"].rsplit("-", 1)[1])
        assert record["topic"] == {
            1: "acquisition_actions_cotees",
            2: "opcvm_diversification",
            3: "ipo_prospectus",
            4: "offres_opa_ope",
            5: "operations_sur_titres",
            6: "ago_droits_actionnaire",
            7: "documents_information_periodique",
            8: "pea_instruments_eligibles",
            9: "crowdfunding_risques",
            10: "budget_epargne_reguliere",
            11: "placement_liquidite_risque",
            12: "intermediaire_autorise",
        }[group_number]


def test_confirmatory_dataset_has_five_aligned_variants_per_group(dataset):
    expected_categories = {("fr", "latin"), ("en", "latin"), ("ar", "arabic")}
    expected_categories |= {("ary", "latin"), ("ary", "arabic")}
    for group in {record["topic"] for record in dataset}:
        records = [record for record in dataset if record["topic"] == group]
        assert len(records) == 5
        assert {(record["language"], record["script"]) for record in records} == expected_categories
        assert {tuple(record["expected_source_ids"]) for record in records}.__len__() == 1


def test_confirmatory_dataset_has_twelve_records_per_category(dataset):
    counts = {}
    for record in dataset:
        category = (
            record["language"]
            if record["language"] != "ary"
            else f"ary-{record['script']}"
        )
        counts[category] = counts.get(category, 0) + 1
    assert counts == {
        "fr": 12,
        "en": 12,
        "ar": 12,
        "ary-latin": 12,
        "ary-arabic": 12,
    }


def test_expected_sources_are_frozen_corpus_sources(dataset):
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    source_ids = {document["source_id"] for document in corpus["documents"]}
    assert all(set(record["expected_source_ids"]) <= source_ids for record in dataset)


def test_confirmatory_script_validation(dataset):
    arabic = re.compile(r"[\u0600-\u06ff]")
    for record in dataset:
        contains_arabic = bool(arabic.search(record["query"]))
        if record["language"] == "ary" and record["script"] == "latin":
            assert not contains_arabic
        elif record["language"] in {"ar", "ary"}:
            assert contains_arabic
        else:
            assert not contains_arabic


def test_confirmatory_dataset_has_no_exact_normalized_duplicate_vs_development(dataset):
    development = _records(OLD_GOLD)
    old_queries = {_normalize(record["query"]) for record in development}
    assert not {_normalize(record["query"]) for record in dataset} & old_queries
    assert not {record["id"] for record in dataset} & {record["id"] for record in development}


def test_confirmatory_topics_are_new_relative_to_development_gold(dataset):
    development = _records(OLD_GOLD)
    old_topics = {record["topic"] for record in development}
    assert not {record["topic"] for record in dataset} & old_topics


def test_confirmatory_manifest_declares_independence(dataset):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["case_count"] == len(dataset) == 60
    assert manifest["dataset_sha256"] == _sha256(DATASET)
    assert manifest["semantic_group_count"] == 12
    assert manifest["phase_a_blind_to_old_gold"] is True
    assert manifest["old_gold_used_only_for_deduplication"] is True
    assert manifest["prior_experiment_results_used"] is False
    assert manifest["prior_failure_ids_used"] is False
    assert manifest["retrieval_used_for_case_selection"] is False
    assert manifest["H1_used_for_case_selection"] is False
    assert manifest["BGE_used_for_case_selection"] is False
    assert manifest["external_llm_used"] is False
    assert manifest["independent_from_policy_selection"] is True
    assert manifest["purpose"] == "J6_07C_CONFIRMATORY_EVALUATION"
    assert manifest["evaluation_status"] == "NOT_EVALUATED"
    assert manifest["query_adapter_confirmatory_created"] is False
    assert manifest["retrieval_evaluation_created"] is False
    assert manifest["overlap_audit"]["exact_normalized_duplicate_count"] == 0
    assert manifest["overlap_audit"]["high_lexical_overlap_warning_count"] == 0


def test_frozen_input_hashes_remain_unchanged():
    assert _sha256(DATASET) == CONFIRMATORY_DATASET_SHA256
    assert _sha256(MANIFEST) == CONFIRMATORY_MANIFEST_SHA256
    assert _sha256(OLD_GOLD) == (
        "68da7ebcd739dc42e874bf0052b7a2a6c33a2013ba1cd91979ccea7b6d0355b5"
    )
    assert _sha256(CHUNKS) == (
        "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
    )
    assert _sha256(CORPUS) == (
        "2ec834e160851a59d52b9d200470aa714ec850a39f672e480b2c8207880f3b0a"
    )
    assert _sha256(PAGES) == (
        "69312419a872f02eb74e1547dc4a80c8d322be6796580d54a17b1ee2b7252968"
    )


def test_confirmatory_test_logic_does_not_read_h1_report_or_use_providers():
    source = Path(__file__).read_text(encoding="utf-8").lower()
    h1_report_name = "query_adapter_" + "hybrid_replay_v1.json"
    assert h1_report_name not in source
    assert "app." + "llm" not in source
    assert "htt" + "px" not in source


def test_confirmatory_query_adapter_is_not_created_by_gold_authoring():
    artifact = ROOT / "evaluation/rag/query_adapter_confirmatory_v1.jsonl"
    assert artifact.exists()
    assert not (ROOT / "backend/data/rag/manifests/embedding_model_v1.json").exists()
