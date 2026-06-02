"use client";

// The click-to-evidence drawer. Slides in from the right and shows the clicked
// value, the section and field it belongs to, its confidence, and the exact
// stored source sentence the value was grounded to. This is the trust layer made
// visible: the banker verifies a value by eye against its source. Highlighting
// the sentence inside the full original document is a later phase; here the
// stored sentence is shown directly.

import { useEffect, useRef } from "react";
import { cx } from "@/lib/cx";
import { confidenceStyle } from "@/lib/sheet/confidence";
import { cellDisplayValue, cellFieldLabel } from "@/lib/sheet/value";
import type { EvidenceTarget } from "./types";

interface EvidenceDrawerProps {
  target: EvidenceTarget | null;
  onClose: () => void;
}

export default function EvidenceDrawer({ target, onClose }: EvidenceDrawerProps) {
  const open = target !== null;
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    // Move focus into the modal dialog on open and restore it to the trigger on
    // close, so keyboard users are not left behind the overlay.
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (previouslyFocused && typeof previouslyFocused.focus === "function") {
        previouslyFocused.focus();
      }
    };
  }, [open, onClose]);

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cx(
          "fixed inset-0 z-30 bg-ink/20 transition-opacity duration-300",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <aside
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Source evidence"
        aria-hidden={!open}
        tabIndex={-1}
        className={cx(
          "fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col border-l border-line bg-surface shadow-2xl transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        {target ? <EvidenceContent target={target} onClose={onClose} /> : null}
      </aside>
    </>
  );
}

function EvidenceContent({
  target,
  onClose,
}: {
  target: EvidenceTarget;
  onClose: () => void;
}) {
  const { cell, section } = target;
  const style = confidenceStyle(cell.confidence);

  return (
    <>
      <header className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 className="font-serif text-lg text-ink">Evidence</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close evidence"
          className="rounded p-1 text-muted transition-colors hover:bg-ink/[0.05]"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 20 20"
            aria-hidden="true"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <dl className="space-y-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-faint">Value</dt>
            <dd className="mt-1 break-words font-mono text-lg text-ink">
              {cellDisplayValue(cell)}
            </dd>
          </div>

          <div className="flex flex-wrap gap-x-8 gap-y-4">
            <div>
              <dt className="text-xs uppercase tracking-wide text-faint">Section</dt>
              <dd className="mt-1 text-sm text-ink">{section.label}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-faint">Field</dt>
              <dd className="mt-1 text-sm text-ink">{cellFieldLabel(cell)}</dd>
            </div>
            {cell.period ? (
              <div>
                <dt className="text-xs uppercase tracking-wide text-faint">Period</dt>
                <dd className="mt-1 text-sm text-ink">{cell.period}</dd>
              </div>
            ) : null}
            {cell.unit ? (
              <div>
                <dt className="text-xs uppercase tracking-wide text-faint">Unit</dt>
                <dd className="mt-1 text-sm text-ink">{cell.unit}</dd>
              </div>
            ) : null}
          </div>

          <div>
            <dt className="text-xs uppercase tracking-wide text-faint">Confidence</dt>
            <dd className="mt-1 flex items-center gap-2 text-sm text-ink">
              <span
                aria-hidden="true"
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: style.color }}
              />
              {style.label}
              {cell.confidence !== null && Number.isFinite(cell.confidence)
                ? ` (${cell.confidence.toFixed(2)})`
                : ""}
            </dd>
          </div>

          <div>
            <dt className="text-xs uppercase tracking-wide text-faint">
              Source sentence
            </dt>
            <dd className="mt-1 break-words rounded-md border border-line bg-paper p-3 font-serif text-[15px] leading-relaxed text-ink">
              {cell.source_snippet}
            </dd>
            <p className="mt-2 text-xs text-faint">
              The exact sentence this value was grounded to in the source document.
            </p>
          </div>
        </dl>
      </div>
    </>
  );
}
