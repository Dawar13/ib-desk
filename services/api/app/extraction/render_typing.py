"""Render typing (Pass 4).

Mostly deterministic given the grounded cells. Applies the chart rule from
BUILD_PLAN.md: a chart hint only when a section is numeric and temporal
(timeseries) or a parts-of-whole breakdown, and only with at least three
comparable numeric points. Otherwise the section falls back to a non-chart hint.
This avoids misleading auto-charts.
"""

from __future__ import annotations

import re

_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")
_CHART_HINTS = {"timeseries_bar", "timeseries_line", "breakdown_pie"}
_MIN_CHART_POINTS = 3


class CellView:
    """The minimal cell fields render typing needs."""

    def __init__(self, value_norm: str | None, period: str | None) -> None:
        self.value_norm = value_norm
        self.period = period


def _is_numeric(cell: CellView) -> bool:
    return cell.value_norm is not None and _NUMERIC.match(cell.value_norm) is not None


def _fallback_for_kind(kind: str) -> str:
    if kind == "scalar":
        return "keyvalue"
    if kind == "list":
        return "chips"
    if kind == "longtext":
        return "longtext"
    # table and timeseries both render safely as a table when no chart is warranted.
    return "table"


def refine_render_hint(kind: str, proposed: str, cells: list[CellView]) -> str:
    """Return the final render hint, enforcing the chart rule."""
    if proposed not in _CHART_HINTS:
        # Keep the proposed non-chart hint, but ensure longtext and scalar map to
        # their natural hints.
        if kind == "longtext":
            return "longtext"
        if kind == "scalar" and proposed not in {"keyvalue", "longtext"}:
            return "keyvalue"
        return proposed

    numeric_cells = [cell for cell in cells if _is_numeric(cell)]
    if proposed in {"timeseries_bar", "timeseries_line"}:
        temporal = [cell for cell in numeric_cells if cell.period]
        if len(temporal) >= _MIN_CHART_POINTS:
            return proposed
    elif proposed == "breakdown_pie":
        if len(numeric_cells) >= _MIN_CHART_POINTS:
            return proposed
    return _fallback_for_kind(kind)
