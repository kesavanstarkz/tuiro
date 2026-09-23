from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
