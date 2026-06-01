-- IB Desk initial schema (Phase 0).
--
-- This migration creates the generic, schema-agnostic data model exactly as
-- defined in the data model section of BUILD_PLAN.md. The table definitions here
-- must match BUILD_PLAN.md field for field. Do not redefine the schema
-- differently in this file.
--
-- Row level security is enabled on the four data tables (documents, sheets,
-- sections, cells) with placeholder policies. IMPORTANT: enforcement is NOT
-- active for the service in Phase 0. The service connects with a privileged
-- (table owner) role, which bypasses row level security. Real per-workspace,
-- per-user enforcement arrives in a later phase (see BUILD_PLAN.md, Phase 5).
-- Do not assume isolation that is not yet enforced.

create extension if not exists vector;
create extension if not exists pgcrypto;

create table documents (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  name text not null,
  source_kind text not null,            -- upload_pdf | upload_docx | paste
  raw_text text not null,               -- normalized plain text
  byte_path text,                       -- object storage key for the original file
  doc_type text,                        -- discovered: company_profile | market_overview | deal | person | technology | other
  primary_topic text,                   -- discovered, free text
  embedding vector(1536),               -- reserved for future similar-sheet search
  created_at timestamptz default now()
);

create table sheets (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) unique,
  title text not null,                  -- usually the primary subject label
  status text not null default 'idle',  -- idle | extracting | done | failed
  field_count int default 0,
  cost_usd numeric default 0,
  created_at timestamptz default now()
);

create table sections (
  id uuid primary key default gen_random_uuid(),
  sheet_id uuid not null references sheets(id) on delete cascade,
  key text not null,                    -- machine key, e.g. investors_capital
  label text not null,                  -- human label, e.g. Investors and capital
  kind text not null,                   -- scalar | list | table | timeseries | longtext
  render_hint text not null,            -- see RenderHint enum in BUILD_PLAN.md
  category text,                        -- soft color category for the UI and export
  columns jsonb,                        -- for table or timeseries: ordered column defs
  sort int not null,
  confidence real
);

create table cells (
  id uuid primary key default gen_random_uuid(),
  section_id uuid not null references sections(id) on delete cascade,
  row_idx int not null default 0,
  col_key text,                         -- null for scalar and longtext
  value_raw text,                       -- exactly as written in the document
  value_norm text,                      -- normalized (number, percent, currency)
  unit text,                            -- e.g. INR, percent
  period text,                          -- e.g. FY24
  source_snippet text not null,         -- the sentence that supports this value
  char_start int,                       -- span into documents.raw_text for highlighting
  char_end int,
  confidence real
);

create table extraction_events (
  id uuid primary key default gen_random_uuid(),
  sheet_id uuid not null references sheets(id) on delete cascade,
  stage text not null,                  -- discovery | extraction | verification | typing | done | error
  message text,
  payload jsonb,
  created_at timestamptz default now()
);

-- Row level security: enabled on the four data tables with placeholder policies.
-- Not enforced for the privileged service role in Phase 0 (see header note).
alter table documents enable row level security;
alter table sheets    enable row level security;
alter table sections  enable row level security;
alter table cells     enable row level security;

-- Placeholder policies. These are intentionally permissive and serve only to
-- declare the RLS surface. They are replaced with real workspace-scoped policies
-- in a later phase.
create policy documents_placeholder on documents using (true) with check (true);
create policy sheets_placeholder    on sheets    using (true) with check (true);
create policy sections_placeholder  on sections  using (true) with check (true);
create policy cells_placeholder     on cells     using (true) with check (true);
