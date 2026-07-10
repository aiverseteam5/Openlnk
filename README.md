# OpenLnk — Gate 0 Spec Pack (Stage 0)

**Product:** OpenLnk — commitment-native communication. The unit of record is the promise, not the message.
**One-liner:** WhatsApp delivers your messages. OpenLnk keeps your promises.
**Entity:** TynkAI. **Founding market:** Chennai, English-medium tuition centers → households.

## Pack contents

| File | Purpose |
|---|---|
| `CLAUDE.md` | Build conventions, code standards, agent workflow (root of monorepo) |
| `PRD.md` | Vision, problem, personas, differentiators, anti-roadmap |
| `REQUIREMENTS.md` | EARS requirements with `OL-###` IDs (CI coverage gates key off these) |
| `adr/ADR-001` … `ADR-007` | Architecture decisions (transport, privacy, policy engine, mobile, PWA, payments, infra) |
| `DB-SCHEMA.sql` | Postgres schema: commitment graph, contexts, RLS axes, audit log |
| `openapi.yaml` | v1 API contract (contract-first; TS client generated from this) |
| `MILESTONES.md` | Gates 0–5, parallel tracks A/B/C, exit metrics, kill conditions |
| `EVAL-HARNESS.md` | Extraction eval spec: labeling rubric, precision/recall CI gates |
| `BLOCKED.md` | Deviation log (no silent workarounds — SOP) |

## Non-negotiables (sacred rules)

1. **Precision ≥ 97%** on commitment extraction. "OpenLnk never invents a promise." Merge-gated in CI.
2. **Autonomy ladder:** Observe → Propose → Bounded-auto → Trusted-auto. No rung-skipping, ever, including demos.
3. **Every feature must create, protect, or close a commitment.** Otherwise it does not ship.
4. **Silence is a metric.** Notifications avoided is reported alongside retention.
5. **Two hard isolation axes** (`household_id`, `business_id`) enforced at the DB layer (RLS), not the app layer.
6. **Raw conversation content is never persisted server-side.** Ephemeral extraction only (ADR-002).
7. **No engagement mechanics** — no feeds, stories, personas, streaks. See PRD anti-roadmap.

## Pre-flight blockers (must clear before Gate 1 code)

- [ ] Entity registration (TynkAI), founder/advisor agreements, Dell employment-clause review
- [ ] Trademark search: "OpenLnk" (IN Class 9/42, US); register openlnk.ai + openlnk.in
- [ ] DPDP consent architecture sign-off (children's data — see ADR-002 §DPDP)
- [ ] On-device inference benchmark (1 week bake-off — ADR-002 §Benchmark; hybrid assumed, benchmark holds veto)
- [ ] WhatsApp in-app webview session-persistence prototype (ADR-005 §Webview)
- [ ] Unit-economics sheet: inference + OTP cost per center/month vs ₹2,000 pricing
