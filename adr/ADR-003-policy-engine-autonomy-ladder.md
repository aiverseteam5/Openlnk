# ADR-003 — Deterministic Policy Engine & Autonomy Ladder

**Status:** Accepted (Gate 0) · **Pattern provenance:** OpsForge (LLM proposes, engine decides)

## Context
A wrong auto-message to a spouse or a hallucinated fee demand to 200 parents is an
extinction-level trust event. Autonomy must be earned, bounded, auditable, and reversible.

## Decision
1. **Separation of powers.** The LLM produces *proposals* (Pydantic objects: draft message,
   suggested state change, suggested schedule). A pure-Python deterministic policy engine is
   the only component that executes sends or state mutations. No LLM output reaches a send
   path without passing the engine.
2. **Ladder.** Rungs per (contact × commitment-class):
   - `observe` — extract & display only
   - `propose` — one-tap approval required (Gate 2 field default)
   - `bounded_auto` — auto-send whitelisted deterministic classes only (reminder,
     confirmation), inside quiet-hour policy
   - `trusted_auto` — negotiation-class actions (reschedule proposals) — Gate 4+, opt-in
3. **Graduation.** One rung at a time; default 20 clean actions over ≥14 days; the track
   record is shown to the user at the graduation prompt (OL-055). Any user correction
   demotes one rung (OL-056). Per-context kill switch to `observe` (OL-057).
4. **Audit.** Every engine decision (allow/deny/queue) and every agent action is an
   immutable audit row: actor=agent, rung, policy rule id, prompt hash, model id.
5. **Speed inside the guardrail.** Graduation windows are measured in weeks not months and
   are per-class, so reminders can reach `bounded_auto` during the first pilot — but rungs
   are never skipped, including for demos. This is a review-failing offense (CLAUDE.md).

## Consequences
+ D2 credibility is mechanical, not aspirational; demo pressure cannot corrupt safety.
+ Policy rules are unit-testable without any model in the loop.
− Slightly slower "wow" in early demos; accepted deliberately — the camera flow carries wow.
