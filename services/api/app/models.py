"""Pydantic response models for the IB Desk API.

These mirror the shared TypeScript types in packages/shared/src/index.ts and the
data model in BUILD_PLAN.md field for field. JSON keys are snake_case so the web
client and the service share one contract. The reserved embedding vector column
on documents is intentionally not part of the API surface in v1.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DocType = Literal[
    "company_profile",
    "market_overview",
    "deal",
    "person",
    "technology",
    "other",
]
SourceKind = Literal["upload_pdf", "upload_docx", "paste"]
SheetStatus = Literal["idle", "extracting", "done", "failed"]
SectionKind = Literal["scalar", "list", "table", "timeseries", "longtext"]
RenderHint = Literal[
    "keyvalue",
    "chips",
    "table",
    "timeseries_bar",
    "timeseries_line",
    "breakdown_pie",
    "longtext",
]


class ColumnDef(BaseModel):
    key: str
    label: str


class Document(BaseModel):
    id: str
    workspace_id: str
    name: str
    source_kind: SourceKind
    raw_text: str
    byte_path: str | None
    doc_type: DocType | None
    primary_topic: str | None
    created_at: datetime


class Sheet(BaseModel):
    id: str
    document_id: str
    title: str
    status: SheetStatus
    field_count: int
    cost_usd: float
    created_at: datetime


class Section(BaseModel):
    id: str
    sheet_id: str
    key: str
    label: str
    kind: SectionKind
    render_hint: RenderHint
    category: str | None
    columns: list[ColumnDef] | None
    sort: int
    confidence: float | None


class Cell(BaseModel):
    id: str
    section_id: str
    row_idx: int
    col_key: str | None
    value_raw: str | None
    value_norm: str | None
    unit: str | None
    period: str | None
    source_snippet: str
    char_start: int | None
    char_end: int | None
    confidence: float | None


class DocumentListItem(Document):
    # Augments the table mirror Document with the id of the document's one sheet
    # (one to one), so the client can navigate to the sheet using only the three
    # Phase 0 endpoints. Null only if a document has no sheet yet.
    sheet_id: str | None


class SectionWithCells(Section):
    cells: list[Cell]


class SheetPayload(BaseModel):
    sheet: Sheet
    sections: list[SectionWithCells]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    database: Literal["connected", "disconnected"]
