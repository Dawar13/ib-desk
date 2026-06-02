"""Value normalization unit tests. No database or model needed.

These guard value-level determinism: the same underlying figure must canonicalize
to the same value_norm every time, and a value that is not clearly numeric falls
back to canonical text rather than an invented number.
"""

from __future__ import annotations

from app.extraction.valuenorm import normalize_value


def test_currency_with_magnitude() -> None:
    assert normalize_value("$24M") == ("24000000", "USD")


def test_percent() -> None:
    assert normalize_value("12.5%") == ("12.5", "percent")


def test_plain_number_with_commas() -> None:
    assert normalize_value("1,234") == ("1234", None)


def test_indian_currency_and_magnitude() -> None:
    assert normalize_value("Rs 5 crore") == ("50000000", "INR")


def test_free_text_falls_back_to_canonical_text() -> None:
    # Not numeric: canonicalized text, no unit, never an invented number.
    assert normalize_value("  Elevation Capital ") == ("Elevation Capital", None)


def test_is_deterministic() -> None:
    for raw in ["$24M", "12.5%", "1,234", "Rs 5 crore", "Series B"]:
        assert normalize_value(raw) == normalize_value(raw)
