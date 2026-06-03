"use client";

// The sheet workspace: the one client component that owns the live behavior. It
// keeps the extract trigger from Phase 2, runs the four-pass pipeline, consumes
// the server-sent events to drive the gradual reveal, fetches the populated sheet
// when the run reaches done, and selects the right state screen. The presentation
// is delegated: the reveal to RevealView, the finished sheet to Sheet, and the
// quiet states to SheetStates. This replaces the Phase 2 debug rendering.

import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { DocType, SheetPayload, SheetStatus } from "@ib-desk/shared";
import { cx } from "@/lib/cx";
import { eventsUrl, getSheet, triggerExtract } from "@/lib/api";
import {
  INITIAL_REVEAL,
  revealReducer,
  type EventFrameInput,
  type RevealState,
} from "@/lib/sheet/reveal";
import DownloadControls from "./DownloadControls";
import RevealView from "./RevealView";
import Sheet from "./Sheet";
import {
  DiscoveringState,
  EmptyState,
  FailedState,
  LoadingState,
} from "./SheetStates";

type Phase = "idle" | "loading" | "extracting" | "done" | "failed";

interface SheetWorkspaceProps {
  sheetId: string;
  initialStatus: SheetStatus;
  docName: string;
  docType: DocType | null;
  primaryTopic: string | null;
  // The canonical document text, passed to the finished sheet so the evidence
  // drawer can highlight a value's span in context.
  documentText?: string | null;
  // Shown in the idle state before the sheet is built (the parsed-text preview),
  // so a freshly ingested document is still useful and the extract action is one
  // click away. Falls back to a plain empty state when not provided.
  idleContent?: ReactNode;
}

// Narrow an untrusted SSE payload to the fields the reveal needs.
function isEventFrame(value: unknown): value is EventFrameInput {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.stage === "string" &&
    (record.message === null || typeof record.message === "string")
  );
}

export default function SheetWorkspace({
  sheetId,
  initialStatus,
  docName,
  docType,
  primaryTopic,
  documentText,
  idleContent,
}: SheetWorkspaceProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [payload, setPayload] = useState<SheetPayload | null>(null);
  const [reveal, setReveal] = useState<RevealState>(INITIAL_REVEAL);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<boolean>(false);
  const [running, setRunning] = useState<boolean>(false);
  // When the events stream drops (for example an HTTP/2 proxy hiccup) the run may
  // still be progressing on the server, so we poll the sheet rather than declare
  // failure. polling drives that fallback.
  const [polling, setPolling] = useState<boolean>(false);

  // Initialize from the known sheet status. A done sheet is fetched and shown; an
  // in-flight sheet opens the stream (which replays from the start); idle and
  // failed render their state screens.
  useEffect(() => {
    let active = true;
    setPayload(null);
    setReveal(INITIAL_REVEAL);
    setError(null);
    setStarting(false);
    setPolling(false);

    if (initialStatus === "done") {
      setPhase("loading");
      setRunning(false);
      void getSheet(sheetId)
        .then((result) => {
          if (active) {
            setPayload(result);
            setPhase("done");
          }
        })
        .catch((err: unknown) => {
          if (active) {
            setError(err instanceof Error ? err.message : "Could not load the sheet");
            setPhase("failed");
          }
        });
    } else if (initialStatus === "extracting") {
      setPhase("extracting");
      setRunning(true);
    } else {
      setPhase(initialStatus === "failed" ? "failed" : "idle");
      setRunning(false);
    }

    return () => {
      active = false;
    };
  }, [sheetId, initialStatus]);

  const onExtract = useCallback(async (): Promise<void> => {
    setStarting(true);
    setError(null);
    setPayload(null);
    setReveal(INITIAL_REVEAL);
    setPolling(false);
    setPhase("extracting");
    try {
      await triggerExtract(sheetId);
      setRunning(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start extraction");
      setPhase("failed");
    } finally {
      setStarting(false);
    }
  }, [sheetId]);

  // Manage the EventSource for one run. Opens when running turns true, folds each
  // frame into the reveal, and on a terminal frame closes the stream and either
  // fetches the populated sheet (done) or surfaces the failure (error). The
  // cleanup closes the stream on unmount and whenever the effect re-runs.
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
      let frame: EventFrameInput | null = null;
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

      setReveal((prev) => revealReducer(prev, frame));

      if (frame.stage === "done") {
        close();
        setRunning(false);
        void getSheet(sheetId)
          .then((result) => {
            setPayload(result);
            setPhase("done");
          })
          .catch((err: unknown) => {
            setError(err instanceof Error ? err.message : "Could not load the sheet");
            setPhase("failed");
          });
      } else if (frame.stage === "error") {
        close();
        setRunning(false);
        setError(frame.message ?? "The extraction failed.");
        setPhase("failed");
      }
    };

    // A transport-level failure (the connection dropped) does not mean the run
    // failed: the engine may still be working on the server. Stop the broken
    // stream and fall back to polling the sheet, rather than showing failure.
    source.onerror = (): void => {
      if (closed) {
        return;
      }
      close();
      setRunning(false);
      setPolling(true);
    };

    return () => {
      close();
    };
  }, [running, sheetId]);

  // Polling fallback. When the stream is lost mid-run, poll the sheet until it
  // reaches a terminal status, then settle. Bounded so it cannot poll forever.
  useEffect(() => {
    if (!polling) {
      return;
    }
    let active = true;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async (): Promise<void> => {
      attempts += 1;
      try {
        const result = await getSheet(sheetId);
        if (!active) {
          return;
        }
        if (result.sheet.status === "done") {
          setPayload(result);
          setPhase("done");
          setPolling(false);
          return;
        }
        if (result.sheet.status === "failed") {
          setError("The extraction failed.");
          setPhase("failed");
          setPolling(false);
          return;
        }
      } catch {
        // A transient read error: keep polling.
      }
      if (!active) {
        return;
      }
      if (attempts >= 120) {
        setError(
          "The extraction is taking longer than expected. Use Re-extract or refresh.",
        );
        setPhase("failed");
        setPolling(false);
        return;
      }
      timer = setTimeout(() => {
        void tick();
      }, 3000);
    };

    timer = setTimeout(() => {
      void tick();
    }, 3000);

    return () => {
      active = false;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [polling, sheetId]);

  // Resolve the subject and classification from the best available source: live
  // discovery first, then the persisted document fields, then the sheet title,
  // then the file name. None of these is invented.
  const resolvedDocType: DocType | null = reveal.docType ?? docType;
  const resolvedSubject =
    reveal.primaryTopic ??
    primaryTopic ??
    (payload ? payload.sheet.title : null) ??
    docName;

  const canExtract =
    !starting &&
    !running &&
    !polling &&
    (phase === "idle" || phase === "done" || phase === "failed");
  const buttonLabel = starting
    ? "Starting"
    : running || phase === "extracting"
      ? "Extracting"
      : phase === "done" || phase === "failed"
        ? "Re-extract"
        : "Extract";

  return (
    <section data-phase={phase}>
      <div className="flex items-center justify-between gap-3 border-b border-line bg-paper/60 px-4 py-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">
          Sheet
        </span>
        <div className="flex items-center gap-2">
          <DownloadControls sheetId={sheetId} disabled={phase !== "done"} />
          <button
            type="button"
            onClick={() => void onExtract()}
            disabled={!canExtract}
            className={cx(
              "px-3 py-1 text-sm font-medium transition-colors",
              canExtract
                ? "bg-ink text-paper hover:bg-ink/90"
                : "cursor-not-allowed bg-line text-faint",
            )}
          >
            {buttonLabel}
          </button>
        </div>
      </div>

      <div>
        {phase === "failed" ? (
          <FailedState message={error} />
        ) : phase === "loading" ? (
          <LoadingState />
        ) : phase === "idle" ? (
          idleContent !== undefined ? (
            idleContent
          ) : (
            <EmptyState />
          )
        ) : phase === "extracting" ? (
          reveal.discovered.length > 0 ? (
            <RevealView
              subject={resolvedSubject}
              docType={resolvedDocType}
              reveal={reveal}
            />
          ) : (
            <DiscoveringState />
          )
        ) : payload ? (
          <Sheet
            subject={resolvedSubject}
            docType={resolvedDocType}
            sections={payload.sections}
            fieldCount={payload.sheet.field_count}
            documentText={documentText}
          />
        ) : (
          <LoadingState />
        )}
      </div>
    </section>
  );
}
