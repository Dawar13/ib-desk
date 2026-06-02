// Value display helpers shared by every renderer.
//
// The display text prefers the value exactly as written in the source
// (value_raw), since that is the human-readable, grounded form the banker can
// check against the evidence. value_norm is the deterministic canonical form and
// is used for computation (chart axes, comparisons), not display. Nothing here
// invents a value: an empty cell shows a neutral placeholder rather than a guess.

import type { Cell } from "@ib-desk/shared";

export const NO_VALUE = "-"; // a plain hyphen placeholder, never an em-dash

export function cellDisplayValue(cell: Cell): string {
  const base = cell.value_raw ?? cell.value_norm ?? "";
  const text = base.trim();
  return text === "" ? NO_VALUE : text;
}

// The numeric value used for charts, parsed from the deterministic value_norm.
// Returns null when the cell is not a clean number (for example a name or a free
// text value), so non-numeric cells are simply excluded from a chart rather than
// coerced.
export function numericValue(cell: Cell): number | null {
  const raw = cell.value_norm;
  if (raw === null || raw === undefined || raw.trim() === "") {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

// The field label for a cell, used in tables and the evidence drawer. Prefers
// the column key; falls back to the row position. Never invents a name.
export function cellFieldLabel(cell: Cell): string {
  if (cell.col_key !== null && cell.col_key.trim() !== "") {
    return cell.col_key;
  }
  return `Row ${cell.row_idx + 1}`;
}
