"""Read-only runtime probes apart from isolated demo conversations/profiles."""

import json
from pathlib import Path
from uuid import uuid4

import httpx


def main():
    prefix = f"level-check-{uuid4().hex[:10]}"
    cases = [
        ("A", "a", "Je suis débutant en Bourse. Propose-moi un parcours de formation e-learning "
         "adapté à mon niveau et présente-moi les modules à suivre."),
        ("B1", "b", "Je veux suivre une formation en Bourse."),
        ("B2", "b", "intermédiaire"),
        ("C", "c", "Je veux évaluer mon niveau en Bourse."),
        ("routing_formation", "d", "Je veux suivre des modules de formation e-learning."),
        ("routing_orientation", "e", "Je ne sais pas par où commencer mon apprentissage."),
    ]
    results = []
    with httpx.Client(base_url="http://127.0.0.1:8080", timeout=180) as client:
        for name, suffix, message in cases:
            response = client.post("/api/v1/chat", json={
                "message": message, "thread_id": f"{prefix}-{suffix}",
            })
            result = {"case": name, "http_status": response.status_code,
                      "response": response.json()}
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
            Path("reports/formation-level-live.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )


if __name__ == "__main__":
    main()
