"""Extract trigger and events-stream endpoint tests. Require a database; replay
mode, so no secret. Cover the trigger contract (sheet moves to extracting and the
call returns immediately) and the server-sent events stream.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient

DB_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DB_URL is None,
    reason="DATABASE_URL is not set; skipping database-backed endpoint tests",
)

WORKSPACE = "00000000-0000-0000-0000-000000000001"


def test_extract_trigger_returns_accepted(client: TestClient) -> None:
    create = client.post(
        "/v1/documents",
        json={
            "name": "Trigger test (sample)",
            "text": "This is sample text used only to exercise the extract trigger.",
        },
    )
    assert create.status_code in (200, 201), create.text
    sheet_id = create.json()["sheet_id"]

    response = client.post(f"/v1/sheets/{sheet_id}/extract")
    assert response.status_code == 202
    body = response.json()
    assert body["sheet_id"] == sheet_id
    assert body["status"] == "extracting"


def test_events_stream_returns_sse(client: TestClient) -> None:
    sheet_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    async def seed() -> None:
        assert DB_URL is not None
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=2)
        try:
            await pool.execute(
                "insert into documents (id, workspace_id, name, source_kind, raw_text) "
                "values ($1::uuid, $2::uuid, $3, 'paste', $4)",
                doc_id,
                WORKSPACE,
                "SSE test (sample)",
                "sample text",
            )
            await pool.execute(
                "insert into sheets (id, document_id, title, status) "
                "values ($1::uuid, $2::uuid, $3, 'done')",
                sheet_id,
                doc_id,
                "SSE test (sample)",
            )
            await pool.execute(
                "insert into extraction_events (sheet_id, stage, message) "
                "values ($1::uuid, 'discovery', 'discovery started')",
                sheet_id,
            )
            await pool.execute(
                "insert into extraction_events (sheet_id, stage, message) "
                "values ($1::uuid, 'done', 'extraction complete')",
                sheet_id,
            )
        finally:
            await pool.close()

    async def cleanup() -> None:
        assert DB_URL is not None
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=2)
        try:
            await pool.execute("delete from sheets where id = $1::uuid", sheet_id)
            await pool.execute("delete from documents where id = $1::uuid", doc_id)
        finally:
            await pool.close()

    asyncio.run(seed())
    try:
        response = client.get(f"/v1/sheets/{sheet_id}/events")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        text = response.text
        assert "discovery" in text
        assert "done" in text
    finally:
        asyncio.run(cleanup())
