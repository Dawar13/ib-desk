"""Headline ingestion round-trip test. Requires a real database connection.

This is the most important Phase 1 service test: it proves that a born-digital
PDF uploaded as multipart goes all the way in (parsed, normalized, stored, and
rows inserted) and comes all the way back out through the public API.

A pass means POST /v1/documents accepted the PDF and returned a document_id and
sheet_id; the document appears in the list with extractable text and an idle
sheet; its detail carries the normalized text containing the known marker; and
the original bytes stream back as a PDF. A failure means the ingestion flow, the
storage round-trip, or the read endpoints are broken.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.fixtures_gen import born_digital_pdf

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)


def test_pdf_upload_round_trip(client: TestClient) -> None:
    pdf_bytes = born_digital_pdf()

    create_response = client.post(
        "/v1/documents",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
    )
    assert create_response.status_code in (200, 201), create_response.text
    body = create_response.json()
    document_id = body["document_id"]
    sheet_id = body["sheet_id"]
    assert document_id
    assert sheet_id

    # The new document appears in the lightweight list with extractable text and
    # an idle sheet.
    list_response = client.get("/v1/documents")
    assert list_response.status_code == 200
    items = list_response.json()
    matched = [item for item in items if item["id"] == document_id]
    assert len(matched) == 1
    item = matched[0]
    assert item["char_count"] > 0
    assert item["sheet_status"] == "idle"
    assert item["sheet_id"] == sheet_id
    assert item["source_kind"] == "upload_pdf"

    # The detail endpoint returns the normalized text with the known marker.
    detail_response = client.get(f"/v1/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["raw_text"]
    assert "born-digital PDF" in detail["raw_text"]
    assert detail["source_kind"] == "upload_pdf"
    assert detail["sheet_id"] == sheet_id
    assert detail["sheet_status"] == "idle"

    # The original bytes stream back as a PDF.
    original_response = client.get(f"/v1/documents/{document_id}/original")
    assert original_response.status_code == 200
    assert original_response.headers["content-type"].startswith("application/pdf")
    assert len(original_response.content) > 0
