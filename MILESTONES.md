# OpenLnk — Milestones: Gates as Quality Bars, Tracks in Parallel

Gates are quality bars, not a queue. Three tracks run simultaneously with a war-clock:
**A Engine** · **B Market** · **C Story**. Target: paid revenue + YC-ready dataset in
~28–32 weeks. Claude Code runs milestone interiors; adversarial review clears gate exits.

**Calendar anchor: wk 1 = 2026-07-10. Gate 3 exit target ≈ 2026-12-03. YC S2027 application
window opens ~2027-01 — reachable with 2-week buffer after Gate 3 exit. Gate 4 exit ≈
2027-02-11; Gate 5 exit ≈ 2027-04. Dates are indicative; gate exit is quality-gated, not
calendar-gated.**

## Track map (weeks, indicative)

```
Wk:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 ... 20 ... 26 ... 32
A:  [G0 spec][----G1 engine: text+voice+camera----][G2 build][G4 build---]
B:  [LOI pre-sales from wk1][owner interviews][--G2 pilot 25 centers--][G5 city2]
C:  [demo video + category naming][--YC app assets--][apply at G3 data][interview]
```

## Gate 0 — Spec lock (wk 1–3)
**Goal:** everything decided on paper; this pack reviewed and cleared.
- Deliverables: this pack; monorepo scaffolded per CLAUDE.md; `just dev` green; eval
  harness skeleton with frozen v0 dataset plan (EVAL-HARNESS.md); pre-flight blockers list.
- **Exit:** adversarial review clears; pre-flight blockers all closed or scheduled:
  entity/Dell review, trademark+domains, DPDP consent design, on-device benchmark run,
  webview prototype validated, unit-economics sheet v1.
- Kill condition: none (table stakes).

## Gate 1 — Extraction engine + sync protocol, dogfooded (wk 4–11, compressed target 8 wks)
**Goal:** the existential bet answered on the founder household's real English traffic.
Text + voice + camera together (1a/1b/1c sub-bars), not staged sequentially.
The sync protocol (ADR-001: WebSocket, per-context sequence numbers, delta replay) is a
Gate 1 deliverable — owners must see live commitment state changes during dogfood; polling
is not acceptable for Gate 2 field deployment.
- Requirements in scope: OL-001..029, OL-040..044, OL-050..053, OL-090..092.
- **Entry criteria (must be met before Gate 1 coding begins):**
  - v0 eval dataset FROZEN: ≥500 messages, ≥60 gold commitments, ≥15% adversarial cases
    (non-commitments that resemble commitments), per EVAL-HARNESS.md.
    **Owner: Vinod. Method: founder-synthesized (60–100 gold examples) + LLM-augmented to
    ≥500 variants. Timeline: wk 1–2 of Gate 1. Adversarial 15%: Vinod-written edge cases.**
  - Extraction Pydantic output model supports `counterparties: list[ExtractedPrincipal]`
    (OL-029b) — schema designed before the pipeline is coded
- **Exit:** precision ≥97% AND recall ≥85% across all three ingestion routes, sustained
  4 consecutive weeks live; zero cross-context leakage (OL-041 a..e); corrections loop working;
  WebSocket sync live in staging with delta replay verified.
- **Kill/pivot:** precision plateaus <93% after two model/prompt iterations → pivot to
  confirm-only commitment inbox (propose-forever), re-scope PRD.

## Gate 2 — Tuition pilot, 25 centers, Chennai English-medium (wk 10–20)
**Goal:** businesses change behavior. CEO runs every onboarding personally.
Launch posture: 25 centers + anonymized collection-lag leaderboard (movement, not pilot).
- Requirements: OL-100..107, OL-060..064, OL-120..123; agent at Propose rung field default.
  NOTE: Bounded-auto for monthly fee cycles NOT achievable in the pilot window (only ~2 fee
  cycles occur in 8 weeks vs. the 20 clean actions over 14 days required by OL-055).
  Gate 2 measures fee-lag reduction at Propose rung only. Bounded-auto for fees is a
  Gate 4 exit criterion after ≥3 months of live data.
  UPI intents live (OL-103). WA loop-close (OL-103a) live by wk 16.
- **Entry criteria (must be met before pilot go-live):**
  - Postgres PITR to S3 (ap-south-1) verified working (OL-142a)
  - businesses.whatsapp_number onboarding flow tested end-to-end
  - Fee-lag baseline measurement protocol in place (5-question intake per center capturing
    avg. days from fee-due to collection for the last 3 cycles; stored in onboarding record)
  - Sentry live in all four apps (OL-143)
- **Exit:** fee-collection lag ↓≥30% vs. per-center baseline; ≥60% parent queries closed
  without owner; week-6 unaided retention ≥70%; onboarding ≤30 min including Excel import.
- **Kill/pivot:** engagement collapses when founder visits stop → freeze features, fix
  self-serve onboarding before any scale.

## Gate 3 — The Link (wk 14–22, overlaps Gate 2 tail)
**Goal:** stranger parents converted through zero-install threads. This dataset IS the
YC application. Multi-vertical dataset adds clinic evidence alongside tuition (E3).
- Requirements: OL-080..085. Webview session prototype must have passed pre-flight.
- **Entry criteria:**
  - Legal review of `health_data:<patient_ref>` consent scope (OL-120a) COMPLETED and
    signed off before first clinic patient is onboarded (Gate 3 pre-flight blocker)
  - Team capacity declared: Gate 2+3 overlap (wk 14-20) requires explicit resource plan
    — CEO-run center onboardings + web-thread build + clinic outreach simultaneously.
    If single-founder, state which track is time-boxed.
- **Exit:** open ≥50% · unprompted return ≥25% within 2 wks · install ≥10% at the
  ≥2-thread offer. Funnel instrumented per center and message class.
  ADD: ≥1 non-tuition vertical (clinic) onboarded with ≥10 active commitments.
- **Decision point:** metrics cleared → YC application filed (Track C), CEO interviews.
- **Kill/pivot:** opens high, returns ~0 → consumer ledger thesis fails; pivot to pure
  B2B tool; re-price ambition honestly before raising.

## Gate 4 — Household companion (wk 22–32)
**Goal:** installed parents become households; public positioning: "the companion that
keeps your word."
- Requirements: OL-008 (assignment-forced invites), OL-070..073 (calendar fusion),
  OL-054..057 (Bounded-auto), OL-093 (learning loop), daily brief as retention surface.
- **Entry criteria (must be completed before Gate 4 coding begins):**
  - Group commitment state machine extension fully designed: per-participant `confirmed_at`,
    acceptance semantics (owner accepts for the group), partial-completion policy (7/10
    participants confirm → commitment stays `in_progress`, not `done`), opt-out without
    cancelling the whole commitment. This spec is a Gate 4 entry blocker.
  - Calendar connector `propose_event` method spec'd for write-capable implementation at
    Gate 5 (interface contract only; no implementation required at Gate 4 entry).
  - Daily brief product spec completed: content algorithm, delivery channel (push + in-app),
    personalization logic, "silence score" UI definition.
- **Exit:** K ≥0.4 from assignment loop · D30 ≥40% (households ≥3 commitments/wk) ·
  notification volume per user **declining** while retention holds (D4 proof).
- **Kill/pivot:** merchant threads used, family contexts never activate → run wedges as
  two products on one engine; drop the forced marriage.

## Gate 5 — Revenue & repeatability (wk 30–44)
**Goal:** paid, self-serve, second city with zero founder onboarding; category named
publicly ("commitment-native communication").
- Requirements: OL-106..107 billing; vertical #2 (clinics, ClinicBharat skeleton);
  five-city champions program prepared (commission-only local sellers).
- **Exit:** pilot→paid ≥40% · CAC payback <3 months · logo churn <5%/month ·
  ≥25 parent threads seeded per new center · city-2 fully self-serve.
- **Kill/pivot:** city-2 needs the founder in the room → services business in SaaS
  costume; fix motion before city 3.

## Post-Gate 5 horizon (named, not scheduled)
$2–3M seed at demo day · Tamil + vernacular moat · on-device extraction upgrade (ADR-002
revisit) · protocol publication (ADR-001 open check) · desktop Tauri wrapper ·
MCP connectors · payment reconciliation webhooks · trust-graph products (carefully).

## Standing rules at every gate
Feature test: create/protect/close a commitment. Silence metric reported. No engagement
mechanics. Adversarial review at boundaries. Rungs never skipped. BLOCKED.md over
workarounds. Excel import and ≤30-min onboarding remain hard requirements from Gate 2 on.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | messenger-first confirmed; ADR-008 added |
| Codex Review | `/codex review` | Independent 2nd opinion | 2 | ran (claude subagent) | issues_found both runs |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | issues_open (PLAN) | 12 issues, 2 critical gaps, 0 unresolved |
| Design Review | `/design-review` | UI/UX gaps | 1 | PASS (FULL) | 7 fixes applied, 2 deferred, Gate verdict: PROCEED |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** Design Review CLEARED (FULL PASS 2026-07-10). Eng Review ran — 12 architecture findings, all decisions resolved, 0 unresolved. 2 critical gaps tracked as implementation tasks (T8: OL-041 RLS tests, T12: Pydantic ValidationError handling). Ready to implement Gate 1.

**Key architecture decisions locked by this review:**
- Two Redis instances: `redis-jobs` (AOF, arq workers) + `redis-extraction` (no persistence, ADR-002)
- Migration 0001 = Gate 1 required deliverable (RLS on thread_participants + autonomy_grants + consent_events + guest policy)
- thread_tokens: multi-use TTL-based (rotated_from removed)
- Extraction timeout: 60s (text) / 120s (voice/camera), hard cancel + visible error
- `openlnk_app` DB role: no UPDATE/DELETE on audit_log, no service-key at runtime
- ConnectorABC Protocol in CLAUDE.md + import-linter CI enforcement
- DailyBriefService: single JOIN query, <200ms at 100 commitments
- OL-041a..e RLS isolation tests = Gate 1 exit blockers
- Sync protocol (WebSocket + delta replay) = Gate 1 deliverable
- UPI iOS fallback: copyable VPA text + client-side QR code on non-Android
- v0 eval dataset: Vinod-synthesized, 60–100 gold examples, LLM-augmented to ≥500, week 1–2 Gate 1

NO UNRESOLVED DECISIONS
