"""Paste ingestion round-trip test. Requires a real database connection.

A pass means POST /v1/documents with a JSON paste body was accepted and the
pasted note comes back through the API as a paste-sourced document with the
normalized text and an idle sheet. A failure means the JSON intake branch, the
paste parse path, or the read endpoints are broken.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)

# Clearly sample content, not real research.
PASTE_NAME = "Sample pasted note"
PASTE_TEXT = "Some sample pasted content."


def test_paste_round_trip(client: TestClient) -> None:
    create_response = client.post(
        "/v1/documents",
        json={"name": PASTE_NAME, "text": PASTE_TEXT},
    )
    assert create_response.status_code in (200, 201), create_response.text
    body = create_response.json()
    document_id = body["document_id"]
    sheet_id = body["sheet_id"]
    assert document_id
    assert sheet_id

    detail_response = client.get(f"/v1/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["source_kind"] == "paste"
    assert detail["name"] == PASTE_NAME
    # Pasted text has no pages, so page_count is null (not a fabricated number).
    assert detail["page_count"] is None
    # The text is normalized but the recognizable content survives.
    assert "Some sample pasted content." in detail["raw_text"]

    # A sheet exists for the document, in the idle status.
    assert detail["sheet_id"] == sheet_id
    assert detail["sheet_status"] == "idle"
