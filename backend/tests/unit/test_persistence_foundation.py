import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.persistence.database import (
    PersistenceConfigurationError,
    PersistenceDatabase,
    PersistenceDisabledError,
    PersistenceUnavailableError,
)
from app.persistence.models import ConversationThreadRecord
from app.persistence.thread_store import ConversationThreadStore


def make_database() -> PersistenceDatabase:
    return PersistenceDatabase(
        enabled=True,
        database_url="sqlite+pysqlite:///:memory:",
        engine_factory=lambda url, **kwargs: create_engine(
            url, poolclass=StaticPool, connect_args={"check_same_thread": False}
        ),
    )


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=value.tzinfo or UTC)


def test_disabled_persistence_does_not_create_engine() -> None:
    calls = 0

    def factory(*args, **kwargs):
        nonlocal calls
        calls += 1
        return create_engine("sqlite+pysqlite:///:memory:")

    database = PersistenceDatabase(enabled=False, database_url="sqlite://", engine_factory=factory)

    with pytest.raises(PersistenceDisabledError):
        database.get_engine()

    assert calls == 0


def test_persistence_enabled_defaults_to_false() -> None:
    from app.config import Settings

    assert Settings().persistence_enabled is False


def test_enabled_persistence_without_database_url_fails_closed() -> None:
    database = PersistenceDatabase(enabled=True, database_url="")

    with pytest.raises(PersistenceConfigurationError):
        database.get_engine()


def test_thread_store_supports_get_get_or_create_and_touch() -> None:
    database = make_database()
    Base.metadata.create_all(database.get_engine())
    store = ConversationThreadStore(database)

    assert store.get("thread-1") is None
    created = store.get_or_create("thread-1")
    assert created.thread_id == "thread-1"
    assert created.created_at is not None
    assert created.updated_at is not None
    assert as_utc(store.get_or_create("thread-1").created_at) == as_utc(created.created_at)

    touched = store.touch("thread-1")
    assert touched is not None
    assert as_utc(touched.updated_at) > as_utc(created.updated_at)
    assert store.touch("missing") is None


def test_model_has_only_one_thread_identity() -> None:
    database = make_database()
    Base.metadata.create_all(database.get_engine())

    columns = {column["name"] for column in inspect(database.get_engine()).get_columns(
        "conversation_threads"
    )}
    assert columns == {"thread_id", "created_at", "updated_at"}


def test_database_repr_does_not_expose_database_url() -> None:
    secret_url = "postgresql+psycopg://user:secret@localhost/db"
    database = PersistenceDatabase(enabled=True, database_url=secret_url)

    assert secret_url not in repr(database)


def test_database_errors_do_not_expose_database_url() -> None:
    secret_url = "postgresql+psycopg://user:SUPER_FAKE_PASSWORD@localhost/test"

    def failing_factory(*args, **kwargs):
        raise IntegrityError("connect", {}, RuntimeError(secret_url))

    database = PersistenceDatabase(
        enabled=True, database_url=secret_url, engine_factory=failing_factory
    )

    with pytest.raises(PersistenceUnavailableError) as error:
        database.check_connection()

    assert "SUPER_FAKE_PASSWORD" not in str(error.value)
    assert "SUPER_FAKE_PASSWORD" not in repr(error.value)


def test_get_or_create_returns_existing_thread_after_concurrent_insert() -> None:
    existing = ConversationThreadRecord(
        thread_id="raced", created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )

    class RaceSession:
        def __init__(self) -> None:
            self.reads = 0
            self.closed = False
            self.rolled_back = False

        def scalar(self, statement):
            self.reads += 1
            return None if self.reads == 1 else existing

        def add(self, record) -> None:
            pass

        def commit(self) -> None:
            raise IntegrityError(
                "insert",
                {},
                RuntimeError("UNIQUE constraint failed: conversation_threads.thread_id"),
            )

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    session = RaceSession()
    database = PersistenceDatabase(
        enabled=True,
        database_url="sqlite://",
        engine_factory=lambda *args, **kwargs: None,
    )
    database._session_factory = lambda: session

    result = ConversationThreadStore(database).get_or_create("raced")

    assert result.thread_id == "raced"
    assert session.rolled_back is True
    assert session.closed is True


def test_alembic_resolves_only_database_url() -> None:
    source_path = Path(__file__).parents[2] / "alembic" / "env.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_persistence_url"
    )
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), "exec"), namespace)

    class Config:
        database_url = "postgresql+psycopg://canonical@localhost/db"
        postgres_dsn = "postgresql+psycopg://legacy@localhost/legacy"

    assert namespace["resolve_persistence_url"](Config()) == Config.database_url

    Config.database_url = ""
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        namespace["resolve_persistence_url"](Config())
