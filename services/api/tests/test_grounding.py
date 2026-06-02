"""Grounding-by-search unit tests. No database or model needed.

These guard the anti-fabrication mechanism: a quoted sentence that exists in the
canonical text resolves to a span that maps back to it, and a sentence that does
not exist is reported ungrounded so the value can be dropped.
"""

from __future__ import annotations

from app.extraction.grounding import find_span, is_grounded

CANONICAL = (
    "Meridian was founded in 2017.\n\nIn 2023 Meridian closed a Series B led by Elevation Capital."
)


def test_exact_match_returns_resolving_span() -> None:
    snippet = "In 2023 Meridian closed a Series B led by Elevation Capital."
    span = find_span(CANONICAL, snippet)
    assert span is not None
    start, end = span
    assert CANONICAL[start:end] == snippet


def test_whitespace_insensitive_match() -> None:
    # The model quote has different spacing than the canonical text.
    snippet = "In 2023  Meridian closed   a Series B led by Elevation Capital."
    span = find_span(CANONICAL, snippet)
    assert span is not None
    start, end = span
    # The resolved span maps back to the canonical sentence (single-spaced).
    assert CANONICAL[start:end] == ("In 2023 Meridian closed a Series B led by Elevation Capital.")


def test_unfindable_snippet_is_ungrounded() -> None:
    # A sentence the model could have invented is not present in the source.
    snippet = "Meridian raised a Series C from SoftBank in 2025."
    assert find_span(CANONICAL, snippet) is None
    assert is_grounded(CANONICAL, snippet) is False


def test_empty_snippet_is_ungrounded() -> None:
    assert find_span(CANONICAL, "") is None
