"""Run the real local J6-05A multilingual embedding benchmark."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from huggingface_hub.errors import HfHubHTTPError

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.embedding_benchmark import (
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
    benchmark_provider_policies,
    classify_index_inputs,
    load_chunks,
    load_gold,
    select_model,
    verify_sentence_transformer_snapshot,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recover_bge_snapshot(model_name: str) -> tuple[Path, str]:
    downloaded = Path(
        snapshot_download(
            model_name,
            force_download=False,
            allow_patterns=[
                "config*.json",
                "modules.json",
                "tokenizer*",
                "sentencepiece*",
                "model.safetensors*",
                "pytorch_model.bin*",
                "1_Pooling/*",
                "2_Normalize/*",
            ],
        )
    )
    candidates = [downloaded, *downloaded.parent.iterdir()]
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        try:
            verify_sentence_transformer_snapshot(candidate)
        except ValueError:
            continue
        return candidate, candidate.name
    raise ValueError("no complete SentenceTransformers snapshot was found")


def _load_previous_results(
    path: Path, gold_sha256: str, chunks_sha256: str, roles: dict[str, str]
) -> dict:
    previous = json.loads(path.read_text(encoding="utf-8"))
    if previous.get("gold_dataset_sha256") != gold_sha256:
        raise ValueError("previous benchmark gold hash does not match")
    if previous.get("chunks_sha256") != chunks_sha256:
        raise ValueError("previous benchmark chunks hash does not match")
    expected_roles = {
        role: sum(value == role for value in roles.values())
        for role in ("content", "navigation", "shared_redundant")
    }
    if previous.get("retrieval_roles") != expected_roles:
        raise ValueError("previous benchmark retrieval roles do not match")
    required = {
        "BAAI/bge-m3::ALL_CANONICAL",
        "BAAI/bge-m3::CONTENT_FILTERED",
        "intfloat/multilingual-e5-base::ALL_CANONICAL",
        "intfloat/multilingual-e5-base::CONTENT_FILTERED",
    }
    if not required.issubset(previous.get("results", {})):
        raise ValueError(
            "previous benchmark does not contain both validated candidates"
        )
    return previous


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    gold_path = root / "evaluation/rag/embedding_gold_v1.jsonl"
    chunks = load_chunks(chunks_path)
    gold = load_gold(gold_path)
    roles, duplicate_groups = classify_index_inputs(chunks)
    chunks_sha256 = _sha256(chunks_path)
    gold_sha256 = _sha256(gold_path)
    previous = _load_previous_results(
        root / "backend/data/rag/manifests/embedding_benchmark_v1.json",
        gold_sha256,
        chunks_sha256,
        roles,
    )
    role_counts = {
        role: sum(value == role for value in roles.values())
        for role in ("content", "navigation", "shared_redundant")
    }
    results: dict[str, dict] = dict(previous["results"])
    providers: dict[str, SentenceTransformerEmbeddingProvider] = {}
    model_errors: dict[str, dict[str, str]] = {}
    target_name = "intfloat/multilingual-e5-large-instruct"
    for spec in MODEL_SPECS:
        if spec.model_name != target_name:
            continue
        print(f"Loading {spec.model_name} ...", flush=True)
        started = time.perf_counter()
        try:
            model_ref = None
            revision = None
            if spec.model_name == target_name:
                snapshot, revision = _recover_bge_snapshot(spec.model_name)
                model_ref = snapshot
            provider = SentenceTransformerEmbeddingProvider(
                spec,
                model_ref=model_ref,
                revision=revision,
                model_kwargs={"torch_dtype": torch.float32},
            )
        except (HfHubHTTPError, OSError, RuntimeError, TypeError, ValueError) as exc:
            model_errors[spec.model_name] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            print(f"Unable to load {spec.model_name}: {type(exc).__name__}", flush=True)
            continue
        load_ms = (time.perf_counter() - started) * 1000
        providers[spec.model_name] = provider
        print(f"Benchmarking {spec.model_name} / ALL_CANONICAL ...", flush=True)
        print(f"Benchmarking {spec.model_name} / CONTENT_FILTERED ...", flush=True)
        for policy, result in benchmark_provider_policies(
            provider, chunks, gold, roles
        ).items():
            result["model_load_ms"] = round(load_ms, 3)
            results[f"{spec.model_name}::{policy}"] = result
    selected_key = select_model(results) if not model_errors else None
    report = {
        "schema_version": "j6-embedding-benchmark-v1",
        "chunks_sha256": chunks_sha256,
        "gold_dataset_sha256": gold_sha256,
        "canonical_chunk_count": len(chunks),
        "gold_query_count": len(gold),
        "gold_language_counts": dict(
            Counter(
                case.language if case.language != "ary" else f"ary-{case.script}"
                for case in gold
            )
        ),
        "retrieval_roles": role_counts,
        "duplicate_groups": duplicate_groups,
        "candidate_models": [],
        "model_errors": model_errors,
        "page_chunk_metric_status": "not_evaluated",
        "results": results,
        "selection": {
            "selected_model_policy": selected_key,
            "status": "selected" if selected_key else "NO_WINNER",
            "rationale": (
                "worst-language Recall@5, then macro Recall@5, MRR@10, Recall@1"
                if selected_key
                else (
                    "Incomplete candidate set; no model selected"
                    if model_errors
                    else (
                        "Neither model met macro Recall@5 >= 0.90 and "
                        "per-language Recall@5 >= 0.80"
                    )
                )
            ),
        },
    }
    previous_candidates = {
        item["model_name"]: item for item in previous.get("candidate_models", [])
    }
    for spec in MODEL_SPECS:
        provider = providers.get(spec.model_name)
        report["candidate_models"].append(
            {
                **previous_candidates.get(spec.model_name, {}),
                "model_name": spec.model_name,
                "resolved_revision": provider.revision
                if provider
                else previous_candidates.get(spec.model_name, {}).get(
                    "resolved_revision"
                ),
                "expected_dimension": spec.expected_dimension,
                "embedding_dimension": provider.dimension
                if provider
                else previous_candidates.get(spec.model_name, {}).get(
                    "embedding_dimension"
                ),
                "load_status": "completed"
                if provider
                else previous_candidates.get(spec.model_name, {}).get(
                    "load_status", "failed"
                ),
                "normalize_embeddings": True,
                "distance_metric": "cosine",
                "query_mode": spec.query_mode,
                "query_format": spec.query_format,
                "query_instruction": spec.query_instruction,
                "passage_mode": spec.passage_mode,
                "passage_format": spec.passage_format,
            }
        )
    output_dir = root / "backend/data/rag/manifests"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "embedding_benchmark_v1.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if selected_key:
        model_name, policy = selected_key.split("::", 1)
        provider = providers[model_name]
        spec = next(spec for spec in MODEL_SPECS if spec.model_name == model_name)
        model_manifest = {
            "model_name": model_name,
            "revision": provider.revision,
            "embedding_dimension": provider.dimension,
            "normalize_embeddings": True,
            "distance_metric": "cosine",
            "query_format": spec.query_format,
            "passage_format": spec.passage_format,
            "chunks_sha256": report["chunks_sha256"],
            "input_policy": policy,
            "gold_dataset_sha256": report["gold_dataset_sha256"],
            "selection_status": "selected",
        }
        (output_dir / "embedding_model_v1.json").write_text(
            json.dumps(model_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"report={report_path}")
    print(f"selection={selected_key or 'NO_WINNER'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
