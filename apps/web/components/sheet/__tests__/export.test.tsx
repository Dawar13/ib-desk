// Deterministic, secret-free gates for the Phase 4 download control and the
// document-preview edge cases. The styled export itself is asserted by the
// service test suite (it reads the generated workbook back); here we cover the
// web contract: the download is disabled until the sheet is done, then offers
// the xlsx and csv, and the preview degrades cleanly on missing or invalid input.

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DocumentPreview from "@/components/sheet/DocumentPreview";
import DownloadControls from "@/components/sheet/DownloadControls";

describe("download control", () => {
  it("is disabled until the sheet is done", () => {
    render(<DownloadControls sheetId="abc" disabled={true} />);
    expect(document.querySelector('[data-download-disabled="true"]')).not.toBeNull();
    expect(document.querySelector('[data-download="xlsx"]')).toBeNull();
  });

  it("offers a styled xlsx and a csv download once enabled", () => {
    render(<DownloadControls sheetId="abc" disabled={false} />);

    const xlsx = document.querySelector('[data-download="xlsx"]');
    const csv = document.querySelector('[data-download="csv"]');
    expect(xlsx).not.toBeNull();
    expect(xlsx?.getAttribute("href")).toContain("/v1/sheets/abc/export?format=xlsx");
    expect(csv).not.toBeNull();
    expect(csv?.getAttribute("href")).toContain("format=csv");
  });
});

describe("document preview robustness", () => {
  it("shows a graceful note when there is no document text", () => {
    render(<DocumentPreview text={null} charStart={0} charEnd={4} />);
    expect(document.querySelector('[data-preview-fallback="true"]')).not.toBeNull();
    expect(document.querySelector('[data-evidence-highlight="true"]')).toBeNull();
  });

  it("shows the text without a highlight when the span is out of range", () => {
    render(<DocumentPreview text="Short text." charStart={50} charEnd={60} />);
    expect(document.querySelector('[data-preview-fallback="true"]')).not.toBeNull();
    expect(document.querySelector('[data-evidence-highlight="true"]')).toBeNull();
    expect(document.body.textContent).toContain("Short text.");
  });

  it("highlights the exact span when the offsets resolve", () => {
    render(<DocumentPreview text="Founded in 2016 here." charStart={11} charEnd={15} />);
    const mark = document.querySelector('[data-evidence-highlight="true"]');
    expect(mark).not.toBeNull();
    expect(mark?.textContent).toBe("2016");
  });
});
