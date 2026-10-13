"""Write the frozen J6 final integration manifest."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

OUTPUT = ROOT / "backend/data/rag/manifests/j6_final_v1.json"
GROUNDED_MANIFEST_SHA256 = "4a98e96df45ad177e311d3a99cbf250b6cdd3cf18e1bb39262921053650c9d7a"
RETRIEVAL_MANIFEST_SHA256 = "4467a6ed7c8a1d23ee2d90a39159ac0c404567d42c8d7da10d30dfce9e450f1e"

MANIFEST = {
    "schema_version": "j6-final-v1",
    "j6_version": 1,
    "retrieval_service_manifest_sha256": RETRIEVAL_MANIFEST_SHA256,
    "grounded_generation_manifest_sha256": GROUNDED_MANIFEST_SHA256,
    "grounding_prompt_sha256": "2339deb276ae2ac3d20ab457a4acb1fb4996fcee6bb1e4156e0cb846beb5dd8d",
    "retrieval_policy": "H1_LANGUAGE_ROUTED_V1",
    "rrf_k": 60,
    "embedding_model": "BAAI/bge-m3",
    "embedding_revision": "5617a9f61b028005a4858fdac845db406aefb181",
    "chroma_collection": "j6_bge_m3_content_v1",
    "content_chunk_count": 353,
    "supported_languages": ["fr", "en", "ar", "ary"],
    "supported_language_script_combinations": 5,
    "direct_target_language_generation": True,
    "structured_citations": True,
    "source_context_delimiter_hardened": True,
    "security_upstream_authoritative": True,
    "supervisor_upstream_authoritative": True,
    "text_voice_shared_business_pipeline": True,
    "retrieval_science_frozen": True,
    "no_more_retrieval_policy_tuning": True,
    "confirmatory_quality_gate": False,
    "retrieval_policy_status": "ACCEPTED_WITH_DOCUMENTED_CONFIRMATORY_LIMITATIONS",
    "known_limitations": [
        "Ary-Latin RRF dilution",
        "thin 3-chunk brochure retrieval competition",
    ],
    "production_integration": True,
    "external_provider_calls_in_tests": 0,
    "j6_complete_candidate": True,
    "next_step": "J6_FINAL_AUDIT",
}


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
