# IB Desk

IB Desk turns any research document about a company, a market, a person, a
technology, or a deal into one clean, dynamic spreadsheet per document, where
every extracted value is grounded back to its exact supporting sentence in the
source. This repository is the monorepo for the product: a Next.js web app, a
FastAPI service, a shared TypeScript types package, and a Postgres schema with
pgvector reserved for future similar-sheet search. This README is the full local
bring-up guide, so a fresh clone can run from this document alone.

Phase 1 adds ingestion and the document store. A user uploads a PDF or DOCX, or
pastes text; the service parses and normalizes it to clean canonical text, stores
the original bytes, records the document and an idle sheet, and the web app lists
and previews it. There is no model intelligence yet: no extraction, no sections
or cells, no grid, no charts, no export, and no authentication. Phase 0 remains a
wiring proof underneath, with the health endpoint and the seeded sample sheet.
See BUILD_PLAN.md for the phase roadmap and CLAUDE.md for the principles and
conventions.

## Prerequisites

- Node.js 20 or newer.
- pnpm 10 (the repo pins pnpm 10.33.0 via the packageManager field).
- Python 3.12.
- uv, the Python package and project manager, for the service.
- A Postgres database with the pgvector extension available. Any of these works:
  Supabase, or the pgvector/pgvector Docker image, or a local Postgres with the
  vector extension installed.
- psql, the Postgres command line client, to apply the migration.

## Repository layout

```
ib-desk/
  apps/web/          # Next.js web app (App Router, TypeScript strict, Tailwind)
  services/api/      # FastAPI service (async, pydantic, asyncpg)
  packages/shared/   # shared TypeScript types for the sheet payload
  db/migrations/     # SQL migrations; 0001_init.sql is the full Phase 0 schema
  evals/             # golden documents and the eval harness (arrive in Phase 2)
  CLAUDE.md          # principles and conventions
  BUILD_PLAN.md      # architecture, data model, API contract, phase roadmap
```

## One time setup

Clone the repository, then install dependencies for both the web workspace and
the service.

Web workspace (from the repo root):

Unix and macOS:

```sh
pnpm install
```

Windows PowerShell:

```powershell
pnpm install
```

Service (in services/api):

Unix and macOS:

```sh
cd services/api
uv sync
cd ../..
```

Windows PowerShell:

```powershell
cd services/api
uv sync
cd ../..
```

## Environment variables

Secrets are never committed. Each package ships a .env.example with placeholder
values. Copy each one to a real .env and fill in your values. The .env files are
gitignored.

Service env (services/api/.env), copied from services/api/.env.example:

Unix and macOS:

```sh
cp services/api/.env.example services/api/.env
```

Windows PowerShell:

```powershell
Copy-Item services/api/.env.example services/api/.env
```

Web env (apps/web/.env.local), copied from apps/web/.env.example:

Unix and macOS:

```sh
cp apps/web/.env.example apps/web/.env.local
```

Windows PowerShell:

```powershell
Copy-Item apps/web/.env.example apps/web/.env.local
```

The settings that matter so far:

- DATABASE_URL: the asyncpg connection string for your Postgres, for example
  postgres://postgres:postgres@localhost:5432/ibdesk. The service reads this to
  open its connection pool, and the migrate and seed steps read it too. When it
  is unset, the service still starts and reports the database as disconnected.
- WEB_ORIGIN: the allowed CORS origin for the web app, default
  http://localhost:3000. CORS now allows GET and POST so the ingestion upload
  and paste requests and their preflight succeed.
- APP_VERSION: the version string the health endpoint reports, default 0.1.0.
- NEXT_PUBLIC_API_BASE_URL: the base URL the web app uses to reach the service,
  default http://localhost:8000.

Storage and ingestion settings (Phase 1), in services/api/.env.example:

- STORAGE_BACKEND: where original uploaded files are stored, either local or
  supabase. Default is local, which writes to the filesystem and needs no
  secret. This is what the document-store and end to end checks use in CI.
- STORAGE_LOCAL_PATH: the directory used by the local backend, default
  ./.local-storage. It is gitignored, so stored uploads stay out of version
  control. Relative paths resolve from the service working directory.
- STORAGE_BUCKET: the bucket name, default documents. For local storage it is a
  subdirectory under STORAGE_LOCAL_PATH; for Supabase it is the Storage bucket.
- MAX_UPLOAD_BYTES: the largest accepted upload, default 25 MiB. Larger uploads
  are rejected before anything is stored.
- SCANNED_MIN_CHARS_PER_PAGE: the scanned-PDF heuristic, default 50. PDFs whose
  average extractable characters per page fall below this are rejected as
  scanned or unreadable rather than ingested as empty text. There is no OCR yet.
- SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY: read only when STORAGE_BACKEND is
  supabase. Leave them blank for local storage.

OPENAI_API_KEY remains reserved in services/api/.env.example for the extraction
phase. It is documented there only and is not read by any code yet.

## Apply the migrations and seed

Set DATABASE_URL in your shell so the migration and seed steps can reach your
database, then apply every schema migration in order and insert the sample row
set. There are two migrations now: 0001_init.sql (the Phase 0 schema) and
0002_document_metadata.sql (the Phase 1 page_count and page_offsets columns on
documents). Apply them in sorted file order. The migrations are idempotent, so
re-running them is safe.

Apply all migrations with a loop:

Unix and macOS:

```sh
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/ibdesk
for f in $(ls db/migrations/*.sql | sort); do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```

Windows PowerShell:

```powershell
$env:DATABASE_URL = "postgres://postgres:postgres@localhost:5432/ibdesk"
Get-ChildItem db/migrations/*.sql | Sort-Object Name | ForEach-Object { psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f $_.FullName }
```

Or apply each file by hand, in order:

Unix and macOS:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0002_document_metadata.sql
```

Windows PowerShell:

```powershell
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f db/migrations/0002_document_metadata.sql
```

Seed the sample document, sheet, section, and cell:

Unix and macOS:

```sh
cd services/api
uv run python -m app.seed
cd ../..
```

Windows PowerShell:

```powershell
cd services/api
uv run python -m app.seed
cd ../..
```

The seed step reads DATABASE_URL from the environment, so make sure it is set in
the same shell. All seeded data is clearly labeled as sample data. It is not real
research and must never be treated as a real source.

## Run the service and the web app

Run the FastAPI service on port 8000.

Unix and macOS:

```sh
cd services/api
uv run uvicorn app.main:app --reload --port 8000
```

Windows PowerShell:

```powershell
cd services/api
uv run uvicorn app.main:app --reload --port 8000
```

In a second terminal, run the Next.js dev server on port 3000.

Unix and macOS:

```sh
pnpm --filter @ib-desk/web dev
```

Windows PowerShell:

```powershell
pnpm --filter @ib-desk/web dev
```

## What you should see

Open http://localhost:3000 in a browser. With the service running and the
database migrated and seeded, the ingestion UI shows a left sidebar that lists
the documents in the workspace, most recent first, with a clear empty state when
there are none, and a main area for the selected document.

If the service is down or the database is not connected, the page does not crash.
It degrades gracefully.

## Using the ingestion UI

Phase 1 lets you get a document into the system as clean text. There is no
extraction, grid, chart, or export yet; the goal is to verify that parsing
worked.

- Upload a PDF or a DOCX. Use the upload control to choose a file, or drag and
  drop a file onto it. The browser sends a multipart POST to /v1/documents while
  a loading state is shown during upload and parsing.
- Paste text. Use the paste control: enter a name, paste the text into the text
  area, and submit. The browser sends a JSON POST to /v1/documents.
- On success the sidebar list refreshes and the new document is selected. The
  main area shows the name, the source kind, the page count and character count,
  a clear "Not yet extracted" status, and the parsed canonical text rendered as
  whitespace-preserving preformatted text so you can confirm parsing worked.
- On a rejected upload the UI shows a clear message for each case: unsupported
  type, file too large, empty input, scanned or unreadable, and parse failed. A
  rejected document writes no row and stores no bytes, so the store stays clean.

Stored originals. With STORAGE_BACKEND=local (the default) the original bytes are
written under STORAGE_LOCAL_PATH (default ./.local-storage), keyed by the
document id. This directory is gitignored.

## Running the tests

Web checks (from the repo root):

Unix and macOS:

```sh
pnpm --filter @ib-desk/web lint
pnpm --filter @ib-desk/web typecheck
pnpm --filter @ib-desk/web build
```

Windows PowerShell:

```powershell
pnpm --filter @ib-desk/web lint
pnpm --filter @ib-desk/web typecheck
pnpm --filter @ib-desk/web build
```

Service checks (in services/api):

Unix and macOS:

```sh
cd services/api
uv run ruff check .
uv run mypy .
uv run pytest
cd ../..
```

Windows PowerShell:

```powershell
cd services/api
uv run ruff check .
uv run mypy .
uv run pytest
cd ../..
```

End to end tests with Playwright:

Unix and macOS:

```sh
pnpm --filter @ib-desk/web e2e
```

Windows PowerShell:

```powershell
pnpm --filter @ib-desk/web e2e
```

The database-backed service tests skip locally when DATABASE_URL is unset, so
the service test suite still runs green on a machine with no database. In CI,
DATABASE_URL points at a pgvector Postgres, so those tests run for real and
exercise the full round trip.

The database-backed and end to end checks in CI use the local storage backend
(STORAGE_BACKEND=local), so they need no Supabase secret. CI applies every
migration in db/migrations in sorted order before seeding, so new migrations run
automatically. The end to end job generates the PDF that the Playwright upload
test consumes from the authored test fixtures, so no binary sample file is
committed to the repository.

On Unix and macOS you can also use the Makefile shortcuts (make setup, make
migrate, make seed, make api, make web, make test, make e2e). The Makefile is
written for Unix and macOS shells; Windows users should follow the explicit
PowerShell commands above.

## Note on sample data

Every seeded value in this repository is sample data, not real research. The
seed fixture exists only to prove the Phase 0 pipe is wired end to end. No real
client document, number, source, or citation is included.

## Phase 0 implementation notes

A few concrete decisions made in Phase 0 are worth recording.

- GET /v1/documents returns a DocumentListItem, which is the table mirror
  Document plus the id of the document's one sheet (sheet_id, from a left join).
  BUILD_PLAN.md describes the list as documents only, but with exactly three
  Phase 0 endpoints the client needs the sheet id to navigate from a document to
  its sheet. The base Document type stays a faithful table mirror; sheet_id is a
  nullable augmentation on the list item only.
- The CI uv version is pinned to the same release that generated services/api/uv.lock
  so the service, e2e, and docker jobs read the committed lock without a schema
  mismatch. Bump the pin and regenerate the lock together if uv is upgraded.
- The web scaffold is hand-authored rather than generated with create-next-app.
  Hand authoring yields an identical result (App Router, strict TypeScript,
  Tailwind, ESLint, and Prettier) while staying deterministic inside the
  monorepo. A generator would pull unpinned versions and write files outside the
  workspace layout, which makes parallel builds and reproducible installs harder.
- The reserved embedding vector column on the documents table is omitted from the
  API surface and the shared TypeScript types in v1. The column exists in the
  migration as a forward-looking placeholder for future similar-sheet search, but
  it is not load bearing now, so it does not appear in the Document type, the
  pydantic models, or any Phase 0 endpoint response.
