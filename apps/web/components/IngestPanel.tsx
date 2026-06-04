"use client";

import { useRef, useState } from "react";
import type { CreateDocumentResponse } from "@ib-desk/shared";
import {
  createDocumentFile,
  createDocumentPaste,
  IngestError,
  isColdStartError,
  withColdStartRetry,
} from "@/lib/api";
import { ingestErrorMessage } from "@/lib/labels";

// The intake controls: a file upload that supports both the file picker and
// drag and drop, and a separate paste control with a name field and a text
// area. On submit it calls POST /v1/documents (multipart for files, JSON for
// paste), shows a loading state during upload and parsing, and on error reads
// the machine-readable code to show a clear, specific message. On success it
// reports the new document id upward so the page can refresh the list and
// select it.

interface IngestPanelProps {
  onCreated: (response: CreateDocumentResponse) => void;
}

export default function IngestPanel({ onCreated }: IngestPanelProps) {
  const [busy, setBusy] = useState<boolean>(false);
  // True while a submit is retrying through a free-tier cold start, so the busy
  // line reads "waking the server" rather than implying the upload is stuck.
  const [waking, setWaking] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [pasteName, setPasteName] = useState<string>("");
  const [pasteText, setPasteText] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function reportError(err: unknown): void {
    if (err instanceof IngestError) {
      setError(ingestErrorMessage(err.code, err.message));
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError("Something went wrong during ingestion.");
    }
  }

  // Retry only a cold-start failure (a 502 the sleeping server never received),
  // never a real validation error, so a retry can never duplicate the document.
  async function submitFile(file: File): Promise<void> {
    setBusy(true);
    setError(null);
    setWaking(false);
    try {
      const response = await withColdStartRetry(
        () => createDocumentFile(file),
        () => setWaking(true),
        undefined,
        isColdStartError,
      );
      onCreated(response);
    } catch (err) {
      reportError(err);
    } finally {
      setBusy(false);
      setWaking(false);
    }
  }

  async function submitPaste(): Promise<void> {
    setBusy(true);
    setError(null);
    setWaking(false);
    try {
      const response = await withColdStartRetry(
        () => createDocumentPaste(pasteName.trim(), pasteText),
        () => setWaking(true),
        undefined,
        isColdStartError,
      );
      setPasteName("");
      setPasteText("");
      onCreated(response);
    } catch (err) {
      reportError(err);
    } finally {
      setBusy(false);
      setWaking(false);
    }
  }

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    // Reset the input so selecting the same file again re-triggers a change.
    event.target.value = "";
    if (file) {
      void submitFile(file);
    }
  }

  function onDrop(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setDragActive(false);
    if (busy) {
      return;
    }
    const file = event.dataTransfer.files?.[0];
    if (file) {
      void submitFile(file);
    }
  }

  function onDragOver(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    if (!busy) {
      setDragActive(true);
    }
  }

  function onDragLeave(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setDragActive(false);
  }

  const canSubmitPaste = !busy && pasteName.trim() !== "" && pasteText !== "";

  return (
    <section
      aria-label="Add a document"
      className="border-b border-line bg-surface p-6"
    >
      <h2 className="font-serif text-lg text-ink">Add a document</h2>
      <p className="mt-1 text-sm text-muted">
        Drop in a research document about anything, a company, a market, a person,
        or a deal, and get back a grounded, structured sheet.
      </p>

      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <div>
          <p className="mb-2 text-sm font-medium text-muted">Upload a file</p>
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload a PDF or DOCX. Drag a file here or click to choose."
            onClick={() => {
              if (!busy) {
                fileInputRef.current?.click();
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (!busy) {
                  fileInputRef.current?.click();
                }
              }
            }}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            className={
              "flex h-40 cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-4 text-center text-sm transition-colors " +
              (dragActive
                ? "border-primary bg-primary-tint text-ink"
                : "border-line bg-paper text-muted hover:border-primary/50")
            }
          >
            <span className="font-medium">
              Drag a file here, or click to choose
            </span>
            <span className="mt-1 text-xs text-faint">
              PDF or DOCX, text-based
            </span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            aria-label="Choose a file to upload"
            onChange={onFileChange}
            disabled={busy}
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-muted">Paste text</p>
          <label className="block">
            <span className="sr-only">Document name</span>
            <input
              type="text"
              value={pasteName}
              onChange={(event) => setPasteName(event.target.value)}
              placeholder="Document name"
              aria-label="Document name"
              disabled={busy}
              className="block w-full rounded-md border border-line px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:bg-paper"
            />
          </label>
          <label className="mt-2 block">
            <span className="sr-only">Pasted text</span>
            <textarea
              value={pasteText}
              onChange={(event) => setPasteText(event.target.value)}
              placeholder="Paste document text here"
              aria-label="Pasted text"
              rows={4}
              disabled={busy}
              className="block w-full resize-y rounded-md border border-line px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:bg-paper"
            />
          </label>
          <button
            type="button"
            onClick={() => void submitPaste()}
            disabled={!canSubmitPaste}
            className="mt-2 rounded-md bg-primary-deep px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary disabled:cursor-not-allowed disabled:bg-line disabled:text-faint"
          >
            Add pasted text
          </button>
        </div>
      </div>

      {busy ? (
        <p className="mt-4 text-sm text-muted" role="status">
          {waking
            ? "Waking the server. The free instance sleeps when idle, so this can take up to a minute."
            : "Uploading and parsing the document"}
        </p>
      ) : null}

      {error ? (
        <p className="mt-4 text-sm" style={{ color: "#b4503e" }} role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
