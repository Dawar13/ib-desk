"""Pipeline logic tests on recorded cassettes. Require a database; replay mode, so
no model and no secret. These are the secret-free hard gates for the engine.

Covered: grounding-by-search drops a fabricated quote and the kept value's span
resolves back to its sentence; verification removes an unsupported value;
normalization produces value_norm; re-extraction atomically replaces (idempotent);
one failing section is isolated and the rest of the sheet still completes.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import asyncpg
import pytest

from app.config import get_settings
from app.extraction.pipeline import run_extraction

DB_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DB_URL is None,
    reason="DATABASE_URL is not set; skipping database-backed pipeline tests",
)

_CASSETTES = os.path.join(os.path.dirname(__file__), "cassettes")
WORKSPACE = "00000000-0000-0000-0000-000000000001"
DOC_NAME = "Acme sample (test)"
RAW_TEXT = (
    "Acme Robotics builds warehouse automation systems.\n\n"
    "In 2023 Acme closed a Series B of 30 million dollars led by Vertex Ventures.\n\n"
    "The company was founded in 2018 in Boston.\n\n"
    "Acme serves over 200 enterprise customers."
)


async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def _make_pool() -> asyncpg.Pool:
    assert DB_URL is not None
    # Small pool: tests do not need many connections, and a hosted session pooler
    # caps total clients, so several pools at once must stay well under that.
    return await asyncpg.create_pool(DB_URL, init=_init_conn, min_size=1, max_size=2)


async def _setup_sheet(pool: asyncpg.Pool) -> tuple[str, str]:
    doc_id = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())
    await pool.execute(
        "insert into documents (id, workspace_id, name, source_kind, raw_text) "
        "values ($1::uuid, $2::uuid, $3, 'paste', $4)",
        doc_id,
        WORKSPACE,
        DOC_NAME,
        RAW_TEXT,
    )
    await pool.execute(
        "insert into sheets (id, document_id, title, status) "
        "values ($1::uuid, $2::uuid, $3, 'idle')",
        sheet_id,
        doc_id,
        DOC_NAME,
    )
    return sheet_id, doc_id


async def _cleanup(pool: asyncpg.Pool, sheet_id: str, doc_id: str) -> None:
    # Deleting the sheet cascades its sections, cells, and events.
    await pool.execute("delete from sheets where id = $1::uuid", sheet_id)
    await pool.execute("delete from documents where id = $1::uuid", doc_id)


async def _sections_with_cells(pool: asyncpg.Pool, sheet_id: str) -> dict[str, list[dict]]:
    sections = await pool.fetch(
        "select * from sections where sheet_id = $1::uuid order by sort", sheet_id
    )
    out: dict[str, list[dict]] = {}
    for section in sections:
        cells = await pool.fetch(
            "select * from cells where section_id = $1::uuid order by row_idx, col_key nulls first",
            str(section["id"]),
        )
        out[section["key"]] = [dict(cell) for cell in cells]
    return out


def _configure(monkeypatch: pytest.MonkeyPatch, scenario: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_mode", "replay")
    monkeypatch.setattr(settings, "cassette_dir", os.path.join(_CASSETTES, scenario))
    monkeypatch.setattr(settings, "openai_model_discovery", "test")
    monkeypatch.setattr(settings, "openai_model_extraction", "test")
    monkeypatch.setattr(settings, "openai_model_verification", "test")
    monkeypatch.setattr(settings, "extraction_concurrency", 4)


def test_grounding_and_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, "basic")

    async def scenario() -> None:
        pool = await _make_pool()
        try:
            sheet_id, doc_id = await _setup_sheet(pool)
            await run_extraction(pool, get_settings(), sheet_id)

            sections = await _sections_with_cells(pool, sheet_id)
            assert set(sections.keys()) == {"investors_capital", "overview"}

            ic_cells = sections["investors_capital"]
            # The fabricated SoftBank quote is dropped by grounding; the
            # unsupported amount is dropped by verification; only the grounded,
            # supported investor remains.
            assert len(ic_cells) == 1
            cell = ic_cells[0]
            assert cell["col_key"] == "investor"
            assert cell["value_raw"] == "Vertex Ventures"
            assert RAW_TEXT[cell["char_start"] : cell["char_end"]] == cell["source_snippet"]
            values = [c["value_raw"] for c in ic_cells]
            assert "SoftBank" not in values
            assert "30 million dollars" not in values

            ov_cells = sections["overview"]
            assert len(ov_cells) == 1
            assert ov_cells[0]["value_norm"] is not None

            sheet = await pool.fetchrow("select status from sheets where id = $1::uuid", sheet_id)
            assert sheet["status"] == "done"
            stages = {
                row["stage"]
                for row in await pool.fetch(
                    "select stage from extraction_events where sheet_id = $1::uuid", sheet_id
                )
            }
            assert {"discovery", "extraction", "verification", "typing", "done"} <= stages

            await _cleanup(pool, sheet_id, doc_id)
        finally:
            await pool.close()

    asyncio.run(scenario())


def test_idempotent_reextraction(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, "basic")

    async def scenario() -> None:
        pool = await _make_pool()
        try:
            sheet_id, doc_id = await _setup_sheet(pool)
            await run_extraction(pool, get_settings(), sheet_id)
            first = await _sections_with_cells(pool, sheet_id)
            await run_extraction(pool, get_settings(), sheet_id)
            second = await _sections_with_cells(pool, sheet_id)

            # Re-extraction replaces rather than duplicates.
            assert list(first.keys()) == list(second.keys())
            assert {k: len(v) for k, v in first.items()} == {k: len(v) for k, v in second.items()}
            section_count = await pool.fetchval(
                "select count(*) from sections where sheet_id = $1::uuid", sheet_id
            )
            assert section_count == 2

            await _cleanup(pool, sheet_id, doc_id)
        finally:
            await pool.close()

    asyncio.run(scenario())


def test_error_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, "error_isolation")

    async def scenario() -> None:
        pool = await _make_pool()
        try:
            sheet_id, doc_id = await _setup_sheet(pool)
            await run_extraction(pool, get_settings(), sheet_id)

            sections = await _sections_with_cells(pool, sheet_id)
            # investors_capital fails (its extract cassette is missing); overview
            # still completes.
            assert set(sections.keys()) == {"overview"}
            errors = await pool.fetch(
                "select message from extraction_events "
                "where sheet_id = $1::uuid and stage = 'error'",
                sheet_id,
            )
            assert any("investors_capital" in (row["message"] or "") for row in errors)
            sheet = await pool.fetchrow("select status from sheets where id = $1::uuid", sheet_id)
            assert sheet["status"] == "done"

            await _cleanup(pool, sheet_id, doc_id)
        finally:
            await pool.close()

    asyncio.run(scenario())
