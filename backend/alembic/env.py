from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import get_settings
from app.database.base import Base
from app.persistence import models as persistence_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def resolve_persistence_url(settings) -> str:
    """Resolve the J8 migration target without falling back to legacy settings."""
    url = settings.database_url.strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for persistence migrations")
    return url


def get_url() -> str:
    return resolve_persistence_url(get_settings())


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
