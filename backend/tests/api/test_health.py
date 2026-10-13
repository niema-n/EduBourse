from fastapi.testclient import TestClient

from app.api import health as health_module
from app.database.postgres import PostgresCheck
from app.main import app
from app.providers.chroma import ChromaCheck
from app.rag.runtime import RagIndexCheck


def _legacy_chroma(*, status="ok", count=0) -> ChromaCheck:
    return ChromaCheck(
        status=status,
        collection_status="present" if status == "ok" else "unknown",
        document_count=count,
    )


def _j6_index(*, status="available", count=353) -> RagIndexCheck:
    return RagIndexCheck(status=status, document_count=count)


def test_health_reports_the_real_j6_index_when_available(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(health_module, "check_retrieval_index", _j6_index)
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    body = TestClient(app).get("/health").json()

    assert body["status"] == "ok"
    assert body["rag_index"] == {
        "status": "available",
        "collection": "j6_bge_m3_content_v1",
        "document_count": 353,
    }


def test_empty_legacy_chroma_does_not_make_j6_unhealthy(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(health_module, "check_retrieval_index", _j6_index)
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    body = TestClient(app).get("/health").json()

    assert body["status"] == "ok"
    assert body["rag_index"]["status"] == "available"
    assert body["chroma_server"] == {
        "status": "ok",
        "collection": "financial_education_foundation",
        "collection_status": "present",
        "document_count": 0,
        "role": "legacy_infrastructure",
    }


def test_health_signals_when_the_real_j6_index_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(
        health_module, "check_retrieval_index", lambda: _j6_index(status="unavailable", count=0)
    )
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    body = TestClient(app).get("/health").json()

    assert body["status"] == "degraded"
    assert body["rag_index"]["status"] == "unavailable"
    assert body["rag_index"]["document_count"] == 0


def test_health_is_unavailable_when_postgres_and_j6_are_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module, "check_postgres", lambda: PostgresCheck(status="unavailable")
    )
    monkeypatch.setattr(
        health_module, "check_retrieval_index", lambda: _j6_index(status="unavailable", count=0)
    )
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    assert TestClient(app).get("/health").json()["status"] == "unavailable"


def test_health_response_schema_has_separate_rag_and_legacy_chroma(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(health_module, "check_retrieval_index", _j6_index)
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    body = TestClient(app).get("/health").json()

    assert set(body) == {
        "status", "app", "version", "environment", "postgres", "rag_index", "chroma_server"
    }
    assert set(body["rag_index"]) == {"status", "collection", "document_count"}
    assert set(body["chroma_server"]) == {
        "status", "collection", "collection_status", "document_count", "role"
    }


def test_health_response_does_not_expose_secrets(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(health_module, "check_retrieval_index", _j6_index)
    monkeypatch.setattr(health_module, "check_chroma", _legacy_chroma)

    response_text = TestClient(app).get("/health").text.lower()

    forbidden_fragments = ["password", "secret", "token", "postgresql+psycopg://"]
    assert all(fragment not in response_text for fragment in forbidden_fragments)


def test_liveness_endpoint_does_not_check_dependencies(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("dependency check should not run during liveness")

    monkeypatch.setattr(health_module, "check_postgres", fail_if_called)
    monkeypatch.setattr(health_module, "check_retrieval_index", fail_if_called)
    monkeypatch.setattr(health_module, "check_chroma", fail_if_called)

    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
