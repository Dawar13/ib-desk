# IB Desk developer tasks.
#
# NOTE: these make targets are written for Unix and macOS shells. Windows users
# should follow the explicit step-by-step commands in README.md, which lists the
# PowerShell equivalents for each task below.

# DATABASE_URL is read from the environment for migrate and seed.
DATABASE_URL ?=

.DEFAULT_GOAL := help

.PHONY: help setup web api dev migrate seed test e2e docker-build

help:
	@echo "IB Desk make targets (Unix and macOS; Windows users see README.md):"
	@echo "  setup         Install web deps (pnpm install) and service deps (uv sync)"
	@echo "  web           Run the Next.js dev server on port 3000"
	@echo "  api           Run the FastAPI service with uvicorn on port 8000"
	@echo "  dev           Run the service and the web app together"
	@echo "  migrate       Apply db/migrations/0001_init.sql with psql using DATABASE_URL"
	@echo "  seed          Insert the sample seed row set via the service CLI"
	@echo "  test          Run web checks and service pytest"
	@echo "  e2e           Run the Playwright end to end tests"
	@echo "  docker-build  Build the service Docker image (services/api)"

setup:
	pnpm install
	cd services/api && uv sync

web:
	pnpm --filter @ib-desk/web dev

api:
	cd services/api && uv run uvicorn app.main:app --reload --port 8000

dev:
	$(MAKE) -j2 api web

migrate:
	psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql

seed:
	cd services/api && uv run python -m app.seed

test:
	pnpm --filter @ib-desk/web lint
	pnpm --filter @ib-desk/web typecheck
	pnpm --filter @ib-desk/web build
	cd services/api && uv run ruff check .
	cd services/api && uv run mypy app
	cd services/api && uv run pytest

e2e:
	pnpm --filter @ib-desk/web e2e

docker-build:
	docker build -t ib-desk-api services/api
