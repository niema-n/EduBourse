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

    persistence_enabled: bool = Field(default=False, alias="PERSISTENCE_ENABLED")
    database_url: str = Field(default="", alias="DATABASE_URL")

    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    chroma_collection: str = Field(
        default="financial_education_foundation",
        alias="CHROMA_COLLECTION",
    )

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    edubourse_n8n_internal_token: str = Field(default="", alias="EDUBOURSE_N8N_INTERNAL_TOKEN")

    voice_provider: str = Field(default="gemini", alias="VOICE_PROVIDER")
    voice_mode: str = Field(default="streaming", alias="VOICE_MODE")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_stt_model: str = Field(default="", alias="GEMINI_STT_MODEL")
    gemini_tts_model: str = Field(default="gemini-2.5-flash-preview-tts", alias="GEMINI_TTS_MODEL")
    gemini_tts_voice: str = Field(default="Kore", alias="GEMINI_TTS_VOICE")
    gemini_http_timeout_ms: int = Field(default=60_000, alias="GEMINI_HTTP_TIMEOUT_MS")
    groq_model: str = Field(default="", alias="GROQ_MODEL")
    darija_localizer_provider: Literal["gemini", "groq"] = Field(
        default="gemini", alias="DARIJA_LOCALIZER_PROVIDER"
    )
    gemini_localizer_model: str = Field(
        default="gemini-3.6-flash", alias="GEMINI_LOCALIZER_MODEL"
    )
    gemini_localizer_max_output_tokens: int = Field(
        default=4096, alias="GEMINI_LOCALIZER_MAX_OUTPUT_TOKENS"
    )
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_final_response_max_output_tokens: int = Field(
        default=4096, alias="AZURE_FINAL_RESPONSE_MAX_OUTPUT_TOKENS"
    )
    final_response_provider: Literal["azure_openai"] = Field(
        default="azure_openai", alias="FINAL_RESPONSE_PROVIDER"
    )
    financial_expert_fallback_enabled: bool = Field(
        default=False, alias="FINANCIAL_EXPERT_FALLBACK_ENABLED"
    )
    financial_expert_web_grounding_enabled: bool = Field(
        default=False, alias="FINANCIAL_EXPERT_WEB_GROUNDING_ENABLED"
    )
    gemini_financial_expert_model: str = Field(
        default="gemini-2.5-flash", alias="GEMINI_FINANCIAL_EXPERT_MODEL"
    )
    # Extra approved web-grounding hosts (comma-separated), added to the project's
    # official hosts (app.rag.domain_policy.APPROVED_SOURCE_HOSTS).
    financial_expert_approved_domains: str = Field(
        default="", alias="FINANCIAL_EXPERT_APPROVED_DOMAINS"
    )
    # Semantic "relevant old memory" (BGE-M3 indexing and search). Independent of
    # PERSISTENCE_ENABLED: history, recent context and checkpoints stay active.
    relevant_memory_enabled: bool = Field(default=True, alias="RELEVANT_MEMORY_ENABLED")
    bge_m3_model_path: str = Field(default="", alias="BGE_M3_MODEL_PATH")
    # Background BGE-M3 warm-up at startup (shared RetrievalService, no LLM call).
    rag_warmup_enabled: bool = Field(default=False, alias="RAG_WARMUP_ENABLED")
    gemini_live_stt_model: str = Field(
        default="gemini-3.5-transcribe-live", alias="GEMINI_LIVE_STT_MODEL"
    )
    voice_ws_max_chunk_bytes: int = Field(default=65_536, alias="VOICE_WS_MAX_CHUNK_BYTES")
    voice_ws_output_chunk_bytes: int = Field(default=4_096, alias="VOICE_WS_OUTPUT_CHUNK_BYTES")
    voice_ws_max_session_seconds: int = Field(default=300, alias="VOICE_WS_MAX_SESSION_SECONDS")
    # Diagnostic only: when set, each voice turn's received PCM is written there as WAV.
    voice_debug_dump_dir: str = Field(default="", alias="VOICE_DEBUG_DUMP_DIR")
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
        if self.voice_ws_output_chunk_bytes <= 0:
            raise ValueError("VOICE_WS_OUTPUT_CHUNK_BYTES must be greater than zero")
        if self.voice_ws_output_chunk_bytes > self.voice_ws_max_chunk_bytes:
            raise ValueError("VOICE_WS_OUTPUT_CHUNK_BYTES must not exceed VOICE_WS_MAX_CHUNK_BYTES")
        if self.gemini_localizer_max_output_tokens < 256:
            raise ValueError("GEMINI_LOCALIZER_MAX_OUTPUT_TOKENS must be at least 256")
        if self.azure_final_response_max_output_tokens < 256:
            raise ValueError("AZURE_FINAL_RESPONSE_MAX_OUTPUT_TOKENS must be at least 256")
        if self.app_env not in {"local", "test"}:
            password = self.postgres_password.strip().lower()
            if password in LOCAL_PLACEHOLDER_PASSWORDS:
                raise ValueError("POSTGRES_PASSWORD must not use a placeholder outside local/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
