-- OpenLnk — Gate 0 core schema (Postgres 16). Crown jewel: the commitment graph.
-- RLS axes: household_id, business_id. Every user-linked row carries exactly one.
-- Raw conversation content is NEVER stored in extraction paths (ADR-002);
-- thread messages persist as product history, scoped and encrypted at rest.
--
-- Review history:
--   eng-review-20260710: RLS on membership tables, thread-scoped guest policy,
--     removed upi_intent_url (ADR-006), removed at_risk stored col (now computed),
--     renamed created_by→extracted_by, partial unique indexes on contexts.label
--   ceo-review-20260710: commitment_participants table (OL-001a E1),
--     businesses.whatsapp_number (E4 loop-close), counterparty_id dual-model comment

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============ Principals & contexts ============

CREATE TABLE principals (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_e164      text UNIQUE,                       -- null for web-thread guests
  display_name    text NOT NULL,
  kind            text NOT NULL CHECK (kind IN ('user','guest','agent')),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE households (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE businesses (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text NOT NULL,
  vertical        text NOT NULL DEFAULT 'tuition',
  upi_vpa         text,                              -- settlement target (ADR-006); computed at render, not stored on commitments
  whatsapp_number text,                              -- WA loop-close mechanic (E4/OL-103a); format: E.164 without +
  subscription_state text NOT NULL DEFAULT 'trial'
      CHECK (subscription_state IN ('trial','active','lapsed')),
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- Membership tables carry the RLS axis values used by policies.
CREATE TABLE household_members (
  household_id    uuid NOT NULL REFERENCES households(id),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  role            text NOT NULL DEFAULT 'member' CHECK (role IN ('coordinator','member')),
  guardian_consent_at timestamptz,                   -- DPDP: set when guardian consent recorded
  PRIMARY KEY (household_id, principal_id)
);
ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY hm_self ON household_members USING (
  principal_id = current_setting('app.principal_id')::uuid
  OR
  household_id IN (SELECT household_id FROM household_members hm2
                   WHERE hm2.principal_id = current_setting('app.principal_id')::uuid)
);

CREATE TABLE business_members (
  business_id     uuid NOT NULL REFERENCES businesses(id),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  role            text NOT NULL DEFAULT 'staff' CHECK (role IN ('owner','staff')),
  PRIMARY KEY (business_id, principal_id)
);
ALTER TABLE business_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY bm_self ON business_members USING (
  principal_id = current_setting('app.principal_id')::uuid
  OR
  business_id IN (SELECT business_id FROM business_members bm2
                  WHERE bm2.principal_id = current_setting('app.principal_id')::uuid)
);

-- A context is the auto-clustered container (PRD §6). Exactly one axis set.
CREATE TABLE contexts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind            text NOT NULL CHECK (kind IN ('household','business_batch')),
  household_id    uuid REFERENCES households(id),
  business_id     uuid REFERENCES businesses(id),
  label           text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT one_axis CHECK (
    (household_id IS NOT NULL)::int + (business_id IS NOT NULL)::int = 1
  )
);
-- Label uniqueness per context owner axis (D11 fix)
CREATE UNIQUE INDEX ctx_label_household ON contexts (household_id, label) WHERE household_id IS NOT NULL;
CREATE UNIQUE INDEX ctx_label_business  ON contexts (business_id,  label) WHERE business_id  IS NOT NULL;

-- ============ Threads & messages (product history, not extraction storage) ==

CREATE TABLE threads (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  context_id      uuid NOT NULL REFERENCES contexts(id),
  seq             bigint NOT NULL DEFAULT 0,          -- monotonic per-thread (ADR-001)
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE thread_participants (
  thread_id       uuid NOT NULL REFERENCES threads(id),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  PRIMARY KEY (thread_id, principal_id)
);

CREATE TABLE messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id       uuid NOT NULL REFERENCES threads(id),
  seq             bigint NOT NULL,
  sender_id       uuid NOT NULL REFERENCES principals(id),
  body            text,                               -- encrypted at rest (storage layer)
  media_ref       text,                               -- client-held media pointer only
  sent_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (thread_id, seq)
);

-- ============ THE COMMITMENT (crown jewel) ============

CREATE TABLE commitments (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  context_id      uuid NOT NULL REFERENCES contexts(id),
  owner_id        uuid NOT NULL REFERENCES principals(id),   -- who must fulfil
  -- counterparty_id: used for 1:1 commitments (simple case, backward-compatible).
  -- For 1:N group commitments, leave null and use commitment_participants table.
  -- Migration path: deprecate this column at Gate 4 exit once group commitments are
  -- live-validated; migrate all 1:1 rows to commitment_participants at that point.
  counterparty_id uuid REFERENCES principals(id),
  title           text NOT NULL,
  class           text NOT NULL CHECK (class IN ('fee','schedule','task','payment','custom')),
  amount_paise    bigint,                                    -- required for fee/payment
  currency        text DEFAULT 'INR',
  due_at          timestamptz,
  state           text NOT NULL DEFAULT 'proposed'
      CHECK (state IN ('proposed','accepted','in_progress','done','broken','cancelled')),
  -- at_risk is a computed flag (OL-012), not a stored column.
  -- Compute at query time: WHERE due_at < now() AND state NOT IN ('done','broken','cancelled')
  version         integer NOT NULL DEFAULT 1,                -- optimistic concurrency OL-006
  provenance_kind text CHECK (provenance_kind IN ('message','voice','camera','manual')),
  provenance_ref  text,                                      -- client-side pointer (ADR-002)
  extraction_confidence numeric(4,3),
  prompt_hash     text,                                      -- OL-027
  model_id        text,
  -- upi_intent_url removed: computed at render from businesses.upi_vpa + amount_paise (ADR-006)
  extracted_by    uuid NOT NULL REFERENCES principals(id),   -- agent principal or manual user
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fee_needs_amount CHECK (
    class NOT IN ('fee','payment') OR amount_paise IS NOT NULL
  )
);
CREATE INDEX ON commitments (context_id, state, due_at);
CREATE INDEX ON commitments (owner_id, state) WHERE state NOT IN ('done','cancelled');

-- ============ Group commitments (OL-001a, E1) ============
-- Extends 1:1 commitments to 1:N. Populated only when counterparty_id IS NULL.
-- RLS: a principal can see a commitment if they are in commitment_participants OR
--      they are owner_id or counterparty_id of the commitment.

CREATE TABLE commitment_participants (
  commitment_id   uuid NOT NULL REFERENCES commitments(id),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  role            text NOT NULL DEFAULT 'counterparty'
                    CHECK (role IN ('owner','counterparty','observer')),
  PRIMARY KEY (commitment_id, principal_id)
);
CREATE INDEX ON commitment_participants (commitment_id);
CREATE INDEX ON commitment_participants (principal_id);
ALTER TABLE commitment_participants ENABLE ROW LEVEL SECURITY;
-- Participants can see the participation rows for commitments they are party to.
CREATE POLICY cp_member ON commitment_participants USING (
  commitment_id IN (
    SELECT id FROM commitments
    WHERE owner_id = current_setting('app.principal_id')::uuid
       OR counterparty_id = current_setting('app.principal_id')::uuid
  )
  OR
  principal_id = current_setting('app.principal_id')::uuid
);

-- ============ Autonomy ladder & audit ============

CREATE TABLE autonomy_grants (                                -- ADR-003, per contact×class
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  granter_id      uuid NOT NULL REFERENCES principals(id),
  contact_id      uuid NOT NULL REFERENCES principals(id),
  context_id      uuid NOT NULL REFERENCES contexts(id),
  commitment_class text NOT NULL,
  rung            text NOT NULL DEFAULT 'observe'
      CHECK (rung IN ('observe','propose','bounded_auto','trusted_auto')),
  clean_actions   integer NOT NULL DEFAULT 0,
  window_started  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (granter_id, contact_id, context_id, commitment_class)
);

CREATE TABLE audit_log (                                      -- immutable: no UPDATE/DELETE grants
  id              bigserial PRIMARY KEY,
  at              timestamptz NOT NULL DEFAULT now(),
  actor_id        uuid NOT NULL REFERENCES principals(id),
  actor_kind      text NOT NULL CHECK (actor_kind IN ('user','agent','system')),
  context_id      uuid REFERENCES contexts(id),
  event           text NOT NULL,                              -- e.g. commitment.state_change
  subject_id      uuid,                                       -- commitment/message/etc id
  detail          jsonb NOT NULL DEFAULT '{}'::jsonb,         -- prior/new state, rule id,
  prompt_hash     text,                                       -- prompt hash for agent acts
  model_id        text
);
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
-- Audit log readable by principals scoped to the context, plus their own actor rows.
CREATE POLICY al_scoped ON audit_log USING (
  actor_id = current_setting('app.principal_id')::uuid
  OR
  context_id IN (
    SELECT id FROM contexts
    WHERE household_id IN (SELECT household_id FROM household_members
                           WHERE principal_id = current_setting('app.principal_id')::uuid)
    OR business_id IN (SELECT business_id FROM business_members
                       WHERE principal_id = current_setting('app.principal_id')::uuid)
  )
);

CREATE TABLE consent_events (                                 -- DPDP OL-120/123
  id              bigserial PRIMARY KEY,
  at              timestamptz NOT NULL DEFAULT now(),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  scope           text NOT NULL,                              -- e.g. child_data:<student_ref>
                                                              --      health_data:<patient_ref> (OL-120a)
  action          text NOT NULL CHECK (action IN ('grant','withdraw')),
  method          text NOT NULL                               -- otp_confirm, in_app, link
);

-- ============ Idempotency & thread tokens ============

CREATE TABLE idempotency_keys (
  key             text PRIMARY KEY,
  principal_id    uuid NOT NULL,
  response_hash   text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()          -- purge >24h via worker (OL-007a)
);

CREATE TABLE thread_tokens (                                  -- ADR-005
  jti             uuid PRIMARY KEY,
  thread_id       uuid NOT NULL REFERENCES threads(id),
  principal_id    uuid NOT NULL REFERENCES principals(id),
  expires_at      timestamptz NOT NULL,
  rotated_from    uuid,
  revoked         boolean NOT NULL DEFAULT false
);

-- ============ RLS (illustrative policies; full set in migration 0001) ============

ALTER TABLE contexts     ENABLE ROW LEVEL SECURITY;
ALTER TABLE threads      ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages     ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments  ENABLE ROW LEVEL SECURITY;

-- Session GUCs set by the API per request: app.principal_id
-- IMPORTANT: if app.principal_id GUC is not set, current_setting() raises an error.
-- The API middleware MUST set this GUC for every connection before any query.
-- Failure mode: unset GUC → PostgreSQL error, not empty results. Sentry + structlog alert.
CREATE POLICY ctx_household ON contexts USING (
  household_id IN (SELECT household_id FROM household_members
                   WHERE principal_id = current_setting('app.principal_id')::uuid)
  OR
  business_id IN (SELECT business_id FROM business_members
                  WHERE principal_id = current_setting('app.principal_id')::uuid)
);
-- NOTE: Web-thread guests (kind='guest') access contexts ONLY via their specific thread,
-- not via household/business membership. Guest context access is granted through the
-- thread_tokens table — the API resolves the thread's context_id and grants thread-scoped
-- access by setting a separate GUC app.thread_id. A guest must NOT see all commitments
-- in a context — only those associated with their specific thread. (D2 fix, OL-041)
-- The full thread-scoped guest policy is in migration 0001.

-- commitments policy: accessible if you own it, are counterparty, or are in commitment_participants
CREATE POLICY comm_member ON commitments USING (
  owner_id = current_setting('app.principal_id')::uuid
  OR counterparty_id = current_setting('app.principal_id')::uuid
  OR id IN (SELECT commitment_id FROM commitment_participants
            WHERE principal_id = current_setting('app.principal_id')::uuid)
  OR context_id IN (SELECT id FROM contexts)  -- inherits ctx_household policy
);

-- messages/threads inherit context reachability via context_id policies
-- (full policies + negative tests in migration 0001; cross-context leakage = sev-1, OL-041)
-- OL-041 isolation tests: OL-041a..e (see REQUIREMENTS.md)
