"""Posting worker configuration."""

import os


class Config:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://core-api:8000")
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    POSTING_DELAY_MIN_SEC: int = int(os.getenv("POSTING_DELAY_MIN_SEC", "30"))
    POSTING_DELAY_MAX_SEC: int = int(os.getenv("POSTING_DELAY_MAX_SEC", "60"))
    POSTING_MAX_PER_SESSION: int = int(os.getenv("POSTING_MAX_PER_SESSION", "10"))
    SESSION_PATH: str = "/data/session.json"
    SCREENSHOTS_DIR: str = "/data/screenshots"
    QUEUE_KEY: str = "posting_queue"


config = Config()
