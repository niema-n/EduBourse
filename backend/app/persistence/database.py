"""Lazy SQLAlchemy database access for optional application persistence."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


class PersistenceDisabledError(RuntimeError):
    """Raised when persistence is used while the feature flag is disabled."""


class PersistenceConfigurationError(RuntimeError):
    """Raised when enabled persistence has no usable database configuration."""


class PersistenceUnavailableError(RuntimeError):
    """Raised when the configured database cannot be reached."""


class PersistenceDatabase:
    """Lazily owns the engine and session factory for persistence operations."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        enabled: bool | None = None,
        database_url: str | None = None,
        engine_factory: Callable[..., Engine] = create_engine,
    ) -> None:
        resolved_settings = settings or get_settings()
        self.enabled = resolved_settings.persistence_enabled if enabled is None else enabled
        self.database_url = (
            resolved_settings.database_url if database_url is None else database_url
        )
        self._engine_factory = engine_factory
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise PersistenceDisabledError("persistence is disabled")

    def _require_url(self) -> str:
        self._require_enabled()
        url = self.database_url.strip()
        if not url:
            raise PersistenceConfigurationError(
                "DATABASE_URL is required when persistence is enabled"
            )
        return url

    def get_engine(self) -> Engine:
        if self._engine is None:
            url = self._require_url()
            engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
            if url.startswith("sqlite"):
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            self._engine = self._engine_factory(url, **engine_kwargs)
        return self._engine

    def get_session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(), autoflush=False, expire_on_commit=False
            )
        return self._session_factory

    def check_connection(self) -> None:
        try:
            with self.get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
        except (PersistenceDisabledError, PersistenceConfigurationError):
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailableError("database connectivity check failed") from exc

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
