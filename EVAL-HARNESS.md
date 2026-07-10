# packages/eval — Extraction Evaluation Harness (the 97% gate, mechanically)

## Purpose
Differentiator D2 ("OpenLnk never invents a promise") is a merge gate, not a slogan.
Any PR touching prompts, models, ASR, OCR, or the extraction pipeline must pass
`just eval` in CI at: **precision ≥ 0.97, recall ≥ 0.85** per ingestion route
(text, voice, camera) and overall.

## Definitions (the rubric IS the product's judgment — fight about it here, not in wk 6)
A **commitment** exists in source content when a reasonable reader would agree that a
specific party undertook (or was asked to undertake, awaiting acceptance) a specific
action, optionally by a time. Required extractable fields: owner, title; optional:
counterparty, due, class, amount.

- **True positive:** extracted commitment matches a gold commitment on owner + normalized
  title intent (semantic match, adjudicated) and due within ±30 min when both present.
- **False positive (the trust-killer):** extracted commitment with no gold counterpart,
  OR wrong owner, OR hallucinated amount/date. Weighted 3× in the tracked "trust score"
  (reported alongside raw precision; the merge gate uses raw precision).
- **False negative:** gold commitment with no extraction.
- **Not commitments:** opinions, plans without an undertaking ("we should meet sometime"),
  rhetorical offers, past completed events, forwarded jokes/greetings, marketing blasts.
- Edge rules: conditional promises ("if it rains, I'll pick up") → commitment with
  condition noted; questions proposing times ("can we do Thu 5?") → `proposed` awaiting
  acceptance; amounts without currency default INR.

## Dataset (cold-start plan — built BEFORE the engine)
1. **v0 seed (wk 1–2):** founder-household exported history (consented), hand-labeled;
   ≥500 messages, ≥60 gold commitments. Plus 300 synthetic tuition-thread messages
   (fee reminders, reschedules, parent queries) generated then human-adjudicated.
   **Composition requirements (Gate 1 entry blocker — must be met before pipeline coding):**
   - ≥15% adversarial cases: non-commitments that pattern-match commitments — rhetorical
     offers ("we should meet sometime"), marketing blasts, forwarded jokes, conditional
     phrases without an undertaking, past completed events.
   - ≥10% multi-counterparty cases: messages with implied group obligation (OL-001a /
     OL-029b), e.g. "I'll pick up all three kids" — tests the list[counterparty] extraction.
   - Documented size floor: v0 ≥500 messages; v1 ≥2,000 messages.
2. **v1 (Gate 2 entry):** first pre-sold centers' real threads, consented + anonymized
   (names → tokens before labeling). Target ≥2,000 messages, ≥250 gold commitments,
   ≥100 voice notes, ≥60 camera captures (circulars, receipts).
   Include ≥10 clinic-type commitment samples (appointment, consultation fee,
   prescription follow-up) in preparation for Gate 3 clinic onboarding.
3. **Freeze discipline:** the eval set is frozen per milestone (OL-091); additions come
   from the correction queue (OL-090) via human adjudication; changes need reviewer
   sign-off. Train/tune data and eval data never mix.

## Labeling process
Two-pass: labeler → adjudicator (founder initially). Disagreements resolved by rubric
amendment PRs (the rubric is versioned). Inter-annotator agreement reported once a second
labeler exists.

## Harness mechanics
- `packages/eval` runs the real pipeline (provider adapter, versioned prompts) against the
  frozen set; outputs JSON report: per-route precision/recall, trust score, confusion
  samples, cost per 1k messages (feeds the unit-economics sheet), latency p50/p95.
- CI job `eval-gate`: triggered by changes under `apps/api/prompts/**`,
  `apps/api/services/llm/**`, extraction services, or model-id config. Fails below bars.
- Regression memory: every run archived; a PR must not reduce precision >0.5pt even if
  still above the bar without an explicit reviewer waiver in the PR description.
- Confidence-threshold sweep published per run so the propose threshold (OL-025) is chosen
  from data, not vibes.

## Reporting
Gate reviews receive: the latest eval report, the trust score trend, the correction-queue
volume, and the live-precision proxy (correction rate on surfaced commitments) — because
lab precision and field precision will diverge, and the field number is the one parents
experience.
