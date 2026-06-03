"""Large-document chunk-and-merge unit tests. Secret-free and database-free.

The deterministic gate for large-document handling: detection, ordered
overlapping chunks that cover the text, the representative sample for discovery,
the truncation report when a document exceeds the chunk cap, and the row
de-duplication that keeps overlap from doubling a fact. A pass means a large
document is handled rather than silently truncated, and the merge preserves
grounding. A failure means large inputs break or lose data.
"""

from __future__ import annotations

from app.extraction import chunking
from app.extraction.persist import ResolvedCell


def _cell(row_idx: int, col_key: str, value: str, start: int, end: int) -> ResolvedCell:
    return ResolvedCell(
        row_idx=row_idx,
        col_key=col_key,
        value_raw=value,
        value_norm=value,
        unit=None,
        period=None,
        source_snippet=value,
        char_start=start,
        char_end=end,
        confidence=0.9,
    )


def test_needs_chunking_detects_oversize() -> None:
    assert chunking.needs_chunking("x" * 101, 100) is True
    assert chunking.needs_chunking("x" * 100, 100) is False


def test_small_text_is_a_single_chunk() -> None:
    chunks, truncated = chunking.split_chunks("hello", budget=100, overlap=10, max_chunks=8)
    assert len(chunks) == 1
    assert chunks[0].text == "hello"
    assert chunks[0].start == 0
    assert truncated is False


def test_large_text_splits_into_ordered_overlapping_chunks_that_cover_it() -> None:
    text = "abcdefghij" * 10  # 100 characters
    chunks, truncated = chunking.split_chunks(text, budget=40, overlap=10, max_chunks=8)

    assert truncated is False
    assert len(chunks) > 1
    assert chunks[0].start == 0
    assert [c.start for c in chunks] == sorted(c.start for c in chunks)
    # The last chunk reaches the end, and every chunk overlaps the previous, so
    # together they cover the text with no gap.
    assert chunks[-1].start + len(chunks[-1].text) == len(text)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.start <= previous.start + len(previous.text)


def test_truncation_past_the_cap_is_reported_not_silent() -> None:
    chunks, truncated = chunking.split_chunks("x" * 1000, budget=100, overlap=10, max_chunks=2)
    assert len(chunks) == 2
    assert truncated is True


def test_representative_sample_within_budget_is_unchanged() -> None:
    assert chunking.representative_sample("short text", 100) == "short text"


def test_representative_sample_covers_head_middle_and_tail() -> None:
    text = "H" * 100 + "M" * 100 + "T" * 100
    sample = chunking.representative_sample(text, budget=90)
    assert len(sample) < len(text)
    assert "H" in sample and "M" in sample and "T" in sample


def test_merge_dedupes_overlap_and_reindexes_rows() -> None:
    # The second chunk repeats the first chunk's fact (same column, same span) and
    # adds a new one. The merge keeps one of the duplicate and re-indexes rows.
    chunk_a = [_cell(0, "name", "Alpha", 10, 15)]
    chunk_b = [
        _cell(0, "name", "Alpha", 10, 15),  # duplicate via overlap, same span
        _cell(1, "name", "Beta", 50, 54),  # genuinely new
    ]
    merged = chunking.merge_resolved([chunk_a, chunk_b])
    assert [c.value_raw for c in merged] == ["Alpha", "Beta"]
    assert [c.row_idx for c in merged] == [0, 1]


def test_merge_keeps_distinct_spans_for_the_same_value() -> None:
    # The same value at two different spans is two real occurrences, both kept.
    chunk_a = [_cell(0, "name", "Alpha", 10, 15)]
    chunk_b = [_cell(0, "name", "Alpha", 90, 95)]
    merged = chunking.merge_resolved([chunk_a, chunk_b])
    assert len(merged) == 2
