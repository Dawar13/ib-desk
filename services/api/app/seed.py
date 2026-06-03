"""Seed fixture for IB Desk Phase 0.

This module is the single source of truth for the seeded sample row set. The
service tests import these constants so the round-trip test compares against the
exact seeded values. Running this module as a script inserts the sample rows.

All content here is clearly labeled as sample. It is not real research data and
must never be treated as a real source. The cell is grounded honestly: the
source snippet is a verbatim prefix of the document raw text, so
raw_text[char_start:char_end] == source_snippet.

Usage:
    DATABASE_URL=postgres://... python -m app.seed
"""

from __future__ import annotations

import asyncio
import os

import asyncpg

# Fixed, known UUIDs so tests are deterministic.
WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DOCUMENT_ID = "11111111-1111-1111-1111-111111111111"
SHEET_ID = "22222222-2222-2222-2222-222222222222"
SECTION_ID = "33333333-3333-3333-3333-333333333333"
CELL_ID = "44444444-4444-4444-4444-444444444444"

# Document. Clearly labeled as sample.
DOCUMENT_NAME = "Phase 0 sample document"
DOCUMENT_SOURCE_KIND = "paste"
DOCUMENT_DOC_TYPE = "other"
DOCUMENT_PRIMARY_TOPIC = "Sample seeded document, not real research"

# The source snippet is the verbatim prefix of the raw text, so the grounding
# span is exact and honest.
SOURCE_SNIPPET = "This is sample seeded data for IB Desk Phase 0 and is not real research."
RAW_TEXT = SOURCE_SNIPPET + " The sheet exists only to prove the pipe is wired end to end."
CHAR_START = 0
CHAR_END = len(SOURCE_SNIPPET)

# Sheet.
SHEET_TITLE = "Sample sheet"
SHEET_STATUS = "idle"
SHEET_FIELD_COUNT = 1

# Section: one longtext Overview section.
SECTION_KEY = "overview"
SECTION_LABEL = "Overview"
SECTION_KIND = "longtext"
SECTION_RENDER_HINT = "longtext"
SECTION_CATEGORY = "overview"
SECTION_SORT = 0

# Cell: one grounded longtext value, clearly sample, confidence 1.0.
CELL_ROW_IDX = 0
CELL_VALUE = (
    "Sample overview: this seeded sheet exists only to prove the Phase 0 pipe is "
    "wired end to end. It is sample data, not real research."
)
CELL_CONFIDENCE = 1.0


def validate() -> None:
    """Fail fast if the grounding invariant does not hold."""
    if RAW_TEXT[CHAR_START:CHAR_END] != SOURCE_SNIPPET:
        raise AssertionError(
            "Seed grounding invariant broken: "
            "raw_text[char_start:char_end] does not equal source_snippet"
        )


async def seed(conn: asyncpg.Connection) -> None:
    """Insert the sample row set, replacing any prior sample rows."""
    validate()
    async with conn.transaction():
        # Delete sheet first (cascades sections and cells), then document.
        await conn.execute("delete from sheets where id = $1::uuid", SHEET_ID)
        await conn.execute("delete from documents where id = $1::uuid", DOCUMENT_ID)

        await conn.execute(
            """
            insert into documents
              (id, workspace_id, name, source_kind, raw_text, doc_type, primary_topic)
            values ($1::uuid, $2::uuid, $3, $4, $5, $6, $7)
            """,
            DOCUMENT_ID,
            WORKSPACE_ID,
            DOCUMENT_NAME,
            DOCUMENT_SOURCE_KIND,
            RAW_TEXT,
            DOCUMENT_DOC_TYPE,
            DOCUMENT_PRIMARY_TOPIC,
        )
        await conn.execute(
            """
            insert into sheets (id, document_id, workspace_id, title, status, field_count)
            values ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6)
            """,
            SHEET_ID,
            DOCUMENT_ID,
            WORKSPACE_ID,
            SHEET_TITLE,
            SHEET_STATUS,
            SHEET_FIELD_COUNT,
        )
        await conn.execute(
            """
            insert into sections
              (id, sheet_id, key, label, kind, render_hint, category, sort)
            values ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8)
            """,
            SECTION_ID,
            SHEET_ID,
            SECTION_KEY,
            SECTION_LABEL,
            SECTION_KIND,
            SECTION_RENDER_HINT,
            SECTION_CATEGORY,
            SECTION_SORT,
        )
        await conn.execute(
            """
            insert into cells
              (id, section_id, row_idx, value_raw, value_norm, source_snippet,
               char_start, char_end, confidence)
            values ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9)
            """,
            CELL_ID,
            SECTION_ID,
            CELL_ROW_IDX,
            CELL_VALUE,
            None,  # value_norm: a longtext value has nothing to normalize
            SOURCE_SNIPPET,
            CHAR_START,
            CHAR_END,
            CELL_CONFIDENCE,
        )


async def run() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set")
    conn = await asyncpg.connect(dsn)
    try:
        await seed(conn)
    finally:
        await conn.close()
    print("Seeded sample document, sheet, section, and cell.")


if __name__ == "__main__":
    asyncio.run(run())
