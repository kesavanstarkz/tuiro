from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./tuiro.db"
    jwt_secret: str = "development-only-change-me"
    jwt_refresh_secret: str = "development-only-refresh-change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    environment: str = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8081", "http://localhost:8082", "http://127.0.0.1:8081", "http://127.0.0.1:8082"])
    cors_origin_regex: Optional[str] = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
