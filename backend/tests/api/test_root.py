from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"]
    assert response.headers["x-request-id"]


def test_request_id_reuses_valid_incoming_header() -> None:
    client = TestClient(app)
    request_id = "4d1bdf2a-3f58-45aa-b76e-721548964f17"

    response = client.get("/", headers={"x-request-id": request_id})

    assert response.headers["x-request-id"] == request_id


def test_request_id_replaces_invalid_incoming_header() -> None:
    client = TestClient(app)

    response = client.get("/", headers={"x-request-id": "not-valid"})

    assert response.headers["x-request-id"] != "not-valid"
    UUID(response.headers["x-request-id"])
