"""Application configuration."""

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Natural Language Database Gateway"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@postgres:5432/nldb"
    REDIS_URL: str = "redis://redis:6379/0"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    JWT_COOKIE_NAME: str = "access_token"

    MAX_RESULT_ROWS: int = 500
    QUERY_TIMEOUT_SECONDS: int = 15

    SENSITIVE_COLUMNS: list[str] = Field(
        default_factory=lambda: ["password", "phone", "national_id", "credit_card", "email"]
    )
    BLACKLISTED_TABLES: list[str] = Field(
        default_factory=lambda: ["users_auth", "audit_logs", "alembic_version"]
    )

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    """Return memoized settings."""

    return Settings()  # type: ignore[arg-type]


settings = get_settings()
