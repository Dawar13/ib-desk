// Pure-logic gates for the sheet helpers. No DOM, no secret. These guard the
// trust-bearing logic: confidence banding, the value display rule, the chart
// safe-fallback decision (three-point rule), table shaping, and the gradual-reveal
// state machine.

import { describe, expect, it } from "vitest";
import type { SectionWithCells } from "@ib-desk/shared";
import {
  allHintsSheet,
  invalidChartSheet,
} from "@/components/sheet/fixtures";
import { categoryAccent } from "@/lib/sheet/category";
import {
  buildChartData,
  isChartHint,
  MIN_CHART_POINTS,
} from "@/lib/sheet/chart";
import {
  CONFIDENCE_LEGEND,
  confidenceBand,
  confidenceStyle,
} from "@/lib/sheet/confidence";
import { humanizeKey } from "@/lib/sheet/key";
import { INITIAL_REVEAL, revealReducer } from "@/lib/sheet/reveal";
import { tableColumns, tableRows, VALUE_COLUMN } from "@/lib/sheet/table";
import { cellDisplayValue, cellFieldLabel, NO_VALUE, numericValue } from "@/lib/sheet/value";

function byHint(hint: SectionWithCells["render_hint"]): SectionWithCells {
  const found = allHintsSheet.sections.find((s) => s.render_hint === hint);
  if (!found) {
    throw new Error(`fixture missing a ${hint} section`);
  }
  return found;
}

describe("confidence bands", () => {
  it("maps scores to bands at the documented thresholds", () => {
    expect(confidenceBand(0.95)).toBe("high");
    expect(confidenceBand(0.8)).toBe("high");
    expect(confidenceBand(0.79)).toBe("medium");
    expect(confidenceBand(0.5)).toBe("medium");
    expect(confidenceBand(0.49)).toBe("low");
    expect(confidenceBand(0)).toBe("low");
  });

  it("treats a missing or non-numeric score as unscored, never guessed", () => {
    expect(confidenceBand(null)).toBe("unknown");
    expect(confidenceBand(undefined)).toBe("unknown");
    expect(confidenceBand(Number.NaN)).toBe("unknown");
  });

  it("exposes a four-band legend that matches the styles", () => {
    expect(CONFIDENCE_LEGEND.map((s) => s.band)).toEqual([
      "high",
      "medium",
      "low",
      "unknown",
    ]);
    expect(confidenceStyle(0.95).color).toBe(CONFIDENCE_LEGEND[0].color);
  });
});

describe("value display", () => {
  it("prefers the value as written and falls back cleanly", () => {
    expect(
      cellDisplayValue({ ...baseCell(), value_raw: "$18M", value_norm: "18000000" }),
    ).toBe("$18M");
    expect(
      cellDisplayValue({ ...baseCell(), value_raw: null, value_norm: "18000000" }),
    ).toBe("18000000");
    expect(
      cellDisplayValue({ ...baseCell(), value_raw: null, value_norm: null }),
    ).toBe(NO_VALUE);
  });

  it("parses numeric values from value_norm only", () => {
    expect(numericValue({ ...baseCell(), value_norm: "18000000" })).toBe(18000000);
    expect(numericValue({ ...baseCell(), value_norm: "Rotterdam" })).toBeNull();
    expect(numericValue({ ...baseCell(), value_norm: null })).toBeNull();
  });

  it("labels a field by column key or row position", () => {
    expect(cellFieldLabel({ ...baseCell(), col_key: "Founded" })).toBe("Founded");
    expect(cellFieldLabel({ ...baseCell(), col_key: null, row_idx: 2 })).toBe("Row 3");
  });
});

describe("chart safe fallback (three-point rule)", () => {
  it("knows which hints are charts", () => {
    expect(isChartHint("timeseries_bar")).toBe(true);
    expect(isChartHint("breakdown_pie")).toBe(true);
    expect(isChartHint("keyvalue")).toBe(false);
    expect(MIN_CHART_POINTS).toBe(3);
  });

  it("builds a valid timeseries from three periodic numeric points", () => {
    const result = buildChartData(byHint("timeseries_bar"));
    expect(result.valid).toBe(true);
    expect(result.data?.kind).toBe("timeseries");
    expect(result.data && result.data.kind === "timeseries" && result.data.points.length).toBe(3);
  });

  it("builds a valid breakdown with labeled slices", () => {
    const result = buildChartData(byHint("breakdown_pie"));
    expect(result.valid).toBe(true);
    expect(result.data?.kind).toBe("breakdown");
    const labels =
      result.data && result.data.kind === "breakdown"
        ? result.data.points.map((p) => p.label)
        : [];
    expect(labels).toEqual(["EMEA", "Americas", "APAC"]);
  });

  it("reports invalid when there are fewer than three comparable points", () => {
    const result = buildChartData(invalidChartSheet.sections[0]);
    expect(result.valid).toBe(false);
    expect(result.data).toBeNull();
  });
});

describe("table shaping", () => {
  it("uses declared columns and groups cells by row", () => {
    const table = byHint("table");
    expect(tableColumns(table).map((c) => c.key)).toEqual(["region", "share"]);
    const rows = tableRows(table);
    expect(rows.length).toBe(2);
    expect(rows[0].cells.region?.value_raw).toBe("EMEA");
    expect(rows[0].cells.share?.value_raw).toBe("45%");
  });

  it("falls back to a single value column when there are no column keys", () => {
    const noColumns: SectionWithCells = {
      ...byHint("chips"),
      columns: null,
    };
    expect(tableColumns(noColumns)).toEqual([{ key: VALUE_COLUMN, label: "Value" }]);
  });
});

describe("category accents", () => {
  it("is deterministic and neutral for a missing category", () => {
    expect(categoryAccent("Market")).toBe(categoryAccent("Market"));
    expect(categoryAccent(null)).toBe(categoryAccent(undefined));
    expect(typeof categoryAccent("Capital")).toBe("string");
  });
});

describe("humanize key", () => {
  it("turns a section key into a readable label", () => {
    expect(humanizeKey("market_size")).toBe("Market size");
    expect(humanizeKey("key-players")).toBe("Key players");
  });
});

describe("reveal reducer", () => {
  it("records discovered sections and classification from the discovery frame", () => {
    const state = revealReducer(INITIAL_REVEAL, {
      stage: "discovery",
      message: "discovery complete",
      payload: {
        doc_type: "market_overview",
        primary_topic: "Mid-market freight software",
        sections: ["market_size", "key_players", "regulation"],
      },
    });
    expect(state.docType).toBe("market_overview");
    expect(state.primaryTopic).toBe("Mid-market freight software");
    expect(state.discovered.map((s) => s.key)).toEqual([
      "market_size",
      "key_players",
      "regulation",
    ]);
    expect(state.completed).toEqual([]);
  });

  it("marks sections complete and adopts their real labels, in arrival order", () => {
    let state = revealReducer(INITIAL_REVEAL, {
      stage: "discovery",
      message: null,
      payload: { sections: ["a", "b", "c"] },
    });
    state = revealReducer(state, {
      stage: "section",
      message: null,
      payload: { key: "a", label: "Alpha", sort: 0, kind: "scalar", cell_count: 2 },
    });
    state = revealReducer(state, {
      stage: "section",
      message: null,
      payload: { key: "c", label: "Charlie", sort: 2, kind: "list", cell_count: 1 },
    });
    expect(state.completed).toEqual(["a", "c"]);
    expect(state.discovered.find((s) => s.key === "a")?.label).toBe("Alpha");
  });

  it("ignores pass-level frames, degrading to a coarser reveal", () => {
    const start = revealReducer(INITIAL_REVEAL, {
      stage: "discovery",
      message: null,
      payload: { sections: ["a"] },
    });
    const after = revealReducer(start, {
      stage: "verification",
      message: "verification started",
      payload: null,
    });
    expect(after).toEqual(start);
  });
});

// A minimal cell for the value-helper tests.
function baseCell() {
  return {
    id: "c",
    section_id: "s",
    row_idx: 0,
    col_key: null,
    value_raw: null,
    value_norm: null,
    unit: null,
    period: null,
    source_snippet: "SAMPLE.",
    char_start: null,
    char_end: null,
    confidence: null,
  };
}
