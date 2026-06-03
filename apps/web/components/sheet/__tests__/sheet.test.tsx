// Deterministic, secret-free UI gates for the rendered sheet, against fixture
// payloads. Covers the headline schema-agnostic test, render-hint coverage,
// confidence markers, click-to-evidence, and charts with their safe fallback.

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DocType, SheetPayload } from "@ib-desk/shared";
import Sheet from "@/components/sheet/Sheet";
import {
  allHintsSheet,
  confidenceSheet,
  emptySheet,
  EVIDENCE_DOC_TEXT,
  invalidBreakdownSheet,
  invalidChartSheet,
  marketSheet,
  spanSheet,
  sparseTableSheet,
} from "@/components/sheet/fixtures";

// recharts needs layout measurement jsdom lacks; the stub renders the chart
// wrapper without throwing so the structure can be asserted.
vi.mock("recharts");

function renderSheet(
  payload: SheetPayload,
  subject = "Sample subject",
  docType: DocType | null = null,
) {
  return render(
    <Sheet
      subject={subject}
      docType={docType}
      sections={payload.sections}
      fieldCount={payload.sheet.field_count}
    />,
  );
}

function card(hint: string): HTMLElement {
  const node = document.querySelector(`[data-render-hint="${hint}"]`);
  if (!node) {
    throw new Error(`no section card for render hint ${hint}`);
  }
  return node as HTMLElement;
}

describe("schema-driven rendering (headline)", () => {
  it("renders a non-company market schema entirely by render hint", () => {
    renderSheet(marketSheet, "Mid-market freight software", "market_overview");

    for (const section of marketSheet.sections) {
      expect(
        screen.getByRole("heading", { name: section.label }),
      ).toBeInTheDocument();
    }

    // Every section is present and rendered by its hint, not a business concept.
    expect(document.querySelectorAll("[data-section-key]").length).toBe(
      marketSheet.sections.length,
    );
    expect(card("breakdown_pie").getAttribute("data-section-key")).toBe(
      "regional_breakdown",
    );
    expect(card("longtext").getAttribute("data-section-key")).toBe("regulation");

    // The primary subject and the doc-type classification chip render.
    expect(
      screen.getByRole("heading", { name: "Mid-market freight software" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Market overview")).toBeInTheDocument();
  });

  it("renders a section by its render hint regardless of its business meaning", () => {
    // A section whose key and label read like a chip list, but the engine typed
    // it as a table, must render as a table. This proves dispatch is on
    // render_hint alone, never on what the section means.
    const investors = allHintsSheet.sections.find((s) => s.key === "investors");
    if (!investors) {
      throw new Error("fixture missing the investors section");
    }
    const asTable = { ...investors, render_hint: "table" as const };
    render(
      <Sheet
        subject="X"
        docType={null}
        sections={[asTable]}
        fieldCount={asTable.cells.length}
      />,
    );
    const node = document.querySelector('[data-section-key="investors"]') as HTMLElement;
    expect(node.getAttribute("data-render-hint")).toBe("table");
    expect(within(node).getByRole("table")).toBeInTheDocument();
    expect(within(node).getByText("Harbor Lane Ventures")).toBeInTheDocument();
  });
});

describe("render-hint coverage", () => {
  it("renders each of the seven render hints correctly", () => {
    renderSheet(allHintsSheet);

    expect(within(card("keyvalue")).getByText("Founded")).toBeInTheDocument();
    expect(
      within(card("chips")).getByText("Harbor Lane Ventures"),
    ).toBeInTheDocument();
    expect(within(card("table")).getByRole("table")).toBeInTheDocument();
    expect(within(card("table")).getByText("Region")).toBeInTheDocument();
    expect(card("timeseries_bar").querySelector('[data-chart="timeseries_bar"]')).toBeTruthy();
    expect(card("timeseries_line").querySelector('[data-chart="timeseries_line"]')).toBeTruthy();
    expect(card("breakdown_pie").querySelector('[data-chart="breakdown_pie"]')).toBeTruthy();
    expect(
      within(card("longtext")).getByText(/generational handover/),
    ).toBeInTheDocument();
  });
});

describe("confidence markers", () => {
  it("shows the correct band on each value and a matching legend", () => {
    renderSheet(confidenceSheet);

    expect(screen.getByRole("button", { name: /Alpha/ })).toHaveAttribute(
      "data-confidence-band",
      "high",
    );
    expect(screen.getByRole("button", { name: /Bravo/ })).toHaveAttribute(
      "data-confidence-band",
      "medium",
    );
    expect(screen.getByRole("button", { name: /Charlie/ })).toHaveAttribute(
      "data-confidence-band",
      "low",
    );
    expect(screen.getByRole("button", { name: /Delta/ })).toHaveAttribute(
      "data-confidence-band",
      "unknown",
    );

    for (const band of ["high", "medium", "low", "unknown"]) {
      expect(document.querySelector(`[data-legend-band="${band}"]`)).toBeTruthy();
    }

    // The dot color on a value matches its legend entry, so the legend cannot
    // drift from the markers.
    const valueDot = screen
      .getByRole("button", { name: /Alpha/ })
      .querySelector('[data-confidence-band="high"]') as HTMLElement;
    const legendDot = document.querySelector(
      '[data-legend-band="high"] span',
    ) as HTMLElement;
    expect(valueDot.style.backgroundColor).not.toBe("");
    expect(valueDot.style.backgroundColor).toBe(legendDot.style.backgroundColor);
  });
});

describe("no fabrication in the grid", () => {
  it("shows a neutral placeholder for a missing cell and never drops a grounded cell", () => {
    renderSheet(sparseTableSheet);
    const grid = card("table");

    // A grounded cell whose column key was not declared still renders.
    expect(within(grid).getByText("Strong demand (sample)")).toBeInTheDocument();
    // The row missing a value shows the neutral placeholder, not a guess.
    expect(within(grid).getAllByText("-").length).toBeGreaterThan(0);
  });
});

describe("empty sheet", () => {
  it("renders a clear no-sections message", () => {
    renderSheet(emptySheet);
    expect(
      screen.getByText(/produced no grounded sections/),
    ).toBeInTheDocument();
  });
});

describe("click-to-evidence", () => {
  it("opens a value's source sentence and closes cleanly", async () => {
    const user = userEvent.setup();
    renderSheet(allHintsSheet);

    await user.click(screen.getByRole("button", { name: /2016/ }));

    const dialog = screen.getByRole("dialog", { name: "Source evidence" });
    expect(
      within(dialog).getByText(/Northwind was founded in 2016 in Rotterdam/),
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Overview")).toBeInTheDocument();
    expect(within(dialog).getByText("Founded")).toBeInTheDocument();
    expect(within(dialog).getByText(/High/)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Close evidence" }));
    expect(
      screen.queryByText(/Northwind was founded in 2016 in Rotterdam/),
    ).not.toBeInTheDocument();
  });
});

describe("in-document evidence highlight", () => {
  function renderWithText() {
    return render(
      <Sheet
        subject="Northwind"
        docType={null}
        sections={spanSheet.sections}
        fieldCount={spanSheet.sheet.field_count}
        documentText={EVIDENCE_DOC_TEXT}
      />,
    );
  }

  it("highlights the value's span inside the document preview on click", async () => {
    const user = userEvent.setup();
    renderWithText();

    await user.click(screen.getByRole("button", { name: /2016/ }));
    const dialog = screen.getByRole("dialog", { name: "Source evidence" });

    // The span is highlighted at the right place, in context, not just echoed.
    const mark = dialog.querySelector('[data-evidence-highlight="true"]');
    expect(mark).not.toBeNull();
    expect(mark).toHaveTextContent("2016");
    const preview = dialog.querySelector('[data-document-preview="true"]');
    expect(preview?.textContent).toContain("Rotterdam");
  });

  it("degrades to the sentence, without breaking, when a span cannot resolve", async () => {
    const user = userEvent.setup();
    renderWithText();

    await user.click(screen.getByRole("button", { name: /Rotterdam/ }));
    const dialog = screen.getByRole("dialog", { name: "Source evidence" });

    // No highlight, a graceful fallback note, and the stored sentence still shown.
    expect(dialog.querySelector('[data-evidence-highlight="true"]')).toBeNull();
    expect(dialog.querySelector('[data-preview-fallback="true"]')).not.toBeNull();
    expect(
      within(dialog).getByText(/Its headquarters is in Rotterdam/),
    ).toBeInTheDocument();
  });
});

describe("charts and safe fallback", () => {
  it("shows the chart with a working Chart/Table toggle", async () => {
    const user = userEvent.setup();
    renderSheet(allHintsSheet);
    const bar = card("timeseries_bar");

    expect(bar.querySelector('[data-chart="timeseries_bar"]')).toBeTruthy();
    expect(within(bar).queryByRole("table")).toBeNull();

    await user.click(within(bar).getByRole("button", { name: "Table" }));
    expect(within(bar).getByRole("table")).toBeInTheDocument();
    expect(bar.querySelector('[data-chart="timeseries_bar"]')).toBeFalsy();
  });

  it("falls back to the table when the data cannot form a chart, without crashing", () => {
    renderSheet(invalidChartSheet);
    const sparse = card("timeseries_bar");

    expect(within(sparse).queryByRole("button", { name: "Chart" })).toBeNull();
    expect(sparse.querySelector('[data-chart-fallback="true"]')).toBeTruthy();
    expect(within(sparse).getByRole("table")).toBeInTheDocument();
  });

  it("falls back to the table for a breakdown with too few slices", () => {
    renderSheet(invalidBreakdownSheet);
    const sparse = card("breakdown_pie");

    expect(within(sparse).queryByRole("button", { name: "Chart" })).toBeNull();
    expect(sparse.querySelector('[data-chart-fallback="true"]')).toBeTruthy();
    expect(within(sparse).getByRole("table")).toBeInTheDocument();
  });
});
