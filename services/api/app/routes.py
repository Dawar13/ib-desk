"""The three Phase 0 endpoints for the IB Desk API.

GET /health             a real SELECT 1 health check.
GET /v1/documents       the workspace documents with their one sheet id.
GET /v1/sheets/{id}     the full sheet payload: sheet, sections, nested cells.

Each handler converts asyncpg records into the pydantic models in app.models
and lets pydantic validate them. uuid columns are converted to str and the
numeric cost_usd is converted to float so the JSON contract matches the shared
TypeScript types.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import db
from app.config import get_settings
from app.models import (
    Cell,
    DocumentListItem,
    HealthResponse,
    Section,
    SectionWithCells,
    Sheet,
    SheetPayload,
)

router = APIRouter()


def _document_item(record: Any) -> DocumentListItem:
    row = dict(record)
    return DocumentListItem(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        name=row["name"],
        source_kind=row["source_kind"],
        raw_text=row["raw_text"],
        byte_path=row["byte_path"],
        doc_type=row["doc_type"],
        primary_topic=row["primary_topic"],
        created_at=row["created_at"],
        sheet_id=str(row["sheet_id"]) if row["sheet_id"] is not None else None,
    )


def _sheet(record: Any) -> Sheet:
    row = dict(record)
    return Sheet(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        title=row["title"],
        status=row["status"],
        field_count=row["field_count"],
        cost_usd=float(row["cost_usd"]),
        created_at=row["created_at"],
    )


def _section(record: Any) -> Section:
    row = dict(record)
    return Section(
        id=str(row["id"]),
        sheet_id=str(row["sheet_id"]),
        key=row["key"],
        label=row["label"],
        kind=row["kind"],
        render_hint=row["render_hint"],
        category=row["category"],
        columns=row["columns"],
        sort=row["sort"],
        confidence=row["confidence"],
    )


def _cell(record: Any) -> Cell:
    row = dict(record)
    return Cell(
        id=str(row["id"]),
        section_id=str(row["section_id"]),
        row_idx=row["row_idx"],
        col_key=row["col_key"],
        value_raw=row["value_raw"],
        value_norm=row["value_norm"],
        unit=row["unit"],
        period=row["period"],
        source_snippet=row["source_snippet"],
        char_start=row["char_start"],
        char_end=row["char_end"],
        confidence=row["confidence"],
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    connected = await db.health_check()
    return HealthResponse(
        status="ok" if connected else "degraded",
        service=settings.service_name,
        version=settings.app_version,
        database="connected" if connected else "disconnected",
    )


@router.get("/v1/documents", response_model=list[DocumentListItem])
async def list_documents() -> list[DocumentListItem]:
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not connected")
    rows = await pool.fetch(
        """
        select
            d.id,
            d.workspace_id,
            d.name,
            d.source_kind,
            d.raw_text,
            d.byte_path,
            d.doc_type,
            d.primary_topic,
            d.created_at,
            s.id as sheet_id
        from documents d
        left join sheets s on s.document_id = d.id
        order by d.created_at
        """
    )
    return [_document_item(row) for row in rows]


@router.get("/v1/sheets/{sheet_id}", response_model=SheetPayload)
async def get_sheet(sheet_id: uuid.UUID) -> SheetPayload:
    # FastAPI parses the path as a UUID, returning 422 for a malformed id. A
    # well-formed but absent id falls through to the 404 below rather than
    # surfacing an asyncpg cast error as a 500.
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not connected")

    sheet_id_str = str(sheet_id)

    sheet_row = await pool.fetchrow(
        "select * from sheets where id = $1::uuid",
        sheet_id_str,
    )
    if sheet_row is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    section_rows = await pool.fetch(
        "select * from sections where sheet_id = $1::uuid order by sort",
        sheet_id_str,
    )

    # Fetch every cell for the sheet in one query (avoiding an N+1 pattern on the
    # canonical read path), then group the cells by their section id.
    cell_rows = await pool.fetch(
        """
        select c.*
        from cells c
        join sections s on s.id = c.section_id
        where s.sheet_id = $1::uuid
        order by s.sort, c.row_idx, c.col_key asc nulls first
        """,
        sheet_id_str,
    )

    cells_by_section: dict[str, list[Cell]] = {}
    for cell_row in cell_rows:
        cell = _cell(cell_row)
        cells_by_section.setdefault(cell.section_id, []).append(cell)

    sections = [
        SectionWithCells(
            **_section(section_row).model_dump(),
            cells=cells_by_section.get(str(section_row["id"]), []),
        )
        for section_row in section_rows
    ]

    return SheetPayload(sheet=_sheet(sheet_row), sections=sections)
