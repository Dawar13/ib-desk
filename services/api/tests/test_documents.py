"""Documents listing test. Requires a real database connection with seed data.

A pass means GET /v1/documents returned the seeded sample document with its
one sheet id populated from the left join. A failure means the listing query,
the left join to sheets, or the model mapping is wrong, or the seed was not run.
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
