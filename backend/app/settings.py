"""
Application settings loaded from environment variables.

Uses pydantic-settings for validation and .env file support.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite://:memory:"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = "stub"

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    @property
    def persistence_mode(self) -> Literal["memory", "sqlite", "postgres"]:
        """Infer persistence mode from DATABASE_URL."""
        if self.database_url.startswith("postgresql"):
            return "postgres"
        if self.database_url.startswith("sqlite"):
            return "sqlite"
        return "memory"


@lru_cache
def get_settings() -> Settings:
    return Settings()
