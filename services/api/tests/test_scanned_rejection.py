"""Scanned-PDF rejection test. Requires a real database connection.

A scanned, image-only PDF has no extractable text layer. It must be rejected
with a clear code and, critically, must leave no row in the database, since the
ingestion flow validates before it stores anything.

A pass means POST /v1/documents returned 422 with detail.code
"scanned_or_unreadable" and the documents row count is unchanged. A failure
means scanned detection did not run, the wrong code was returned, or a row was
created for an unreadable document.

This is a synchronous test: the sync Starlette TestClient must not be driven from
inside a running asyncio loop, so the row count uses asyncio.run on a small
asyncpg helper instead of an async test body.
"""

from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from tests.fixtures_gen import scanned_pdf

DB_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DB_URL is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


async def _document_count() -> int:
    assert DB_URL is not None
    conn = await asyncpg.connect(DB_URL)
    try:
        count = await conn.fetchval("select count(*) from documents")
    finally:
        await conn.close()
    return int(count)


def test_scanned_pdf_is_rejected_and_creates_no_row(client: TestClient) -> None:
    before = asyncio.run(_document_count())

    response = client.post(
        "/v1/documents",
        files={"file": ("scanned.pdf", scanned_pdf(), "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "scanned_or_unreadable"

    after = asyncio.run(_document_count())
    assert after == before
