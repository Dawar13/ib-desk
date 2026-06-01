"""Migration shape test. Requires a real database with the migration applied.

A pass means the five core tables exist and two key columns are present and
correctly constrained: cells.source_snippet is NOT NULL (grounding is
mandatory) and documents has the reserved embedding column. A failure means the
migration did not run or drifted from the canonical schema.
"""

from __future__ import annotations

import os

import asyncpg
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)

DB_URL: str = os.environ.get("DATABASE_URL", "")

EXPECTED_TABLES = (
    "documents",
    "sheets",
    "sections",
    "cells",
    "extraction_events",
)


async def test_migration_shape() -> None:
    conn = await asyncpg.connect(DB_URL)
    try:
        for table in EXPECTED_TABLES:
            exists = await conn.fetchval(
                """
                select exists (
                    select 1 from information_schema.tables
                    where table_schema = 'public' and table_name = $1
                )
                """,
                table,
            )
            assert exists, f"expected table {table} to exist"

        snippet_nullable = await conn.fetchval(
            """
            select is_nullable from information_schema.columns
            where table_schema = 'public'
              and table_name = 'cells'
              and column_name = 'source_snippet'
            """
        )
        assert snippet_nullable == "NO", "cells.source_snippet must be NOT NULL"

        embedding_exists = await conn.fetchval(
            """
            select exists (
                select 1 from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'documents'
                  and column_name = 'embedding'
            )
            """
        )
        assert embedding_exists, "documents must have an embedding column"
    finally:
        await conn.close()
