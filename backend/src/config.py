"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Academic Hunter configuration."""

    # Database
    database_url: str = "postgresql+asyncpg://hunter:hunter@localhost:5432/academic_hunter"

    # JWT
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

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

    # NCBI / PubMed
    ncbi_api_key: str = ""
    ncbi_email: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
