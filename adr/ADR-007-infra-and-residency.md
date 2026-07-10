# ADR-007 — Infra: Supabase-Mumbai Postgres (DB-only), VPS API, India Residency

**Status:** Accepted (Gate 0)

## Decisions
1. **Postgres: Supabase, ap-south-1 Mumbai — as a managed database only.** Native RLS for
   the two isolation axes, PITR backups, monthly restore drills (OL-142). No Supabase
   auth/product lock-in: FastAPI owns auth and access. Rationale: children's data + a
   part-time team ⇒ self-managed backup discipline is a risk not worth signing.
2. **API + workers:** Docker Compose on a Mumbai VPS (Hostinger pattern), Caddy for TLS and
   per-IP rate limiting. Boring, cheap, sufficient through Gate 5.
3. **Auth:** phone-OTP via **MSG91** (Indian provider, predictable per-OTP paise for the
   unit-economics sheet, one fewer US-tech dependency in a privacy-branded product).
4. **Push:** Expo Push (FCM transport). **Observability:** Sentry in all four apps
   (OL-143), structlog JSON, OTel instrumentation now / dashboards later, Uptime Kuma.
5. **Secrets:** gitignored `.env` locally; **Infisical** for shared/prod; gitleaks
   pre-commit; SSH-only git remotes. (The IntelliLab credential lessons, encoded as
   tooling: no PATs, no committed passwords, rotate on any suspicion.)
6. **Residency:** all personal data in Mumbai region (OL-122). LLM provider endpoints and
   data-processing terms reviewed against DPDP before Gate 2 field deployment; provider
   choice recorded in the unit-economics sheet alongside cost.
7. **Environments:** `dev` (local compose) / `staging` (VPS) / `prod` (VPS, separate DB).
   Alembic migrations gated by the standing rule: verify with `\d` on the target DB;
   never trust `alembic current` alone.

## Consequences
+ DPDP-grade ops on a shoestring; one command surface (`just`) across all environments.
− VPS single-node until Gate 5; accepted, with restore drills as the real insurance.
