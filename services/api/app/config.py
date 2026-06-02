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
    # Connection pool sizing, kept modest so multiple service instances stay under
    # a hosted session pooler's client cap (for example Supabase Session mode caps
    # total clients at 15, and the staging service runs two machines).
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5
    web_origin: str = "http://localhost:3000"
    service_name: str = "ib-desk-api"
    app_version: str = "0.1.0"

    # Default workspace id, carried over from Phase 0 until real auth arrives.
    default_workspace_id: str = "00000000-0000-0000-0000-000000000001"

    # Ingestion (Phase 1).
    # Storage backend: "local" (filesystem, used by tests and CI) or "supabase".
    storage_backend: str = "local"
    storage_local_path: str = "./.local-storage"
    storage_bucket: str = "documents"
    # Supabase Storage credentials, used only when storage_backend is "supabase".
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    # Maximum accepted upload size in bytes (25 MiB).
    max_upload_bytes: int = 26_214_400
    # Scanned-PDF heuristic: reject when the average extractable characters per
    # page is below this. A tunable starting threshold, not a final value.
    scanned_min_chars_per_page: int = 50

    # Extraction engine (Phase 2).
    # LLM mode: "replay" replays recorded cassettes with no secret (the default,
    # used by tests and the CI logic gates); "live" calls OpenAI; "record" calls
    # OpenAI and writes a cassette.
    llm_mode: str = "replay"
    openai_api_key: str | None = None
    # Per-pass model identifiers, configurable per the spec (no model name is
    # hardcoded). Set these to the strongest available models before a live run;
    # the live client requires them to be set.
    openai_model_discovery: str = ""
    openai_model_extraction: str = ""
    openai_model_verification: str = ""
    # Per-section extraction concurrency limit for the parallel extraction pass.
    extraction_concurrency: int = 5
    # Directory (relative to the service root) holding recorded cassettes.
    cassette_dir: str = "tests/cassettes"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
