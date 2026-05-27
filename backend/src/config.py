"""Application configuration loaded from environment variables."""

import secrets

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Academic Hunter configuration.

    All secrets MUST be set via environment variables or .env file.
    No hardcoded defaults for credentials — fail fast if missing.
    """

    # Database
    database_url: str = ""

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or v in ("", "change-me-in-production-use-a-long-random-string"):
            raise ValueError(
                "JWT_SECRET must be set to a strong random string. "
                "Generate one: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    # DeepSeek AI
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # AI scoring thresholds
    ai_score_threshold: float = 6.0
    credibility_high_threshold: float = 8.0
    credibility_medium_threshold: float = 5.0

    # Brief limits
    brief_max_papers: int = 20

    # Time window
    daily_window_hours: int = 24
    weekly_window_days: int = 7

    # Semantic Scholar
    s2_api_key: str = ""
    s2_base_url: str = ""  # Empty = use default api.semanticscholar.org
    # Credit budget (ai4scholar.net proxy)
    s2_credit_budget: int = 50  # Minimum credits to run pipeline

    # NCBI / PubMed
    ncbi_api_key: str = ""
    ncbi_email: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
