from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnvironment = Literal["local", "test", "development", "staging", "production"]
LOCAL_PLACEHOLDER_PASSWORDS = {"change_me_for_local_only", "postgres", "password", "changeme"}


class Settings(BaseSettings):
    app_name: str = Field(default="EduBourse AI API", alias="APP_NAME")
    app_env: AppEnvironment = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_public_port: int = Field(default=8080, alias="BACKEND_PUBLIC_PORT")
    frontend_public_port: int = Field(default=5173, alias="FRONTEND_PUBLIC_PORT")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="financial_education", alias="POSTGRES_DB")
    postgres_user: str = Field(default="financial_app", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me_for_local_only", alias="POSTGRES_PASSWORD")

    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    chroma_collection: str = Field(
        default="financial_education_foundation",
        alias="CHROMA_COLLECTION",
    )

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    voice_provider: str = Field(default="gemini", alias="VOICE_PROVIDER")
    voice_mode: str = Field(default="streaming", alias="VOICE_MODE")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_stt_model: str = Field(default="", alias="GEMINI_STT_MODEL")
    gemini_tts_model: str = Field(
        default="gemini-3.1-flash-tts-preview", alias="GEMINI_TTS_MODEL"
    )
    gemini_tts_voice: str = Field(default="Kore", alias="GEMINI_TTS_VOICE")
    gemini_http_timeout_ms: int = Field(default=60_000, alias="GEMINI_HTTP_TIMEOUT_MS")
    voice_max_audio_bytes: int = Field(default=10_485_760, alias="VOICE_MAX_AUDIO_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @model_validator(mode="after")
    def reject_placeholder_credentials_outside_local(self) -> "Settings":
        if self.app_env not in {"local", "test"}:
            password = self.postgres_password.strip().lower()
            if password in LOCAL_PLACEHOLDER_PASSWORDS:
                raise ValueError("POSTGRES_PASSWORD must not use a placeholder outside local/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
