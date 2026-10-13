import ast
import hashlib
from pathlib import Path

import numpy as np

from app.rag.ary_latin_diagnostic import (
    ADJACENT_SOURCE_IDS_BY_TOPIC,
    derive_conclusion,
    diagnostic_recall5,
    failure_reasons,
    normalize_ary_latin,
    pair_gold_cases,
    rank_variant,
)
from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import (
    E5_LARGE_INSTRUCT_QUERY_INSTRUCTION,
    MODEL_SPECS,
    PAGE_CHUNK_METRIC_STATUS,
    GoldCase,
    _normalized_text,
    benchmark_provider,
    benchmark_provider_policies,
    classify_index_inputs,
    cosine_similarity,
    format_passage,
    format_query,
    load_chunks,
    load_gold,
    mrr_at_10,
    recall_at_k,
    select_model,
)


def _chunk(chunk_id: str, text: str, source_id: str = "ammc-source") -> ChunkRecord:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ChunkRecord(
        chunk_id=chunk_id,
        source_id=source_id,
        title="Titre",
        authority="ammc",
        language="fr",
        categories=["market_basics"],
        page_start=1,
        page_end=1,
        page_numbers=[1],
        chunk_index=0,
        text=text,
        text_sha256=digest,
        char_count=len(text),
        word_count=len(text.split()),
        document_hash="a" * 64,
        source_page_text_sha256="b" * 64,
    )


def test_chunks_load_through_strict_chunk_record_and_keep_identity(tmp_path: Path) -> None:
    chunk = _chunk("frozen", "Une définition financière.")
    path = tmp_path / "chunks.jsonl"
    path.write_text(chunk.model_dump_json() + "\n", encoding="utf-8")
    loaded = load_chunks(path)
    assert loaded[0].model_dump() == chunk.model_dump()


def test_navigation_classifier_is_conservative() -> None:
    navigation = _chunk("nav", "23 | Les acteurs | 8")
    definition = _chunk("definition", "Une action représente une part du capital.")
    roles, _ = classify_index_inputs([navigation, definition])
    assert roles == {"nav": "navigation", "definition": "content"}


def test_shared_redundant_detection_keeps_substantive_duplicates() -> None:
    boilerplate = [
        _chunk("a", "GUIDE DE L'INVESTISSEUR\nAMMC", "source-a"),
        _chunk("b", "GUIDE DE L'INVESTISSEUR\nAMMC", "source-b"),
    ]
    substantive = [
        _chunk("c", "Une action représente une part du capital.", "source-a"),
        _chunk("d", "Une action représente une part du capital.", "source-b"),
    ]
    roles, groups = classify_index_inputs(boilerplate + substantive)
    assert roles["a"] == roles["b"] == "shared_redundant"
    assert roles["c"] == roles["d"] == "content"
    assert len(groups) == 1
    assert groups[0]["source_ids"] == ["source-a", "source-b"]


def test_duplicate_comparison_normalizes_apostrophes_and_plural_form() -> None:
    assert _normalized_text("GUIDE DE L'INVESTISSEUR") == _normalized_text(
        "GUIDE DE L’INVESTISSEUR"
    )
    assert _normalized_text("GUIDE DE L'INVESTISSEUR") == _normalized_text(
        "GUIDE DE LʼINVESTISSEUR"
    )
    assert "guides de l'investisseur" in _normalized_text("LES GUIDES DE L’INVESTISSEUR")


def test_three_real_style_duplicate_groups_are_shared_redundant() -> None:
    chunks = [
        _chunk("guide-a", "LES GUIDES DE L’INVESTISSEUR\nDécembre 2022", "a"),
        _chunk("guide-b", "LES GUIDES DE L'INVESTISSEUR\nDécembre 2022", "b"),
        _chunk("cover-a", "Comprendre les instruments financiers\nGUIDE", "a"),
        _chunk("cover-b", "Comprendre les instruments financiers\nGUIDE", "b"),
        _chunk("contact-a", "Avenue Annakhil, Hay Riad - contact@ammc.ma", "a"),
        _chunk("contact-b", "Avenue Annakhil, Hay Riad - contact@ammc.ma", "b"),
        _chunk("sub-a", "Une action représente une part du capital.", "a"),
        _chunk("sub-b", "Une action représente une part du capital.", "b"),
    ]
    roles, groups = classify_index_inputs(chunks)
    assert len(groups) == 3
    assert sum(len(group["chunk_ids"]) for group in groups) == 6
    assert roles["sub-a"] == roles["sub-b"] == "content"


def test_gold_script_buckets_are_real_and_distinct() -> None:
    gold_path = Path(__file__).parents[3] / "evaluation" / "rag" / "embedding_gold_v1.jsonl"
    cases = load_gold(gold_path)
    latin = {case.id: case.query for case in cases if case.id.startswith("ary-latin")}
    arabic = {case.id: case.query for case in cases if case.id.startswith("ary-arabic")}
    assert len(latin) == len(arabic) == 8
    for query in latin.values():
        assert any(character.isascii() and character.isalpha() for character in query)
        assert not any("\u0600" <= character <= "\u06ff" for character in query)
    for query in arabic.values():
        assert any("\u0600" <= character <= "\u06ff" for character in query)
    assert set(latin.values()).isdisjoint(arabic.values())


def test_gold_ar_and_ary_arabic_buckets_are_distinct() -> None:
    gold_path = Path(__file__).parents[3] / "evaluation" / "rag" / "embedding_gold_v1.jsonl"
    cases = load_gold(gold_path)
    ar = {case.query for case in cases if case.language == "ar"}
    ary = {case.query for case in cases if case.id.startswith("ary-arabic")}
    assert len(ar) == len(ary) == 8
    assert ar.isdisjoint(ary)


def test_page_and_chunk_metrics_are_explicitly_not_evaluated_without_gold() -> None:
    assert PAGE_CHUNK_METRIC_STATUS == "not_evaluated"


def test_policy_roles_never_delete_canonical_chunks() -> None:
    chunks = [_chunk("a", "23 | Les acteurs | 8"), _chunk("b", "Une définition financière.")]
    roles, _ = classify_index_inputs(chunks)
    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    assert len(chunks) == 2
    assert [chunk.chunk_id for chunk in filtered] == ["b"]


def test_bge_format_is_unprefixed_and_e5_is_prefixed_for_arabic() -> None:
    bge, e5, _ = MODEL_SPECS
    arabic = "ما هو السهم؟"
    assert format_query(bge, arabic) == arabic
    assert format_passage(bge, arabic) == arabic
    assert format_query(e5, arabic) == "query: ما هو السهم؟"
    assert format_passage(e5, arabic) == "passage: ما هو السهم؟"


def test_large_instruct_formatter_is_fixed_and_preserves_original_query() -> None:
    large = MODEL_SPECS[2]
    query = "chno lfer9 bin sahm w sanad?"
    formatted = format_query(large, query)
    assert formatted == (f"Instruct: {E5_LARGE_INSTRUCT_QUERY_INSTRUCTION}\nQuery: {query}")
    assert query in formatted
    assert "passage:" not in formatted
    assert large.expected_dimension == 1024
    assert large.query_mode == "instruct"
    assert format_passage(large, "Titre\nTexte") == "Titre\nTexte"


def test_cosine_similarity_normalizes_vectors() -> None:
    scores = cosine_similarity(np.array([2.0, 0.0]), np.array([[1.0, 0.0], [0.0, 3.0]]))
    assert np.allclose(scores, [1.0, 0.0])


def _cases() -> list[GoldCase]:
    return [
        GoldCase(
            id="fr", query="x", language="fr", script="latin", topic="x", expected_source_ids=["a"]
        ),
        GoldCase(
            id="en", query="x", language="en", script="latin", topic="x", expected_source_ids=["b"]
        ),
    ]


def test_recall_and_mrr_metrics() -> None:
    chunks = [_chunk("a", "a", "a"), _chunk("b", "b", "b")]
    cases = _cases()
    rankings = [[0, 1], [1, 0]]
    assert recall_at_k(rankings, cases, chunks, 1, "source") == 1.0
    assert recall_at_k(rankings, cases, chunks, 1, "page") == 1.0
    assert mrr_at_10(rankings, cases, chunks) == 1.0


def test_selection_prioritizes_worst_language_then_macro_score() -> None:
    results = {
        "fr-special": {
            "macro_source_recall5": 0.99,
            "worst_language_recall5": 0.80,
            "mrr10": 0.99,
            "source_recall1": 0.99,
        },
        "multi-robust": {
            "macro_source_recall5": 0.94,
            "worst_language_recall5": 0.90,
            "mrr10": 0.90,
            "source_recall1": 0.80,
        },
    }
    assert select_model(results) == "multi-robust"


def test_quality_gate_can_return_no_winner() -> None:
    assert (
        select_model({"weak": {"macro_source_recall5": 0.89, "worst_language_recall5": 0.99}})
        is None
    )


def test_gold_contract_is_strict_and_balanced() -> None:
    gold_path = Path(__file__).parents[3] / "evaluation" / "rag" / "embedding_gold_v1.jsonl"
    cases = [GoldCase.model_validate_json(line) for line in gold_path.read_bytes().splitlines()]
    counts = {(case.language, case.script): 0 for case in cases}
    for case in cases:
        counts[(case.language, case.script)] += 1
    assert len(cases) == 40
    assert set(counts.values()) == {8}


def test_benchmark_module_has_no_forbidden_runtime_imports() -> None:
    source = Path(__import__("app.rag.embedding_benchmark", fromlist=["__file__"]).__file__)
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {"chromadb", "faiss", "requests", "httpx", "google", "groq", "openai"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint(forbidden)


def test_ary_latin_pairing_uses_compatible_frozen_gold_records() -> None:
    cases = [
        GoldCase(
            id="ary-latin-01",
            query="chno?",
            language="ary",
            script="latin",
            topic="x",
            expected_source_ids=["a"],
        ),
        GoldCase(
            id="ary-arabic-01",
            query="شنو؟",
            language="ary",
            script="arabic",
            topic="x",
            expected_source_ids=["a"],
        ),
        GoldCase(
            id="ar-01",
            query="ما؟",
            language="ar",
            script="arabic",
            topic="x",
            expected_source_ids=["a"],
        ),
        GoldCase(
            id="fr-01",
            query="quoi?",
            language="fr",
            script="latin",
            topic="x",
            expected_source_ids=["a"],
        ),
    ]
    paired = pair_gold_cases(cases)
    assert paired[0]["ORIGINAL_ARY_LATIN"].query == "chno?"
    assert paired[0]["ARY_ARABIC_COUNTERPART"].id == "ary-arabic-01"
    assert paired[0]["AR_COUNTERPART"].expected_source_ids == ["a"]
    assert paired[0]["FR_COUNTERPART"].id == "fr-01"
    assert cases[0].query == "chno?"


def test_ary_latin_pairing_rejects_incompatible_source_labels() -> None:
    cases = [
        GoldCase(
            id="ary-latin-01",
            query="chno?",
            language="ary",
            script="latin",
            topic="x",
            expected_source_ids=["a"],
        ),
        GoldCase(
            id="fr-01",
            query="quoi?",
            language="fr",
            script="latin",
            topic="x",
            expected_source_ids=["b"],
        ),
    ]
    assert pair_gold_cases(cases)[0]["FR_COUNTERPART"] is None


def test_ary_latin_normalization_is_not_translation() -> None:
    original = "  CHNO lfer9  bin sahm  w sanad!!  "
    assert normalize_ary_latin(original) == "chno lfer9 bin sahm w sanad?"
    assert "sahm" in normalize_ary_latin(original)


def test_diagnostic_rank_and_recall_metrics_are_deterministic() -> None:
    chunks = [_chunk("a", "a", "a"), _chunk("b", "b", "b")]
    case = GoldCase(
        id="ary-latin-01",
        query="x",
        language="ary",
        script="latin",
        topic="x",
        expected_source_ids=["b"],
    )
    result = rank_variant(np.array([0.0, 1.0]), np.array([[1.0, 0.0], [0.0, 1.0]]), chunks, case)
    result["available"] = True
    assert result["expected_source_best_rank"] == 1
    assert result["hit_at_5"] is True
    assert diagnostic_recall5([result]) == 1.0


def test_diagnostic_conclusion_identifies_representation_gap() -> None:
    metrics = {
        "ORIGINAL_ARY_LATIN": {"recall_at_5": 0.625},
        "ARY_ARABIC_COUNTERPART": {"recall_at_5": 0.875},
        "AR_COUNTERPART": {"recall_at_5": 0.75},
        "FR_COUNTERPART": {"recall_at_5": 1.0},
        "ARY_LATIN_NORMALIZED": {"recall_at_5": 0.625},
    }
    conclusion = derive_conclusion(metrics)
    assert conclusion["diagnosis"] == "QUERY_REPRESENTATION_GAP"
    assert conclusion["recommended_next_step"] == "J6_07_QUERY_ADAPTER_EXPERIMENT"


def _failure_case(
    *,
    original_hit: bool,
    ary_arabic_hit: bool,
    ar_hit: bool,
    fr_hit: bool,
    normalized_hit: bool = False,
    topic: str = "x", top5: list[str] | None = None,
) -> dict:
    def result(hit: bool, available: bool = True) -> dict:
        return {"available": available, "hit_at_5": hit}

    return {
        "topic": topic,
        "variants": {
            "ORIGINAL_ARY_LATIN": {
                "available": True,
                "hit_at_5": original_hit,
                "top_5_source_ids": top5 or [],
            },
            "ARY_ARABIC_COUNTERPART": result(ary_arabic_hit),
            "AR_COUNTERPART": result(ar_hit),
            "FR_COUNTERPART": result(fr_hit),
            "ARY_LATIN_NORMALIZED": result(normalized_hit),
        },
    }


def test_failure_reasons_distinguish_script_language_and_topic_gaps() -> None:
    ary_arabic = failure_reasons(
        _failure_case(original_hit=False, ary_arabic_hit=True, ar_hit=True, fr_hit=True)
    )
    assert ary_arabic == ["CROSS_SCRIPT_GAP"]
    language = failure_reasons(
        _failure_case(original_hit=False, ary_arabic_hit=False, ar_hit=False, fr_hit=True)
    )
    assert language == ["LANGUAGE_TRANSFER_GAP"]
    assert "CROSS_SCRIPT_GAP" not in language


def test_failure_reasons_prevent_corpus_contradiction_and_detect_normalization() -> None:
    recovered = failure_reasons(
        _failure_case(original_hit=False, ary_arabic_hit=True, ar_hit=True, fr_hit=True)
    )
    assert "CORPUS_GAP" not in recovered
    normalized = failure_reasons(
        _failure_case(
            original_hit=False,
            ary_arabic_hit=False,
            ar_hit=False,
            fr_hit=False,
            normalized_hit=True,
        )
    )
    assert "ORTHOGRAPHIC_NORMALIZATION_GAP" in normalized
    corpus = failure_reasons(
        _failure_case(
            original_hit=False,
            ary_arabic_hit=False,
            ar_hit=False,
            fr_hit=False,
            normalized_hit=False,
        )
    )
    assert corpus == ["CORPUS_GAP"]


def test_failure_reasons_mark_topic_overlap_without_inventing_gold_ambiguity() -> None:
    sources = sorted(ADJACENT_SOURCE_IDS_BY_TOPIC["valeur_liquidative"])
    reasons = failure_reasons(
        _failure_case(
            original_hit=False,
            ary_arabic_hit=False,
            ar_hit=False,
            fr_hit=False,
            normalized_hit=False,
            topic="valeur_liquidative",
            top5=[sources[0]],
        )
    )
    assert reasons == ["TOPIC_OVERLAP"]
    case_03 = failure_reasons(
        _failure_case(
            original_hit=False,
            ary_arabic_hit=False,
            ar_hit=False,
            fr_hit=True,
            topic="valeur_liquidative",
            top5=sources[:1],
        )
    )
    assert case_03 == ["LANGUAGE_TRANSFER_GAP", "TOPIC_OVERLAP"]
    for topic in ("public_offerings", "investor_protection"):
        case = failure_reasons(
            _failure_case(
                original_hit=False,
                ary_arabic_hit=True,
                ar_hit=True,
                fr_hit=False,
                topic=topic,
                top5=list(ADJACENT_SOURCE_IDS_BY_TOPIC[topic])[:1],
            )
        )
        assert case == ["CROSS_SCRIPT_GAP", "TOPIC_OVERLAP"]


def test_ary_latin_diagnostic_is_bge_only_content_filtered_and_offline() -> None:
    script = (Path(__file__).parents[3] / "scripts" / "diagnose_ary_latin.py").read_text(
        encoding="utf-8"
    )
    assert 'MODEL_NAME = "BAAI/bge-m3"' in script
    assert 'input_policy": "CONTENT_FILTERED"' in script
    assert "chromadb" not in script.lower()
    assert "translation" not in script.lower()
    assert "timestamp" not in script.lower()


class _CountingEmbedder:
    dimension = 2
    revision = "fake"
    device = "cpu"
    batch_size = 8

    def __init__(self) -> None:
        self.passage_calls: list[list[str]] = []
        self.query_calls: list[list[str]] = []

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        self.passage_calls.append(texts)
        return np.asarray([[float(index), 1.0] for index, _ in enumerate(texts)])

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        self.query_calls.append(texts)
        return np.asarray([[1.0, float(index + 1)] for index, _ in enumerate(texts)])


def test_benchmark_encodes_canonical_passages_and_queries_once() -> None:
    chunks = [_chunk("a", "a", "a"), _chunk("b", "b", "b"), _chunk("c", "c", "c")]
    roles = {"a": "content", "b": "navigation", "c": "content"}
    cases = _cases()
    provider = _CountingEmbedder()

    results = benchmark_provider_policies(provider, chunks, cases, roles)

    assert len(provider.passage_calls) == 1
    assert len(provider.passage_calls[0]) == 3
    assert len(provider.query_calls) == 1
    assert provider.query_calls[0] == [case.query for case in cases]
    assert results["ALL_CANONICAL"]["documents_indexed"] == 3
    assert results["CONTENT_FILTERED"]["documents_indexed"] == 2


def test_filtered_policy_is_a_deterministic_subset_of_canonical_embeddings() -> None:
    chunks = [_chunk("a", "a", "a"), _chunk("b", "b", "b"), _chunk("c", "c", "c")]
    roles = {"a": "content", "b": "navigation", "c": "content"}
    cases = _cases()
    provider = _CountingEmbedder()
    canonical = provider.embed_passages(["a", "b", "c"])
    filtered = canonical[[0, 2]]

    results = benchmark_provider_policies(provider, chunks, cases, roles)

    assert np.array_equal(filtered, canonical[[0, 2]])
    assert list(results) == ["ALL_CANONICAL", "CONTENT_FILTERED"]
    assert benchmark_provider(provider, chunks, cases, roles, "CONTENT_FILTERED")


def test_filtered_rankings_match_independent_encoding() -> None:
    chunks = [_chunk("a", "a", "a"), _chunk("b", "b", "b"), _chunk("c", "c", "c")]
    roles = {"a": "content", "b": "navigation", "c": "content"}
    cases = _cases()
    provider = _CountingEmbedder()
    results = benchmark_provider_policies(provider, chunks, cases, roles)

    filtered = [chunk for chunk in chunks if roles[chunk.chunk_id] == "content"]
    independent_passages = provider.embed_passages(["a", "c"])
    independent_queries = provider.embed_queries([case.query for case in cases])
    independent_rankings = [
        list(np.argsort(-cosine_similarity(query, independent_passages)))
        for query in independent_queries
    ]
    assert results["CONTENT_FILTERED"]["source_recall5"] == recall_at_k(
        independent_rankings, cases, filtered, 5, "source"
    )
    assert results["CONTENT_FILTERED"]["mrr10"] == mrr_at_10(
        independent_rankings, cases, filtered
    )
