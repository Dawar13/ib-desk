"""Large-document chunk-and-merge for the extraction engine (Phase 5).

A document whose canonical text exceeds the single-pass budget cannot be read in
one model call. Rather than truncate it silently, the engine discovers the schema
from a representative sample of the whole document, extracts each section over
ordered overlapping chunks, grounds every value against the FULL canonical text,
and merges the per-chunk results with row de-duplication.

Two design choices keep grounding correct and the Phase 4 in-document highlight
working on large documents:

  - Grounding is against the full canonical text, not the chunk, so a value's
    char span is already a full-text offset. There is no fragile chunk-offset
    translation to get wrong.
  - Chunks overlap, so a sentence on a chunk boundary still appears whole in at
    least one chunk. A fact that falls in the overlap of two chunks is extracted
    twice but grounds to the same full-text span, so it de-dupes to one row.

If a document is so large it would need more chunks than the cap, the leading
portion is processed and the truncation is reported as an event, never silent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.extraction.persist import ResolvedCell


@dataclass
class Chunk:
    text: str
    start: int  # character offset of this chunk's start in the full canonical text


def needs_chunking(text: str, budget: int) -> bool:
    return len(text) > budget


def representative_sample(text: str, budget: int) -> str:
    """A bounded sample of the document for discovery: head, middle, and tail.

    For a document within budget this is the whole text unchanged, so the
    single-pass path is byte-identical to before. For a larger document it gives
    discovery a view across the whole document rather than only its opening.
    """
    if len(text) <= budget:
        return text
    third = max(1, budget // 3)
    head = text[:third]
    mid_start = max(0, (len(text) - third) // 2)
    middle = text[mid_start : mid_start + third]
    tail = text[-third:]
    return f"{head}\n...\n{middle}\n...\n{tail}"


def split_chunks(text: str, budget: int, overlap: int, max_chunks: int) -> tuple[list[Chunk], bool]:
    """Split text into ordered overlapping chunks of at most `budget` characters.

    Returns the chunks and whether the text was truncated because it would need
    more than `max_chunks`. A document within budget yields a single chunk and no
    truncation, so small documents take the unchanged single-pass path.
    """
    if len(text) <= budget:
        return [Chunk(text=text, start=0)], False
    if overlap >= budget:
        overlap = budget // 4
    step = max(1, budget - overlap)
    chunks: list[Chunk] = []
    start = 0
    while start < len(text) and len(chunks) < max_chunks:
        chunks.append(Chunk(text=text[start : start + budget], start=start))
        start += step
    truncated = start < len(text)
    return chunks, truncated


def merge_resolved(chunk_cell_lists: list[list[ResolvedCell]]) -> list[ResolvedCell]:
    """Merge per-chunk grounded cells into one section, de-duping repeated rows.

    Rows are re-indexed sequentially in chunk order. A row is a duplicate when its
    grounded cells share the same (column key, character span) set as a row already
    kept, which is exactly what the chunk overlap produces, so overlap never
    doubles a fact. Mutates each kept cell's row_idx to its merged position.
    """
    seen: set[frozenset[tuple[str | None, int | None, int | None]]] = set()
    merged: list[ResolvedCell] = []
    next_row = 0
    for cells in chunk_cell_lists:
        by_row: dict[int, list[ResolvedCell]] = {}
        for cell in cells:
            by_row.setdefault(cell.row_idx, []).append(cell)
        for _original_row, row_cells in sorted(by_row.items()):
            signature = frozenset(
                (cell.col_key, cell.char_start, cell.char_end) for cell in row_cells
            )
            if signature in seen:
                continue
            seen.add(signature)
            for cell in row_cells:
                cell.row_idx = next_row
                merged.append(cell)
            next_row += 1
    return merged
