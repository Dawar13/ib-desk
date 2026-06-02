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
  invalidChartSheet,
  marketSheet,
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

    expect(document.querySelector('[data-legend-band="high"]')).toBeTruthy();
    expect(document.querySelector('[data-legend-band="unknown"]')).toBeTruthy();
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
});
