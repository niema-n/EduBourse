from pathlib import Path

from app.rag import retrieval_service


class ReadOnlyCollection:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


class ReadOnlyClient:
    def __init__(self, count: int) -> None:
        self.collection = ReadOnlyCollection(count)
        self.created = False

    def get_collection(self, *, name: str, embedding_function):
        assert name == "j6_bge_m3_content_v1"
        assert embedding_function is None
        return self.collection

    def get_or_create_collection(self, *args, **kwargs):
        self.created = True
        raise AssertionError("health inspection must not create a collection")


def test_persisted_j6_health_reads_expected_collection_without_writing(monkeypatch) -> None:
    client = ReadOnlyClient(count=353)
    monkeypatch.setattr(retrieval_service.chromadb, "PersistentClient", lambda path: client)

    count = retrieval_service.inspect_persisted_index(Path("/repo"))

    assert count == 353
    assert client.created is False


def test_persisted_j6_health_rejects_an_unexpected_count(monkeypatch) -> None:
    client = ReadOnlyClient(count=0)
    monkeypatch.setattr(retrieval_service.chromadb, "PersistentClient", lambda path: client)

    try:
        retrieval_service.inspect_persisted_index(Path("/repo"))
    except retrieval_service.RetrievalConfigurationError as exc:
        assert "cardinality" in str(exc)
    else:
        raise AssertionError("invalid J6 index count was accepted")
