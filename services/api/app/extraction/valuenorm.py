"""Deterministic value normalization.

value_norm is computed on the service side, never by the model, so the same
underlying figure renders identically on every run. Recognized numbers,
currencies, and percents are canonicalized to a plain decimal string with a unit;
everything else is canonicalized text (trim plus NFC). The parser is conservative:
when a value does not clearly parse as a number it falls back to text, so it never
invents a figure. Deterministic.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

# Currency markers mapped to ISO-like codes. Longer markers are tried first.
_CURRENCY: dict[str, str] = {
    "us$": "USD",
    "usd": "USD",
    "rs.": "INR",
    "inr": "INR",
    "rs": "INR",
    "eur": "EUR",
    "gbp": "GBP",
    "$": "USD",
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
}

# Magnitude words and suffixes mapped to their multiplier. Longer keys first.
_MAGNITUDE: dict[str, Decimal] = {
    "trillion": Decimal(1_000_000_000_000),
    "billion": Decimal(1_000_000_000),
    "million": Decimal(1_000_000),
    "thousand": Decimal(1_000),
    "crore": Decimal(10_000_000),
    "lakh": Decimal(100_000),
    "lac": Decimal(100_000),
    "bn": Decimal(1_000_000_000),
    "mn": Decimal(1_000_000),
    "cr": Decimal(10_000_000),
    "k": Decimal(1_000),
    "m": Decimal(1_000_000),
    "b": Decimal(1_000_000_000),
    "t": Decimal(1_000_000_000_000),
}

_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _canonical_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _format_decimal(number: Decimal) -> str:
    """Render a Decimal without exponent or trailing zeros, deterministically."""
    normalized = number.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _first_number(text: str) -> Decimal | None:
    match = _NUMBER.search(text)
    if match is None:
        return None
    try:
        return Decimal(match.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def normalize_value(value_raw: str) -> tuple[str, str | None]:
    """Return (value_norm, unit).

    For a recognized percent, value_norm is the decimal string and unit is
    "percent". For a recognized currency or magnitude amount, value_norm is the
    multiplied decimal string and unit is the currency code when present.
    Otherwise value_norm is the canonicalized text and unit is None.
    """
    text = _canonical_text(value_raw)
    if text == "":
        return "", None

    lowered = text.lower()

    if lowered.endswith("%") or lowered.endswith(" percent") or lowered.endswith(" pct"):
        number = _first_number(lowered)
        if number is not None:
            return _format_decimal(number), "percent"
        return text, None

    work = lowered
    unit: str | None = None
    for marker, code in sorted(_CURRENCY.items(), key=lambda kv: -len(kv[0])):
        if marker in work:
            unit = code
            work = work.replace(marker, " ")
            break

    magnitude = Decimal(1)
    for word, multiplier in sorted(_MAGNITUDE.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", work):
            magnitude = multiplier
            work = re.sub(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", " ", work, count=1)
            break

    number = _first_number(work)
    # Treat as numeric only when there is a clear numeric signal: a currency, a
    # magnitude, or a value that is essentially just the number.
    leftover = _NUMBER.sub("", work).strip()
    is_plain_number = leftover == ""
    if number is not None and (unit is not None or magnitude != Decimal(1) or is_plain_number):
        return _format_decimal(number * magnitude), unit

    return text, None
