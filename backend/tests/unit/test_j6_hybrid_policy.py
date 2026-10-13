import hashlib
import json
from pathlib import Path

import pytest

from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import GoldCase
from app.rag.hybrid_policy import (
    HYBRID_POLICY_ID,
    RRF_K,
    expected_rank,
    fuse_rankings,
    hybrid_branches,
    quality_gate,
    rrf_scores,
)


def _case(language="ary", script="latin"):
    return GoldCase(
        id="case-1",
        query="original",
        language=language,
        script=script,
        topic="topic",
        expected_source_ids=["source-a"],
    )


def _record():
    return {
        "case_id": "case-1",
        "original_query": "original",
        "language": "ignored",
        "script": "ignored",
        "retrieval_query_fr": "french",
        "retrieval_query_ary_arabic": "arabic",
        "expected_source_ids": ["must-not-route"],
        "topic": "must-not-route",
    }


REPO_ROOT = Path(__file__).resolve().parents[3]
H1_REPORT = REPO_ROOT / "backend/data/rag/manifests/query_adapter_hybrid_replay_v1.json"


def _h1_report():
    return json.loads(H1_REPORT.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("language", "script", "expected"),
    [
        ("fr", "latin", ["original"]),
        ("en", "latin", ["french"]),
        ("ar", "arabic", ["original", "french"]),
        ("ary", "arabic", ["original", "french"]),
        ("ary", "latin", ["original", "french", "ary_arabic"]),
    ],
)
def test_h1_routes_only_by_language_and_script(language, script, expected):
    branches = hybrid_branches(language, script, _record())
    assert [name for name, _ in branches] == expected
    assert HYBRID_POLICY_ID == "H1_LANGUAGE_ROUTED_V1"


def test_h1_rejects_unknown_language_script():
    for language, script in (("xx", "latin"), ("xx", "arabic")):
        with pytest.raises(ValueError):
            hybrid_branches(language, script, _record())


def test_h1_routing_is_independent_of_gold_metadata():
    for language, script in (("en", "latin"), ("ary", "latin")):
        first = _record()
        second = _record() | {
            "case_id": "different-case",
            "topic": "different-topic",
            "expected_source_ids": ["different-source"],
        }
        assert hybrid_branches(language, script, first) == hybrid_branches(
            language, script, second
        )


def test_h1_report_scientific_status_guards():
    report = _h1_report()
    assert report["policy_id"] == "H1_LANGUAGE_ROUTED_V1"
    assert report["policy_origin"] == "POST_HOC_FROM_J6_07_EXP1"
    assert report["evaluation_type"] == "SAME_GOLD_REPLAY"
    assert report["independent_validation"] is False
    assert report["selection_bias_acknowledged"] is True
    assert report["deployment_ready"] is False
    assert report["chroma_ready"] is False
    assert report["recommended_next_step"] == "INDEPENDENT_CONFIRMATORY_EVALUATION"


def test_h1_report_provenance_hash_guards():
    expected = {
        "evaluation/rag/query_adapter_v1.jsonl":
            "b510a4a772175e1567f5fefd18131d6464de05a12d632acf5b3aca4e5f1939ef",
        "backend/data/rag/manifests/query_adapter_experiment_v1.json":
            "3a7c42908f346b5d11dfe9f35c2509dd6a49cca24e6692f5948ce643972880f3",
        "backend/data/rag/manifests/query_adapter_hybrid_replay_v1.json":
            "23e5899b03e2ffabf01fbd687f3e51ee5b10af2abea813ab92a1ac8a8cb8e483",
        "evaluation/rag/embedding_gold_v1.jsonl":
            "68da7ebcd739dc42e874bf0052b7a2a6c33a2013ba1cd91979ccea7b6d0355b5",
        "backend/data/rag/processed/chunks_v1.jsonl":
            "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1",
    }
    assert {
        relative: _sha256(REPO_ROOT / relative) for relative in expected
    } == expected


def test_h1_report_transition_and_quality_guards():
    report = _h1_report()
    assert report["recovered_vs_p0"] == [
        "en-03",
        "ar-03",
        "ary-latin-03",
        "ary-latin-05",
        "ary-latin-06",
        "ary-arabic-03",
    ]
    assert report["regressed_vs_p0"] == []
    assert report["recovered_vs_p1"] == ["ary-latin-03", "ary-latin-05"]
    assert report["regressed_vs_p1"] == []
    assert report["macro_recall5"] == pytest.approx(0.950)
    assert report["worst_recall5"] == pytest.approx(0.875)
    assert report["replay_quality_gate"] is True
    assert report["independent_validation"] is False
    assert report["deployment_ready"] is False
    assert report["chroma_ready"] is False


def test_rrf_is_unweighted_one_based_with_k_60():
    scores = rrf_scores([[0, 1, 2]], RRF_K)
    assert scores[0] == pytest.approx(1 / 61)
    assert scores[1] == pytest.approx(1 / 62)
    assert scores[2] == pytest.approx(1 / 63)


def test_fusion_uses_stable_chunk_id_tie_break():
    chunks = [
        ChunkRecord(
            chunk_id="b", source_id="b", title="B", authority="a", categories=["x"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=0, text="b",
            text_sha256="b" * 64, char_count=1, word_count=1,
            document_hash="c" * 64, source_page_text_sha256="d" * 64,
        ),
        ChunkRecord(
            chunk_id="a", source_id="a", title="A", authority="a", categories=["x"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=1, text="a",
            text_sha256="e" * 64, char_count=1, word_count=1,
            document_hash="f" * 64, source_page_text_sha256="0" * 64,
        ),
    ]
    assert fuse_rankings([[0], [1]], chunks) == [1, 0]


def test_quality_gate_is_computed():
    assert quality_gate(0.95, 0.875) is True
    assert quality_gate(0.95, 0.75) is False


def test_expected_rank_is_evaluation_only():
    case = _case("fr", "latin")
    chunks = [
        ChunkRecord(
            chunk_id="one", source_id="other", title="One", authority="a", categories=["x"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=0, text="one",
            text_sha256="1" * 64, char_count=3, word_count=1,
            document_hash="2" * 64, source_page_text_sha256="3" * 64,
        ),
        ChunkRecord(
            chunk_id="two", source_id="source-a", title="Two", authority="a", categories=["x"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=1, text="two",
            text_sha256="4" * 64, char_count=3, word_count=1,
            document_hash="5" * 64, source_page_text_sha256="6" * 64,
        ),
    ]
    assert expected_rank([0, 1], case, chunks) == 2


def test_hybrid_module_has_no_provider_or_chroma_import():
    from pathlib import Path

    source = Path(__import__("app.rag.hybrid_policy", fromlist=["__file__"]).__file__).read_text()
    forbidden = ("groq", "openai", "google", "anthropic", "chromadb")
    assert not any(name in source.lower() for name in forbidden)
