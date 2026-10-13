from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import rag_admin
from app.main import app


def _client(monkeypatch, token: str = "test-token") -> TestClient:
    monkeypatch.setattr(
        rag_admin,
        "get_settings",
        lambda: SimpleNamespace(edubourse_n8n_internal_token=token),
    )
    monkeypatch.setattr(rag_admin, "_validate_local_corpus", lambda _root: (3, 353))
    return TestClient(app)


def test_rag_update_rejects_missing_or_invalid_token(monkeypatch) -> None:
    client = _client(monkeypatch)

    missing = client.post("/api/v1/admin/rag/update", json={"mode": "validate"})
    invalid = client.post(
        "/api/v1/admin/rag/update",
        headers={"X-EduBourse-Internal-Token": "wrong"},
        json={"mode": "validate"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_rag_update_accepts_authorized_local_source(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/api/v1/admin/rag/update",
        headers={"X-EduBourse-Internal-Token": "test-token"},
        json={"mode": "incremental_update", "source": "local_approved_corpus"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mode": "incremental_update",
        "source": "local_approved_corpus",
        "sources_checked": 3,
        "documents_changed": 0,
        "chunks_added": 0,
        "chunks_updated": 0,
        "chunks_unchanged": 353,
    }


def test_rag_update_rejects_arbitrary_url_source(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/api/v1/admin/rag/update",
        headers={"X-EduBourse-Internal-Token": "test-token"},
        json={"mode": "validate", "source": "https://example.com"},
    )

    assert response.status_code == 422


def test_repeated_incremental_update_is_idempotent(monkeypatch) -> None:
    client = _client(monkeypatch)
    headers = {"X-EduBourse-Internal-Token": "test-token"}

    first = client.post(
        "/api/v1/admin/rag/update",
        headers=headers,
        json={"mode": "incremental_update"},
    )
    second = client.post(
        "/api/v1/admin/rag/update",
        headers=headers,
        json={"mode": "incremental_update"},
    )

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_unconfigured_rag_update_is_controlled(monkeypatch) -> None:
    client = _client(monkeypatch, token="")

    response = client.post("/api/v1/admin/rag/update", json={"mode": "validate"})

    assert response.status_code == 503
    assert response.json() == {"detail": "RAG administration is not configured"}
