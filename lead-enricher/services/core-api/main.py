from fastapi import FastAPI
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    environment: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()

app = FastAPI(
    title="Lead Enricher API",
    description="Backend service for n8n orchestrator to extract and verify company data",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.environment}

@app.get("/")
async def root():
    return {"message": "Lead Enricher Core API is running"}
