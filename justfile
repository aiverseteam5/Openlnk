# OpenLnk — single command surface
# Usage: just <recipe>

set dotenv-load

# Default recipe
default:
    @just --list

# ─── Development ───

# Start all services (Postgres + Redis × 2)
up:
    docker compose up -d

# Stop all services
down:
    docker compose down

# Start API dev server
dev-api:
    cd apps/api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start all dev servers
dev: up dev-api

# ─── Database ───

# Run Alembic migrations
migrate:
    cd apps/api && uv run alembic upgrade head

# Create a new migration
migration name:
    cd apps/api && uv run alembic revision --autogenerate -m "{{name}}"

# Verify schema with \d (standing gotcha: never trust alembic current alone)
db-verify table:
    docker compose exec postgres psql -U openlnk_app -d openlnk_dev -c "\d {{table}}"

# ─── Testing ───

# Run all Python tests
test:
    cd apps/api && uv run pytest -v --ignore=tests/test_rls_isolation.py

# Run tests with requirement marker
test-req req:
    cd apps/api && uv run pytest -v -m "req('{{req}}')"

# Run Playwright E2E tests (web-owner + web-thread)
test-e2e:
    pnpm --filter web-owner build && pnpm --filter web-thread build && npx playwright test

# Run RLS isolation tests (OL-041 — Gate 1 exit blocker)
test-rls:
    cd apps/api && uv run pytest -v -k "test_rls"

# Run extraction eval harness
eval:
    cd packages/eval && uv run python -m eval_harness

# ─── Lint & Format ───

# Lint + format Python
lint-py:
    cd apps/api && uv run ruff check . && uv run ruff format --check .

# Type check Python
typecheck:
    cd apps/api && uv run mypy --strict .

# Lint all JS/TS
lint-ts:
    pnpm -r run lint

# All lints
lint: lint-py typecheck lint-ts

# ─── Code Generation ───

# Regenerate TS client from OpenAPI spec
gen:
    cd packages/api-client && pnpm run generate

# ─── Size Budget ───

# Check web-thread bundle size (≤120KB gzip gate)
size-check:
    cd apps/web-thread && pnpm run size
