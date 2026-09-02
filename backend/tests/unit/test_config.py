import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_build_postgres_dsn_without_hardcoded_secret() -> None:
    settings = Settings(
        APP_NAME="Test App",
        APP_ENV="test",
        APP_VERSION="0.0.1",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5432,
        POSTGRES_DB="app",
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="local-password",
    )

    assert settings.postgres_dsn == "postgresql+psycopg://user:local-password@db:5432/app"
    assert settings.app_env == "test"


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="demo")


def test_settings_reject_placeholder_password_outside_local_or_test() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", POSTGRES_PASSWORD="change_me_for_local_only")
