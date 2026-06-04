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
    # Logging level for the service (Phase 5 observability). Logs go to stdout,
    # which the platform (Render) captures, so a failure for the person you shared
    # with is visible after the fact.
    log_level: str = "INFO"

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

    # In-app cost estimate (Phase 5). Prices per 1,000,000 tokens. Defaults are
    # 0.0 so no cost is fabricated until you set your actual model prices; with
    # them set, sheets.cost_usd reflects real spend, including the cheaper cached-
    # input rate that the extraction prompt's caching produces. Set the cached
    # input price to roughly half the input price (model-dependent) to see the
    # saving the document-as-cached-prefix ordering yields.
    openai_price_input_per_1m: float = 0.0
    openai_price_cached_input_per_1m: float = 0.0
    openai_price_output_per_1m: float = 0.0
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
    # overlap so a boundary sentence still appears whole in one chunk. The chunk
    # cap is a safety backstop against a pathological input rather than a cost
    # control: it is set high so ordinary large documents are processed in full,
    # and only a truly enormous input is truncated, which is then reported as an
    # event, never silent. At this budget the cap covers documents into the
    # millions of characters (thousands of pages).
    single_pass_char_budget: int = 120_000
    chunk_overlap_chars: int = 2_000
    max_chunks: int = 50


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
