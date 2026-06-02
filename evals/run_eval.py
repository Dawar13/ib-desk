"""Label-free Phase 2 evaluation harness.

Runs the live extraction pipeline over the sample documents under evals/docs and
computes the metrics that need no hand labels: grounding resolution, fabrication
rate, and value-level stability. Prints a human-readable summary, writes
evals/report.json, and exits non-zero if the fabrication rate exceeds a small
threshold so it can gate.

The owner declined the labeled golden set, so there is no precision, recall, or
schema-sensibleness score here. Those require hand labeling that is out of scope.

This is a script, not part of the mypy app scope, but it is typed where that helps
readability. It consumes the engine core unchanged: it inserts a temporary
documents and sheets row per document, calls app.extraction.pipeline.run_extraction,
reads back the persisted sections and cells, then deletes what it created.

Run it from services/api so the app modules import cleanly:

    cd services/api
    uv run python ../../evals/run_eval.py

Requires LLM_MODE=live, OPENAI_API_KEY, the three OPENAI_MODEL_* settings, and a
writable DATABASE_URL. See evals/README.md.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Locate the repo root from this file and put services/api on sys.path so the app
# package imports the same way it does when running from the service directory.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent
_API_DIR = _REPO_ROOT / "services" / "api"
_DOCS_DIR = _THIS_FILE.parent / "docs"
_REPORT_PATH = _THIS_FILE.parent / "report.json"

if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

import asyncpg  # noqa: E402 - imported after sys.path is set up

from app.config import Settings, get_settings  # noqa: E402
from app.extraction import grounding  # noqa: E402
from app.extraction.pipeline import run_extraction  # noqa: E402

# The default workspace used across the build until real auth arrives. The sample
# documents are inserted under this workspace and deleted again at the end.
WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

# Default number of repeated runs per document for the value-level stability
# metric, overridable via EVAL_STABILITY_RUNS.
_DEFAULT_STABILITY_RUNS = 3
# Default maximum fabrication rate before the harness exits non-zero (the gate),
# overridable via EVAL_FABRICATION_THRESHOLD.
_DEFAULT_FABRICATION_THRESHOLD = 0.01


@dataclass
class CellRecord:
    """One emitted cell read back from the database, with the fields the metrics
    need. value_key identifies the value position for stability comparison."""

    section_key: str
    row_idx: int
    col_key: str | None
    value_norm: str | None
    source_snippet: str
    char_start: int | None
    char_end: int | None

    @property
    def value_key(self) -> tuple[str, int, str | None]:
        return (self.section_key, self.row_idx, self.col_key)


@dataclass
class DocReport:
    """Per-document metrics for the report."""

    name: str
    cell_count: int = 0
    grounded_count: int = 0
    grounding_resolution: float = 1.0
    fabrication_rate: float = 0.0
    stability_runs: int = 0
    stable_value_share: float = 1.0
    notes: list[str] = field(default_factory=list)


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Install the json and jsonb codecs, mirroring services/api/app/db.py, so
    jsonb columns decode to native Python objects."""
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


def _read_documents() -> list[tuple[str, str]]:
    """Return (name, raw_text) for each .txt document under evals/docs, sorted by
    filename so runs are reproducible."""
    docs: list[tuple[str, str]] = []
    for path in sorted(_DOCS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        docs.append((path.name, text))
    return docs


async def _insert_temp_document(
    pool: asyncpg.Pool, name: str, raw_text: str
) -> tuple[str, str]:
    """Insert a temporary documents row and an idle sheets row for it.

    Returns (sheet_id, document_id). The document is a paste source so it needs no
    object storage. Only the columns the pipeline reads are set; the rest default.
    """
    document_id = str(uuid.uuid4())
    sheet_id = str(uuid.uuid4())
    await pool.execute(
        "insert into documents (id, workspace_id, name, source_kind, raw_text) "
        "values ($1::uuid, $2::uuid, $3, 'paste', $4)",
        document_id,
        WORKSPACE_ID,
        name,
        raw_text,
    )
    await pool.execute(
        "insert into sheets (id, document_id, title, status) "
        "values ($1::uuid, $2::uuid, $3, 'idle')",
        sheet_id,
        document_id,
        name,
    )
    return sheet_id, document_id


async def _cleanup_temp(pool: asyncpg.Pool, sheet_id: str, document_id: str) -> None:
    """Delete the temporary sheet (cascading its sections, cells, and events) and
    then the document. The sheet must go first: sheets references documents without
    on delete cascade."""
    await pool.execute("delete from sheets where id = $1::uuid", sheet_id)
    await pool.execute("delete from documents where id = $1::uuid", document_id)


async def _read_cells(pool: asyncpg.Pool, sheet_id: str) -> list[CellRecord]:
    """Read back every emitted cell for a sheet, joined to its section key."""
    rows = await pool.fetch(
        """
        select s.key as section_key,
               c.row_idx,
               c.col_key,
               c.value_norm,
               c.source_snippet,
               c.char_start,
               c.char_end
        from cells c
        join sections s on s.id = c.section_id
        where s.sheet_id = $1::uuid
        order by s.sort, c.row_idx, c.col_key asc nulls first
        """,
        sheet_id,
    )
    return [
        CellRecord(
            section_key=row["section_key"],
            row_idx=row["row_idx"],
            col_key=row["col_key"],
            value_norm=row["value_norm"],
            source_snippet=row["source_snippet"],
            char_start=row["char_start"],
            char_end=row["char_end"],
        )
        for row in rows
    ]


def _is_grounded(cell: CellRecord, raw_text: str) -> bool:
    """A cell is grounded when its supporting sentence is independently locatable
    in the source text by the engine's own search, and its stored character span
    maps back to that same sentence. Both checks must pass.

    The span check uses find_span (the engine's locator) rather than a raw slice
    so it tolerates the whitespace-insensitive match the engine itself allows: the
    stored span points at the located occurrence, and slicing it back out must
    locate the snippet again at offset zero.
    """
    located = grounding.find_span(raw_text, cell.source_snippet)
    if located is None:
        return False
    if cell.char_start is None or cell.char_end is None:
        return False
    if not (0 <= cell.char_start <= cell.char_end <= len(raw_text)):
        return False
    span_text = raw_text[cell.char_start : cell.char_end]
    # The stored span must itself contain exactly the supporting sentence. An exact
    # slice equality is the strict case; the whitespace-insensitive locate covers
    # the spacing differences the engine permits, anchored at the span start.
    if span_text == cell.source_snippet:
        return True
    relocated = grounding.find_span(span_text, cell.source_snippet)
    return relocated is not None and relocated[0] == 0


def _grounding_metrics(cells: list[CellRecord], raw_text: str) -> tuple[int, int]:
    """Return (grounded_count, total_count)."""
    total = len(cells)
    grounded = sum(1 for cell in cells if _is_grounded(cell, raw_text))
    return grounded, total


def _stability_share(runs: list[list[CellRecord]]) -> tuple[float, int]:
    """Share of value positions whose value_norm is identical across all runs.

    A value position is (section_key, row_idx, col_key). A position is stable when
    it appears in every run and carries the same value_norm in each. The share is
    over the union of positions seen across runs, so a value that appears in some
    runs but not others counts against stability rather than being ignored.
    Returns (share, position_count). With fewer than two runs, stability is trivially
    1.0 over zero compared positions.
    """
    if len(runs) < 2:
        return 1.0, 0

    per_run: list[dict[tuple[str, int, str | None], str | None]] = []
    for run in runs:
        mapping: dict[tuple[str, int, str | None], str | None] = {}
        for cell in run:
            # If a position somehow repeats within a run, keep the first; the read
            # order is deterministic.
            mapping.setdefault(cell.value_key, cell.value_norm)
        per_run.append(mapping)

    all_positions: set[tuple[str, int, str | None]] = set()
    for mapping in per_run:
        all_positions.update(mapping.keys())

    if not all_positions:
        return 1.0, 0

    stable = 0
    for position in all_positions:
        present_everywhere = all(position in mapping for mapping in per_run)
        if not present_everywhere:
            continue
        values = {mapping[position] for mapping in per_run}
        if len(values) == 1:
            stable += 1

    return stable / len(all_positions), len(all_positions)


async def _run_document(
    pool: asyncpg.Pool,
    settings: Settings,
    name: str,
    raw_text: str,
    stability_runs: int,
) -> DocReport:
    """Run the pipeline stability_runs times for one document and compute metrics.

    The grounding and fabrication metrics are computed on the first run; the
    stability metric compares value_norm across all runs. Each run uses its own
    temporary document and sheet so a run never reads another run's content.
    """
    report = DocReport(name=name, stability_runs=stability_runs)
    runs: list[list[CellRecord]] = []

    for run_index in range(stability_runs):
        sheet_id, document_id = await _insert_temp_document(pool, name, raw_text)
        try:
            await run_extraction(pool, settings, sheet_id)
            status = await pool.fetchval(
                "select status from sheets where id = $1::uuid", sheet_id
            )
            if status != "done":
                report.notes.append(
                    f"run {run_index} finished with sheet status {status!r}, not 'done'"
                )
            cells = await _read_cells(pool, sheet_id)
            runs.append(cells)
        finally:
            await _cleanup_temp(pool, sheet_id, document_id)

    first_run = runs[0] if runs else []
    grounded, total = _grounding_metrics(first_run, raw_text)
    report.cell_count = total
    report.grounded_count = grounded
    # Grounding resolution is the share of emitted cells that resolve. With no
    # emitted cells there is nothing ungrounded, so resolution is 1.0 and the
    # fabrication rate is 0.0 (it cannot fabricate what it did not emit).
    report.grounding_resolution = (grounded / total) if total else 1.0
    report.fabrication_rate = 1.0 - report.grounding_resolution

    share, positions = _stability_share(runs)
    report.stable_value_share = share
    if positions == 0 and stability_runs >= 2:
        report.notes.append("no value positions to compare for stability")

    return report


def _check_live_config(settings: Settings) -> list[str]:
    """Return a list of configuration problems that block a live run. Empty means
    the configuration is good to run live."""
    problems: list[str] = []
    if settings.llm_mode != "live":
        problems.append(
            f"LLM_MODE is {settings.llm_mode!r}; the eval harness requires 'live'. "
            "Set LLM_MODE=live."
        )
    if not settings.openai_api_key:
        problems.append("OPENAI_API_KEY is not set; a live run needs the key.")
    if not settings.openai_model_discovery:
        problems.append("OPENAI_MODEL_DISCOVERY is not set.")
    if not settings.openai_model_extraction:
        problems.append("OPENAI_MODEL_EXTRACTION is not set.")
    if not settings.openai_model_verification:
        problems.append("OPENAI_MODEL_VERIFICATION is not set.")
    return problems


def _print_summary(
    reports: list[DocReport],
    aggregate: dict[str, Any],
    threshold: float,
) -> None:
    """Print a plain, readable per-document and aggregate summary."""
    print("")
    print("IB Desk label-free Phase 2 eval")
    print("(no labeled golden set; fabrication, grounding, and stability only)")
    print("=" * 64)
    for report in reports:
        print(f"document: {report.name}")
        print(f"  emitted cells:        {report.cell_count}")
        print(f"  grounded cells:       {report.grounded_count}")
        print(f"  grounding resolution: {report.grounding_resolution:.4f}")
        print(f"  fabrication rate:     {report.fabrication_rate:.4f}")
        print(
            f"  value stability:      {report.stable_value_share:.4f} "
            f"over {report.stability_runs} runs"
        )
        for note in report.notes:
            print(f"  note: {note}")
        print("-" * 64)
    print("aggregate")
    print(f"  documents:            {aggregate['document_count']}")
    print(f"  total emitted cells:  {aggregate['total_cells']}")
    print(f"  grounding resolution: {aggregate['grounding_resolution']:.4f}")
    print(f"  fabrication rate:     {aggregate['fabrication_rate']:.4f}")
    print(f"  value stability:      {aggregate['stable_value_share']:.4f}")
    print(f"  fabrication gate:     <= {threshold:.4f}")
    print("=" * 64)


async def _amain() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set. The eval harness needs a writable database.")
        return 2

    settings = get_settings()
    problems = _check_live_config(settings)
    if problems:
        print("The eval harness runs live and is not configured to:")
        for problem in problems:
            print(f"  - {problem}")
        print("See evals/README.md for the required environment.")
        return 2

    documents = _read_documents()
    if not documents:
        print(f"No .txt documents found under {_DOCS_DIR}.")
        return 2

    stability_runs = max(1, int(os.environ.get("EVAL_STABILITY_RUNS", _DEFAULT_STABILITY_RUNS)))
    threshold = float(
        os.environ.get("EVAL_FABRICATION_THRESHOLD", _DEFAULT_FABRICATION_THRESHOLD)
    )

    # Small pool: this script does light, mostly sequential work, and a hosted
    # session pooler caps total clients.
    pool = await asyncpg.create_pool(
        database_url, init=_init_connection, min_size=1, max_size=3
    )
    reports: list[DocReport] = []
    try:
        for name, raw_text in documents:
            print(f"running pipeline {stability_runs}x for {name} ...")
            report = await _run_document(pool, settings, name, raw_text, stability_runs)
            reports.append(report)
    finally:
        await pool.close()

    total_cells = sum(report.cell_count for report in reports)
    total_grounded = sum(report.grounded_count for report in reports)
    aggregate_resolution = (total_grounded / total_cells) if total_cells else 1.0
    aggregate_fabrication = 1.0 - aggregate_resolution
    # Aggregate stability is the simple mean of per-document stability shares.
    aggregate_stability = (
        sum(report.stable_value_share for report in reports) / len(reports)
        if reports
        else 1.0
    )

    aggregate: dict[str, Any] = {
        "document_count": len(reports),
        "total_cells": total_cells,
        "total_grounded": total_grounded,
        "grounding_resolution": aggregate_resolution,
        "fabrication_rate": aggregate_fabrication,
        "stable_value_share": aggregate_stability,
        "stability_runs": stability_runs,
        "fabrication_threshold": threshold,
    }

    report_payload: dict[str, Any] = {
        "eval": "label_free_phase2",
        "note": (
            "Label-free Phase 2 eval. No hand-labeled golden set: the owner "
            "descoped it. Metrics: grounding resolution, fabrication rate, "
            "value-level stability. Sample documents are fictional."
        ),
        "models": {
            "discovery": settings.openai_model_discovery,
            "extraction": settings.openai_model_extraction,
            "verification": settings.openai_model_verification,
        },
        "documents": [
            {
                "name": report.name,
                "cell_count": report.cell_count,
                "grounded_count": report.grounded_count,
                "grounding_resolution": report.grounding_resolution,
                "fabrication_rate": report.fabrication_rate,
                "stability_runs": report.stability_runs,
                "stable_value_share": report.stable_value_share,
                "notes": report.notes,
            }
            for report in reports
        ],
        "aggregate": aggregate,
    }
    _REPORT_PATH.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    _print_summary(reports, aggregate, threshold)
    print(f"wrote {_REPORT_PATH}")

    # Gate on the fabrication rate. Near zero is the target; above the threshold
    # the harness fails so it can block a regression.
    if aggregate_fabrication > threshold:
        print(
            f"FAIL: fabrication rate {aggregate_fabrication:.4f} exceeds the "
            f"threshold {threshold:.4f}."
        )
        return 1
    print(
        f"PASS: fabrication rate {aggregate_fabrication:.4f} is within the "
        f"threshold {threshold:.4f}."
    )
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
