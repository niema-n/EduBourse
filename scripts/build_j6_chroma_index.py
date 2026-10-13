"""Build the isolated persistent J6 BGE-M3 Chroma index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.chroma_index import build_collection


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = build_collection(root)
    path = root / "backend/data/rag/manifests/chroma_index_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"INDEX_PATH = {manifest['index_path']}")
    print(f"COLLECTION_NAME = {manifest['collection_name']}")
    print(f"INDEXED_CHUNK_COUNT = {manifest['indexed_chunk_count']}")
    print(f"PERSISTENCE_REOPEN_TEST = {'PASS' if manifest['persistence_reopen_test'] else 'FAIL'}")
    print(f"CHROMA_VS_OFFLINE_RANKING = {manifest['chroma_vs_offline_ranking']}")
    print(f"MANIFEST_PATH = {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
