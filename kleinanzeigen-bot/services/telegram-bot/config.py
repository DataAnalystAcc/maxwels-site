"""Telegram bot configuration."""

import os


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ALLOWED_TELEGRAM_CHAT_ID: int = int(os.getenv("ALLOWED_TELEGRAM_CHAT_ID", "0"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5433/kleinanzeigen_bot",
    )
    N8N_WEBHOOK_ITEM_INTAKE: str = os.getenv(
        "N8N_WEBHOOK_ITEM_INTAKE",
        "http://n8n:5678/webhook/item-intake",
    )
    IMAGES_DIR: str = "/data/images"
    REVIEW_BASE_URL: str = os.getenv("REVIEW_BASE_URL", "http://localhost:8001")
    MEDIA_GROUP_TIMEOUT_SEC: float = 3.0
    NOTE_WAIT_TIMEOUT_SEC: float = 5.0
    THUMB_MAX_SIZE: int = 512


config = Config()
