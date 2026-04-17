import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5433/kleinanzeigen_bot",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")

    # OpenRouter
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv(
        "OPENROUTER_MODEL", "google/gemma-4-27b-it:free"
    )
    openrouter_fallback_model: str = os.getenv(
        "OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash"
    )

    # Defaults
    default_zip: str = os.getenv("DEFAULT_ZIP", "10115")
    default_price_strategy: str = os.getenv("DEFAULT_PRICE_STRATEGY", "competitive")

    # Telegram (for draft-ready notifications)
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    review_base_url: str = os.getenv("REVIEW_BASE_URL", "http://localhost:8001")

    # Paths
    data_dir: str = "/data"
    images_dir: str = "/data/images"
    screenshots_dir: str = "/data/screenshots"


settings = Settings()
