// Deterministic, secret-free gates for the gradual reveal and the sheet states.
// The reveal is driven through a scripted, mocked event stream so it is fully
// deterministic without the live engine; the API and EventSource are mocked.

import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SheetPayload } from "@ib-desk/shared";

const api = vi.hoisted(() => ({
  triggerExtract: vi.fn(),
  getSheet: vi.fn(),
}));

vi.mock("recharts");
vi.mock("@/lib/api", () => ({
  triggerExtract: api.triggerExtract,
  getSheet: api.getSheet,
  eventsUrl: () => "http://localhost/events",
}));

import RevealView from "@/components/sheet/RevealView";
import SheetWorkspace from "@/components/sheet/SheetWorkspace";
import { allHintsSheet } from "@/components/sheet/fixtures";
import type { RevealState } from "@/lib/sheet/reveal";

// A controllable EventSource stand-in: jsdom has no EventSource.
class MockEventSource {
  static last: MockEventSource | null = null;
  url: string;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: ((event?: unknown) => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.last = this;
  }

  close(): void {
    this.closed = true;
  }

  emit(frame: unknown): void {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(frame) }),
    );
  }
}

beforeEach(() => {
  vi.stubGlobal("EventSource", MockEventSource);
  MockEventSource.last = null;
  api.triggerExtract.mockReset();
  api.getSheet.mockReset();
  api.triggerExtract.mockResolvedValue({ sheet_id: "s", status: "extracting" });
  api.getSheet.mockResolvedValue(allHintsSheet);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("gradual reveal (RevealView)", () => {
  it("renders a skeleton per discovered section and marks completed ones", () => {
    const reveal: RevealState = {
      docType: null,
      primaryTopic: "Subject",
      discovered: [
        { key: "a", label: "Alpha" },
        { key: "b", label: "Bravo" },
        { key: "c", label: "Charlie" },
      ],
      completed: ["a", "b"],
    };
    render(<RevealView subject="Subject" docType={null} reveal={reveal} />);

    expect(document.querySelectorAll('[data-skeleton="true"]').length).toBe(3);
    expect(
      document.querySelectorAll('[data-skeleton="true"][data-ready="true"]').length,
    ).toBe(2);
  });
});

describe("workspace states and reveal off the stream", () => {
  it("idle shows the empty state", () => {
    render(
      <SheetWorkspace
        sheetId="s"
        initialStatus="idle"
        docName="Doc"
        docType={null}
        primaryTopic={null}
      />,
    );
    expect(screen.getByText("No sheet yet")).toBeInTheDocument();
  });

  it("extracting before discovery shows the discovering state", () => {
    render(
      <SheetWorkspace
        sheetId="s"
        initialStatus="extracting"
        docName="Doc"
        docType={null}
        primaryTopic={null}
      />,
    );
    expect(screen.getByText(/Discovering structure/)).toBeInTheDocument();
  });

  it("failed shows the failed state", () => {
    render(
      <SheetWorkspace
        sheetId="s"
        initialStatus="failed"
        docName="Doc"
        docType={null}
        primaryTopic={null}
      />,
    );
    expect(screen.getByText("Extraction failed")).toBeInTheDocument();
  });

  it("a finished sheet goes through loading and settles into the sheet", async () => {
    let resolveSheet: (value: SheetPayload) => void = () => {};
    api.getSheet.mockImplementation(
      () =>
        new Promise<SheetPayload>((resolve) => {
          resolveSheet = resolve;
        }),
    );

    render(
      <SheetWorkspace
        sheetId="s"
        initialStatus="done"
        docName="Doc"
        docType={null}
        primaryTopic={null}
      />,
    );

    expect(screen.getByText(/Loading the sheet/)).toBeInTheDocument();
    await act(async () => {
      resolveSheet(allHintsSheet);
    });
    expect(await screen.findByRole("heading", { name: "Investors" })).toBeInTheDocument();
  });

  it("extracts, reveals section by section, and settles into the populated sheet", async () => {
    const user = userEvent.setup();
    render(
      <SheetWorkspace
        sheetId="s"
        initialStatus="idle"
        docName="Doc"
        docType={null}
        primaryTopic={null}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Extract" }));
    expect(screen.getByText(/Discovering structure/)).toBeInTheDocument();

    await waitFor(() => expect(MockEventSource.last).not.toBeNull());
    const stream = MockEventSource.last as MockEventSource;

    act(() => {
      stream.emit({
        stage: "discovery",
        message: "discovery complete",
        payload: {
          doc_type: null,
          primary_topic: "Subject",
          sections: ["overview", "investors"],
        },
      });
    });
    // One skeleton per discovered section, none ready yet.
    expect(await screen.findByText("Overview")).toBeInTheDocument();
    expect(document.querySelectorAll('[data-skeleton="true"]').length).toBe(2);
    expect(
      document.querySelectorAll('[data-skeleton="true"][data-ready="true"]').length,
    ).toBe(0);

    act(() => {
      stream.emit({
        stage: "section",
        message: null,
        payload: { key: "overview", label: "Overview", sort: 0, kind: "scalar", cell_count: 2 },
      });
    });
    // Exactly the one completed section settles; the reveal is per-section.
    await waitFor(() =>
      expect(
        document.querySelectorAll('[data-skeleton="true"][data-ready="true"]').length,
      ).toBe(1),
    );
    expect(document.querySelectorAll('[data-skeleton="true"]').length).toBe(2);

    // done fetches the populated sheet (an async microtask), so flush it in act.
    await act(async () => {
      stream.emit({
        stage: "done",
        message: "extraction complete",
        payload: { sections: 2, fields: 5 },
      });
      await Promise.resolve();
    });

    // Settles into the populated sheet read from the payload, and the stream closes.
    expect(await screen.findByText("Harbor Lane Ventures")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Investors" }),
    ).toBeInTheDocument();
    expect(stream.closed).toBe(true);
  });
});
