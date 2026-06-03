"""Colors, number formats, and comment text for the styled export.

The category accent palette is ported verbatim from the web client
(apps/web/lib/sheet/category.ts): same colors, same order, same 32-bit hash, so a
section's header color in the downloaded workbook is the exact color it has on
screen. The theme tokens mirror the warm paper palette in
apps/web/tailwind.config.ts. The confidence thresholds mirror
apps/web/lib/sheet/confidence.ts so the comment label matches the on-screen dot.

Nothing here invents a value: it only decides how an already-grounded value is
colored, formatted, and annotated.
"""

from __future__ import annotations

from app.models import Cell

# Theme tokens, mirroring apps/web/tailwind.config.ts.
PAPER = "#F4EEE2"
SURFACE = "#FFFDF9"
LINE = "#E6DDCC"
INK = "#2B2722"
MUTED = "#6C6456"
FAINT = "#9A9182"

# Export-only tones derived from the theme.
TITLE_BG = "#2B2722"  # ink, for the merged title block
TITLE_TEXT = "#FFFDF9"  # surface, light text on the dark title
HEADER_TEXT = "#FFFFFF"  # white text on a category-colored section header
TABLE_HEADER_BG = "#EFE8DA"  # a shade darker than paper for table header rows
BAND_BG = "#FBF7F0"  # subtle banding on alternate table rows

# Category accent palette, ported from apps/web/lib/sheet/category.ts. Keep this
# in sync with that file: same colors, same order, same hash.
_PALETTE = [
    "#8C6B4F",
    "#4F6D8C",
    "#5D7D57",
    "#8C5F6F",
    "#6F5D9C",
    "#9C7A3C",
    "#3F7D7A",
    "#9C5A4A",
]
_NEUTRAL = "#7D756A"

# Number formats. Percent uses a literal percent sign rather than Excel's percent
# operator, because value_norm for a percentage is already the displayed number
# (45 means 45 percent); the percent operator would multiply by 100 and show
# 4500 percent. Currency uses the Indian lakh and crore grouping for the rupee.
PERCENT_FORMAT = '0.##"%"'
RUPEE_FORMAT = "₹#,##,##0"
USD_FORMAT = "$#,##0"
PLAIN_FORMAT = "General"

_PERCENT_UNITS = {"percent", "%", "pct"}
_RUPEE_UNITS = {"inr", "rs", "rs.", "rupees", "rupee", "₹"}
_USD_UNITS = {"usd", "$", "us$", "dollar", "dollars"}

# Confidence thresholds, mirroring apps/web/lib/sheet/confidence.ts.
_CONFIDENCE_HIGH = 0.8
_CONFIDENCE_MEDIUM = 0.5


def _hash_string(value: str) -> int:
    # Mirrors the 32-bit signed hash in category.ts: hash = (hash * 31 + c) | 0.
    h = 0
    for ch in value:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return abs(h)


def category_accent(category: str | None) -> str:
    """The stable accent for a category, identical to the on-screen accent."""
    if category is None or category.strip() == "":
        return _NEUTRAL
    return _PALETTE[_hash_string(category) % len(_PALETTE)]


def numeric_value(value_norm: str | None) -> float | None:
    """Parse value_norm as a finite number, or None when it is not numeric."""
    if value_norm is None or value_norm.strip() == "":
        return None
    try:
        parsed = float(value_norm)
    except ValueError:
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def number_format_for(unit: str | None) -> str:
    """The Excel number format for a numeric value, decided by its unit."""
    normalized = (unit or "").strip().lower()
    if normalized in _PERCENT_UNITS:
        return PERCENT_FORMAT
    if normalized in _RUPEE_UNITS:
        return RUPEE_FORMAT
    if normalized in _USD_UNITS:
        return USD_FORMAT
    return PLAIN_FORMAT


def confidence_label(score: float | None) -> str:
    if score is None or score != score:  # None or NaN
        return "Unscored"
    if score >= _CONFIDENCE_HIGH:
        return "High"
    if score >= _CONFIDENCE_MEDIUM:
        return "Medium"
    return "Low"


def comment_text(source_snippet: str, confidence: float | None) -> str:
    """The cell comment that carries the grounding into the workbook itself."""
    label = confidence_label(confidence)
    if confidence is not None and confidence == confidence:  # not NaN
        confidence_part = f"{label} ({confidence:.2f})"
    else:
        confidence_part = label
    return f"Source: {source_snippet}\nConfidence: {confidence_part}"


def field_label(cell: Cell) -> str:
    """The field name for a value: its column key, else a positional fallback."""
    if cell.col_key is not None and cell.col_key.strip() != "":
        return cell.col_key
    return f"Row {cell.row_idx + 1}"


def display_text(cell: Cell) -> str:
    """The value as written, preferred over the normalized form for display."""
    if cell.value_raw is not None and cell.value_raw.strip() != "":
        return cell.value_raw
    return cell.value_norm or "-"
