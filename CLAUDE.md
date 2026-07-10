# CLAUDE.md — OpenLnk Monorepo

You are building **OpenLnk**: commitment-native communication. The atomic unit is the
**commitment** (a shared, two-party obligation with owner, counterparty, due, state,
provenance), not the message. Read `PRD.md` before any milestone.

## Design System

Always read `DESIGN.md` before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match `DESIGN.md`.

Key rules enforced by DESIGN.md:
- DM Sans (UI) + JetBrains Mono (amounts/dates/IDs/state) — no other fonts
- `#F5F2EC` page background, `#FFFFFF` card surface, `#1A4FBF` accent — no gradients
- State as ALL-CAPS JetBrains Mono label, no icon, no toast, no animation
- 3px left state-color bar on commitment cards — state is read before title
- No dark mode, no avatars, no skeleton loaders, no bottom tab bars, no emoji keyboards

## Repository layout

```
openlnk/
├── apps/
│   ├── api/            # FastAPI (Python 3.12, uv). routers/ services/ connectors/ workers/
│   ├── mobile/         # Expo (dev-client) + React Native + NativeWind v4
│   ├── web-owner/      # React + Vite + MUI + TanStack Query + Zustand (center console)
│   └── web-thread/     # Preact + Vite PWA (Gate 3 link mechanic). Perf-budgeted.
├── packages/
│   ├── schema/         # OpenAPI spec (source of truth) + generated TS types + error taxonomy
│   ├── api-client/     # Generated TS client (openapi-typescript). NEVER hand-edited.
│   ├── ui/             # Shared design tokens (colors/spacing/type). Tokens, not components.
│   └── eval/           # Extraction eval harness (see EVAL-HARNESS.md)
├── adr/                # Architecture decision records
├── justfile            # Single command surface: just dev|test|lint|eval|gen
├── REQUIREMENTS.md     # EARS requirements OL-###
├── MILESTONES.md       # Gates, tracks, exit metrics
└── BLOCKED.md          # Deviation log
```

## Build model

- Claude Code runs milestone interiors autonomously; chains on adversarial-review clearance.
- Surface only architecture-shaping forks to the reviewer. Everything else: decide, note in PR.
- Adversarial review (second model instance) at every gate boundary before merge to main.
- Any deviation from spec goes through `BLOCKED.md` — never a silent code workaround.
- Trunk-based development. Short-lived branches. Conventional Commits. PR review is the
  reviewer flow (no patch/`git am` flow in this repo). release-please for changelogs.

## Sacred rules (violations fail review automatically)

1. Extraction precision ≥ 97% — enforced by `packages/eval` CI job on every prompt/model change.
2. Autonomy ladder rungs never skipped (ADR-003). The policy engine decides; the LLM only proposes.
3. Raw conversation content is never written to any persistent store server-side (ADR-002).
4. RLS on `household_id` / `business_id` at the DB layer. App-layer-only filtering fails review.
5. Every feature PR states which commitment lifecycle stage it serves: create / protect / close.
6. Every mutation endpoint requires an idempotency key. Every commitment write checks `version`.

## Python standards (apps/api)

- Python 3.12, uv workspace, `pyproject.toml`. Layering: routers → services → connectors.
  Routers hold zero business logic. Connectors hold zero business logic.
- Pydantic v2 everywhere; LLM outputs parsed into Pydantic models before touching services.
- ruff (lint + format, no Black), mypy `--strict`. Both in pre-commit and CI.
- pytest; **every test carries a requirement marker**: `@pytest.mark.req("OL-042")`.
  CI fails if any active-milestone requirement in REQUIREMENTS.md has zero passing tests.
- Integration tests via testcontainers-Postgres. No mocking the DB in integration tests.
- Errors: RFC 9457 `application/problem+json`, typed taxonomy in `packages/schema`.
- structlog JSON logging; OpenTelemetry instrumentation on all routers and workers.
- Async workers: arq on Redis. All scheduled sends (reminders) go through workers, never inline.
- Migrations: Alembic. **Note the standing gotcha:** verify schema with `\d table` on the real
  DB after migrating; never trust `alembic current` alone.

## TypeScript standards (all JS apps/packages)

- `strict: true`. No `any` without an inline `// any-justified:` comment.
- ESLint 9 flat config + Prettier. pnpm workspaces + Turborepo (JS packages only).
- zod validation at every runtime boundary: API responses, deep links, storage reads.
- Types come from `packages/api-client` (generated). CI runs the drift gate:
  regenerate from `apps/api` OpenAPI export; fail if committed spec differs.
- State: TanStack Query for server state; Zustand for local state. No Redux.
- Mobile styling: NativeWind v4. Web-owner: MUI. web-thread: hand-rolled Tailwind only.

## web-thread performance budget (CI-enforced, failing test not guideline)

- ≤ 120 KB gzipped total JS+CSS (`size-limit`).
- Interactive < 3 s on throttled Moto-G-class Lighthouse CI profile.
- No design-system imports. Preact via `preact/compat`. One screen, no router.

## Testing pyramid (all blocking in CI)

pytest (api) · Jest + RN Testing Library (mobile units) · Maestro (mobile E2E happy paths) ·
Playwright (web-owner, web-thread) · `packages/eval` (extraction precision/recall).

## Security & secrets

- gitleaks in pre-commit. No credential ever committed (standing lesson — enforced by tooling).
- Local: gitignored `.env` (set multiline creds via `read -rs`, terminals corrupt pastes).
- Shared/prod: Infisical. SSH keys only for git remotes; no PATs.
- OWASP ASVS L2 checklist at each gate review. Dependabot + pip-audit + pnpm audit weekly.
- Rate limiting at Caddy (IP) and in FastAPI (per-token). Thread tokens per ADR-005.
- DPDP: consent events are audit-log entries. Child-linked data per ADR-002 §DPDP.

## API standards

- `/v1` prefix from day one. Breaking changes only at gate boundaries.
- Cursor pagination only. Idempotency-Key header honored on all POST/PATCH.
- Commitment writes carry `version` (optimistic concurrency); stale write → 409 problem+json.

## Prompts & models

- Prompts are versioned files in `apps/api/prompts/`, referenced by hash in the audit log.
- Provider access through one adapter in `services/llm/`. Structured outputs → Pydantic.
- **Any change to a prompt, model, or extraction pipeline must pass `just eval` in CI
  before merge.** The 97% bar is a merge gate, mechanically.
