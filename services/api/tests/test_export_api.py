"""Export endpoint test. Requires a real database with seed data.

Confirms the route wiring end to end: GET /v1/sheets/{id}/export returns a valid
styled xlsx workbook by default and a csv carrying the seeded value on request,
that an unknown format is a 400, and that an absent sheet is a 404. The styling,
charts, and comments are asserted in detail by the secret-free builder gates in
test_export.py; this test covers the endpoint against the database.

A pass means the export endpoint serves the right content for a real sheet and
rejects bad input cleanly. A failure means the route, content type, or error
handling is broken.
"""

from __future__ import annotations

import io
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import seed

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="DATABASE_URL is not set; skipping database-backed test",
)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_export_xlsx_is_default(client: TestClient) -> None:
    response = client.get(f"/v1/sheets/{seed.SHEET_ID}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(_XLSX_MIME)
    assert "attachment" in response.headers.get("content-disposition", "")
    # A real xlsx is a zip whose container holds the workbook part.
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "xl/workbook.xml" in archive.namelist()


def test_export_csv_carries_the_seeded_value(client: TestClient) -> None:
    response = client.get(f"/v1/sheets/{seed.SHEET_ID}/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert seed.CELL_VALUE in response.content.decode("utf-8")


def test_export_rejects_an_unknown_format(client: TestClient) -> None:
    response = client.get(f"/v1/sheets/{seed.SHEET_ID}/export?format=docx")
    assert response.status_code == 400


def test_export_missing_sheet_is_404(client: TestClient) -> None:
    response = client.get("/v1/sheets/00000000-0000-0000-0000-000000000000/export")
    assert response.status_code == 404
