// Sidebar layout contract (visual restyle gate). Asserts the new arrangement: the
// Documents header, then the decorative sky banner (empty alt, cover fit), then
// the document list, and that the empty state still renders below the banner when
// there are no documents. A failure means the new arrangement broke the list or
// the empty state.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DocumentListItem } from "@ib-desk/shared";
import DocumentSidebar from "@/components/DocumentSidebar";

function doc(id: string, name: string): DocumentListItem {
  return {
    id,
    name,
    source_kind: "paste",
    created_at: "2026-06-04T00:00:00Z",
    sheet_id: null,
    sheet_status: null,
    char_count: 1234,
    page_count: null,
  };
}

// True when `later` appears after `earlier` in document order.
function follows(earlier: Element, later: Element): boolean {
  return Boolean(
    earlier.compareDocumentPosition(later) & Node.DOCUMENT_POSITION_FOLLOWING,
  );
}

describe("DocumentSidebar layout", () => {
  it("orders header, then the sky banner, then the document list", () => {
    const { container } = render(
      <DocumentSidebar
        documents={[doc("a", "Alpha doc"), doc("b", "Beta doc")]}
        selectedId={null}
        loading={false}
        error={null}
        onSelect={() => {}}
      />,
    );
    const header = screen.getByRole("heading", { name: /documents/i });
    const banner = container.querySelector("img");
    const list = container.querySelector("ul");

    expect(banner).not.toBeNull();
    expect(list).not.toBeNull();
    // The banner image is decorative and crops to a landscape band.
    expect(banner!.getAttribute("alt")).toBe("");
    expect(banner!.getAttribute("src")).toBe("/brand/sky.jpg");
    expect(banner!.className).toContain("object-cover");

    // Order: header, then banner, then list.
    expect(follows(header, banner!)).toBe(true);
    expect(follows(banner!, list!)).toBe(true);
  });

  it("renders the empty state below the banner when there are no documents", () => {
    const { container } = render(
      <DocumentSidebar
        documents={[]}
        selectedId={null}
        loading={false}
        error={null}
        onSelect={() => {}}
      />,
    );
    const banner = container.querySelector("img");
    const empty = screen.getByText(/no documents yet/i);
    expect(banner).not.toBeNull();
    expect(follows(banner!, empty)).toBe(true);
  });
});
