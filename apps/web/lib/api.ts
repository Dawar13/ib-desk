// Typed API client for the IB Desk FastAPI service.
//
// This is the only place the web app talks to the service. It imports the
// shared contract types with import type so they never reach the JavaScript
// bundle. Request URLs are built by plain string concatenation against a single
// base URL. Each function throws on a non-ok response; the page wraps calls in
// try/catch so the UI never crashes when the service is down.
//
// On a non-ok response the body is the FastAPI ApiErrorBody shape
// { detail: { code, message } }. We parse it and throw an IngestError that
// carries the machine-readable code so the page can branch per error case
// (unsupported_type, file_too_large, empty_input, scanned_or_unreadable,
// parse_failed). When the body is not parseable we fall back to a status-based
// message so a network or server failure still surfaces a clear error.

import type {
  DocumentListItem,
  DocumentDetail,
  CreateDocumentResponse,
  IngestErrorCode,
  ApiErrorBody,
  SheetPayload,
} from "@ib-desk/shared";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Error subclass that carries the machine-readable ingestion code. The code is
// optional because a failure may come from the network or a non-contract
// status, in which case there is no detail.code to branch on.
export class IngestError extends Error {
  readonly code: IngestErrorCode | null;

  constructor(message: string, code: IngestErrorCode | null) {
    super(message);
    this.name = "IngestError";
    this.code = code;
  }
}

// Read the ApiErrorBody from a non-ok response and throw an IngestError. If the
// body cannot be parsed as the contract shape, throw a status-based message.
async function throwFromResponse(res: Response): Promise<never> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  const detail = (body as Partial<ApiErrorBody> | null)?.detail;
  if (detail && typeof detail.message === "string") {
    throw new IngestError(detail.message, detail.code ?? null);
  }

  throw new IngestError("Request failed with status " + res.status, null);
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await fetch(API_BASE + "/v1/documents", { cache: "no-store" });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as DocumentListItem[];
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const res = await fetch(API_BASE + "/v1/documents/" + id, {
    cache: "no-store",
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as DocumentDetail;
}

export async function createDocumentFile(
  file: File,
): Promise<CreateDocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(API_BASE + "/v1/documents", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as CreateDocumentResponse;
}

export async function createDocumentPaste(
  name: string,
  text: string,
): Promise<CreateDocumentResponse> {
  const res = await fetch(API_BASE + "/v1/documents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, text }),
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as CreateDocumentResponse;
}

export function originalUrl(id: string): string {
  return API_BASE + "/v1/documents/" + id + "/original";
}

// Fetch the populated sheet payload (sheet, sections, nested cells) for a sheet.
// This is the canonical read path; the web app calls it once a done event arrives
// on the extraction events stream.
export async function getSheet(id: string): Promise<SheetPayload> {
  const res = await fetch(API_BASE + "/v1/sheets/" + id, { cache: "no-store" });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as SheetPayload;
}

// Trigger the four-pass extraction pipeline for a sheet. The service sets the
// sheet to extracting and runs the pipeline as a background task, returning 202
// with the sheet id and the new status. Progress is observed on the events
// stream (see eventsUrl) rather than in this response.
export async function triggerExtract(
  sheetId: string,
): Promise<{ sheet_id: string; status: string }> {
  const res = await fetch(API_BASE + "/v1/sheets/" + sheetId + "/extract", {
    method: "POST",
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as { sheet_id: string; status: string };
}

// The server-sent events URL for a sheet's extraction progress. Returned as a
// plain string so the caller can hand it directly to the browser EventSource,
// which performs its own GET rather than going through fetch.
export function eventsUrl(sheetId: string): string {
  return API_BASE + "/v1/sheets/" + sheetId + "/events";
}

// The export URL for a sheet, returned as a plain string so a download control
// can use it directly as an anchor href. The server sets Content-Disposition to
// attachment, so the browser downloads the styled xlsx (default) or csv.
export function exportUrl(sheetId: string, format: "xlsx" | "csv" = "xlsx"): string {
  return API_BASE + "/v1/sheets/" + sheetId + "/export?format=" + format;
}
