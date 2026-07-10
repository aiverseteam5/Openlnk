# OpenLnk — Product Requirements Document (Gate 0)

## 1. Vision

Communication where **promises, not messages, are the unit of record** — and your attention
is spent only where you are the blocker. Endgame: the trust protocol of the service economy.
UPI standardized money movement in India; OpenLnk standardizes promise movement.

**One-liner:** *WhatsApp delivers your messages. OpenLnk keeps your promises.*

## 2. Problem statement

Messaging apps are optimized for delivery, not accountability. The 2B+ people who run their
families and the 350M+ micro/small businesses that run customer relationships through chat
have no system of record for what was promised, to whom, and by when. The result is a silent,
universal tax: missed pickups, forgotten follow-ups, no-show appointments, unpaid fees chased
manually, and the cognitive load of being your own secretary across a dozen scrolling threads.

OpenLnk is the first **commitment-native communication network** — a messenger where every
conversation automatically becomes a tracked, calendar-aware, agent-managed set of
obligations, and your attention is interrupted only when you are the bottleneck.

## 3. Why now

1. LLMs make reliable obligation extraction from messy human conversation feasible for the
   first time — the arbitrage moment, equivalent to WhatsApp's SMS-cost arbitrage in 2010.
2. Meta banned general-purpose AI assistants from the WhatsApp Business Platform
   (effective 2026-01-15) and its terms prohibit Business Services for personal/family use.
   The agent layer structurally cannot be built on the incumbent's rails.
3. US mental-load assistants (Ohai, Milo, Maple) prove willingness to pay for this job at
   $10–40/month while leaving India entirely unserved; Indian coaching ERPs (Classplus,
   Teachmint) prove the vertical at 70M-student scale while remaining one-way, non-agentic
   admin tools. The seam between these facts is OpenLnk-shaped. Window: 12–18 months before
   OS-level extraction (Google/Apple) is commoditized.

## 4. Personas

- **P1 — Center owner (buyer):** runs a Chennai English-medium tuition center, 30–200
  students, chases fees monthly by hand, drowns in parent queries in batch WhatsApp groups.
  Pays ₹1,500–2,500/month if fee lag provably drops.
- **P2 — Household coordinator (growth engine):** the parent who carries the family's mental
  load. Enters via a center link; converts to the app when the unified ledger becomes
  visible; activates the household context; assigns commitments (the viral loop).
- **P3 — Counterparty parent / family member:** zero-install web-thread user first;
  assignment-invited household member second.

## 5. Differentiators (testable claims — every spec decision is checked against these)

| # | Claim | Test |
|---|---|---|
| D1 | The unit is the promise, not the message | Two parties see the same obligation object with owner, due, state |
| D2 | OpenLnk never invents a promise | Published precision ≥97%; provenance from every commitment to its source |
| D3 | Zero-install for the other side | Stranger time-to-first-value < 10 s via link |
| D4 | Success measured in silence | Notification volume per user declines while retention holds |
| D5 | The promise carries the payment | Fee committed → paid via UPI without leaving the thread |
| D6 | DPDP-native | Verifiable-consent architecture for child-linked data from day one |

## 6. Core product concepts

- **Commitment:** shared two-party object. Fields: owner, counterparty, title, due, state
  machine (`proposed → accepted → in_progress → done | broken | cancelled`), class
  (`fee | schedule | task | payment | custom`), provenance pointer, version, context.
- **Context:** auto-clustered container (typed `household` | `business_batch`). Contexts are
  formed by the agent from signal, not by users tapping "New Group".
- **Autonomy ladder (ADR-003):** Observe → Propose → Bounded-auto → Trusted-auto, graduated
  per contact × commitment-class on visible track record. Weeks, not months — but no skipping.
- **Daily brief:** the retention surface. "How your day looks", conflicts surfaced before they
  occur, commitments at risk, and *nothing else*.
- **The link mechanic:** every business message is an openlnk.in link opening a zero-install
  thread (ADR-005). Every assignment is an invite (household loop).
- **Ingestion:** in-thread chat, voice notes, camera capture of circulars/notices/receipts,
  and forward-to-OpenLnk. All routes converge on the same extraction pipeline.

## 7. Success metrics by gate (full detail in MILESTONES.md)

Gate 1: precision ≥97% / recall ≥85%, 4 consecutive weeks, text+voice+camera.
Gate 2: fee-collection lag ↓≥30%; ≥60% parent queries closed without owner; W6 retention ≥70%.
Gate 3: link open ≥50%; unprompted return ≥25%; install ≥10% (offer only at ≥2 active threads).
Gate 4: K ≥0.4 from assignment loop; D30 ≥40% (households ≥3 commitments/week); notifications ↓.
Gate 5: pilot→paid ≥40%; CAC payback <3 months; churn <5%/month; ≥25 threads seeded/center.

## 8. Anti-roadmap (named rejections — do not relitigate under pressure)

- No feeds, stories, channels, stickers, streaks, or any engagement mechanic.
- No emotional-companion persona (AlphaMa's lane). The companion keeps promises, not company.
- No meal planners / chore charts / notes bundles (Maple's sprawl). Single-player features
  that don't touch a two-party commitment do not ship.
- No content-selling / branded-app machinery (Classplus's business, not ours).
- No commerce integrations (Instacart-style) before Gate 5+.
- No desktop app before Gate 5+ (then: Tauri wrapper over web-owner, ~1 week).
- No Matrix/federation before the protocol story matures (ADR-001).
- **The test for every proposed feature: does it create, protect, or close a commitment?**

## 9. Monetization

- Household side: free. Trust brand + consumer graph, not the revenue engine.
- Business side: ₹1,500–2,500/month per center (Razorpay subscription). ROI framing in-product:
  "fees recovered this month" vs subscription cost on the owner home screen.
- Center↔parent settlement: UPI intent deep-links, funds never touch OpenLnk (ADR-006).

## 10. Structure & operating model

- Entity: TynkAI. Founder/CEO runs Gates 2–3 field execution personally (sales, onboarding,
  YC interview). Technical advisor mentors architecture and reviews gates.
- Tracks run in parallel (MILESTONES.md): A Engine · B Market (LOI pre-sales from week 1) ·
  C Story (YC application, category naming, camera-flow demo video).
