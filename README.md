# IB Desk

IB Desk turns any research document about a company, a market, a person, a
technology, or a deal into one clean, dynamic spreadsheet per document, where
every extracted value is grounded back to its exact supporting sentence in the
source. This repository is the monorepo for the product: a Next.js web app, a
FastAPI service, a shared TypeScript types package, and a Postgres schema with
pgvector reserved for future similar-sheet search. This README is the full local
bring-up guide, so a fresh clone can run from this document alone.

Phase 0 is a wiring proof only. There is no document parsing, no model calls, no
authentication, and no real spreadsheet UI yet. The home page proves that the
path web -> service -> database -> back is connected, by reading a health
endpoint and rendering a single seeded sample sheet. See BUILD_PLAN.md for the
phase roadmap and CLAUDE.md for the principles and conventions.

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

The settings that matter in Phase 0:

- DATABASE_URL: the asyncpg connection string for your Postgres, for example
  postgres://postgres:postgres@localhost:5432/ibdesk. The service reads this to
  open its connection pool, and the migrate and seed steps read it too. When it
  is unset, the service still starts and reports the database as disconnected.
- WEB_ORIGIN: the allowed CORS origin for the web app, default
  http://localhost:3000.
- APP_VERSION: the version string the health endpoint reports, default 0.1.0.
- NEXT_PUBLIC_API_BASE_URL: the base URL the web app uses to reach the service,
  default http://localhost:8000.

Several additional keys (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, the STORAGE_
keys, and OPENAI_API_KEY) are reserved in services/api/.env.example for later
phases. They are documented there only and are not read by any Phase 0 code.

## Apply the migration and seed

Set DATABASE_URL in your shell so the migration and seed steps can reach your
database, then apply the schema and insert the sample row set.

Apply the migration:

Unix and macOS:

```sh
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/ibdesk
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql
```

Windows PowerShell:

```powershell
$env:DATABASE_URL = "postgres://postgres:postgres@localhost:5432/ibdesk"
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql
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
database migrated and seeded, the page shows:

- A clear "Connected" indicator, derived from the health endpoint database field.
- The seeded sheet titled "Sample sheet".
- Its "Overview" section label.
- The single seeded sample cell value rendered as plain text.

If the service is down or the database is not connected, the page does not crash.
It shows a "Not connected" indicator and degrades gracefully.

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

On Unix and macOS you can also use the Makefile shortcuts (make setup, make
migrate, make seed, make api, make web, make test, make e2e). The Makefile is
written for Unix and macOS shells; Windows users should follow the explicit
PowerShell commands above.

## Note on sample data

Every seeded value in this repository is sample data, not real research. The
seed fixture exists only to prove the Phase 0 pipe is wired end to end. No real
client document, number, source, or citation is included.

## Phase 0 implementation notes

Two concrete decisions made in Phase 0 are worth recording.

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
