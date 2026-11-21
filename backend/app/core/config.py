from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "FrameForge AI Video Backend"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str = "sqlite:///./frameforge.db"

    FRONTEND_ORIGINS: str = (
        "http://localhost:3000,https://frameforge-ai-video-three.vercel.app"
    )

    GENERATION_MODE: str = "demo"

    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "storage/videos"
    TEMP_STORAGE_PATH: str = "storage/tmp"

    MAX_CONCURRENT_JOBS: int = 1
    MAX_PROMPT_LENGTH: int = 2000
    JOB_TIMEOUT_SECONDS: int = 900
    JOB_MAX_RETRIES: int = 1
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 10

    AI_PROVIDER: str = "none"
    AI_API_KEY: str = ""
    TTS_PROVIDER: str = "none"

    @field_validator("GENERATION_MODE")
    @classmethod
    def validate_generation_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"demo", "ai"}:
            raise ValueError("GENERATION_MODE must be 'demo' or 'ai'")
        return normalized

    @property
    def cors_origins(self) -> List[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.FRONTEND_ORIGINS.split(",")
            if origin.strip()
        ]
        # Always ensure production Vercel origin is allowed if configured
        return origins

    @property
    def normalized_database_url(self) -> str:
        url = self.DATABASE_URL.strip()
        # Render / Heroku sometimes provide postgres:// which SQLAlchemy 2 rejects
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def storage_dir(self) -> Path:
        return Path(self.LOCAL_STORAGE_PATH)

    @property
    def temp_dir(self) -> Path:
        return Path(self.TEMP_STORAGE_PATH)


@lru_cache
def get_settings() -> Settings:
    return Settings()
