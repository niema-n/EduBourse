"""Write the immutable J6-06 retrieval-service manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.rag.retrieval_service import service_manifest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "backend/data/rag/manifests/retrieval_service_v1.json"
    path.write_text(
        json.dumps(service_manifest(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
