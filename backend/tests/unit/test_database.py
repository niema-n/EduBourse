from app.database import postgres


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_get_db_closes_session(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(postgres, "get_sessionmaker", lambda: lambda: session)

    dependency = postgres.get_db()
    yielded = next(dependency)

    assert yielded is session

    try:
        next(dependency)
    except StopIteration:
        pass

    assert session.closed is True
