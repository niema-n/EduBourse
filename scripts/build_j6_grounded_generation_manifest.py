"""Write the frozen J6 grounded-generation manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.grounded_generation import (
    GENERATION_MODEL,
    GROUNDING_PROMPT_SHA256,
    RETRIEVAL_SERVICE_MANIFEST_SHA256,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "backend/data/rag/manifests/grounded_generation_v1.json"
    manifest = {
        "schema_version": "j6-grounded-generation-v1",
        "service_version": 1,
        "retrieval_service_manifest_sha256": RETRIEVAL_SERVICE_MANIFEST_SHA256,
        "retrieval_policy": "H1_LANGUAGE_ROUTED_V1",
        "retrieval_top_k_default": 5,
        "generation_model": GENERATION_MODEL,
        "temperature": 0,
        "grounding_prompt_sha256": GROUNDING_PROMPT_SHA256,
        "supported_languages": ["fr", "en", "ar", "ary"],
        "supported_language_script_combinations": [
            "fr/latin",
            "en/latin",
            "ar/arabic",
            "ary/latin",
            "ary/arabic",
        ],
        "supported_scripts": ["latin", "arabic"],
        "corpus_language": "fr",
        "direct_target_language_generation": True,
        "whole_corpus_translation": False,
        "structured_evidence_required": True,
        "unknown_evidence_fail_closed": True,
        "empty_evidence_answer_fail_closed": True,
        "prompt_injection_context_is_data": True,
        "personalized_advice_defense_in_depth": True,
        "answer_generation": True,
        "citation_rendering": False,
        "production_integration": False,
        "next_step": "J6_FINAL_INTEGRATION_AND_E2E",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
