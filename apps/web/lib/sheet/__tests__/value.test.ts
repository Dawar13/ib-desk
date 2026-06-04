// Gate for value rendering uniformity: monospace is used only for short, genuinely
// numeric values, so descriptive sentences (even ones containing a number) render
// in the regular font and the sheet does not switch fonts cell to cell.

import { describe, expect, it } from "vitest";
import type { Cell } from "@ib-desk/shared";
import { valueVariant } from "@/lib/sheet/value";

function cell(over: Partial<Cell>): Cell {
  return {
    id: "c",
    section_id: "s",
    row_idx: 0,
    col_key: null,
    value_raw: null,
    value_norm: null,
    unit: null,
    period: null,
    source_snippet: "s",
    char_start: null,
    char_end: null,
    confidence: null,
    ...over,
  };
}

describe("valueVariant", () => {
  it("uses monospace for short numeric values", () => {
    expect(valueVariant(cell({ value_raw: "2016", value_norm: "2016" }))).toBe("mono");
    expect(valueVariant(cell({ value_raw: "45%", value_norm: "45" }))).toBe("mono");
    expect(valueVariant(cell({ value_raw: "$24M", value_norm: "24000000" }))).toBe("mono");
  });

  it("uses plain for non-numeric text", () => {
    expect(
      valueVariant(cell({ value_raw: "Elevation Capital", value_norm: "Elevation Capital" })),
    ).toBe("plain");
  });

  it("uses plain for a long value even if it normalizes to a number", () => {
    const long = "Positioned category-creating program solving a 10.5M job gap";
    expect(valueVariant(cell({ value_raw: long, value_norm: "10.5" }))).toBe("plain");
  });
})
