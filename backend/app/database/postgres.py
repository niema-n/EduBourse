from collections.abc import Generator
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@dataclass(frozen=True)
class PostgresCheck:
    status: str


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.postgres_dsn, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def check_postgres() -> PostgresCheck:
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return PostgresCheck(status="unavailable")
    return PostgresCheck(status="ok")
