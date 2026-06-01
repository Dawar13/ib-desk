"""Sheet round-trip test. Requires a real database connection with seed data.

This is the most important service test: it proves the full read path from the
database back through the API matches the seeded values exactly, including the
grounding invariant that the source snippet is a verbatim span of the raw text.

A pass means GET /v1/sheets/{id} returned the seeded sheet, its single section,
and its single grounded cell with every field intact. A failure means the sheet
assembly, ordering, model mapping, or the grounding contract is broken.
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


def test_sheet_payload_round_trip(client: TestClient) -> None:
    response = client.get(f"/v1/sheets/{seed.SHEET_ID}")
    assert response.status_code == 200
    payload = response.json()

    sheet = payload["sheet"]
    assert sheet["title"] == seed.SHEET_TITLE
    assert sheet["status"] == seed.SHEET_STATUS
    assert sheet["field_count"] == seed.SHEET_FIELD_COUNT

    sections = payload["sections"]
    assert len(sections) == 1
    section = sections[0]
    assert section["key"] == seed.SECTION_KEY
    assert section["label"] == seed.SECTION_LABEL
    assert section["kind"] == seed.SECTION_KIND
    assert section["render_hint"] == seed.SECTION_RENDER_HINT
    assert section["sort"] == seed.SECTION_SORT

    cells = section["cells"]
    assert len(cells) == 1
    cell = cells[0]
    assert cell["value_raw"] == seed.CELL_VALUE
    # A longtext value has nothing to normalize, so value_norm is null.
    assert cell["value_norm"] is None
    assert cell["source_snippet"] == seed.SOURCE_SNIPPET
    assert cell["char_start"] == seed.CHAR_START
    assert cell["char_end"] == seed.CHAR_END
    assert cell["confidence"] == seed.CELL_CONFIDENCE

    # Grounding invariant: the snippet is a verbatim span of the raw text.
    assert seed.RAW_TEXT[seed.CHAR_START : seed.CHAR_END] == seed.SOURCE_SNIPPET
