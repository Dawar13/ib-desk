// Typed API client for the IB Desk FastAPI service.
//
// This is the only place the web app talks to the service. It imports the
// shared contract types with import type so they never reach the JavaScript
// bundle. Request URLs are built by plain string concatenation against a single
// base URL. Each function throws on a non-ok response; callers wrap calls in
// try/catch so the page never crashes when the service is down.

import type {
  HealthResponse,
  DocumentListItem,
  SheetPayload,
} from "@ib-desk/shared";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(API_BASE + "/health", { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Health request failed with status " + res.status);
  }
  return (await res.json()) as HealthResponse;
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await fetch(API_BASE + "/v1/documents", { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Documents request failed with status " + res.status);
  }
  return (await res.json()) as DocumentListItem[];
}

export async function getSheet(id: string): Promise<SheetPayload> {
  const res = await fetch(API_BASE + "/v1/sheets/" + id, { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Sheet request failed with status " + res.status);
  }
  return (await res.json()) as SheetPayload;
}
