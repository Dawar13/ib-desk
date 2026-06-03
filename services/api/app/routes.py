"""The IB Desk API endpoints (Phase 0 read paths plus Phase 1 ingestion).

Phase 0 (unchanged):
  GET /health                       a real SELECT 1 health check.
  GET /v1/sheets/{id}               the full sheet payload: sheet, sections, cells.

Phase 1 (ingestion and document store):
  POST /v1/documents                multipart file upload or pasted JSON text.
  GET  /v1/documents                lightweight document list for the workspace.
  GET  /v1/documents/{id}           full document detail including raw_text.
  GET  /v1/documents/{id}/original  stream the stored original bytes.

Ingestion validates the input in memory before storing anything, so neither the
database nor object storage ever holds an empty or rejected document. Every
rejection is a clear 4xx with a machine-readable code, never a 500. The error
body is HTTPException(detail={"code": ..., "message": ...}) so the JSON is
{"detail": {"code", "message"}}, matching ApiError/ApiErrorBody in the shared
types.

Each handler converts asyncpg records into the pydantic models in app.models and
lets pydantic validate them. uuid columns are converted to str and the numeric
cost_usd is converted to float so the JSON contract matches the shared
TypeScript types.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from starlette.datastructures import UploadFile

from app import db
from app.config import get_settings
from app.export import build_csv, build_xlsx
from app.extraction.pipeline import run_extraction
from app.extraction.prompts import EXTRACTION_PROMPT_VERSION
from app.models import (
    Cell,
    CreateDocumentResponse,
    DocumentDetail,
    DocumentListItem,
    HealthResponse,
    Section,
    SectionWithCells,
    Sheet,
    SheetPayload,
)
from app.normalization import assemble_raw_text
from app.parsing import ParseResult, looks_scanned, parse_docx, parse_pdf, parse_text
from app.storage import get_storage

router = APIRouter()

# References to in-flight extraction background tasks, held so they are not
# garbage collected before they finish.
_EXTRACTION_TASKS: set[asyncio.Task[None]] = set()

# Content type strings used to detect and serve each source kind.
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TEXT_MIME = "text/plain; charset=utf-8"

# Export content types and the filename sanitizer for the download.
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_CSV_MIME = "text/csv; charset=utf-8"
_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    cleaned = _FILENAME_UNSAFE.sub("_", name).strip("_")
    return cleaned or "sheet"


# Maps a stored document's source kind to the content type used when streaming the
# original bytes back from object storage.
_ORIGINAL_CONTENT_TYPES: dict[str, str] = {
    "upload_pdf": _PDF_MIME,
    "upload_docx": _DOCX_MIME,
    "paste": _TEXT_MIME,
}


def _ingest_error(status_code: int, code: str, message: str) -> HTTPException:
    """Build the machine-readable ingestion error matching ApiError/ApiErrorBody."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _require_pool() -> Any:
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not connected")
    return pool


def _document_list_item(record: Any) -> DocumentListItem:
    row = dict(record)
    return DocumentListItem(
        id=str(row["id"]),
        name=row["name"],
        source_kind=row["source_kind"],
        created_at=row["created_at"],
        sheet_id=str(row["sheet_id"]) if row["sheet_id"] is not None else None,
        sheet_status=row["sheet_status"],
        char_count=row["char_count"],
        page_count=row["page_count"],
    )


def _document_detail(record: Any) -> DocumentDetail:
    row = dict(record)
    return DocumentDetail(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        name=row["name"],
        source_kind=row["source_kind"],
        raw_text=row["raw_text"],
        byte_path=row["byte_path"],
        doc_type=row["doc_type"],
        primary_topic=row["primary_topic"],
        created_at=row["created_at"],
        page_count=row["page_count"],
        sheet_id=str(row["sheet_id"]) if row["sheet_id"] is not None else None,
        sheet_status=row["sheet_status"],
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
        extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
    )


def _detect_upload_kind(filename: str | None, content_type: str | None) -> str | None:
    """Return the source_kind for an uploaded file, or None if unsupported.

    Type is decided by content type and filename extension: .pdf or
    application/pdf is a PDF; .docx or the OpenXML wordprocessing mime is a DOCX.
    """
    name = (filename or "").lower()
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if name.endswith(".pdf") or ctype == _PDF_MIME:
        return "upload_pdf"
    if name.endswith(".docx") or ctype == _DOCX_MIME:
        return "upload_docx"
    return None


def _parse_upload(source_kind: str, data: bytes) -> ParseResult:
    """Parse uploaded bytes for the detected kind, mapping failures to parse_failed."""
    try:
        if source_kind == "upload_pdf":
            return parse_pdf(data)
        return parse_docx(data)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - any parser error becomes a clean 422.
        raise _ingest_error(422, "parse_failed", f"Could not parse the document: {exc}") from exc


async def _read_paste_body(request: Request) -> tuple[str, str]:
    """Read and validate a JSON paste body, returning (name, text)."""
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 - malformed JSON is bad input, not a 500.
        raise _ingest_error(400, "empty_input", "Request body was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise _ingest_error(400, "empty_input", "Request body must be a JSON object.")
    name = body.get("name")
    text = body.get("text")
    if not isinstance(name, str) or not isinstance(text, str):
        raise _ingest_error(400, "empty_input", "Both name and text are required.")
    return name, text


async def _insert_document(
    *,
    document_id: str,
    name: str,
    source_kind: str,
    raw_text: str,
    byte_path: str,
    page_count: int | None,
    page_offsets: list[int],
) -> str:
    """Insert the documents and sheets rows, returning the new sheet id."""
    pool = _require_pool()
    settings = get_settings()
    sheet_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                insert into documents
                  (id, workspace_id, name, source_kind, raw_text, byte_path,
                   doc_type, primary_topic, page_count, page_offsets)
                values
                  ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
                """,
                document_id,
                settings.default_workspace_id,
                name,
                source_kind,
                raw_text,
                byte_path,
                None,
                None,
                page_count,
                page_offsets,
            )
            await conn.execute(
                """
                insert into sheets (id, document_id, title, status)
                values ($1::uuid, $2::uuid, $3, 'idle')
                """,
                sheet_id,
                document_id,
                name,
            )
    return sheet_id


@router.post("/v1/documents", response_model=CreateDocumentResponse, status_code=201)
async def create_document(request: Request) -> CreateDocumentResponse:
    """Ingest a document from a multipart file upload or a JSON paste body.

    Validates entirely in memory before storing, so a rejected upload leaves no
    row in the database and no object in storage. The flow is: determine input,
    validate, parse, normalize, then store and insert.
    """
    settings = get_settings()
    # Ensure the database is available before doing any parsing or storage work.
    _require_pool()

    content_type = (request.headers.get("content-type") or "").lower()

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise _ingest_error(400, "empty_input", "No file was provided in the upload.")
        data = await upload.read()
        if len(data) == 0:
            raise _ingest_error(400, "empty_input", "The uploaded file was empty.")
        if len(data) > settings.max_upload_bytes:
            raise _ingest_error(
                413,
                "file_too_large",
                f"The file exceeds the maximum upload size of {settings.max_upload_bytes} bytes.",
            )
        source_kind = _detect_upload_kind(upload.filename, upload.content_type)
        if source_kind is None:
            raise _ingest_error(
                415,
                "unsupported_type",
                "Only PDF and DOCX files are supported.",
            )
        name = upload.filename or "Untitled document"
        result = _parse_upload(source_kind, data)
        stored_bytes = data
        store_content_type = _PDF_MIME if source_kind == "upload_pdf" else _DOCX_MIME
    else:
        name, text = await _read_paste_body(request)
        if len(text) == 0:
            raise _ingest_error(400, "empty_input", "Pasted text was empty.")
        if len(text.encode("utf-8")) > settings.max_upload_bytes:
            raise _ingest_error(
                413,
                "file_too_large",
                f"The text exceeds the maximum upload size of {settings.max_upload_bytes} bytes.",
            )
        source_kind = "paste"
        result = parse_text(text)
        stored_bytes = text.encode("utf-8")
        store_content_type = _TEXT_MIME

    # Reject scanned or unreadable uploads before storing anything. The per-page
    # heuristic applies only to uploaded files; pasted text has no pages, so an
    # empty paste is caught by the empty-text checks instead.
    if source_kind != "paste" and looks_scanned(result, settings.scanned_min_chars_per_page):
        raise _ingest_error(
            422,
            "scanned_or_unreadable",
            "The document has no extractable text. It may be scanned or image-only.",
        )

    raw_text, page_offsets = assemble_raw_text(result.segments)
    if raw_text == "":
        if source_kind == "paste":
            raise _ingest_error(400, "empty_input", "Pasted text was empty after normalization.")
        raise _ingest_error(
            422,
            "scanned_or_unreadable",
            "The document yielded no readable text after normalization.",
        )

    document_id = str(uuid.uuid4())
    await get_storage().put(key=document_id, data=stored_bytes, content_type=store_content_type)

    # Only PDFs have a meaningful page count. DOCX pagination is decided by the
    # renderer and is not stored in the file, and pasted text has no pages, so
    # both persist null rather than a fabricated number.
    page_count = result.page_count if source_kind == "upload_pdf" else None
    sheet_id = await _insert_document(
        document_id=document_id,
        name=name,
        source_kind=source_kind,
        raw_text=raw_text,
        byte_path=document_id,
        page_count=page_count,
        page_offsets=page_offsets,
    )

    return CreateDocumentResponse(document_id=document_id, sheet_id=sheet_id)


@router.get("/v1/documents", response_model=list[DocumentListItem])
async def list_documents() -> list[DocumentListItem]:
    pool = _require_pool()
    settings = get_settings()
    rows = await pool.fetch(
        """
        select
            d.id,
            d.name,
            d.source_kind,
            d.created_at,
            d.page_count,
            char_length(d.raw_text) as char_count,
            s.id as sheet_id,
            s.status as sheet_status
        from documents d
        left join sheets s on s.document_id = d.id
        where d.workspace_id = $1::uuid
        order by d.created_at desc
        """,
        settings.default_workspace_id,
    )
    return [_document_list_item(row) for row in rows]


@router.get("/v1/documents/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: uuid.UUID) -> DocumentDetail:
    # FastAPI parses the path as a UUID, so a malformed id is a 422, not a 500.
    pool = _require_pool()
    row = await pool.fetchrow(
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
            d.page_count,
            s.id as sheet_id,
            s.status as sheet_status
        from documents d
        left join sheets s on s.document_id = d.id
        where d.id = $1::uuid
        """,
        str(document_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_detail(row)


@router.get("/v1/documents/{document_id}/original")
async def get_document_original(document_id: uuid.UUID) -> Response:
    # FastAPI parses the path as a UUID, so a malformed id is a 422, not a 500.
    pool = _require_pool()
    row = await pool.fetchrow(
        "select source_kind, byte_path from documents where id = $1::uuid",
        str(document_id),
    )
    if row is None or row["byte_path"] is None:
        raise HTTPException(status_code=404, detail="Original document not found")

    key = row["byte_path"]
    storage = get_storage()
    if not await storage.exists(key):
        raise HTTPException(status_code=404, detail="Original document not found")

    data = await storage.get(key)
    content_type = _ORIGINAL_CONTENT_TYPES.get(row["source_kind"], "application/octet-stream")
    return Response(content=data, media_type=content_type)


async def _load_sheet_payload(pool: Any, sheet_id_str: str) -> SheetPayload | None:
    """Assemble the full sheet payload (sheet, sections, nested cells), or None.

    Shared by the read path and the export path so both see exactly the same
    sections and grounded cells, in the same order.
    """
    sheet_row = await pool.fetchrow(
        "select * from sheets where id = $1::uuid",
        sheet_id_str,
    )
    if sheet_row is None:
        return None

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


@router.get("/v1/sheets/{sheet_id}", response_model=SheetPayload)
async def get_sheet(sheet_id: uuid.UUID) -> SheetPayload:
    # FastAPI parses the path as a UUID, returning 422 for a malformed id. A
    # well-formed but absent id falls through to the 404 below rather than
    # surfacing an asyncpg cast error as a 500.
    pool = _require_pool()
    payload = await _load_sheet_payload(pool, str(sheet_id))
    if payload is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return payload


@router.get("/v1/sheets/{sheet_id}/export")
async def export_sheet(sheet_id: uuid.UUID, format: str = "xlsx") -> Response:
    """Export a sheet as a styled xlsx (default) or a flat csv.

    The export is computed from the stored sheet payload, so it needs no model
    call. xlsx is the primary, styled format with native charts and source
    comments; csv is the secondary flat format. An unknown format is a 400.
    """
    requested = format.lower()
    if requested not in ("xlsx", "csv"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Use xlsx or csv.",
        )

    pool = _require_pool()
    sheet_id_str = str(sheet_id)
    payload = await _load_sheet_payload(pool, sheet_id_str)
    if payload is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # The document fields drive the title block. They are always available even
    # when discovery did not classify, so the export never fabricates a subject.
    doc_row = await pool.fetchrow(
        """
        select d.name, d.doc_type, d.primary_topic
        from documents d
        join sheets s on s.document_id = d.id
        where s.id = $1::uuid
        """,
        sheet_id_str,
    )
    doc_name = doc_row["name"] if doc_row is not None else payload.sheet.title
    doc_type = doc_row["doc_type"] if doc_row is not None else None
    primary_topic = doc_row["primary_topic"] if doc_row is not None else None

    filename_base = _safe_filename(payload.sheet.title or doc_name or "sheet")
    if requested == "csv":
        body = build_csv(payload)
        media_type = _CSV_MIME
        filename = f"{filename_base}.csv"
    else:
        body = build_xlsx(
            payload,
            doc_name=doc_name,
            doc_type=doc_type,
            primary_topic=primary_topic,
        )
        media_type = _XLSX_MIME
        filename = f"{filename_base}.xlsx"

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/v1/sheets/{sheet_id}/extract", status_code=202)
async def trigger_extract(sheet_id: uuid.UUID) -> dict[str, str]:
    """Start the extraction pipeline for a sheet and return immediately.

    Sets the sheet to extracting synchronously so the response reflects it, then
    runs the four-pass pipeline as a background task. Progress is observable on
    the events stream and the sheet ends done or failed.
    """
    pool = _require_pool()
    sheet_id_str = str(sheet_id)
    exists = await pool.fetchrow("select id from sheets where id = $1::uuid", sheet_id_str)
    if exists is None:
        raise HTTPException(status_code=404, detail="Sheet not found")

    await pool.execute(
        "update sheets set status = 'extracting' where id = $1::uuid",
        sheet_id_str,
    )
    settings = get_settings()
    task: asyncio.Task[None] = asyncio.create_task(run_extraction(pool, settings, sheet_id_str))
    _EXTRACTION_TASKS.add(task)
    task.add_done_callback(_EXTRACTION_TASKS.discard)
    return {"sheet_id": sheet_id_str, "status": "extracting"}


@router.get("/v1/sheets/{sheet_id}/events")
async def stream_events(sheet_id: uuid.UUID) -> StreamingResponse:
    """Stream the sheet's extraction_events as server-sent events.

    Polls for new events and yields each as an SSE data frame, stopping after a
    terminal event (done or error) or a bounded number of polls.
    """
    pool = _require_pool()
    sheet_id_str = str(sheet_id)

    async def generate() -> AsyncIterator[str]:
        seen: set[str] = set()
        # Poll for new events. The window is long enough for a slow multi-section
        # extraction to reach a terminal event, and a keepalive comment is sent
        # each tick so an HTTP/2 proxy does not drop the connection as idle while
        # the engine is between events.
        for _ in range(600):
            rows = await pool.fetch(
                """
                select id, stage, message, payload, created_at
                from extraction_events
                where sheet_id = $1::uuid
                order by created_at, id
                """,
                sheet_id_str,
            )
            terminal = False
            for row in rows:
                event_id = str(row["id"])
                if event_id in seen:
                    continue
                seen.add(event_id)
                frame = {
                    "stage": row["stage"],
                    "message": row["message"],
                    "payload": row["payload"],
                    "created_at": row["created_at"].isoformat(),
                }
                yield f"data: {json.dumps(frame)}\n\n"
                if row["stage"] in ("done", "error"):
                    terminal = True
            if terminal:
                return
            # A comment line (ignored by EventSource) keeps the stream alive.
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
