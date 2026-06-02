// Shared display helpers for the ingestion UI. Kept out of the React tree so
// both the sidebar and the document panel render source kinds the same way and
// so the per-code error copy lives in one place.

import type { IngestErrorCode, SourceKind } from "@ib-desk/shared";

// Human label for a source kind, used in the sidebar and the document header.
export function sourceKindLabel(kind: SourceKind): string {
  switch (kind) {
    case "upload_pdf":
      return "PDF";
    case "upload_docx":
      return "DOCX";
    case "paste":
      return "Pasted text";
    default:
      return kind;
  }
}

// Clear, specific copy for each machine-readable ingestion error code. A code we
// do not recognize, or a network failure with no code, falls back to the raw
// message so the user still sees something actionable.
export function ingestErrorMessage(
  code: IngestErrorCode | null,
  fallback: string,
): string {
  switch (code) {
    case "unsupported_type":
      return "That file type is not supported. Upload a PDF or a DOCX, or paste text.";
    case "file_too_large":
      return "That file is too large to upload.";
    case "empty_input":
      return "There is nothing to ingest. Choose a file or enter some text.";
    case "scanned_or_unreadable":
      return "This document appears to be scanned or has no readable text. Upload a text-based PDF or DOCX.";
    case "parse_failed":
      return "The document could not be parsed. It may be corrupt or in an unexpected format.";
    default:
      return fallback;
  }
}
