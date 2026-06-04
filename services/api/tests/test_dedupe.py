"""Cross-section de-duplication unit test. Secret-free and database-free.

A fact a later section repeats from an earlier one (same source span and written
value) is kept only in the first section, so the sheet is not bulked up by the
same data appearing in several sections. Two distinct values quoted from the same
sentence are both kept, so genuinely different facts are never lost.
"""

from __future__ import annotations

from app.extraction.persist import ResolvedCell, ResolvedSection
from app.extraction.pipeline import _dedupe_across_sections


def _cell(value: str, start: int, end: int) -> ResolvedCell:
    return ResolvedCell(
        row_idx=0,
        col_key=None,
        value_raw=value,
        value_norm=value,
        unit=None,
        period=None,
        source_snippet="supporting sentence",
        char_start=start,
        char_end=end,
        confidence=0.9,
    )


def _section(key: str, cells: list[ResolvedCell]) -> ResolvedSection:
    return ResolvedSection(
        key=key,
        label=key,
        kind="list",
        render_hint="chips",
        category=None,
        columns=None,
        sort=0,
        confidence=None,
        cells=cells,
    )


def test_repeated_fact_kept_only_in_the_first_section() -> None:
    a = _section("overview", [_cell("Alpha", 10, 20)])
    b = _section("traction", [_cell("Alpha", 10, 20), _cell("Beta", 30, 40)])
    removed = _dedupe_across_sections([a, b])
    assert removed == 1
    assert [c.value_raw for c in a.cells] == ["Alpha"]
    assert [c.value_raw for c in b.cells] == ["Beta"]


def test_distinct_values_from_the_same_sentence_are_both_kept() -> None:
    # Same source span, different values (e.g. "Elevation Capital" and "$24M").
    a = _section("capital", [_cell("Elevation Capital", 100, 160), _cell("$24M", 100, 160)])
    removed = _dedupe_across_sections([a])
    assert removed == 0
    assert len(a.cells) == 2


def test_same_value_at_different_spans_is_kept() -> None:
    a = _section("s", [_cell("2024", 5, 9), _cell("2024", 50, 54)])
    removed = _dedupe_across_sections([a])
    assert removed == 0
    assert len(a.cells) == 2
