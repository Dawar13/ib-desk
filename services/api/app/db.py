"""Asyncpg connection pool lifecycle for the IB Desk API.

The pool is held at module level so the routes and the health check share a
single set of connections. A json and jsonb type codec is installed on each
connection so jsonb columns (for example sections.columns) decode to native
Python objects instead of raw JSON strings.
"""

from __future__ import annotations

import json

import asyncpg

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Install json and jsonb codecs so jsonb columns return Python objects."""
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def open_pool(dsn: str, *, min_size: int = 1, max_size: int = 5) -> None:
    """Create the global asyncpg pool from the given DSN.

    The size is kept modest by default so several service instances stay under a
    hosted session pooler's client cap (Supabase Session mode caps total clients).
    """
    global _pool
    _pool = await asyncpg.create_pool(
        dsn, init=_init_connection, min_size=min_size, max_size=max_size
    )


async def close_pool() -> None:
    """Close and clear the global asyncpg pool if it is open."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    """Return the global pool, or None if it has not been opened."""
    return _pool


async def health_check() -> bool:
    """Run a real SELECT 1 against the pool.

    Returns True on success, and False if there is no pool or the query fails.
    Never raises.
    """
    if _pool is None:
        return False
    try:
        async with _pool.acquire() as conn:
            await conn.execute("select 1")
        return True
    except Exception:
        return False
