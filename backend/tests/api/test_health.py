from fastapi.testclient import TestClient

from app.api import health as health_module
from app.database.postgres import PostgresCheck
from app.main import app
from app.providers.chroma import ChromaCheck


def test_health_endpoint_ok(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="ok", collection_status="missing", document_count=0),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["postgres"] == {"status": "ok"}
    assert body["chroma"]["status"] == "ok"
    assert body["chroma"]["collection_status"] == "missing"
    assert body["chroma"]["document_count"] == 0


def test_health_endpoint_degraded_when_postgres_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "check_postgres",
        lambda: PostgresCheck(status="unavailable"),
    )
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="ok", collection_status="missing", document_count=0),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["postgres"]["status"] == "unavailable"


def test_health_endpoint_degraded_when_chroma_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="unavailable", collection_status="unknown", document_count=0),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["chroma"]["status"] == "unavailable"


def test_health_endpoint_unavailable_when_all_dependencies_are_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_module,
        "check_postgres",
        lambda: PostgresCheck(status="unavailable"),
    )
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="unavailable", collection_status="unknown", document_count=0),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"


def test_health_response_schema_has_expected_fields(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="ok", collection_status="present", document_count=3),
    )
    client = TestClient(app)

    body = client.get("/health").json()

    assert set(body) == {"status", "app", "version", "environment", "postgres", "chroma"}
    assert set(body["chroma"]) == {"status", "collection", "collection_status", "document_count"}


def test_health_response_does_not_expose_secrets(monkeypatch) -> None:
    monkeypatch.setattr(health_module, "check_postgres", lambda: PostgresCheck(status="ok"))
    monkeypatch.setattr(
        health_module,
        "check_chroma",
        lambda: ChromaCheck(status="ok", collection_status="missing", document_count=0),
    )
    client = TestClient(app)

    response_text = client.get("/health").text.lower()

    forbidden_fragments = ["password", "secret", "token", "postgresql+psycopg://"]
    assert all(fragment not in response_text for fragment in forbidden_fragments)


def test_liveness_endpoint_does_not_check_dependencies(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("dependency check should not run during liveness")

    monkeypatch.setattr(health_module, "check_postgres", fail_if_called)
    monkeypatch.setattr(health_module, "check_chroma", fail_if_called)
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
