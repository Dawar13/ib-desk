// SAMPLE DATA for the deterministic UI tests.
//
// Every value below is invented to exercise the renderers and must never be shown
// as real research. These payloads mirror the GET /v1/sheets/{id} contract. They
// deliberately include sections that are not a company template (a market
// document with market-size, players, regulation, and regional-breakdown
// sections) to prove the UI renders by render hint alone, assuming nothing about
// which sections exist.

import type {
  Cell,
  ColumnDef,
  SectionWithCells,
  Sheet,
  SheetPayload,
} from "@ib-desk/shared";

let seq = 0;
function nextId(prefix: string): string {
  seq += 1;
  return `${prefix}-${seq}`;
}

function cell(over: Partial<Cell> = {}): Cell {
  return {
    id: nextId("cell"),
    section_id: "section",
    row_idx: 0,
    col_key: null,
    value_raw: null,
    value_norm: null,
    unit: null,
    period: null,
    source_snippet: "SAMPLE: supporting sentence for this value.",
    char_start: null,
    char_end: null,
    confidence: null,
    ...over,
  };
}

type SectionInput = Partial<SectionWithCells> &
  Pick<SectionWithCells, "key" | "label" | "kind" | "render_hint" | "cells">;

function section(input: SectionInput): SectionWithCells {
  return {
    id: nextId("section"),
    sheet_id: "sheet-sample",
    category: null,
    columns: null,
    sort: 0,
    confidence: null,
    ...input,
  };
}

function payload(
  sections: SectionWithCells[],
  over: Partial<Sheet> = {},
): SheetPayload {
  const ordered = sections.map((entry, index) => ({ ...entry, sort: index }));
  const sheet: Sheet = {
    id: "sheet-sample",
    document_id: "doc-sample",
    title: "Sample subject (sample)",
    status: "done",
    field_count: ordered.reduce((total, entry) => total + entry.cells.length, 0),
    cost_usd: 0,
    created_at: "2026-01-01T00:00:00Z",
    ...over,
  };
  return { sheet, sections: ordered };
}

const SHARE_COLUMNS: ColumnDef[] = [
  { key: "region", label: "Region" },
  { key: "share", label: "Share" },
];

// One section per render hint, each with valid data.
export const allHintsSheet: SheetPayload = payload([
  section({
    key: "overview",
    label: "Overview",
    kind: "scalar",
    render_hint: "keyvalue",
    category: "Overview",
    cells: [
      cell({
        col_key: "Founded",
        value_raw: "2016",
        value_norm: "2016",
        confidence: 0.95,
        source_snippet: "SAMPLE: Northwind was founded in 2016 in Rotterdam.",
      }),
      cell({
        col_key: "Headquarters",
        value_raw: "Rotterdam",
        value_norm: "Rotterdam",
        confidence: 0.82,
        source_snippet: "SAMPLE: Its headquarters is in Rotterdam.",
      }),
    ],
  }),
  section({
    key: "investors",
    label: "Investors",
    kind: "list",
    render_hint: "chips",
    category: "Capital",
    cells: [
      cell({ value_raw: "Harbor Lane Ventures", confidence: 0.7 }),
      cell({ value_raw: "Polder Capital", confidence: 0.66, row_idx: 1 }),
    ],
  }),
  section({
    key: "regional_share",
    label: "Revenue by region",
    kind: "table",
    render_hint: "table",
    category: "Financials",
    columns: SHARE_COLUMNS,
    cells: [
      cell({ row_idx: 0, col_key: "region", value_raw: "EMEA", value_norm: "EMEA", confidence: 0.8 }),
      cell({ row_idx: 0, col_key: "share", value_raw: "45%", value_norm: "45", unit: "percent", confidence: 0.78 }),
      cell({ row_idx: 1, col_key: "region", value_raw: "Americas", value_norm: "Americas", confidence: 0.8 }),
      cell({ row_idx: 1, col_key: "share", value_raw: "35%", value_norm: "35", unit: "percent", confidence: 0.74 }),
    ],
  }),
  section({
    key: "arr_history",
    label: "ARR history",
    kind: "timeseries",
    render_hint: "timeseries_bar",
    category: "Financials",
    cells: [
      cell({ row_idx: 0, col_key: "arr", period: "2021", value_raw: "$6M", value_norm: "6000000", unit: "USD", confidence: 0.7 }),
      cell({ row_idx: 1, col_key: "arr", period: "2022", value_raw: "$9M", value_norm: "9000000", unit: "USD", confidence: 0.72 }),
      cell({ row_idx: 2, col_key: "arr", period: "2023", value_raw: "$18M", value_norm: "18000000", unit: "USD", confidence: 0.8 }),
    ],
  }),
  section({
    key: "headcount_history",
    label: "Headcount history",
    kind: "timeseries",
    render_hint: "timeseries_line",
    category: "People",
    cells: [
      cell({ row_idx: 0, col_key: "headcount", period: "2021", value_raw: "90", value_norm: "90", confidence: 0.6 }),
      cell({ row_idx: 1, col_key: "headcount", period: "2022", value_raw: "140", value_norm: "140", confidence: 0.6 }),
      cell({ row_idx: 2, col_key: "headcount", period: "2023", value_raw: "210", value_norm: "210", confidence: 0.65 }),
    ],
  }),
  section({
    key: "revenue_split",
    label: "Revenue split",
    kind: "table",
    render_hint: "breakdown_pie",
    category: "Financials",
    columns: SHARE_COLUMNS,
    cells: [
      cell({ row_idx: 0, col_key: "region", value_raw: "EMEA", value_norm: "EMEA", confidence: 0.8 }),
      cell({ row_idx: 0, col_key: "share", value_raw: "45%", value_norm: "45", unit: "percent", confidence: 0.8 }),
      cell({ row_idx: 1, col_key: "region", value_raw: "Americas", value_norm: "Americas", confidence: 0.8 }),
      cell({ row_idx: 1, col_key: "share", value_raw: "35%", value_norm: "35", unit: "percent", confidence: 0.78 }),
      cell({ row_idx: 2, col_key: "region", value_raw: "APAC", value_norm: "APAC", confidence: 0.8 }),
      cell({ row_idx: 2, col_key: "share", value_raw: "20%", value_norm: "20", unit: "percent", confidence: 0.7 }),
    ],
  }),
  section({
    key: "why_now",
    label: "Why now",
    kind: "longtext",
    render_hint: "longtext",
    category: "Thesis",
    cells: [
      cell({
        value_raw:
          "SAMPLE: A generational handover among operators and rising rate volatility are pulling mid-market firms toward modern software faster than before.",
        value_norm:
          "A generational handover among operators and rising rate volatility are pulling mid-market firms toward modern software faster than before.",
        confidence: 0.55,
        source_snippet:
          "SAMPLE: The combination of a generational handover and rate volatility is pulling firms toward modern software.",
      }),
    ],
  }),
]);

// A market document. Its sections are not a company template, which is the point:
// the same renderers must display them with no code change.
export const marketSheet: SheetPayload = payload(
  [
    section({
      key: "market_size",
      label: "Market size",
      kind: "timeseries",
      render_hint: "timeseries_bar",
      category: "Market",
      cells: [
        cell({ row_idx: 0, period: "2021", value_raw: "$8B", value_norm: "8000000000", unit: "USD", confidence: 0.7 }),
        cell({ row_idx: 1, period: "2022", value_raw: "$10B", value_norm: "10000000000", unit: "USD", confidence: 0.72 }),
        cell({ row_idx: 2, period: "2023", value_raw: "$12B", value_norm: "12000000000", unit: "USD", confidence: 0.75 }),
      ],
    }),
    section({
      key: "key_players",
      label: "Key players",
      kind: "list",
      render_hint: "chips",
      category: "Competition",
      cells: [
        cell({ value_raw: "Acme Freight (sample)", confidence: 0.6 }),
        cell({ value_raw: "Polder Systems (sample)", confidence: 0.6, row_idx: 1 }),
        cell({ value_raw: "Harbor Software (sample)", confidence: 0.55, row_idx: 2 }),
      ],
    }),
    section({
      key: "regulation",
      label: "Regulation",
      kind: "longtext",
      render_hint: "longtext",
      category: "Risk",
      cells: [
        cell({
          value_raw:
            "SAMPLE: New customs digitization rules raise the bar for compliance and favor vendors with built-in reporting.",
          value_norm:
            "New customs digitization rules raise the bar for compliance and favor vendors with built-in reporting.",
          confidence: 0.5,
          source_snippet:
            "SAMPLE: New customs digitization rules favor vendors with built-in reporting.",
        }),
      ],
    }),
    section({
      key: "regional_breakdown",
      label: "Regional breakdown",
      kind: "table",
      render_hint: "breakdown_pie",
      category: "Market",
      columns: SHARE_COLUMNS,
      cells: [
        cell({ row_idx: 0, col_key: "region", value_raw: "EMEA", value_norm: "EMEA", confidence: 0.7 }),
        cell({ row_idx: 0, col_key: "share", value_raw: "50%", value_norm: "50", unit: "percent", confidence: 0.7 }),
        cell({ row_idx: 1, col_key: "region", value_raw: "Americas", value_norm: "Americas", confidence: 0.7 }),
        cell({ row_idx: 1, col_key: "share", value_raw: "30%", value_norm: "30", unit: "percent", confidence: 0.68 }),
        cell({ row_idx: 2, col_key: "region", value_raw: "APAC", value_norm: "APAC", confidence: 0.7 }),
        cell({ row_idx: 2, col_key: "share", value_raw: "20%", value_norm: "20", unit: "percent", confidence: 0.66 }),
      ],
    }),
    section({
      key: "market_summary",
      label: "Market summary",
      kind: "scalar",
      render_hint: "keyvalue",
      category: "Market",
      cells: [
        cell({ col_key: "CAGR", value_raw: "14%", value_norm: "14", unit: "percent", confidence: 0.6 }),
        cell({ col_key: "Geography", value_raw: "Global", value_norm: "Global", confidence: 0.8 }),
      ],
    }),
    section({
      key: "comparable_deals",
      label: "Comparable deals",
      kind: "table",
      render_hint: "table",
      category: "Deals",
      columns: [
        { key: "target", label: "Target" },
        { key: "multiple", label: "EV/Revenue" },
      ],
      cells: [
        cell({ row_idx: 0, col_key: "target", value_raw: "Cargo Co (sample)", value_norm: "Cargo Co (sample)", confidence: 0.6 }),
        cell({ row_idx: 0, col_key: "multiple", value_raw: "6.0x", value_norm: "6", confidence: 0.55 }),
        cell({ row_idx: 1, col_key: "target", value_raw: "Freight Inc (sample)", value_norm: "Freight Inc (sample)", confidence: 0.6 }),
        cell({ row_idx: 1, col_key: "multiple", value_raw: "5.2x", value_norm: "5.2", confidence: 0.55 }),
      ],
    }),
  ],
  { title: "Mid-market freight software (sample)", document_id: "doc-market" },
);

// Distinct confidence bands in one section, for the confidence-marker gate.
export const confidenceSheet: SheetPayload = payload([
  section({
    key: "scores",
    label: "Scores",
    kind: "scalar",
    render_hint: "keyvalue",
    cells: [
      cell({ col_key: "Alpha", value_raw: "Alpha", value_norm: "Alpha", confidence: 0.95 }),
      cell({ col_key: "Bravo", value_raw: "Bravo", value_norm: "Bravo", confidence: 0.6 }),
      cell({ col_key: "Charlie", value_raw: "Charlie", value_norm: "Charlie", confidence: 0.3 }),
      cell({ col_key: "Delta", value_raw: "Delta", value_norm: "Delta", confidence: null }),
    ],
  }),
]);

// A chart-hinted section whose data cannot form a sound chart (only two points),
// for the safe-fallback gate.
export const invalidChartSheet: SheetPayload = payload([
  section({
    key: "sparse_series",
    label: "Sparse series",
    kind: "timeseries",
    render_hint: "timeseries_bar",
    category: "Financials",
    cells: [
      cell({ row_idx: 0, col_key: "arr", period: "2022", value_raw: "$9M", value_norm: "9000000", confidence: 0.6 }),
      cell({ row_idx: 1, col_key: "arr", period: "2023", value_raw: "$18M", value_norm: "18000000", confidence: 0.6 }),
    ],
  }),
]);

// A breakdown-hinted section with only two slices, for the breakdown safe-fallback gate.
export const invalidBreakdownSheet: SheetPayload = payload([
  section({
    key: "thin_split",
    label: "Thin split",
    kind: "table",
    render_hint: "breakdown_pie",
    category: "Financials",
    columns: SHARE_COLUMNS,
    cells: [
      cell({ row_idx: 0, col_key: "region", value_raw: "EMEA", value_norm: "EMEA", confidence: 0.7 }),
      cell({ row_idx: 0, col_key: "share", value_raw: "60%", value_norm: "60", unit: "percent", confidence: 0.7 }),
      cell({ row_idx: 1, col_key: "region", value_raw: "Americas", value_norm: "Americas", confidence: 0.7 }),
      cell({ row_idx: 1, col_key: "share", value_raw: "40%", value_norm: "40", unit: "percent", confidence: 0.7 }),
    ],
  }),
]);

// A table with a row missing one column's cell and a cell whose column key was
// not declared. Guards the no-fabrication placeholder and the column-union rule:
// a missing cell shows the neutral placeholder, and a grounded cell with an
// undeclared key is still rendered rather than silently dropped.
export const sparseTableSheet: SheetPayload = payload([
  section({
    key: "metrics",
    label: "Metrics",
    kind: "table",
    render_hint: "table",
    category: "Financials",
    columns: [
      { key: "metric", label: "Metric" },
      { key: "value", label: "Value" },
    ],
    cells: [
      cell({ row_idx: 0, col_key: "metric", value_raw: "Revenue", value_norm: "Revenue", confidence: 0.8 }),
      cell({ row_idx: 0, col_key: "value", value_raw: "$10M", value_norm: "10000000", confidence: 0.8 }),
      // Row 1 has no "value" cell: the value column shows the neutral placeholder.
      cell({ row_idx: 1, col_key: "metric", value_raw: "EBITDA", value_norm: "EBITDA", confidence: 0.7 }),
      // Row 2 carries a cell whose column key was not declared: it must still show.
      cell({ row_idx: 2, col_key: "metric", value_raw: "Note", value_norm: "Note", confidence: 0.7 }),
      cell({
        row_idx: 2,
        col_key: "remark",
        value_raw: "Strong demand (sample)",
        value_norm: "Strong demand (sample)",
        confidence: 0.6,
      }),
    ],
  }),
]);

// An empty sheet (no grounded sections), for the empty-state gate.
export const emptySheet: SheetPayload = payload([]);
