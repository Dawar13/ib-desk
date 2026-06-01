"""Application settings for the IB Desk API.

Settings load from the process environment and an optional .env file. Unknown
keys are ignored so the reserved Phase 0 keys documented in .env.example
(SUPABASE_URL, storage keys, OPENAI_API_KEY, and similar) do not need to be
declared here. Those keys are intentionally not settings fields in Phase 0.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    web_origin: str = "http://localhost:3000"
    service_name: str = "ib-desk-api"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
