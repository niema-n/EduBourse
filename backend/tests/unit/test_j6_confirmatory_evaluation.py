import hashlib
import json
from pathlib import Path

import pytest

from app.rag.embedding_benchmark import GoldCase
from app.rag.hybrid_policy import HYBRID_POLICY_ID, RRF_K, quality_gate
from app.rag.query_adapter import adapter_request_payload

ROOT = Path(__file__).resolve().parents[3]
GOLD = ROOT / "evaluation/rag/embedding_gold_confirmatory_v1.jsonl"
MANIFEST = ROOT / "backend/data/rag/manifests/confirmatory_gold_v1.json"
ARTIFACT = ROOT / "evaluation/rag/query_adapter_confirmatory_v1.jsonl"
REPORT = ROOT / "backend/data/rag/manifests/query_adapter_confirmatory_result_v1.json"
OLD_REPORT = ROOT / "backend/data/rag/manifests/query_adapter_hybrid_replay_v1.json"

CONFIRMATORY_GOLD_SHA256 = "09984f65ceab47d5b0aafdaec051cedf45219c183d765985bd95b2652b839289"
CONFIRMATORY_MANIFEST_SHA256 = "aa83584e1bf9daa89dafa946c29fb100688645f4b25c4d3b6e28cab15a3787d8"
CONFIRMATORY_QUERY_ARTIFACT_SHA256 = (
    "b133e0bb14a4e0303ace70d217296e8d9fa4c560a387c228234c680f526a4230"
)
CONFIRMATORY_RESULT_REPORT_SHA256 = (
    "796f962921f91f429e5cf3eeba37be7dbbd2a091cb366f05930f99fc4257b6cf"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _report() -> dict:
    if not REPORT.exists():
        pytest.fail("confirmatory result report has not been generated")
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_confirmatory_inputs_remain_frozen():
    assert _sha256(GOLD) == CONFIRMATORY_GOLD_SHA256
    assert _sha256(MANIFEST) == CONFIRMATORY_MANIFEST_SHA256
    assert _sha256(ARTIFACT) == CONFIRMATORY_QUERY_ARTIFACT_SHA256
    assert _sha256(REPORT) == CONFIRMATORY_RESULT_REPORT_SHA256


def test_adapter_payload_excludes_gold_metadata():
    case = GoldCase(
        id="confirm-en-01",
        query="What are the general steps for acquiring listed shares?",
        language="en",
        script="latin",
        topic="acquisition_actions_cotees",
        expected_source_ids=["secret-source-that-must-not-be-sent"],
    )
    assert adapter_request_payload(case) == {
        "case_id": case.id,
        "original_query": case.query,
        "language": case.language,
        "script": case.script,
    }


def test_confirmatory_result_report_has_frozen_policy_and_model():
    report = _report()
    assert report["policy_id"] == HYBRID_POLICY_ID == "H1_LANGUAGE_ROUTED_V1"
    assert report["embedding_model"] == "BAAI/bge-m3"
    assert report["embedding_revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert report["adapter_model"] == "qwen/qwen3.6-27b"
    assert report["pacing_interval_seconds"] == 2.5
    assert report["record_counts"] == {
        "ary_latin_arabic_queries": 12,
        "confirmatory_records": 60,
        "content_filtered_chunks": 353,
        "french_queries": 60,
        "null_ary_arabic_branches": 48,
    }
    assert RRF_K == 60


def test_confirmatory_result_report_is_independent_and_not_production_ready():
    report = _report()
    assert report["evaluation_type"] == "INDEPENDENT_CONFIRMATORY_EVALUATION"
    assert report["independent_validation"] is True
    assert report["policy_frozen_before_evaluation"] is True
    assert report["confirmatory_gold_frozen_before_evaluation"] is True
    assert report["query_adapter_frozen_before_evaluation"] is True
    assert report["selection_bias_from_development_set_acknowledged"] is True
    assert report["deployment_ready"] is False
    assert report["no_more_retrieval_policy_tuning"] is True
    assert report["next_step"] == "J6_05B_CHROMA"


def test_confirmatory_gate_is_computed_from_report_metrics():
    report = _report()
    metrics = report["metrics"]
    assert report["quality_gate"] is quality_gate(
        metrics["macro_recall5"], metrics["worst_recall5"]
    )


def test_confirmatory_artifact_structure_and_no_result_path_collision():
    records = [json.loads(line) for line in ARTIFACT.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 60
    assert len({record["case_id"] for record in records}) == 60
    assert sum(record["retrieval_query_ary_arabic"] is not None for record in records) == 12
    assert set(REPORT.parts[-1:]) == {"query_adapter_confirmatory_result_v1.json"}
    assert OLD_REPORT.exists()
    assert not (ROOT / "backend/data/rag/manifests/embedding_model_v1.json").exists()
