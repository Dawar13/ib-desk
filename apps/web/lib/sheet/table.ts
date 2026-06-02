// Table shaping for tabular sections.
//
// A table or timeseries section is a grid: cells carry a row index and a column
// key, and the section may declare ordered columns. This turns the flat cell list
// into header columns and keyed rows for rendering, deriving columns from the
// data when the section did not declare them, and falling back to a single value
// column when there are no column keys at all. It assumes nothing about which
// columns a section has, in keeping with the discovered-schema rule.

import type { Cell, ColumnDef, SectionWithCells } from "@ib-desk/shared";

// Synthetic column key used when a section's cells carry no column key.
export const VALUE_COLUMN = "__value__";

export function tableColumns(section: SectionWithCells): ColumnDef[] {
  if (section.columns && section.columns.length > 0) {
    return section.columns;
  }
  const seen = new Map<string, string>();
  for (const cell of section.cells) {
    if (cell.col_key !== null && cell.col_key.trim() !== "" && !seen.has(cell.col_key)) {
      seen.set(cell.col_key, cell.col_key);
    }
  }
  if (seen.size === 0) {
    return [{ key: VALUE_COLUMN, label: "Value" }];
  }
  return Array.from(seen.entries()).map(([key, label]) => ({ key, label }));
}

export interface TableRow {
  rowIdx: number;
  cells: Record<string, Cell>;
}

export function tableRows(section: SectionWithCells): TableRow[] {
  const byRow = new Map<number, Record<string, Cell>>();
  for (const cell of section.cells) {
    const key =
      cell.col_key !== null && cell.col_key.trim() !== "" ? cell.col_key : VALUE_COLUMN;
    const row = byRow.get(cell.row_idx) ?? {};
    row[key] = cell;
    byRow.set(cell.row_idx, row);
  }
  return Array.from(byRow.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([rowIdx, cells]) => ({ rowIdx, cells }));
}
