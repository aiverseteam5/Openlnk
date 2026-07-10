# OpenLnk Requirements (EARS) — Gate 0 baseline

Convention: `OL-###`. EARS patterns: Ubiquitous ("The system shall…"), Event-driven
("WHEN … the system shall…"), State-driven ("WHILE … the system shall…"), Unwanted-behavior
("IF … THEN the system shall…"), Optional ("WHERE … the system shall…").
Every requirement must be covered by ≥1 passing test carrying `@pytest.mark.req("OL-###")`
(or the JS-suite equivalent tag) before its milestone closes.

## 1. Commitment core (OL-001 – OL-019)

- OL-001 ✅ The system shall represent every obligation as a Commitment with owner,
  counterparty, title, due timestamp (optional), class, state, version, context_id, and
  provenance pointer.
- OL-001a ✅ The system shall support 0..N counterparties per commitment via the
  `commitment_participants` table; `counterparty_id` is retained for 1:1 backward compat
  and shall be deprecated at Gate 4 exit.
- OL-002 ✅ The system shall implement the commitment state machine
  `proposed → accepted → in_progress → done | broken | cancelled`, rejecting invalid
  transitions with a 409 problem+json.
- OL-002a ✅ WHEN a commitment's title, due date, or amount is amended after `accepted` state,
  the system shall notify the counterparty; WHERE commitment class is `fee` or `payment`,
  amendment SHALL require counterparty re-acceptance before the commitment progresses.
- OL-003 ✅ WHEN both parties are OpenLnk principals, the system shall render the identical
  commitment state to both within 5 s of any change (online conditions).
- OL-003a ✅ The delta-stream replay window SHALL be bounded: ≤ 200 events or ≤ 30 days,
  whichever is smaller; clients beyond this bound shall use the checkpoint API to fetch
  current state rather than replaying the full delta log.
- OL-004 ✅ The system shall record every commitment state change in the immutable audit log
  with actor, timestamp, prior state, new state, and (if agent-initiated) prompt hash.
- OL-005 ✅ The system shall link every extracted commitment to its provenance source
  (message id, media id, or capture id).
- OL-006 ✅ IF a client submits a commitment write with a stale `version`, THEN the system
  shall reject it with 409 and the current object.
- OL-007 ✅ The system shall honor an `Idempotency-Key` header on all mutation endpoints,
  returning the original result for a repeated key within 24 h.
- OL-007a ✅ The system shall run an arq worker that purges idempotency keys older than 24 h
  on a scheduled cadence (≥ once per hour); key accumulation without purge is a Gate 1
  exit blocker.
- OL-008 ✅ WHEN a commitment is assigned to a person not yet on OpenLnk, the system shall
  generate an invite link and hold the commitment in `proposed` until acceptance.
- OL-009 ✅ The system shall support commitment classes `fee`, `schedule`, `task`, `payment`,
  `custom`, with class-specific validation (e.g., `fee` requires amount and currency).
- OL-010 ✅ WHERE a commitment carries class `fee` or `payment`, the system shall attach a UPI
  intent deep-link per ADR-006.
- OL-011 ✅ The system shall never delete commitments; terminal states are `done`, `broken`,
  `cancelled`, all retained and auditable.
- OL-012 ✅ WHEN a due timestamp passes with state not terminal, the system shall mark the
  commitment `at_risk` (flag, not state) and evaluate notification policy per OL-060.

## 2. Extraction engine (OL-020 – OL-034)

- OL-020 ✅ The system shall extract candidate commitments from thread text messages in English.
- OL-021 ✅ The system shall extract candidate commitments from English voice notes via ASR
  followed by the same extraction pipeline.
- OL-022 ✅ The system shall extract candidate commitments from photographed documents
  (circulars, notices, receipts) — exactly this camera flow, nothing broader.
- OL-023 ✅ The extraction pipeline shall achieve precision ≥ 0.97 and recall ≥ 0.85 on the
  frozen eval set (EVAL-HARNESS.md) as a CI merge gate.
- OL-024 ✅ The system shall not persist raw message text, audio, or images server-side beyond
  the ephemeral extraction window (≤ 60 s in-memory), per ADR-002.
- OL-025 ✅ WHEN extraction confidence is below the propose threshold, the system shall discard
  the candidate silently rather than surface a low-confidence commitment.
- OL-026 ✅ The system shall allow the user to correct or reject any extracted commitment in
  ≤ 2 taps; corrections shall be appended to the eval-candidate queue (OL-090).
- OL-027 ✅ The system shall attribute every extraction to a versioned prompt hash and model
  identifier in the audit log.
- OL-028 ✅ IF the LLM provider is unreachable, THEN the system shall queue extraction jobs in
  arq with exponential backoff and shall not lose source pointers.
- OL-029 ✅ The system shall run all extraction through a single provider adapter with
  structured (Pydantic-validated) outputs; free-text LLM output shall not enter services.
- OL-029a ✅ The extraction confidence threshold (propose threshold for OL-025) shall be a
  versioned configuration value, not a hardcoded constant; changes to the threshold are
  logged in the audit log with the old and new values.
- OL-029b ✅ The extraction Pydantic output model SHALL include `counterparties: list[ExtractedPrincipal]`
  (length ≥ 1); extraction of group commitments with multiple named counterparties shall
  populate the list accordingly. Single-counterparty results use a list of length 1.

## 3. Contexts & isolation (OL-040 – OL-049)

- OL-040 ✅ The system shall scope every row of user-linked data by exactly one of
  `household_id` or `business_id`, enforced by Postgres RLS.
- OL-041 ✅ The system shall prevent any query from returning rows across household/business
  boundaries; cross-context leakage is a sev-1 defect and a Gate 1 exit blocker.
- OL-041a ✅ A principal in household A SHALL NOT be able to read commitments, messages, or
  threads belonging to household B under any authenticated session.
- OL-041b ✅ A principal in business X SHALL NOT be able to read commitments, messages, or
  threads belonging to business Y under any authenticated session.
- OL-041c ✅ A web-thread guest token for thread T SHALL NOT grant read access to any
  commitment, message, or thread outside of thread T's context, even if the guest is added
  as a participant on a second thread in the same context.
- OL-041d ✅ The above isolation properties (OL-041a..c) shall be verified by dedicated
  negative-path integration tests using testcontainers-Postgres; these tests shall run in
  CI and gate every merge to main.
- OL-041e ✅ WHEN a new RLS policy is added or modified, the change SHALL include a test
  asserting that the prior leakage scenario is now blocked.
- OL-042 ✅ The system shall auto-cluster threads into typed contexts (`household`,
  `business_batch`) from participant and content signal, with user override.
- OL-043 ✅ WHILE a user belongs to multiple contexts, the system shall render a unified ledger
  view without merging underlying context data.
- OL-044 ✅ The system shall support RBAC roles within a business context: `owner`, `staff`.

## 4. Autonomy ladder & policy engine (OL-050 – OL-059)

- OL-050 ✅ The system shall implement rungs Observe, Propose, Bounded-auto, Trusted-auto,
  configured per (contact × commitment-class).
- OL-051 ✅ The policy engine shall be deterministic; the LLM shall only produce proposals,
  never execute sends or state changes.
- OL-052 ✅ WHILE at rung Observe, the system shall extract and display but send nothing.
- OL-053 ✅ WHILE at rung Propose, the system shall draft messages/actions requiring explicit
  one-tap approval before send.
- OL-054 ✅ WHILE at rung Bounded-auto, the system shall auto-send only whitelisted deterministic
  classes (reminder, confirmation) within configured quiet hours.
- OL-055 ✅ The system shall graduate a (contact × class) pair one rung only after N clean
  actions over ≥ 14 days (N configurable, default 20), and shall show the user the track
  record at the moment of graduation. Clean actions accumulate on a sliding window: the
  14-day check evaluates whether ≥ N actions occurred within the most recent 14-day period,
  not since window_started; window_started resets on each graduation or demotion.
- OL-056 ✅ IF any agent action is corrected or reverted by the user, THEN the system shall
  demote that (contact × class) pair one rung and log the cause.
- OL-057 ✅ The system shall provide a per-context kill switch reverting all pairs to Observe.

## 5. Notifications & silence (OL-060 – OL-066)

- OL-060 ✅ The system shall notify a user only when they are the blocker: a commitment
  assigned to them is `at_risk`, awaiting their acceptance, or awaiting their approval.
- OL-061 ✅ The system shall batch all non-blocking information into the daily brief.
- OL-062 ✅ The system shall record notifications-avoided (suppressed candidate notifications)
  as a first-class metric per user per day.
- OL-063 ✅ The system shall respect per-user quiet hours; Bounded-auto sends outside quiet
  hours queue to the next window.
- OL-064 ✅ The daily brief shall include today's commitments, conflicts, and at-risk items,
  and shall exclude everything else.

## 6. Calendar fusion (OL-070 – OL-075)

- OL-070 The system shall sync read-only with Google Calendar per household member who
  grants consent.
- OL-071 WHEN a new commitment with a due time conflicts with an existing calendar event or
  commitment of the assignee, the system shall surface the conflict before acceptance.
- OL-072 The system shall render a household calendar overlay combining member calendars
  and commitments, scoped by OL-040.
- OL-073 ✅ Calendar ingestion shall live behind the connector interface (ADR-001 §Interfaces)
  so future MCP-based connectors are additive, not a rewrite. The connector interface SHALL
  include a `propose_event(commitment) -> PendingCalendarEvent | None` method stub (E5);
  read-only ships at Gate 4, write-capable ships at Gate 5 with explicit user consent for
  the broader OAuth scope.

## 7. Link mechanic / web-thread (OL-080 – OL-088)

- OL-080 The system shall open a functional thread from an openlnk.in link with no signup,
  first meaningful render < 3 s on the reference low-end Android profile.
- OL-081 Thread links shall embed signed, thread-scoped, expiring tokens that rotate on use
  (ADR-005); a token shall grant access to exactly one thread.
- OL-082 The web-thread client shall persist session across visits inside the WhatsApp
  in-app webview (localStorage primary, cookie fallback).
- OL-083 The system shall present the app-install offer only when a web principal has ≥ 2
  active threads, and never before.
- OL-084 The web-thread bundle shall not exceed 120 KB gzipped (CI-enforced).
- OL-085 The system shall instrument the funnel (open, return, install) per center and per
  message class from first deployment.

## 8. Business console & payments (OL-100 – OL-112)

- OL-100 ✅ The system shall import a center's student/parent roster from an Excel/CSV upload,
  onboarding a center to first proposed reminder in ≤ 30 minutes.
- OL-100a ✅ WHEN a center imports child-linked data (student name, schedule, fee), the system
  SHALL hold that data in a staging state pending each parent's first OTP-confirmed login
  as the consent event; child-linked commitments SHALL NOT be created until consent is
  recorded in consent_events.
- OL-100b ✅ WHEN a clinic imports patient data, the system SHALL require
  `health_data:<patient_ref>` consent (recorded in consent_events) before creating any
  appointment commitment. Clinic onboarding SHALL fail-safe: a patient without consent
  SHALL receive no commitment until OTP-confirmed opt-in.
- OL-101 ✅ The console shall show batches, schedule, fee cycle, and a commitments dashboard
  (pending / at-risk / closed).
- OL-102 ✅ WHEN a fee cycle date arrives, the system shall generate fee commitments for each
  enrolled student and (per rung) propose or send reminders.
- OL-103 ✅ Fee reminders shall include a UPI intent deep-link resolving to the center's VPA;
  funds shall never transit an OpenLnk account (ADR-006).
- OL-103a ✅ WHEN a commitment transitions to state `done`, the system SHALL surface a
  one-tap "Share confirmation to WhatsApp" CTA in the commitment detail view, generating a
  `wa.me/{whatsapp_number}?text=...` deep-link pre-composed with the commitment title and
  date. This action is user-triggered only and is NOT eligible for Bounded-auto execution.
- OL-103b ✅ WHEN a fee commitment is created for a business, the system SHALL validate that
  `businesses.upi_vpa` is non-null and matches the format `{name}@{bank}`; WHERE the VPA
  is absent or malformed, the system SHALL surface an owner warning before the commitment
  is proposed to the counterparty.
- OL-104 ✅ WHEN a parent reports payment (or a confirmation is received), the system shall
  move the fee commitment toward `done` per rung policy, keeping owner confirmation at
  Propose rung.
- OL-105 ✅ The owner home screen shall display fees-recovered-this-period against
  subscription cost (ROI framing).
- OL-106 ✅ The system shall bill centers via Razorpay subscriptions with GST-compliant invoices.
- OL-107 ✅ IF a center's subscription lapses, THEN the system shall degrade to read-only for
  the owner while preserving parent access to existing commitments for 90 days. Household
  commitments that originated from a lapsed business context SHALL persist with an
  anonymized business reference; they SHALL NOT be deleted. The business entity data MAY
  be deleted per ADR-002 §Erasure; the commitment graph is anonymized, not destroyed, to
  preserve the household ledger integrity.

## 9. Consent, privacy, DPDP (OL-120 – OL-129)

- OL-120 ✅ The system shall obtain recorded, verifiable guardian consent before processing any
  child-linked data (name, schedule, attendance-adjacent, fee-adjacent), per DPDP Act 2023.
- OL-120a The system SHALL implement a `health_data:<patient_ref>` consent scope in
  consent_events for clinic contexts. Consent records SHALL include: stated processing
  purpose, data fiduciary name (OpenLnk / TynkAI), and explicit withdrawal mechanism.
  Legal review of this scope is REQUIRED before first clinic patient is onboarded (Gate 3
  pre-flight blocker). See also OL-100b.
- OL-121 ✅ The system shall not perform behavioral tracking or targeted advertising of any
  principal; child-linked data shall carry a stricter minimization schema (ADR-002).
- OL-122 ✅ All personal data shall reside in the ap-south-1 (Mumbai) region.
- OL-123 ✅ The system shall log every consent grant/withdrawal as an audit event and honor
  withdrawal by ceasing processing within 72 h.
- OL-124 The system shall provide data export and account deletion (commitment graph
  anonymized, not destroyed, to preserve counterparty ledgers) — deletion semantics per
  ADR-002 §Erasure.

## 10. Eval & learning loop (OL-090 – OL-094)

- OL-090 ✅ User corrections/rejections of extractions shall enter a labeled-candidate queue
  for human adjudication into the eval set.
- OL-091 ✅ The eval set shall be frozen per milestone; changes to it require reviewer sign-off.
- OL-092 ✅ CI shall block any merge touching prompts, models, or the extraction pipeline
  unless `just eval` meets OL-023 thresholds.
- OL-093 The system shall learn per-user nudge timing and quiet-hour patterns only through
  features that create, protect, or close commitments (PRD §8 test).

## 11. Non-functional (OL-140 – OL-148)

- OL-140 API p95 latency < 400 ms for reads, < 800 ms for writes (excluding LLM paths).
- OL-141 ✅ All services containerized; single `just dev` brings up the full stack locally.
- OL-142 Nightly Postgres PITR verified restore drill monthly.
- OL-142a Postgres PITR to S3 (ap-south-1) SHALL be configured and a successful restore
  verified BEFORE Gate 2 pilot go-live; this is a Gate 2 entry blocker. The monthly drill
  (OL-142) does not satisfy this requirement — a pre-Gate-2 restore drill is required.
- OL-143 Sentry wired in all four apps before Gate 2 field deployment.
- OL-144 Rate limiting: Caddy per-IP and FastAPI per-token; web-thread tokens additionally
  per-thread throttled.
- OL-145 Secrets never in repo (gitleaks pre-commit); shared secrets in Infisical.
- OL-146 OTP auth via MSG91 with cost telemetry feeding the unit-economics sheet.
- OL-146a Session tokens: access token 15-min TTL; refresh token 90-day TTL rotated on use;
  stored in httpOnly cookie (web) / Keychain (mobile). WHERE MSG91 is unreachable for OTP
  delivery, the system SHALL fall back to a secondary provider (e.g., Kaleyra or Twilio)
  configured in Infisical; fallback SHALL be tested in staging before Gate 2 deployment.
