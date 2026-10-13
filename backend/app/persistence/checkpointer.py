"""LangGraph checkpoint selection for the optional persistence mode."""

from collections.abc import Callable
from threading import Lock
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row

from app.config import Settings


class PersistentPostgresCheckpointer:
    """Lazy owner of the official PostgresSaver connection and schema setup."""

    def __init__(
        self,
        database_url: str,
        *,
        connection_factory: Callable[..., Any] = Connection.connect,
        saver_factory: Callable[..., PostgresSaver] = PostgresSaver,
    ) -> None:
        self._database_url = database_url
        self._connection_factory = connection_factory
        self._saver_factory = saver_factory
        self._connection: Any | None = None
        self._saver: PostgresSaver | None = None
        self._initialization_error: Exception | None = None
        self._initialization_lock = Lock()

    def _normalized_url(self) -> str:
        if self._database_url.startswith("postgresql+psycopg://"):
            return "postgresql://" + self._database_url.removeprefix("postgresql+psycopg://")
        return self._database_url

    def _ensure_saver(self) -> PostgresSaver:
        if self._saver is not None:
            return self._saver
        if self._initialization_error is not None:
            raise self._initialization_error
        with self._initialization_lock:
            if self._saver is not None:
                return self._saver
            if self._initialization_error is not None:
                raise self._initialization_error
            connection = None
            try:
                connection = self._connection_factory(
                    self._normalized_url(),
                    autocommit=True,
                    prepare_threshold=0,
                    row_factory=dict_row,
                )
                saver = self._saver_factory(connection)
                saver.setup()
            except Exception as exc:
                if connection is not None:
                    connection.close()
                self._initialization_error = exc
                raise
            self._connection = connection
            self._saver = saver
        return self._saver

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ensure_saver(), name)

    def close(self) -> None:
        with self._initialization_lock:
            if self._connection is not None:
                self._connection.close()
            self._connection = None
            self._saver = None
            self._initialization_error = None


def create_graph_checkpointer(settings: Settings) -> Any:
    """Select one checkpointer backend without touching the database when disabled."""
    if not settings.persistence_enabled:
        return MemorySaver()
    database_url = settings.database_url.strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required when persistence is enabled")
    return PersistentPostgresCheckpointer(database_url)
