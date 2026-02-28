from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Natural Language Database Gateway"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ENABLE_DOCS: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@postgres:5432/nldb"
    REDIS_URL: str = "redis://redis:6379/0"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    JWT_COOKIE_NAME: str = "access_token"

    MAX_RESULT_ROWS: int = 500
    QUERY_TIMEOUT_SECONDS: int = 15

    SENSITIVE_COLUMNS: list[str] = Field(
        default_factory=lambda: [
            "password",
            "hashed_password",
            "phone",
            "national_id",
            "credit_card",
            "email",
        ]
    )
    BLACKLISTED_TABLES: list[str] = Field(
        default_factory=lambda: ["users", "audit_logs", "alembic_version"]
    )

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])
    REQUEST_SLOW_THRESHOLD_SECONDS: float = 1.0

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production"
                )
            if len(self.ADMIN_PASSWORD) < 12:
                raise ValueError(
                    "ADMIN_PASSWORD must be at least 12 characters in production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
