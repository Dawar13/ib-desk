"""Documents listing test. Requires a real database connection with seed data.

A pass means GET /v1/documents returned the seeded sample document in the
lightweight DocumentListItem shape, with its one sheet id and status populated
from the left join and a positive char_count derived from char_length(raw_text)
in SQL. A failure means the listing query, the left join to sheets, the
char_count derivation, or the model mapping is wrong, or the seed was not run.

The list may contain other documents (ingestion tests add rows), so the seeded
document is found by id rather than assuming the list has exactly one item.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import seed

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_documents_includes_seeded_document(client: TestClient) -> None:
    response = client.get("/v1/documents")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)

    matched = [item for item in items if item["id"] == seed.DOCUMENT_ID]
    assert len(matched) == 1
    item = matched[0]

    assert item["name"] == seed.DOCUMENT_NAME
    assert item["sheet_id"] == seed.SHEET_ID
    assert item["sheet_status"] == "idle"
    assert item["char_count"] > 0

    # The lightweight list item must not carry the full raw_text.
    assert "raw_text" not in item
