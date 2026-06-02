"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  SheetPayload,
  SectionWithCells,
  Cell,
  SheetStatus,
} from "@ib-desk/shared";
import { eventsUrl, getSheet, triggerExtract } from "@/lib/api";

// Debug-only extraction panel. It shows the sheet status, an Extract button that
// triggers the four-pass pipeline, a plain live log of the server-sent events,
// and a plain rendering of the populated sheet once extraction is done. This is
// deliberately not the product UI: there is no grid, no charts, and no evidence
// drawer here. Those arrive in a later phase. The point is to exercise the
// engine and let a developer read what it produced and where each value came
// from in the source.

interface ExtractionPanelProps {
  sheetId: string;
  // The sheet status as known when the document was loaded. The panel keeps its
  // own working status from here so the Extract button and re-extraction behave
  // correctly without refetching the document.
  initialStatus: SheetStatus;
}

// One streamed progress event as rendered in the live log. The service sends a
// JSON object per SSE frame with these fields; payload is opaque here and shown
// only when present so the log stays readable.
interface LogEntry {
  stage: string;
  message: string | null;
  payload: unknown;
}

// The shape of a single SSE frame as emitted by GET /v1/sheets/{id}/events. Only
// stage and message are rendered; created_at and payload are accepted but not
// required by the debug log.
interface EventFrame {
  stage: string;
  message: string | null;
  payload: unknown;
  created_at: string;
}

// A status is re-extractable when no run is in flight: idle (never run), done (a
// prior run finished), or failed (a prior run errored). extracting is excluded
// so the user cannot start a second concurrent run.
function canExtract(status: SheetStatus): boolean {
  return status === "idle" || status === "done" || status === "failed";
}

function statusLabel(status: SheetStatus): string {
  switch (status) {
    case "idle":
      return "Not yet extracted";
    case "extracting":
      return "Extracting";
    case "done":
      return "Extraction complete";
    case "failed":
      return "Extraction failed";
    default:
      return status;
  }
}

// Type guard that narrows a parsed SSE payload to an EventFrame. The stream is
// untrusted JSON from the wire, so we validate the two fields the log relies on
// before reading them.
function isEventFrame(value: unknown): value is EventFrame {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.stage === "string" &&
    (record.message === null || typeof record.message === "string")
  );
}

export default function ExtractionPanel({
  sheetId,
  initialStatus,
}: ExtractionPanelProps) {
  const [status, setStatus] = useState<SheetStatus>(initialStatus);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [sheet, setSheet] = useState<SheetPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  // running drives the EventSource useEffect: setting it true (after a
  // successful trigger) opens the stream; a terminal event or unmount closes it.
  const [running, setRunning] = useState<boolean>(false);
  const [starting, setStarting] = useState<boolean>(false);

  // Reset all working state when the selected sheet changes so a freshly selected
  // document never shows a previous sheet's log or result.
  useEffect(() => {
    setStatus(initialStatus);
    setLog([]);
    setSheet(null);
    setError(null);
    setStarting(false);
    setRunning(initialStatus === "extracting");
  }, [sheetId, initialStatus]);

  const onExtract = useCallback(async (): Promise<void> => {
    setStarting(true);
    setError(null);
    setLog([]);
    setSheet(null);
    try {
      const response = await triggerExtract(sheetId);
      setStatus((response.status as SheetStatus) || "extracting");
      setRunning(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start extraction");
      setStatus("failed");
    } finally {
      setStarting(false);
    }
  }, [sheetId]);

  // Manage the EventSource for the lifetime of one run. Opens when running turns
  // true, appends each frame to the live log, and on a terminal event (done or
  // error) closes the stream and, for done, fetches the populated sheet. The
  // cleanup closes the connection on unmount and whenever the effect re-runs, so
  // there is never a leaked or duplicated stream.
  useEffect(() => {
    if (!running) {
      return;
    }

    const source = new EventSource(eventsUrl(sheetId));
    let closed = false;

    const close = (): void => {
      if (!closed) {
        closed = true;
        source.close();
      }
    };

    source.onmessage = (event: MessageEvent<string>): void => {
      let frame: EventFrame | null = null;
      try {
        const parsed: unknown = JSON.parse(event.data);
        if (isEventFrame(parsed)) {
          frame = parsed;
        }
      } catch {
        frame = null;
      }
      if (frame === null) {
        return;
      }

      const entry: LogEntry = {
        stage: frame.stage,
        message: frame.message,
        payload: frame.payload,
      };
      setLog((prev) => [...prev, entry]);

      if (frame.stage === "done") {
        close();
        setStatus("done");
        setRunning(false);
        void getSheet(sheetId)
          .then((payload) => {
            setSheet(payload);
          })
          .catch((err: unknown) => {
            setError(
              err instanceof Error ? err.message : "Could not load the sheet",
            );
          });
      } else if (frame.stage === "error") {
        close();
        setStatus("failed");
        setRunning(false);
      }
    };

    // A transport-level failure (the connection dropped) is distinct from an
    // engine error frame. Surface it, stop, and close so the browser does not
    // silently keep retrying the stream.
    source.onerror = (): void => {
      if (closed) {
        return;
      }
      close();
      setRunning(false);
      setError("The extraction events stream was interrupted.");
    };

    return () => {
      close();
    };
  }, [running, sheetId]);

  const extractDisabled = starting || running || !canExtract(status);

  return (
    <section className="border-t border-gray-200 px-6 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
          Extraction (debug)
        </h2>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
          {statusLabel(status)}
        </span>
        <button
          type="button"
          onClick={() => void onExtract()}
          disabled={extractDisabled}
          className={
            "rounded-md px-3 py-1 text-sm font-medium transition-colors " +
            (extractDisabled
              ? "cursor-not-allowed bg-gray-200 text-gray-500"
              : "bg-blue-600 text-white hover:bg-blue-700")
          }
        >
          {starting
            ? "Starting"
            : running
              ? "Extracting"
              : status === "done" || status === "failed"
                ? "Re-extract"
                : "Extract"}
        </button>
      </div>

      {error ? (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {log.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Live log
          </h3>
          <ol className="mt-2 space-y-1 rounded-md border border-gray-200 bg-gray-50 p-3 font-mono text-xs text-gray-800">
            {log.map((entry, index) => (
              <li key={index} className="break-words">
                <span className="font-semibold">{entry.stage}</span>
                {entry.message !== null ? (
                  <span>: {entry.message}</span>
                ) : null}
                {entry.payload !== null && entry.payload !== undefined ? (
                  <span className="text-gray-500">
                    {" "}
                    {JSON.stringify(entry.payload)}
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {sheet !== null ? <SheetResult payload={sheet} /> : null}
    </section>
  );
}

// Plain rendering of a populated sheet. For each section it shows the label,
// kind, and render hint, then lists the section's cells. This is a readable
// debug dump, not the styled grid, so every section uses the same flat layout
// regardless of its render hint.
function SheetResult({ payload }: { payload: SheetPayload }) {
  const { sheet, sections } = payload;

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-gray-900">
        {sheet.title}
      </h3>
      <p className="mt-1 text-xs text-gray-500">
        {sections.length} {sections.length === 1 ? "section" : "sections"} -{" "}
        {sheet.field_count} {sheet.field_count === 1 ? "field" : "fields"}
      </p>

      {sections.length === 0 ? (
        <p className="mt-3 text-sm text-gray-600">
          The extraction produced no grounded sections for this document.
        </p>
      ) : (
        <div className="mt-3 space-y-6">
          {sections.map((section) => (
            <SectionBlock key={section.id} section={section} />
          ))}
        </div>
      )}
    </div>
  );
}

function SectionBlock({ section }: { section: SectionWithCells }) {
  return (
    <div className="rounded-md border border-gray-200 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h4 className="text-sm font-semibold text-gray-900">{section.label}</h4>
        <span className="text-xs text-gray-500">kind: {section.kind}</span>
        <span className="text-xs text-gray-500">
          render hint: {section.render_hint}
        </span>
        {section.confidence !== null ? (
          <span className="text-xs text-gray-500">
            confidence: {section.confidence.toFixed(2)}
          </span>
        ) : null}
      </div>

      {section.cells.length === 0 ? (
        <p className="mt-2 text-sm text-gray-600">
          No grounded values in this section.
        </p>
      ) : (
        <ul className="mt-3 space-y-3">
          {section.cells.map((cell) => (
            <CellRow key={cell.id} cell={cell} />
          ))}
        </ul>
      )}
    </div>
  );
}

function CellRow({ cell }: { cell: Cell }) {
  // Prefer the deterministically normalized value; fall back to the raw value
  // when normalization left it untouched. Both can be null in principle, so guard
  // for a missing value rather than printing the string "null".
  const value =
    cell.value_norm !== null
      ? cell.value_norm
      : cell.value_raw !== null
        ? cell.value_raw
        : "(no value)";

  return (
    <li className="border-l-2 border-gray-200 pl-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
        {cell.col_key !== null ? (
          <span className="text-xs text-gray-500">{cell.col_key}:</span>
        ) : null}
        <span className="font-medium text-gray-900">{value}</span>
        {cell.unit !== null ? (
          <span className="text-xs text-gray-500">unit: {cell.unit}</span>
        ) : null}
        {cell.period !== null ? (
          <span className="text-xs text-gray-500">period: {cell.period}</span>
        ) : null}
        {cell.confidence !== null ? (
          <span className="text-xs text-gray-500">
            confidence: {cell.confidence.toFixed(2)}
          </span>
        ) : null}
      </div>
      <p className="mt-1 text-xs italic text-gray-600 break-words">
        Source: {cell.source_snippet}
      </p>
    </li>
  );
}
