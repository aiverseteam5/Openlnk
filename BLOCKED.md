# BLOCKED.md — Deviation Log + Pre-flight Checklist (SOP: no silent workarounds)

Any deviation from REQUIREMENTS.md, an ADR, or CLAUDE.md is recorded here BEFORE the
workaround is merged, with: date · requirement/ADR id · what blocked · proposed deviation ·
approver · expiry/remediation plan. An empty deviation table is the goal state.

## Deviations

| Date | Ref | Blocked by | Deviation | Approver | Remediation due |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

---

## Pre-flight Checklist (Gate 0 exit → Gate 1 entry)

Items that must be resolved before Gate 1 coding begins. Each item blocks the start of
extraction engine implementation.

| Item | Owner | Status | Notes |
|---|---|---|---|
| Entity/legal review — TynkAI incorporation | CEO | OPEN | — |
| Trademark + domain — openlnk.in registered | CEO | OPEN | — |
| DPDP consent design — legal sign-off on consent_events schema | CEO + Legal | OPEN | Required before Gate 2 center onboarding |
| On-device extraction benchmark run | Tech Advisor | OPEN | For ADR-002 revisit decision at Gate 5 |
| WA in-app webview prototype validated on physical Moto G device | Eng | OPEN | Gate 3 pre-flight; blocks Gate 3 entry |
| Unit economics sheet v1 — CAC, LTV, payback calc | CEO | OPEN | — |
| v0 eval dataset frozen (≥500 msgs, ≥60 gold, ≥15% adversarial) | Founder | OPEN | Gate 1 entry blocker; see EVAL-HARNESS.md |
| MSG91 fallback OTP provider configured in Infisical + staging test | Eng | OPEN | Gate 2 entry blocker; OL-146a |
| Postgres PITR to S3 (ap-south-1) verified restore | Eng | OPEN | Gate 2 entry blocker; OL-142a |
| Fee-lag baseline measurement protocol — 5Q intake instrument drafted | CEO | OPEN | Gate 2 entry blocker |
| DPDP `health_data:<patient_ref>` consent scope — legal review | CEO + Legal | OPEN | Gate 3 entry blocker; OL-120a |
| Team resource plan for Gate 2+3 overlap (wk 14-20) declared | CEO | OPEN | States second hire or solo-with-timeboxing |
| WA Business Platform policy changelog — monthly monitoring set up | CEO | OPEN | ADR-008 standing review |

---

## Standing Rules

- Feature test: create / protect / close a commitment. Silence metric reported.
- No engagement mechanics. Adversarial review at every gate boundary.
- Rungs never skipped (ADR-003). BLOCKED.md over silent workarounds.
- Excel import and ≤30-min onboarding remain hard requirements from Gate 2 on.
