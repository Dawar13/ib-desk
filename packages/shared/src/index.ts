// IB Desk shared sheet payload types.
//
// These types are the single contract shared between the Next.js web client and
// the FastAPI service. They mirror the data model in BUILD_PLAN.md field for
// field. The reserved embedding vector column on documents is intentionally not
// part of the API surface in v1 and is omitted here.
//
// Sample or seeded values are always labeled as sample in fixtures, never here.

export type DocType =
  | "company_profile"
  | "market_overview"
  | "deal"
  | "person"
  | "technology"
  | "other";

export type SourceKind = "upload_pdf" | "upload_docx" | "paste";

export type SheetStatus = "idle" | "extracting" | "done" | "failed";

export type SectionKind =
  | "scalar"
  | "list"
  | "table"
  | "timeseries"
  | "longtext";

// RenderHint mirrors the enum in BUILD_PLAN.md.
export type RenderHint =
  | "keyvalue"
  | "chips"
  | "table"
  | "timeseries_bar"
  | "timeseries_line"
  | "breakdown_pie"
  | "longtext";

// Ordered column definition used by table and timeseries sections.
export interface ColumnDef {
  key: string;
  label: string;
}

// Mirrors the documents table.
export interface Document {
  id: string;
  workspace_id: string;
  name: string;
  source_kind: SourceKind;
  raw_text: string;
  byte_path: string | null;
  doc_type: DocType | null;
  primary_topic: string | null;
  created_at: string;
}

// Mirrors the sheets table.
export interface Sheet {
  id: string;
  document_id: string;
  title: string;
  status: SheetStatus;
  field_count: number;
  cost_usd: number;
  created_at: string;
}

// Mirrors the sections table.
export interface Section {
  id: string;
  sheet_id: string;
  key: string;
  label: string;
  kind: SectionKind;
  render_hint: RenderHint;
  category: string | null;
  columns: ColumnDef[] | null;
  sort: number;
  confidence: number | null;
}

// Mirrors the cells table. One row is one grounded fact.
export interface Cell {
  id: string;
  section_id: string;
  row_idx: number;
  col_key: string | null;
  value_raw: string | null;
  value_norm: string | null;
  unit: string | null;
  period: string | null;
  source_snippet: string;
  char_start: number | null;
  char_end: number | null;
  confidence: number | null;
}

// A lightweight document list item as returned by GET /v1/documents. It carries
// only the fields the sidebar needs and omits raw_text, which is fetched per
// document via GET /v1/documents/{id}. sheet_id and sheet_status come from the
// document's one sheet (the sheets to documents relationship is one to one).
// char_count is the length of the canonical raw_text; page_count is null when
// pages do not apply (pasted text).
export interface DocumentListItem {
  id: string;
  name: string;
  source_kind: SourceKind;
  created_at: string;
  sheet_id: string | null;
  sheet_status: SheetStatus | null;
  char_count: number;
  page_count: number | null;
}

// Full document detail as returned by GET /v1/documents/{id}, including the
// canonical raw_text for the parsed-text preview, the page count, and the
// document's sheet id and status.
export interface DocumentDetail extends Document {
  page_count: number | null;
  sheet_id: string | null;
  sheet_status: SheetStatus | null;
}

// Returned by POST /v1/documents on success.
export interface CreateDocumentResponse {
  document_id: string;
  sheet_id: string;
}

// Machine-readable reason codes for a rejected ingestion. Returned in the error
// body so the client can show a clear, specific message.
export type IngestErrorCode =
  | "unsupported_type"
  | "file_too_large"
  | "empty_input"
  | "scanned_or_unreadable"
  | "parse_failed";

// Error body shape. FastAPI nests the payload under detail.
export interface ApiError {
  code: IngestErrorCode;
  message: string;
}

export interface ApiErrorBody {
  detail: ApiError;
}

// A section together with its cells, as returned by GET /v1/sheets/{id}.
export interface SectionWithCells extends Section {
  cells: Cell[];
}

// Full payload returned by GET /v1/sheets/{id}.
export interface SheetPayload {
  sheet: Sheet;
  sections: SectionWithCells[];
}

// Returned by GET /health. The database field reflects a real SELECT 1 check.
export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  version: string;
  database: "connected" | "disconnected";
  // The live extraction prompt version, so a deploy can be confirmed from /health
  // before a re-extraction is spent.
  extraction_prompt_version: string;
}
