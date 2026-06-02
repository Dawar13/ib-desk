// Chart data and the safe-fallback decision.
//
// A chart appears only where the engine marked a section as a chart (the typing
// pass already enforced the "warranted only" rule), and only when the section's
// data can actually form a sound chart. This module turns a chart-hinted section
// into chart points and reports whether the result is valid, so the renderer can
// fall back to the table when it is not. The guardrail is explicit: a chart is
// never drawn from fewer than three comparable points, and a section that cannot
// produce them degrades to its table rather than throwing.

import type { Cell, RenderHint, SectionWithCells } from "@ib-desk/shared";
import { numericValue } from "./value";

export const CHART_HINTS: readonly RenderHint[] = [
  "timeseries_bar",
  "timeseries_line",
  "breakdown_pie",
];

export function isChartHint(hint: RenderHint): boolean {
  return CHART_HINTS.includes(hint);
}

// The minimum number of comparable points for a chart. Below this the section
// falls back to its table.
export const MIN_CHART_POINTS = 3;

export interface ChartPoint {
  label: string;
  value: number;
  // The cell the point came from, so a click on the chart can open its evidence.
  cell: Cell;
}

export interface TimeseriesChartData {
  kind: "timeseries";
  variant: "bar" | "line";
  points: ChartPoint[];
}

export interface BreakdownChartData {
  kind: "breakdown";
  points: ChartPoint[];
}

export type ChartData = TimeseriesChartData | BreakdownChartData;

export interface ChartResult {
  valid: boolean;
  data: ChartData | null;
}

const INVALID: ChartResult = { valid: false, data: null };

function buildTimeseries(
  section: SectionWithCells,
  variant: "bar" | "line",
): ChartResult {
  const points: ChartPoint[] = [];
  for (const cell of section.cells) {
    const value = numericValue(cell);
    if (value === null) {
      continue;
    }
    if (cell.period === null || cell.period.trim() === "") {
      continue;
    }
    points.push({ label: cell.period.trim(), value, cell });
  }
  if (points.length < MIN_CHART_POINTS) {
    return INVALID;
  }
  return { valid: true, data: { kind: "timeseries", variant, points } };
}

function buildBreakdown(section: SectionWithCells): ChartResult {
  // A breakdown row pairs a label cell with a numeric value cell. Group the
  // section's cells by row, take the numeric cell as the slice value and a
  // non-numeric sibling (or the value cell's column key) as the slice label.
  const byRow = new Map<number, Cell[]>();
  for (const cell of section.cells) {
    const list = byRow.get(cell.row_idx) ?? [];
    list.push(cell);
    byRow.set(cell.row_idx, list);
  }

  const rows = Array.from(byRow.entries()).sort((a, b) => a[0] - b[0]);
  const points: ChartPoint[] = [];
  for (const [rowIdx, cells] of rows) {
    const valueCell = cells.find((cell) => numericValue(cell) !== null);
    if (valueCell === undefined) {
      continue;
    }
    const value = numericValue(valueCell);
    if (value === null) {
      continue;
    }
    const labelCell = cells.find(
      (cell) =>
        cell !== valueCell &&
        numericValue(cell) === null &&
        (cell.value_raw ?? "").trim() !== "",
    );
    const rawLabel =
      labelCell?.value_raw ?? valueCell.col_key ?? `Item ${rowIdx + 1}`;
    const label = rawLabel.trim() === "" ? `Item ${rowIdx + 1}` : rawLabel.trim();
    points.push({ label, value, cell: valueCell });
  }

  if (points.length < MIN_CHART_POINTS) {
    return INVALID;
  }
  return { valid: true, data: { kind: "breakdown", points } };
}

export function buildChartData(section: SectionWithCells): ChartResult {
  switch (section.render_hint) {
    case "timeseries_bar":
      return buildTimeseries(section, "bar");
    case "timeseries_line":
      return buildTimeseries(section, "line");
    case "breakdown_pie":
      return buildBreakdown(section);
    default:
      return INVALID;
  }
}
