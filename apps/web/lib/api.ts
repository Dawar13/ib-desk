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
import { getWorkspaceId } from "./workspace";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Phase 5: every request carries the anonymous per-visitor workspace id so the
// service can scope it to that visitor's private space. fetch() calls send it as
// a header; the EventSource stream and the download anchors cannot set headers,
// so those URL builders append it as the ws query parameter instead.
const WORKSPACE_HEADER = "X-Workspace-Id";

function workspaceHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  headers.set(WORKSPACE_HEADER, getWorkspaceId());
  return headers;
}

// Error subclass that carries the machine-readable ingestion code and the HTTP
// status. The code is optional because a failure may come from the network or a
// non-contract status, in which case there is no detail.code to branch on. The
// status lets callers tell a real validation error (4xx) from a transient
// server-side failure (5xx) worth retrying.
export class IngestError extends Error {
  readonly code: IngestErrorCode | null;
  readonly status: number | null;

  constructor(message: string, code: IngestErrorCode | null, status: number | null = null) {
    super(message);
    this.name = "IngestError";
    this.code = code;
    this.status = status;
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
    throw new IngestError(detail.message, detail.code ?? null, res.status);
  }

  throw new IngestError("Request failed with status " + res.status, null, res.status);
}

// Whether an error looks like a transient cold start, as opposed to a real
// validation error to show immediately. A sleeping free instance returns a
// header-less 502; because it has no CORS headers the browser blocks reading it
// and fetch rejects with a TypeError, so a network-level failure is treated as a
// cold start. A readable 5xx is too. A contract 4xx (which carries a sub-500
// status) is a real error and is not retried, so a retry can never resubmit an
// upload the server actually rejected, only one a cold server never received.
export function isColdStartError(err: unknown): boolean {
  if (err instanceof IngestError) {
    return err.status === null || err.status >= 500;
  }
  return err instanceof TypeError;
}

// Render's free tier spins the service down after idle, so the first request
// after a quiet spell can fail or time out during the ~50 second cold start. Run
// a request through this to retry on failure with backoff, calling onWaking so
// the UI can show a friendly "waking the server" message instead of a scary
// failure, then give up with the last error.
//
// shouldRetry decides which errors are retried; it defaults to all (right for an
// idempotent GET). For a non-idempotent write like an upload, pass
// isColdStartError so only a cold-start failure (a 502 the server never received)
// is retried and a real validation error surfaces at once, so a retry can never
// duplicate a document the server actually created.
export async function withColdStartRetry<T>(
  fn: () => Promise<T>,
  onWaking?: () => void,
  delaysMs: number[] = [2000, 4000, 6000, 9000, 12000, 15000, 18000],
  shouldRetry: (err: unknown) => boolean = () => true,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= delaysMs.length; attempt += 1) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      if (attempt === delaysMs.length || !shouldRetry(err)) {
        break;
      }
      onWaking?.();
      await new Promise((resolve) => setTimeout(resolve, delaysMs[attempt]));
    }
  }
  throw lastError;
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await fetch(API_BASE + "/v1/documents", {
    cache: "no-store",
    headers: workspaceHeaders(),
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as DocumentListItem[];
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const res = await fetch(API_BASE + "/v1/documents/" + id, {
    cache: "no-store",
    headers: workspaceHeaders(),
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
  // Only the workspace header is set; fetch still sets the multipart boundary.
  const res = await fetch(API_BASE + "/v1/documents", {
    method: "POST",
    headers: workspaceHeaders(),
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
    headers: workspaceHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ name, text }),
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as CreateDocumentResponse;
}

export function originalUrl(id: string): string {
  return (
    API_BASE +
    "/v1/documents/" +
    id +
    "/original?ws=" +
    encodeURIComponent(getWorkspaceId())
  );
}

// Fetch the populated sheet payload (sheet, sections, nested cells) for a sheet.
// This is the canonical read path; the web app calls it once a done event arrives
// on the extraction events stream.
export async function getSheet(id: string): Promise<SheetPayload> {
  const res = await fetch(API_BASE + "/v1/sheets/" + id, {
    cache: "no-store",
    headers: workspaceHeaders(),
  });
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
    headers: workspaceHeaders(),
  });
  if (!res.ok) {
    await throwFromResponse(res);
  }
  return (await res.json()) as { sheet_id: string; status: string };
}

// The server-sent events URL for a sheet's extraction progress. Returned as a
// plain string so the caller can hand it directly to the browser EventSource,
// which performs its own GET rather than going through fetch. The workspace id
// rides as a query parameter, since EventSource cannot set a header.
export function eventsUrl(sheetId: string): string {
  return (
    API_BASE +
    "/v1/sheets/" +
    sheetId +
    "/events?ws=" +
    encodeURIComponent(getWorkspaceId())
  );
}

// The export URL for a sheet, returned as a plain string so a download control
// can use it directly as an anchor href. The server sets Content-Disposition to
// attachment, so the browser downloads the styled xlsx (default) or csv. The
// workspace id rides as a query parameter, since an anchor cannot set a header.
export function exportUrl(sheetId: string, format: "xlsx" | "csv" = "xlsx"): string {
  return (
    API_BASE +
    "/v1/sheets/" +
    sheetId +
    "/export?format=" +
    format +
    "&ws=" +
    encodeURIComponent(getWorkspaceId())
  );
}
