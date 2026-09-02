from app.providers import chroma


class MissingCollectionClient:
    def __init__(self) -> None:
        self.create_called = False

    def heartbeat(self) -> int:
        return 1

    def get_collection(self, _name: str):
        raise RuntimeError("collection does not exist")

    def get_or_create_collection(self, _name: str):
        self.create_called = True
        raise AssertionError("health check must not create collections")


def test_chroma_health_is_read_only_when_collection_is_missing(monkeypatch) -> None:
    client = MissingCollectionClient()
    monkeypatch.setattr(chroma, "get_chroma_client", lambda: client)

    result = chroma.check_chroma()

    assert result.status == "ok"
    assert result.collection_status == "missing"
    assert result.document_count == 0
    assert client.create_called is False
