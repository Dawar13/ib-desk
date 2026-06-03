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

    # Rate limiting and the usage backstop (Phase 5). The burst window throttles
    # uploads and extracts per caller (workspace plus client address); the usage
    # window caps extractions per workspace as a second guard behind the OpenAI
    # spend cap. Generous enough for a real visitor, low enough to stop abuse.
    rate_limit_window_seconds: float = 60.0
    rate_limit_upload_max: int = 20
    rate_limit_extract_max: int = 10
    usage_window_seconds: float = 3600.0
    usage_extract_max: int = 50

    # Large-document budget (Phase 5). A document whose canonical text exceeds
    # this character count is too large for a single model pass; it is handled by
    # chunk-and-merge rather than truncated. A safe budget for the 20 to 40 page
    # research documents in scope, below typical model context limits. Chunks
    # overlap so a boundary sentence still appears whole in one chunk, and the
    # number of chunks is capped so a runaway document cannot fan out unbounded
    # model calls; beyond the cap the leading portion is processed and the
    # truncation is reported, never silent.
    single_pass_char_budget: int = 120_000
    chunk_overlap_chars: int = 2_000
    max_chunks: int = 8


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
