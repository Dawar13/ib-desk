"""The four-pass extraction pipeline.

Pass 1 discovery: one call over the canonical text proposing the schema.
Pass 2 extraction: one call returns every section, so the document is sent once
  rather than once per section (the dominant cost). A document too large for one
  pass is split into ordered overlapping chunks and each chunk is one such call,
  with exponential backoff on transient errors and per-chunk error isolation so one
  failing chunk does not halt the sheet. Each value is then grounded by search (its
  quoted sentence located in the canonical text, ungrounded values dropped) and
  normalized deterministically, and multi-chunk results are merged per section.
Pass 3 verification: one call checks every value against its quoted sentence and
  any the model marks unsupported are removed.
Pass 4 render typing: each section is typed with the chart rule.
The result replaces the sheet's sections and cells atomically, with progress
written to extraction_events and token usage recorded as telemetry.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import Settings
from app.extraction import chunking, cost, grounding, valuenorm
from app.extraction.llm import LLMClient, Usage, get_llm
from app.extraction.persist import (
    ResolvedCell,
    ResolvedSection,
    replace_content,
    set_status,
    write_event,
)
from app.extraction.prompts import (
    build_discovery_messages,
    build_extraction_messages,
    build_verification_messages,
)
from app.extraction.render_typing import CellView, refine_render_hint
from app.extraction.schemas import (
    DiscoveryResult,
    DiscoverySection,
    ExtractionResult,
    ExtractionRow,
    VerificationResult,
)

logger = logging.getLogger(__name__)

_TRANSIENT = {
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
    "APIStatusError",
}


def _is_transient(exc: Exception) -> bool:
    return type(exc).__name__ in _TRANSIENT


async def _call(
    llm: LLMClient,
    logical_id: str,
    model: str,
    messages: list[dict[str, str]],
    schema: type[Any],
    usages: list[Usage],
    attempts: int = 4,
) -> Any:
    delay = 1.0
    for attempt in range(attempts):
        try:
            parsed, usage = await asyncio.to_thread(
                llm.complete, logical_id, model, messages, schema
            )
            usages.append(usage)
            return parsed
        except Exception as exc:  # noqa: BLE001 - retry transient, re-raise the rest
            if not _is_transient(exc) or attempt == attempts - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


async def _load_raw_text(pool: Any, sheet_id: str) -> str | None:
    row = await pool.fetchrow(
        """
        select d.raw_text
        from documents d
        join sheets s on s.document_id = d.id
        where s.id = $1::uuid
        """,
        sheet_id,
    )
    return row["raw_text"] if row is not None else None


def _section_definition(section: DiscoverySection) -> str:
    parts = [
        f"key: {section.key}",
        f"label: {section.label}",
        f"kind: {section.kind}",
        f"rationale: {section.rationale}",
    ]
    if section.columns:
        cols = ", ".join(f"{c.key} ({c.label})" for c in section.columns)
        parts.append(f"columns: {cols}")
    return "\n".join(parts)


def _sections_block(sections: list[DiscoverySection]) -> str:
    """Render every section definition into one block for the single extraction call."""
    return "\n\n".join(
        f"--- section {i + 1} ---\n{_section_definition(section)}"
        for i, section in enumerate(sections)
    )


def _ground_and_normalize(raw_text: str, rows: list[ExtractionRow]) -> list[ResolvedCell]:
    """Locate each value's quoted sentence, drop the ungrounded, and normalize."""
    resolved: list[ResolvedCell] = []
    for row in rows:
        for cell in row.cells:
            span = grounding.find_span(raw_text, cell.source_snippet)
            if span is None:
                # Ungrounded: the quoted sentence is not in the document. Drop it.
                continue
            value_norm, norm_unit = valuenorm.normalize_value(cell.value)
            resolved.append(
                ResolvedCell(
                    row_idx=row.row_idx,
                    col_key=cell.col_key,
                    value_raw=cell.value,
                    value_norm=value_norm,
                    unit=norm_unit or cell.unit,
                    period=cell.period,
                    source_snippet=cell.source_snippet,
                    char_start=span[0],
                    char_end=span[1],
                    confidence=cell.confidence,
                )
            )
    return resolved


def _all_values_block(sections: list[ResolvedSection]) -> str:
    """Render every value across all sections for the single verification call.

    Each line carries the section key alongside the row index and column key, so a
    verdict maps back to exactly one value.
    """
    lines = []
    for section in sections:
        for cell in section.cells:
            col = cell.col_key if cell.col_key is not None else "(value)"
            lines.append(
                f"section {section.key} | row {cell.row_idx} | col {col} | "
                f"value: {cell.value_raw} | quote: {cell.source_snippet}"
            )
    return "\n".join(lines)


def _apply_verdicts(sections: list[ResolvedSection], verification: VerificationResult) -> None:
    """Remove only the values verification explicitly marked unsupported.

    Grounding already guarantees every value's quote exists in the document, so a
    value that the verification model does not address survives, but anything it
    flags as not genuinely supported is removed. Verdicts are matched by section
    key, row index, and column key.
    """
    rejected = {
        (verdict.section_key, verdict.row_idx, verdict.col_key)
        for verdict in verification.verdicts
        if not verdict.supported
    }
    for section in sections:
        section.cells = [
            cell
            for cell in section.cells
            if (section.key, cell.row_idx, cell.col_key) not in rejected
        ]


def _dedupe_across_sections(sections: list[ResolvedSection]) -> int:
    """Drop a value that a later section repeats from an earlier one.

    Each section is extracted independently and cannot see the others, so the same
    grounded fact can land in several sections and read as repetition. A fact is
    identified by its source span plus its written value, so two distinct values
    quoted from the same sentence are both kept, but the identical value from the
    identical sentence is kept only in the first section that has it (sections are
    in display order). Returns how many duplicates were removed.
    """
    seen: set[tuple[int | None, int | None, str]] = set()
    removed = 0
    for section in sections:
        kept: list[ResolvedCell] = []
        for cell in section.cells:
            key = (cell.char_start, cell.char_end, cell.value_raw or cell.value_norm or "")
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            kept.append(cell)
        section.cells = kept
    return removed


async def run_extraction(pool: Any, settings: Settings, sheet_id: str) -> None:
    """Run the four passes for one sheet and persist the result idempotently."""
    llm = get_llm()
    usages: list[Usage] = []
    try:
        await set_status(pool, sheet_id, "extracting")
        logger.info("extraction started for sheet %s", sheet_id)

        # Pass 1: discovery.
        await write_event(pool, sheet_id, "discovery", "discovery started")
        raw_text = await _load_raw_text(pool, sheet_id)
        if not raw_text:
            await write_event(pool, sheet_id, "error", "no document text for this sheet")
            await set_status(pool, sheet_id, "failed")
            return

        # Large-document handling: a document within budget yields a single chunk
        # and the unchanged single-pass behavior; a larger one is split into
        # ordered overlapping chunks and discovery sees a representative sample of
        # the whole. Truncation past the chunk cap is reported below, never silent.
        chunks, truncated = chunking.split_chunks(
            raw_text,
            settings.single_pass_char_budget,
            settings.chunk_overlap_chars,
            settings.max_chunks,
        )
        discovery: DiscoveryResult = await _call(
            llm,
            "discovery",
            settings.openai_model_discovery,
            build_discovery_messages(
                chunking.representative_sample(raw_text, settings.single_pass_char_budget)
            ),
            DiscoveryResult,
            usages,
        )
        await write_event(
            pool,
            sheet_id,
            "discovery",
            "discovery complete",
            {
                "doc_type": discovery.doc_type,
                "primary_topic": discovery.primary_topic,
                "sections": [section.key for section in discovery.sections],
            },
        )

        # Report large-document handling so it is never silent. The leading
        # portion is processed when a document exceeds the chunk cap.
        if len(chunks) > 1:
            await write_event(
                pool,
                sheet_id,
                "extraction",
                f"large document: extracting over {len(chunks)} overlapping chunks",
                {"chunks": len(chunks), "truncated": truncated},
            )
            if truncated:
                await write_event(
                    pool,
                    sheet_id,
                    "extraction",
                    "document exceeds the chunk budget; extracted the leading portion",
                    {"truncated": True},
                )

        # Pass 2: extraction. One call per chunk returns every section, so the
        # document is sent once instead of once per section, which is the dominant
        # extraction cost and also cuts the call count and the latency. Each value
        # is grounded against the full canonical text and normalized; for a
        # multi-chunk document the per-chunk results are merged per section. Error
        # isolation is per chunk: a chunk that fails after retries is skipped and
        # reported and the run proceeds on the chunks that succeeded; only if every
        # chunk fails does the run fail.
        await write_event(
            pool,
            sheet_id,
            "extraction",
            "extraction started",
            {"section_count": len(discovery.sections)},
        )
        sections_block = _sections_block(discovery.sections)
        per_section_chunks: dict[str, list[list[ResolvedCell]]] = {
            disc.key: [] for disc in discovery.sections
        }
        any_chunk_succeeded = False
        for chunk_index, chunk in enumerate(chunks):
            logical_id = "extract" if len(chunks) == 1 else f"extract.c{chunk_index}"
            try:
                result: ExtractionResult = await _call(
                    llm,
                    logical_id,
                    settings.openai_model_extraction,
                    build_extraction_messages(sections_block, chunk.text),
                    ExtractionResult,
                    usages,
                )
            except Exception as exc:  # noqa: BLE001 - isolate one chunk's failure
                logger.exception("extraction chunk %d failed for sheet %s", chunk_index, sheet_id)
                await write_event(
                    pool,
                    sheet_id,
                    "error",
                    f"extraction chunk {chunk_index} failed: {exc}",
                    {"chunk": chunk_index},
                )
                continue
            any_chunk_succeeded = True
            by_key = {se.section_key: se for se in result.sections}
            for disc in discovery.sections:
                extracted_section = by_key.get(disc.key)
                rows = extracted_section.rows if extracted_section is not None else []
                per_section_chunks[disc.key].append(_ground_and_normalize(raw_text, rows))

        if not any_chunk_succeeded:
            raise RuntimeError("extraction failed for every chunk")

        sections: list[ResolvedSection] = []
        for index, disc in enumerate(discovery.sections):
            cell_lists = per_section_chunks[disc.key]
            cells = cell_lists[0] if len(cell_lists) == 1 else chunking.merge_resolved(cell_lists)
            columns = (
                [{"key": c.key, "label": c.label} for c in disc.columns] if disc.columns else None
            )
            # Per-section completion event (after grounding, before verification and
            # typing) so the UI can reveal the sheet section by section off the
            # stream. The render_hint here is the discovery proposal; the final hint
            # is settled in the typing pass and read from the sheet payload.
            await write_event(
                pool,
                sheet_id,
                "section",
                f"section {disc.label} extracted",
                {
                    "key": disc.key,
                    "label": disc.label,
                    "sort": index,
                    "kind": disc.kind,
                    "cell_count": len(cells),
                },
            )
            sections.append(
                ResolvedSection(
                    key=disc.key,
                    label=disc.label,
                    kind=disc.kind,
                    render_hint=disc.render_hint,
                    category=disc.category,
                    columns=columns,
                    sort=index,
                    confidence=None,
                    cells=cells,
                )
            )

        # Drop facts a later section repeats from an earlier one, before
        # verification, so the sheet is not bulkier than it needs to be and the
        # repeated values are not paid for again in the verification pass.
        removed = _dedupe_across_sections(sections)
        if removed:
            await write_event(
                pool,
                sheet_id,
                "extraction",
                f"removed {removed} duplicate values repeated across sections",
                {"deduped": removed},
            )
        await write_event(pool, sheet_id, "extraction", "extraction complete")

        # Pass 3: verification. One call checks every value across all sections,
        # dropping only those it explicitly marks unsupported. Grounding already
        # guarantees every quote exists, so a value the model does not address
        # survives. A verification failure must not invent trust: if the call fails
        # after retries, the values are dropped rather than kept unverified.
        await write_event(pool, sheet_id, "verification", "verification started")
        if any(section.cells for section in sections):
            try:
                verification: VerificationResult = await _call(
                    llm,
                    "verify",
                    settings.openai_model_verification,
                    build_verification_messages(_all_values_block(sections)),
                    VerificationResult,
                    usages,
                )
                _apply_verdicts(sections, verification)
            except Exception as exc:  # noqa: BLE001 - drop rather than keep unverified
                logger.warning("verification failed for sheet %s: %s", sheet_id, exc)
                await write_event(
                    pool,
                    sheet_id,
                    "error",
                    f"verification failed: {exc}",
                    None,
                )
                for section in sections:
                    section.cells = []
        await write_event(pool, sheet_id, "verification", "verification complete")

        # Pass 4: render typing (deterministic, chart rule).
        await write_event(pool, sheet_id, "typing", "render typing started")
        for section in sections:
            views = [CellView(cell.value_norm, cell.period) for cell in section.cells]
            section.render_hint = refine_render_hint(section.kind, section.render_hint, views)
        await write_event(pool, sheet_id, "typing", "render typing complete")

        # Persist atomically and finish.
        total_prompt = sum(u.prompt_tokens for u in usages)
        total_completion = sum(u.completion_tokens for u in usages)
        total_cached = sum(u.cached_prompt_tokens for u in usages)
        cost_usd = cost.estimate_cost_usd(
            usages,
            settings.openai_price_input_per_1m,
            settings.openai_price_cached_input_per_1m,
            settings.openai_price_output_per_1m,
        )
        field_count = await replace_content(pool, sheet_id, sections, cost_usd, "done")
        await write_event(
            pool,
            sheet_id,
            "done",
            "extraction complete",
            {
                "sections": len(sections),
                "fields": field_count,
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "cached_prompt_tokens": total_cached,
                "cost_usd": cost_usd,
            },
        )
        logger.info(
            "extraction complete for sheet %s: %d sections, %d fields, "
            "%d of %d input tokens cached, est cost $%.4f",
            sheet_id,
            len(sections),
            field_count,
            total_cached,
            total_prompt,
            cost_usd,
        )
    except Exception as exc:  # noqa: BLE001 - any pipeline failure marks the sheet failed
        logger.exception("extraction pipeline failed for sheet %s", sheet_id)
        await write_event(pool, sheet_id, "error", f"pipeline failed: {exc}")
        await set_status(pool, sheet_id, "failed")
