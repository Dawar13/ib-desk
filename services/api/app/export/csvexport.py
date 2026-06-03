"""CSV export: a flat table of the visible values.

A straightforward secondary format. One row per grounded value, carrying the
section, the field, the period, the value as written, and the unit, so every
visible value is present in a tool-agnostic form. The value as written
(value_raw) is used so the CSV reads the way the screen does.
"""

from __future__ import annotations

import csv
import io

from app.export import palette
from app.models import SheetPayload


def build_csv(payload: SheetPayload) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["Section", "Field", "Period", "Value", "Unit"])
    for section in payload.sections:
        for cell in section.cells:
            writer.writerow(
                [
                    section.label,
                    palette.field_label(cell),
                    cell.period or "",
                    palette.display_text(cell),
                    cell.unit or "",
                ]
            )
    return buffer.getvalue().encode("utf-8")
