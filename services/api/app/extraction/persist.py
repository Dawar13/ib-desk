"""Persistence for the extraction engine.

Writes extraction_events for progress, and replaces a sheet's sections and cells
atomically: a single transaction deletes the prior content and inserts the new,
so a re-run never leaves a half-updated or duplicated sheet (idempotent
re-extraction). Cost is recorded as telemetry only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ResolvedCell:
    row_idx: int
    col_key: str | None
    value_raw: str
    value_norm: str | None
    unit: str | None
    period: str | None
    source_snippet: str
    char_start: int | None
    char_end: int | None
    confidence: float | None


@dataclass
class ResolvedSection:
    key: str
    label: str
    kind: str
    render_hint: str
    category: str | None
    columns: list[dict[str, str]] | None
    sort: int
    confidence: float | None
    cells: list[ResolvedCell]


async def write_event(
    pool: Any,
    sheet_id: str,
    stage: str,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    await pool.execute(
        """
        insert into extraction_events (sheet_id, stage, message, payload)
        values ($1::uuid, $2, $3, $4::jsonb)
        """,
        sheet_id,
        stage,
        message,
        json.dumps(payload) if payload is not None else None,
    )


async def set_status(pool: Any, sheet_id: str, status: str) -> None:
    await pool.execute(
        "update sheets set status = $2 where id = $1::uuid",
        sheet_id,
        status,
    )


async def replace_content(
    pool: Any,
    sheet_id: str,
    sections: list[ResolvedSection],
    cost_usd: float,
    status: str,
) -> int:
    """Atomically replace the sheet's sections and cells, returning the field count.

    Deletes the sheet's existing sections (cells cascade) and inserts the new
    sections and cells in one transaction, then updates the sheet status, field
    count, and cost. A re-run therefore replaces rather than duplicates.
    """
    field_count = sum(len(section.cells) for section in sections)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "delete from sections where sheet_id = $1::uuid",
                sheet_id,
            )
            for section in sections:
                section_id = await conn.fetchval(
                    """
                    insert into sections
                      (sheet_id, key, label, kind, render_hint, category, columns,
                       sort, confidence)
                    values ($1::uuid, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
                    returning id
                    """,
                    sheet_id,
                    section.key,
                    section.label,
                    section.kind,
                    section.render_hint,
                    section.category,
                    json.dumps(section.columns) if section.columns is not None else None,
                    section.sort,
                    section.confidence,
                )
                for cell in section.cells:
                    await conn.execute(
                        """
                        insert into cells
                          (section_id, row_idx, col_key, value_raw, value_norm, unit,
                           period, source_snippet, char_start, char_end, confidence)
                        values
                          ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        str(section_id),
                        cell.row_idx,
                        cell.col_key,
                        cell.value_raw,
                        cell.value_norm,
                        cell.unit,
                        cell.period,
                        cell.source_snippet,
                        cell.char_start,
                        cell.char_end,
                        cell.confidence,
                    )
            await conn.execute(
                "update sheets set status = $2, field_count = $3, cost_usd = $4 "
                "where id = $1::uuid",
                sheet_id,
                status,
                field_count,
                cost_usd,
            )
    return field_count
