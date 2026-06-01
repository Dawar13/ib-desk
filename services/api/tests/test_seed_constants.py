"""Seed constant checks. No database required.

This is the local green test. It verifies the seed module's invariants and that
its sample content is honestly labeled, so the round-trip test can rely on these
constants without a live database.

A pass means the seed fixture is internally consistent and clearly marked as
sample. A failure means the seed constants drifted and the round-trip
expectations would be wrong.
"""

from __future__ import annotations

from app import seed


def test_seed_validate_does_not_raise() -> None:
    seed.validate()


def test_document_name_labeled_sample() -> None:
    assert "sample" in seed.DOCUMENT_NAME.lower()


def test_raw_text_starts_with_source_snippet() -> None:
    assert seed.RAW_TEXT.startswith(seed.SOURCE_SNIPPET)


def test_char_end_matches_snippet_length() -> None:
    assert seed.CHAR_END == len(seed.SOURCE_SNIPPET)


def test_cell_confidence_is_full() -> None:
    assert seed.CELL_CONFIDENCE == 1.0
