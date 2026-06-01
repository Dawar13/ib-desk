# Staging deploy runbook

This runbook stands up the IB Desk staging environment for Phase 0: a Supabase
Postgres database, the FastAPI service on Fly.io, and the Next.js web app on
Vercel. The Phase 0 acceptance for deployment (test 10) is that the deployed
service answers GET /health with the database reported as connected.

There is no real research data in Phase 0. Only the labeled sample seed is
loaded. Do not load any real client document until the confidentiality gate in
CLAUDE.md section 9 is decided.

Secrets are never committed. The database connection string lives only in a
local, gitignored services/api/.env and in the Fly secret store.

## Accounts you create (one time)

1. Supabase account and a new project (free tier is fine). Postgres includes the
   pgvector extension that the migration enables.
2. Fly.io account. Fly requires a payment card on file even for small machines.
3. Vercel account (hobby tier is fine).

## Step 1: Supabase database

1. Create a new Supabase project and wait for it to finish provisioning.
2. In Project Settings, Database, Connection string, copy the Session pooler URI.
   The Session pooler is IPv4 and works with prepared statements, which suits the
   asyncpg pool. Make sure the URI ends with `?sslmode=require` (add it if it is
   not present). It looks like:
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require`
3. Save it locally so it is never committed:
   - Create services/api/.env (this path is gitignored) containing one line:
     `DATABASE_URL=postgresql://...?sslmode=require`

The migration and seed are then applied to this database. With the connection
string in services/api/.env, the migration is applied with asyncpg and the seed
is run with the canonical seed module:

```
uv run --directory services/api python -m app.seed
```

The migration itself (db/migrations/0001_init.sql) can be applied either from the
Supabase SQL editor by pasting the file, or programmatically against the same
DATABASE_URL. The seed is always run from the canonical module so it stays the
single source of truth.

## Step 2: Fly.io service

1. Authenticate the Fly CLI in a terminal (this opens a browser):
   ```
   fly auth login
   ```
2. Pick a globally unique app name and create the app. Update the `app` field in
   services/api/fly.toml to match:
   ```
   fly apps create <app-name>
   ```
3. Set the database secret (the value comes from services/api/.env, so it is not
   typed by hand here):
   ```
   fly secrets set DATABASE_URL="<the Session pooler URI>" --app <app-name>
   ```
4. Deploy from the service directory (Fly uses the remote builder, no local
   Docker needed):
   ```
   fly deploy --config services/api/fly.toml --dockerfile services/api/Dockerfile services/api
   ```
5. Confirm the acceptance check. This is Phase 0 test 10:
   ```
   curl https://<app-name>.fly.dev/health
   ```
   Expect a body with `"database":"connected"` and `"status":"ok"`.

## Step 3: Vercel web

1. Authenticate Vercel in a terminal (opens a browser):
   ```
   npx vercel login
   ```
2. Deploy the web app. Set the root directory to apps/web and the API base URL to
   the Fly service URL from Step 2:
   ```
   npx vercel deploy --cwd apps/web --build-env NEXT_PUBLIC_API_BASE_URL="https://<app-name>.fly.dev" --prod
   ```
   In a pnpm monorepo, set the Vercel project Root Directory to apps/web and the
   install command to run at the workspace root so @ib-desk/shared resolves. The
   environment variable NEXT_PUBLIC_API_BASE_URL must point at the Fly service.
3. Allow the web origin for CORS on the service, then restart it:
   ```
   fly secrets set WEB_ORIGIN="https://<your-web>.vercel.app" --app <app-name>
   ```

## Step 4: Confirm the full pipe

Open the Vercel URL. The page should show a green Connected indicator, the title
Sample sheet, the Overview section, and the sample cell value, all read from
Supabase through the Fly service.

## Notes

- Fly health checks pass on any HTTP 200, and GET /health returns 200 even when
  the database is down (reporting status degraded). The acceptance check is the
  body reporting database connected, verified with curl, not the Fly check alone.
- If asyncpg cannot connect, confirm the URI uses the Session pooler host and ends
  with `?sslmode=require`.
- Teardown to avoid charges: `fly apps destroy <app-name>`, remove the Vercel
  project, and pause or delete the Supabase project.
