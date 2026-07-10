# ADR-005 — web-thread: Zero-install Link Mechanic (Preact PWA)

**Status:** Accepted (Gate 0) · **The Gate 3 funnel lives or dies here.**

## Context
Differentiator D3: the counterparty installs nothing. Links will overwhelmingly be opened
inside the **WhatsApp in-app webview** on ₹10k Android phones — a hostile environment with
unreliable cookies, no service-worker persistence guarantees, and weak hardware.

## Decision
- **Stack:** Vite + Preact (`preact/compat`), one screen, no router, hand-rolled Tailwind.
  No design-system imports.
- **Performance budget as failing tests:** ≤120 KB gzipped total (size-limit in CI);
  interactive <3 s on throttled Moto-G Lighthouse CI profile (OL-080, OL-084).
- **Token design (security review item):** links carry a signed JWT scoped to exactly one
  thread, short-lived, rotating on use; refresh happens transparently while the session is
  live. Compromised link = one thread, time-boxed, revocable server-side. Per-thread rate
  limiting (OL-144).
- **Session persistence:** localStorage primary, cookie fallback, token re-issue via the
  original link if both are wiped (OL-082). **Pre-flight prototype:** link → thread →
  return next day inside WhatsApp webview with history intact — validated before Gate 3
  spec is considered buildable.
- **Install offer discipline:** only at ≥2 active threads (OL-083) — the unified-ledger
  moment. Never a nag before it.
- **Funnel instrumentation from first deploy:** open / return / install per center and per
  message class (OL-085). This dataset *is* the YC application.

## Consequences
+ CAC ≈ ₹0 distribution; strangers reach value in <10 s; the incumbent's network becomes
  our rail (links forwarded inside WhatsApp groups).
− Webview quirks are a moving target; mitigated by the budget, the prototype gate, and
  long-poll fallback (ADR-001).
