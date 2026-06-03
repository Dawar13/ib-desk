"""Styled xlsx export built with xlsxwriter.

Produces a colored, section-organized workbook that mirrors the on-screen sheet:
a merged title block, each discovered section under a category-colored header,
key-value and list and table layouts chosen by render hint, native embedded
charts for chart sections, number formats from the normalized value and unit,
banded table rows, a frozen title, and a cell comment on every value carrying its
source sentence and confidence. The builder reads the sheet payload (sections and
grounded cells), never the internal tidy store, so the download reflects the
visual sheet.

xlsxwriter is write-only, which is fine because the export always generates a
fresh file. The workbook is returned as bytes. The builder is a pure function of
the payload, so it is tested directly with no database and no model.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import xlsxwriter

from app.export import palette
from app.models import Cell, SectionWithCells, SheetPayload

# Chart render hints mapped to xlsxwriter chart types.
_CHART_TYPES = {
    "timeseries_bar": "column",
    "timeseries_line": "line",
    "breakdown_pie": "pie",
}

# The minimum number of comparable points for a sound chart, matching the
# conservative chart rule in BUILD_PLAN.md. Below this, a chart-hinted section
# exports its table only, never a misleading chart from too few points.
_MIN_CHART_POINTS = 3

_SHEET_NAME = "Sheet"
_VALUE_COLUMN = "__value__"

_DOC_TYPE_LABELS = {
    "company_profile": "Company profile",
    "market_overview": "Market overview",
    "deal": "Deal",
    "person": "Person",
    "technology": "Technology",
    "other": "Document",
}


@dataclass
class _Point:
    label: str
    value: float
    cell: Cell


class _Formats:
    """Lazily built, cached cell formats keyed by their properties."""

    def __init__(self, workbook: Any) -> None:
        self._workbook = workbook
        self._cache: dict[tuple[tuple[str, Any], ...], Any] = {}

    def get(self, **props: Any) -> Any:
        key = tuple(sorted(props.items()))
        fmt = self._cache.get(key)
        if fmt is None:
            fmt = self._workbook.add_format(props)
            self._cache[key] = fmt
        return fmt


def build_xlsx(
    payload: SheetPayload,
    *,
    doc_name: str,
    doc_type: str | None,
    primary_topic: str | None,
) -> bytes:
    """Build the styled workbook for a sheet payload and return it as bytes."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet(_SHEET_NAME)
    fmts = _Formats(workbook)

    sections = payload.sections
    span = _content_span(sections)

    # Sensible column widths: a wide first column for labels and categories, and
    # readable widths for the rest.
    worksheet.set_column(0, 0, 30)
    worksheet.set_column(1, max(1, span - 1), 22)

    row = _write_title(worksheet, fmts, payload.sheet.title, doc_type, primary_topic, span)
    # Freeze below the title block so the subject stays visible while scrolling.
    worksheet.freeze_panes(row, 0)

    for section in sections:
        row += 1  # a blank spacer row before each section
        row = _write_section(workbook, worksheet, fmts, section, row, span)

    workbook.close()
    return buffer.getvalue()


def _content_span(sections: list[SectionWithCells]) -> int:
    """The number of columns the title and section headers should merge across."""
    width = 2
    for section in sections:
        if section.render_hint in _CHART_TYPES:
            cols = 2
        elif section.render_hint == "table":
            cols = len(_table_columns(section))
        else:
            cols = 2
        width = max(width, cols)
    return width


def _subtitle(doc_type: str | None, primary_topic: str | None) -> str:
    label = _DOC_TYPE_LABELS.get(doc_type or "", "")
    parts = [part for part in (label, primary_topic) if part]
    return "  |  ".join(parts) if parts else "IB Desk sheet"


def _write_title(
    worksheet: Any,
    fmts: _Formats,
    subject: str,
    doc_type: str | None,
    primary_topic: str | None,
    span: int,
) -> int:
    last_col = max(1, span - 1)
    title_fmt = fmts.get(
        bold=True,
        font_size=16,
        font_color=palette.TITLE_TEXT,
        bg_color=palette.TITLE_BG,
        align="left",
        valign="vcenter",
    )
    worksheet.merge_range(0, 0, 0, last_col, subject, title_fmt)
    worksheet.set_row(0, 28)

    subtitle_fmt = fmts.get(
        italic=True,
        font_size=10,
        font_color=palette.TITLE_TEXT,
        bg_color=palette.TITLE_BG,
        align="left",
        valign="vcenter",
    )
    worksheet.merge_range(1, 0, 1, last_col, _subtitle(doc_type, primary_topic), subtitle_fmt)
    worksheet.set_row(1, 18)
    return 2


def _write_section(
    workbook: Any,
    worksheet: Any,
    fmts: _Formats,
    section: SectionWithCells,
    row: int,
    span: int,
) -> int:
    accent = palette.category_accent(section.category)
    header_fmt = fmts.get(
        bold=True,
        font_color=palette.HEADER_TEXT,
        bg_color=accent,
        align="left",
        valign="vcenter",
        border=1,
        border_color=palette.SURFACE,
    )
    last_col = max(1, span - 1)
    worksheet.merge_range(row, 0, row, last_col, section.label, header_fmt)
    worksheet.set_row(row, 20)
    row += 1

    if not section.cells:
        worksheet.write_string(
            row,
            0,
            "No grounded values in this section.",
            fmts.get(italic=True, font_color=palette.FAINT),
        )
        return row + 1

    hint = section.render_hint
    if hint == "keyvalue":
        return _write_keyvalue(worksheet, fmts, section, row)
    if hint == "chips":
        return _write_list(worksheet, fmts, section, row)
    if hint in _CHART_TYPES:
        return _write_chart_section(workbook, worksheet, fmts, section, row)
    if hint == "longtext":
        return _write_longtext(worksheet, fmts, section, row, span)
    return _write_table(worksheet, fmts, section, row)


def _write_value(
    worksheet: Any,
    fmts: _Formats,
    row: int,
    col: int,
    cell: Cell,
    *,
    banded: bool,
) -> None:
    """Write one grounded value, formatted by its unit, with its source comment."""
    base: dict[str, Any] = {
        "border": 1,
        "border_color": palette.LINE,
        "valign": "top",
        "font_color": palette.INK,
    }
    if banded:
        base["bg_color"] = palette.BAND_BG

    number = palette.numeric_value(cell.value_norm)
    if number is not None:
        fmt = fmts.get(**base, align="right", num_format=palette.number_format_for(cell.unit))
        worksheet.write_number(row, col, number, fmt)
    else:
        fmt = fmts.get(**base, align="left")
        worksheet.write_string(row, col, palette.display_text(cell), fmt)

    worksheet.write_comment(
        row,
        col,
        palette.comment_text(cell.source_snippet, cell.confidence),
        {"x_scale": 2.0, "y_scale": 2.0},
    )


def _write_keyvalue(worksheet: Any, fmts: _Formats, section: SectionWithCells, row: int) -> int:
    label_fmt = fmts.get(
        font_color=palette.MUTED,
        align="left",
        valign="top",
        border=1,
        border_color=palette.LINE,
    )
    for cell in section.cells:
        worksheet.write_string(row, 0, palette.field_label(cell), label_fmt)
        _write_value(worksheet, fmts, row, 1, cell, banded=False)
        row += 1
    return row


def _write_list(worksheet: Any, fmts: _Formats, section: SectionWithCells, row: int) -> int:
    for cell in section.cells:
        _write_value(worksheet, fmts, row, 0, cell, banded=False)
        row += 1
    return row


def _write_table(worksheet: Any, fmts: _Formats, section: SectionWithCells, row: int) -> int:
    columns = _table_columns(section)
    header_fmt = fmts.get(
        bold=True,
        bg_color=palette.TABLE_HEADER_BG,
        font_color=palette.INK,
        align="left",
        valign="bottom",
        border=1,
        border_color=palette.LINE,
        text_wrap=True,
    )
    for col, (_key, label) in enumerate(columns):
        worksheet.write_string(row, col, label, header_fmt)
    row += 1

    for band_index, (_row_idx, cells) in enumerate(_table_rows(section)):
        banded = band_index % 2 == 1
        for col, (key, _label) in enumerate(columns):
            cell = cells.get(key)
            if cell is not None:
                _write_value(worksheet, fmts, row, col, cell, banded=banded)
            else:
                placeholder: dict[str, Any] = {
                    "border": 1,
                    "border_color": palette.LINE,
                    "font_color": palette.FAINT,
                    "align": "center",
                }
                if banded:
                    placeholder["bg_color"] = palette.BAND_BG
                worksheet.write_string(row, col, "-", fmts.get(**placeholder))
        row += 1
    return row


def _write_longtext(
    worksheet: Any, fmts: _Formats, section: SectionWithCells, row: int, span: int
) -> int:
    last_col = max(1, span - 1)
    text_fmt = fmts.get(
        text_wrap=True,
        valign="top",
        align="left",
        border=1,
        border_color=palette.LINE,
        font_color=palette.INK,
    )
    for cell in section.cells:
        worksheet.merge_range(row, 0, row, last_col, palette.display_text(cell), text_fmt)
        worksheet.set_row(row, 64)
        worksheet.write_comment(
            row,
            0,
            palette.comment_text(cell.source_snippet, cell.confidence),
            {"x_scale": 3.0, "y_scale": 3.0},
        )
        row += 1
    return row


def _write_chart_section(
    workbook: Any, worksheet: Any, fmts: _Formats, section: SectionWithCells, row: int
) -> int:
    """Write a chart section as a clean two-column data table plus a native chart.

    The chart is emitted only when there are at least three comparable points, in
    keeping with the conservative chart rule. Below that the table stands alone.
    """
    points = _chart_points(section)
    category_label, value_label = _chart_labels(section)

    header_fmt = fmts.get(
        bold=True,
        bg_color=palette.TABLE_HEADER_BG,
        font_color=palette.INK,
        align="left",
        valign="bottom",
        border=1,
        border_color=palette.LINE,
    )
    category_fmt_plain = fmts.get(
        border=1, border_color=palette.LINE, align="left", font_color=palette.INK
    )
    category_fmt_band = fmts.get(
        border=1,
        border_color=palette.LINE,
        align="left",
        font_color=palette.INK,
        bg_color=palette.BAND_BG,
    )

    table_top = row
    worksheet.write_string(row, 0, category_label, header_fmt)
    worksheet.write_string(row, 1, value_label, header_fmt)
    row += 1
    first_data_row = row
    for band_index, point in enumerate(points):
        banded = band_index % 2 == 1
        worksheet.write_string(
            row, 0, point.label, category_fmt_band if banded else category_fmt_plain
        )
        _write_value(worksheet, fmts, row, 1, point.cell, banded=banded)
        row += 1
    last_data_row = row - 1

    if len(points) >= _MIN_CHART_POINTS:
        chart = workbook.add_chart({"type": _CHART_TYPES[section.render_hint]})
        chart.add_series(
            {
                "name": value_label,
                "categories": [_SHEET_NAME, first_data_row, 0, last_data_row, 0],
                "values": [_SHEET_NAME, first_data_row, 1, last_data_row, 1],
                "data_labels": {"value": section.render_hint == "breakdown_pie"},
            }
        )
        chart.set_title({"name": section.label})
        chart.set_legend({"none": section.render_hint != "breakdown_pie"})
        chart.set_size({"width": 480, "height": 288})
        worksheet.insert_chart(table_top, 3, chart)
        # Advance past whichever is taller, the table or the floating chart, so the
        # next section starts clear of the chart (a chart is roughly 15 rows tall).
        row = max(row, table_top + 15)
    return row


def _chart_labels(section: SectionWithCells) -> tuple[str, str]:
    columns = section.columns or []
    if section.render_hint == "breakdown_pie":
        category = columns[0].label if columns else "Category"
        value = columns[1].label if len(columns) > 1 else "Value"
        return category, value
    value = columns[0].label if columns else "Value"
    return "Period", value


def _chart_points(section: SectionWithCells) -> list[_Point]:
    """The comparable points for a chart section, dropping non-numeric values.

    For a breakdown the category is a text cell in the row and the value is the
    numeric cell. For a timeseries the category is the period (or the column key)
    and the value is the numeric cell.
    """
    points: list[_Point] = []
    if section.render_hint == "breakdown_pie":
        for row_idx, cells in _table_rows(section):
            value_cell: Cell | None = None
            value_number = 0.0
            label: str | None = None
            for cell in cells.values():
                number = palette.numeric_value(cell.value_norm)
                if number is not None and value_cell is None:
                    value_cell = cell
                    value_number = number
                elif number is None and label is None:
                    label = cell.value_raw or cell.value_norm
            if value_cell is not None:
                resolved = label or value_cell.period or f"Item {row_idx + 1}"
                points.append(_Point(resolved, value_number, value_cell))
    else:
        for cell in section.cells:
            number = palette.numeric_value(cell.value_norm)
            if number is None:
                continue
            resolved = cell.period or cell.col_key or f"Point {cell.row_idx + 1}"
            points.append(_Point(resolved, number, cell))
    return points


def _table_columns(section: SectionWithCells) -> list[tuple[str, str]]:
    """Header columns for a tabular section, mirroring the web table helper.

    Declared columns first, then any column key actually present on a cell, then a
    value column for cells with no column key, so no grounded cell is dropped.
    """
    declared = section.columns or []
    columns: list[tuple[str, str]] = [(column.key, column.label) for column in declared]
    seen = {column.key for column in declared}
    has_valueless = False
    for cell in section.cells:
        key = cell.col_key
        if key is not None and key.strip() != "":
            if key not in seen:
                seen.add(key)
                columns.append((key, key))
        else:
            has_valueless = True
    if has_valueless and _VALUE_COLUMN not in seen:
        columns.append((_VALUE_COLUMN, "Value"))
    if not columns:
        return [(_VALUE_COLUMN, "Value")]
    return columns


def _table_rows(section: SectionWithCells) -> list[tuple[int, dict[str, Cell]]]:
    by_row: dict[int, dict[str, Cell]] = {}
    for cell in section.cells:
        key = cell.col_key if (cell.col_key and cell.col_key.strip() != "") else _VALUE_COLUMN
        by_row.setdefault(cell.row_idx, {})[key] = cell
    return sorted(by_row.items())
