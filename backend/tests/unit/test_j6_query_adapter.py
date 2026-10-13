from inspect import getsource
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.rag.chunking import ChunkRecord
from app.rag.embedding_benchmark import GoldCase
from app.rag.query_adapter import (
    ADAPTER_MODEL,
    ADAPTER_PROMPT_SHA256,
    ADAPTER_SYSTEM_PROMPT,
    MIN_REQUEST_INTERVAL_SECONDS,
    RRF_K,
    AdapterOutput,
    GroqQueryAdapterProvider,
    adapter_request_payload,
    deduplicate_branches,
    evaluate_policy,
    experiment_gate,
    generate_artifact_records,
    generate_then_evaluate,
    policy_branches,
    quality_gate_from_metrics,
    query_artifact_record,
    query_quality_flags,
    resolve_embedding_model_spec,
    rrf_fuse,
    rrf_scores,
    sanitized_provider_error,
    validate_content_filtered_count,
    validate_embedding_model_revision,
    validate_query_artifact,
)


def _case(language="ary", script="latin"):
    return GoldCase(
        id="case-1", query="chno lborsa?", language=language, script=script,
        topic="x", expected_source_ids=["source-a"],
    )


def test_adapter_input_excludes_gold_fields_and_preserves_metadata():
    payload = adapter_request_payload(_case())
    assert set(payload) == {"case_id", "original_query", "language", "script"}
    assert "expected_source_ids" not in payload
    assert "topic" not in payload


def test_adapter_output_contract_and_ary_branch_rules():
    output = AdapterOutput(
        retrieval_query_fr="Que signifie la Bourse ?",
        retrieval_query_ary_arabic="شنو هي البورصة؟",
    )
    record = query_artifact_record(_case(), output)
    assert record["original_query"] == "chno lborsa?"
    assert record["retrieval_query_ary_arabic"] is not None
    french_record = query_artifact_record(
        _case("fr", "latin"), AdapterOutput(retrieval_query_fr="Que signifie la Bourse ?")
    )
    assert french_record["retrieval_query_ary_arabic"] is None
    with pytest.raises(ValueError):
        query_artifact_record(_case(), AdapterOutput(retrieval_query_fr="Que signifie la Bourse ?"))


def test_artifact_validation_rejects_gold_leakage_and_requires_all_queries():
    case = _case("fr", "latin")
    record = query_artifact_record(
        case, AdapterOutput(retrieval_query_fr="Que signifie la Bourse ?")
    )
    assert validate_query_artifact([record], [case]) == [record]
    leaked = {**record, "topic": "x"}
    with pytest.raises(ValueError):
        validate_query_artifact([leaked], [case])


def test_rrf_formula_deduplication_and_stable_tie_breaking():
    assert deduplicate_branches([("a", "Question"), ("b", " question ")]) == [("a", "Question")]
    assert rrf_fuse([[0, 1], [1, 0]], ["b", "a"], RRF_K) == [1, 0]
    assert rrf_fuse([[0]], ["chunk"], RRF_K) == [0]


def test_rrf_uses_one_based_frozen_formula():
    formula_scores = rrf_scores([[0, 1, 2]], RRF_K)
    assert rrf_fuse([[0, 1, 2]], ["a", "b", "c"], RRF_K) == [0, 1, 2]
    assert formula_scores[0] == pytest.approx(1 / 61)
    assert formula_scores[1] == pytest.approx(1 / 62)
    assert formula_scores[2] == pytest.approx(1 / 63)


@pytest.mark.parametrize(
    ("macro", "worst", "expected"),
    [(0.62, 0.25, False), (0.90, 0.80, True), (0.10, 0.00, False)],
)
def test_quality_gate_and_experiment_gate_are_derived_booleans(macro, worst, expected):
    gate = quality_gate_from_metrics({"fr": worst}, macro, worst)
    assert type(gate) is bool
    assert gate is expected
    assert experiment_gate(gate) == ("PASS" if expected else "FAIL")


def test_quality_gate_empty_metrics_is_false_bool():
    gate = quality_gate_from_metrics({}, 1.0, 1.0)
    assert type(gate) is bool
    assert gate is False


def test_model_spec_is_resolved_by_name_not_position():
    first = SimpleNamespace(model_name="another-model")
    bge = SimpleNamespace(model_name="BAAI/bge-m3")
    assert resolve_embedding_model_spec([first, bge], "BAAI/bge-m3") is bge
    with pytest.raises(ValueError):
        resolve_embedding_model_spec([first], "BAAI/bge-m3")


def test_frozen_model_revision_and_content_count_guards():
    validate_embedding_model_revision("revision", "revision")
    with pytest.raises(ValueError):
        validate_embedding_model_revision("wrong", "revision")
    validate_content_filtered_count(353)
    with pytest.raises(ValueError):
        validate_content_filtered_count(352)


def _artifact_cases(count=40):
    return [
        GoldCase(
            id=f"case-{index}", query=f"question {index}", language="fr", script="latin",
            topic="x", expected_source_ids=["source-a"],
        )
        for index in range(count)
    ]


def _artifact_records(cases):
    return [
        query_artifact_record(case, AdapterOutput(retrieval_query_fr="requête française"))
        for case in cases
    ]


@pytest.mark.parametrize("count", [39, 41])
def test_artifact_record_count_must_be_exactly_frozen_gold(count):
    gold = _artifact_cases(40)
    records = _artifact_records(gold[:count]) if count == 39 else _artifact_records(gold) + [
        _artifact_records(gold[:1])[0]
    ]
    with pytest.raises(ValueError):
        validate_query_artifact(records, gold)


def test_artifact_duplicate_case_id_is_rejected():
    gold = _artifact_cases(40)
    records = _artifact_records(gold)
    records[-1] = {**records[-1], "case_id": records[0]["case_id"]}
    with pytest.raises(ValueError):
        validate_query_artifact(records, gold)


class _FailingProvider:
    def generate(self, payload):
        raise RuntimeError("429 rate limit; api_key=secret-value")


class _FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class _RecordingProvider:
    model = "qwen/qwen3.6-27b"

    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def generate(self, payload):
        self.calls.append(payload)
        if self.fail_at is not None and len(self.calls) == self.fail_at:
            raise RuntimeError("provider failed")
        return AdapterOutput(retrieval_query_fr=f"French query {len(self.calls)}")


def test_request_pacing_does_not_delay_first_call_and_spaces_following_calls():
    clock = _FakeClock()
    provider = _RecordingProvider()
    gold = _artifact_cases(3)
    generate_artifact_records(gold, provider, clock=clock.clock, sleep=clock.sleep)
    assert provider.calls[0]["case_id"] == "case-0"
    assert clock.sleeps == [MIN_REQUEST_INTERVAL_SECONDS, MIN_REQUEST_INTERVAL_SECONDS]
    assert all(interval >= 2.5 for interval in clock.sleeps)
    assert 60 / MIN_REQUEST_INTERVAL_SECONDS <= 24


def test_request_pacing_fake_clock_does_not_really_sleep():
    clock = _FakeClock()
    generate_artifact_records(
        _artifact_cases(2), _RecordingProvider(), clock=clock.clock, sleep=clock.sleep
    )
    assert clock.now == 100.0 + MIN_REQUEST_INTERVAL_SECONDS


def test_provider_failure_stops_generation_without_retry():
    clock = _FakeClock()
    provider = _RecordingProvider(fail_at=2)
    with pytest.raises(RuntimeError, match="provider failed"):
        generate_artifact_records(
            _artifact_cases(3), provider, clock=clock.clock, sleep=clock.sleep
        )
    assert len(provider.calls) == 2


def test_frozen_provider_contract_remains_unchanged():
    # qwen/qwen3.6-27b (the model evaluated in the frozen confirmatory manifests)
    # was retired by Groq (confirmed live: it now returns 404) and replaced by
    # qwen/qwen3.8-27b, which is what production actually runs today.
    assert ADAPTER_MODEL == "qwen/qwen3.8-27b"
    assert ADAPTER_PROMPT_SHA256 == (
        "b786ecd5ceed65dfd2fe418551732b67612863f771ebd89aafcd0865527d0300"
    )
    source = getsource(GroqQueryAdapterProvider.generate)
    assert "temperature=0" in source
    assert 'reasoning_effort="none"' in source
    assert "max_completion_tokens=160" in source
    assert 'response_format={"type": "json_object"}' in source
    assert "max_retries=0" not in source
    init_source = getsource(GroqQueryAdapterProvider.__init__)
    assert "max_retries=0" in init_source


def test_provider_failure_stops_before_evaluation():
    evaluation_called = False

    def evaluate(_records):
        nonlocal evaluation_called
        evaluation_called = True
        return "unexpected"

    with pytest.raises(RuntimeError):
        generate_then_evaluate(_artifact_cases(40), _FailingProvider(), evaluate)
    assert evaluation_called is False


def test_language_mismatch_is_structural_and_only_flags():
    fr_record = {
        "retrieval_query_fr": "سؤال عن البورصة",
        "retrieval_query_ary_arabic": None,
    }
    for language, script in (("fr", "latin"), ("en", "latin"), ("ar", "arabic"), ("ary", "arabic")):
        assert "LANGUAGE_MISMATCH" in query_quality_flags(
            _case(language, script), fr_record
        )
    ary_case = _case("ary", "latin")
    ary_record = {
        "retrieval_query_fr": "Question sur la bourse",
        "retrieval_query_ary_arabic": "chno lborsa",
    }
    assert "LANGUAGE_MISMATCH" in query_quality_flags(ary_case, ary_record)
    assert ary_record["retrieval_query_fr"] == "Question sur la bourse"


def test_provider_error_message_is_sanitized():
    message = sanitized_provider_error(RuntimeError("429 https://api.test/x api_key=secret"))
    assert "secret" not in message
    assert "https://" not in message
    assert len(message) <= 240


@pytest.mark.parametrize(
    "error_text",
    [
        "Authorization: Bearer gsk_FAKEKEY123456789012345678_AUDITONLY",
        "authorization: bearer gsk_FAKEKEY123456789012345678_AUDITONLY",
        "Bearer gsk_FAKEKEY123456789012345678_AUDITONLY",
        "api_key=gsk_FAKEKEY123456789012345678_AUDITONLY",
        "api_key='gsk_FAKEKEY123456789012345678_AUDITONLY'",
        "api-key: gsk_FAKEKEY123456789012345678_AUDITONLY",
        "x-api-key: gsk_FAKEKEY123456789012345678_AUDITONLY",
        "headers={'x-api-key': 'gsk_FAKEKEY123456789012345678_AUDITONLY'}",
        "Incorrect API key provided: gsk_FAKEKEY123456789012345678_AUDITONLY",
    ],
)
def test_provider_error_redacts_synthetic_credentials(error_text):
    sanitized = sanitized_provider_error(RuntimeError(error_text))
    assert "gsk_" not in sanitized
    assert "FAKEKEY" not in sanitized
    assert "AUDITONLY" not in sanitized


@pytest.mark.parametrize(
    ("error_text", "context"),
    [
        ("429 Too Many Requests - rate limit exceeded", "429"),
        ("401 Unauthorized - Invalid API Key", "401"),
        ("connection timeout", "timeout"),
        ("model not found", "model not found"),
    ],
)
def test_provider_error_preserves_safe_context(error_text, context):
    assert context.casefold() in sanitized_provider_error(RuntimeError(error_text)).casefold()


def test_policy_branch_matrix():
    record = {"retrieval_query_fr": "question française", "retrieval_query_ary_arabic": "سؤال"}
    assert len(policy_branches(_case("fr", "latin"), record, "P3_ORIGINAL_PLUS_ADAPTIVE_RRF")) == 2
    assert len(policy_branches(_case("en", "latin"), record, "P3_ORIGINAL_PLUS_ADAPTIVE_RRF")) == 2
    assert len(
        policy_branches(_case("ary", "arabic"), record, "P3_ORIGINAL_PLUS_ADAPTIVE_RRF")
    ) == 2
    assert len(
        policy_branches(_case("ary", "latin"), record, "P3_ORIGINAL_PLUS_ADAPTIVE_RRF")
    ) == 3


def test_p0_evaluation_uses_original_query_and_metrics_unchanged():
    case = _case("fr", "latin")
    chunks = [
        ChunkRecord(
            chunk_id="chunk-a", source_id="source-a", title="A", authority="ammc", language="fr",
            categories=["test"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=0, text="a",
            text_sha256="a" * 64, char_count=1, word_count=1, document_hash="b" * 64,
            source_page_text_sha256="c" * 64,
        ),
        ChunkRecord(
            chunk_id="chunk-b", source_id="source-b", title="B", authority="ammc", language="fr",
            categories=["test"],
            page_start=1, page_end=1, page_numbers=[1], chunk_index=1, text="b",
            text_sha256="d" * 64, char_count=1, word_count=1, document_hash="e" * 64,
            source_page_text_sha256="f" * 64,
        ),
    ]
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
    metrics, rankings = evaluate_policy(
        "P0_ORIGINAL_ONLY",
        [case],
        {case.id: {"retrieval_query_fr": "fr", "retrieval_query_ary_arabic": None}},
        chunks, vectors, {case.query: np.array([1.0, 0.0])},
    )
    assert rankings == [[0, 1]]
    assert metrics["source_recall5"] == 1.0


def test_query_adapter_module_has_no_chroma_or_fourth_model():
    source = Path(__file__).parents[2] / "app" / "rag" / "query_adapter.py"
    text = source.read_text(encoding="utf-8")
    assert "chromadb" not in text.lower()
    assert "BAAI/bge-m3" not in text
    assert "expected_source_ids" not in ADAPTER_SYSTEM_PROMPT
