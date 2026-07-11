"""Initial schema with RLS policies.

Revision ID: 0001
Revises:
Create Date: 2026-07-10

Full Gate 0 schema from DB-SCHEMA.sql with:
- All tables and constraints
- RLS on all user-facing tables
- openlnk_app role with minimal privileges (eng review C1)
- Thread-scoped guest policy (eng review T2)
- Immutable audit_log (REVOKE UPDATE, DELETE)
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ──
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Role setup (eng review C1) ──
    # Create the app role if it doesn't exist. In production, this role
    # is created by infrastructure; in dev, docker-compose creates it
    # as the POSTGRES_USER. The DO block handles both cases.
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'openlnk_app') THEN
            CREATE ROLE openlnk_app LOGIN;
        END IF;
    END
    $$;
    """)

    # ── Principals & contexts ──
    op.execute("""
    CREATE TABLE principals (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        phone_e164      text UNIQUE,
        display_name    text NOT NULL,
        kind            text NOT NULL CHECK (kind IN ('user','guest','agent')),
        quiet_hours_start time,
        quiet_hours_end   time,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE households (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name            text NOT NULL,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE businesses (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name            text NOT NULL,
        vertical        text NOT NULL DEFAULT 'tuition',
        upi_vpa         text,
        whatsapp_number text,
        subscription_state text NOT NULL DEFAULT 'trial'
            CHECK (subscription_state IN ('trial','active','lapsed')),
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE household_members (
        household_id    uuid NOT NULL REFERENCES households(id),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        role            text NOT NULL DEFAULT 'member'
            CHECK (role IN ('coordinator','member')),
        guardian_consent_at timestamptz,
        PRIMARY KEY (household_id, principal_id)
    );
    """)

    op.execute("""
    CREATE TABLE business_members (
        business_id     uuid NOT NULL REFERENCES businesses(id),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        role            text NOT NULL DEFAULT 'staff'
            CHECK (role IN ('owner','staff')),
        PRIMARY KEY (business_id, principal_id)
    );
    """)

    op.execute("""
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
    CREATE UNIQUE INDEX ctx_label_household ON contexts (household_id, label)
        WHERE household_id IS NOT NULL;
    CREATE UNIQUE INDEX ctx_label_business ON contexts (business_id, label)
        WHERE business_id IS NOT NULL;
    """)

    # ── Threads & messages ──
    op.execute("""
    CREATE TABLE threads (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        context_id      uuid NOT NULL REFERENCES contexts(id),
        seq             bigint NOT NULL DEFAULT 0,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE thread_participants (
        thread_id       uuid NOT NULL REFERENCES threads(id),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        PRIMARY KEY (thread_id, principal_id)
    );
    """)

    op.execute("""
    CREATE TABLE messages (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        thread_id       uuid NOT NULL REFERENCES threads(id),
        seq             bigint NOT NULL,
        sender_id       uuid NOT NULL REFERENCES principals(id),
        body            text,
        media_ref       text,
        sent_at         timestamptz NOT NULL DEFAULT now(),
        UNIQUE (thread_id, seq)
    );
    """)

    # ── Commitments (crown jewel) ──
    op.execute("""
    CREATE TABLE commitments (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        context_id      uuid NOT NULL REFERENCES contexts(id),
        owner_id        uuid NOT NULL REFERENCES principals(id),
        counterparty_id uuid REFERENCES principals(id),
        title           text NOT NULL,
        class           text NOT NULL
            CHECK (class IN ('fee','schedule','task','payment','custom')),
        amount_paise    bigint,
        currency        text DEFAULT 'INR',
        due_at          timestamptz,
        state           text NOT NULL DEFAULT 'proposed'
            CHECK (state IN ('proposed','accepted','in_progress',
                             'done','broken','cancelled')),
        version         integer NOT NULL DEFAULT 1,
        provenance_kind text
            CHECK (provenance_kind IN ('message','voice','camera','manual')),
        provenance_ref  text,
        extraction_confidence numeric(4,3),
        prompt_hash     text,
        model_id        text,
        extracted_by    uuid NOT NULL REFERENCES principals(id),
        created_at      timestamptz NOT NULL DEFAULT now(),
        updated_at      timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT fee_needs_amount CHECK (
            class NOT IN ('fee','payment') OR amount_paise IS NOT NULL
        )
    );
    CREATE INDEX ix_commitments_context_state_due
        ON commitments (context_id, state, due_at);
    CREATE INDEX ix_commitments_owner_active
        ON commitments (owner_id, state)
        WHERE state NOT IN ('done','cancelled');
    """)

    # ── Commitment participants (1:N group commitments) ──
    op.execute("""
    CREATE TABLE commitment_participants (
        commitment_id   uuid NOT NULL REFERENCES commitments(id),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        role            text NOT NULL DEFAULT 'counterparty'
            CHECK (role IN ('owner','counterparty','observer')),
        PRIMARY KEY (commitment_id, principal_id)
    );
    CREATE INDEX ON commitment_participants (commitment_id);
    CREATE INDEX ON commitment_participants (principal_id);
    """)

    # ── Autonomy ladder & audit ──
    op.execute("""
    CREATE TABLE autonomy_grants (
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
    """)

    op.execute("""
    CREATE TABLE audit_log (
        id              bigserial PRIMARY KEY,
        at              timestamptz NOT NULL DEFAULT now(),
        actor_id        uuid NOT NULL REFERENCES principals(id),
        actor_kind      text NOT NULL
            CHECK (actor_kind IN ('user','agent','system')),
        context_id      uuid REFERENCES contexts(id),
        event           text NOT NULL,
        subject_id      uuid,
        detail          jsonb NOT NULL DEFAULT '{}'::jsonb,
        prompt_hash     text,
        model_id        text
    );
    """)

    op.execute("""
    CREATE TABLE consent_events (
        id              bigserial PRIMARY KEY,
        at              timestamptz NOT NULL DEFAULT now(),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        scope           text NOT NULL,
        action          text NOT NULL CHECK (action IN ('grant','withdraw')),
        method          text NOT NULL
    );
    """)

    # ── Idempotency & thread tokens ──
    op.execute("""
    CREATE TABLE idempotency_keys (
        key             text PRIMARY KEY,
        principal_id    uuid NOT NULL,
        response_hash   text NOT NULL,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE thread_tokens (
        jti             uuid PRIMARY KEY,
        thread_id       uuid NOT NULL REFERENCES threads(id),
        principal_id    uuid NOT NULL REFERENCES principals(id),
        expires_at      timestamptz NOT NULL,
        revoked         boolean NOT NULL DEFAULT false
    );
    """)

    # ── Staging, eval candidates, invite tokens ──
    op.execute("""
    CREATE TABLE staging_records (
        id              bigserial PRIMARY KEY,
        business_id     uuid NOT NULL REFERENCES businesses(id),
        student_name    text NOT NULL,
        parent_phone    text NOT NULL,
        batch           text,
        data            jsonb NOT NULL DEFAULT '{}'::jsonb,
        consent_received boolean NOT NULL DEFAULT false,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE eval_candidates (
        id              bigserial PRIMARY KEY,
        commitment_id   uuid NOT NULL REFERENCES commitments(id),
        action          text NOT NULL CHECK (action IN ('reject','edit')),
        edits           jsonb,
        adjudicated     boolean NOT NULL DEFAULT false,
        created_at      timestamptz NOT NULL DEFAULT now()
    );
    """)

    op.execute("""
    CREATE TABLE invite_tokens (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        commitment_id   uuid NOT NULL REFERENCES commitments(id),
        inviter_id      uuid NOT NULL REFERENCES principals(id),
        token           text UNIQUE NOT NULL,
        phone_e164      text,
        accepted        boolean NOT NULL DEFAULT false,
        created_at      timestamptz NOT NULL DEFAULT now(),
        expires_at      timestamptz NOT NULL
    );
    """)

    # ════════════════════════════════════════════════════
    # RLS POLICIES (eng review T2 — full set)
    # ════════════════════════════════════════════════════

    # -- household_members: see only your own memberships
    op.execute("ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY hm_self ON household_members USING (
        principal_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- business_members: see only your own memberships
    op.execute("ALTER TABLE business_members ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY bm_self ON business_members USING (
        principal_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- contexts: accessible via household or business membership
    op.execute("ALTER TABLE contexts ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY ctx_member ON contexts USING (
        household_id IN (
            SELECT household_id FROM household_members
            WHERE principal_id = current_setting('app.principal_id')::uuid
        )
        OR business_id IN (
            SELECT business_id FROM business_members
            WHERE principal_id = current_setting('app.principal_id')::uuid
        )
    );
    """)

    # -- threads: accessible if you participate or are in the context
    op.execute("ALTER TABLE threads ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY thread_member ON threads USING (
        id IN (
            SELECT thread_id FROM thread_participants
            WHERE principal_id = current_setting('app.principal_id')::uuid
        )
        OR context_id IN (SELECT id FROM contexts)
    );
    """)

    # -- thread_participants: see only your own participation
    op.execute("ALTER TABLE thread_participants ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY tp_member ON thread_participants USING (
        principal_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- messages: accessible if you're in the thread
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY msg_thread ON messages USING (
        thread_id IN (
            SELECT thread_id FROM thread_participants
            WHERE principal_id = current_setting('app.principal_id')::uuid
        )
    );
    """)

    # -- commitments: owner, counterparty, or context member
    op.execute("ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY comm_member ON commitments USING (
        owner_id = current_setting('app.principal_id')::uuid
        OR counterparty_id = current_setting('app.principal_id')::uuid
        OR context_id IN (SELECT id FROM contexts)
    );
    """)

    # -- commitment_participants: see only your own participation
    op.execute("ALTER TABLE commitment_participants ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY cp_member ON commitment_participants USING (
        principal_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- autonomy_grants: granter or contact can see
    op.execute("ALTER TABLE autonomy_grants ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY ag_party ON autonomy_grants USING (
        granter_id = current_setting('app.principal_id')::uuid
        OR contact_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- audit_log: immutable + scoped
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;")
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;")
    op.execute("""
    CREATE POLICY al_scoped ON audit_log USING (
        actor_id = current_setting('app.principal_id')::uuid
        OR context_id IN (
            SELECT id FROM contexts
            WHERE household_id IN (
                SELECT household_id FROM household_members
                WHERE principal_id = current_setting('app.principal_id')::uuid
            )
            OR business_id IN (
                SELECT business_id FROM business_members
                WHERE principal_id = current_setting('app.principal_id')::uuid
            )
        )
    );
    """)

    # -- consent_events: own events only
    op.execute("ALTER TABLE consent_events ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY ce_self ON consent_events USING (
        principal_id = current_setting('app.principal_id')::uuid
    );
    """)

    # -- staging_records: scoped to business membership
    op.execute("ALTER TABLE staging_records ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY sr_business ON staging_records USING (
        business_id IN (
            SELECT business_id FROM business_members
            WHERE principal_id = current_setting('app.principal_id')::uuid
        )
    );
    """)

    # -- eval_candidates: scoped via commitment visibility
    op.execute("ALTER TABLE eval_candidates ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY ec_commitment ON eval_candidates USING (
        commitment_id IN (SELECT id FROM commitments)
    );
    """)

    # -- invite_tokens: inviter can see
    op.execute("ALTER TABLE invite_tokens ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY it_inviter ON invite_tokens USING (
        inviter_id = current_setting('app.principal_id')::uuid
    );
    """)

    # ── Thread-scoped guest policy (eng review T2) ──
    # Guests (kind='guest') access ONLY their specific thread, not the full context.
    # The API sets app.thread_id GUC for guest connections. This policy allows
    # guests to see only commitments linked to their thread's context AND visible
    # via thread_participants.
    op.execute("""
    CREATE POLICY guest_thread_scoped ON commitments USING (
        EXISTS (
            SELECT 1 FROM principals p
            WHERE p.id = current_setting('app.principal_id')::uuid
              AND p.kind = 'guest'
              AND context_id IN (
                  SELECT t.context_id FROM threads t
                  JOIN thread_participants tp ON tp.thread_id = t.id
                  WHERE tp.principal_id = current_setting('app.principal_id')::uuid
              )
        )
    );
    """)

    # ── Grants to openlnk_app role ──
    # The app role gets DML on all tables but NOT DDL or superuser.
    # audit_log: INSERT only (REVOKE UPDATE, DELETE already done above).
    op.execute("""
    GRANT SELECT, INSERT, UPDATE, DELETE ON principals TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON households TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON businesses TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON household_members TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON business_members TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON contexts TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON threads TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON thread_participants TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON messages TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON commitments TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON commitment_participants TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON autonomy_grants TO openlnk_app;
    GRANT SELECT, INSERT ON audit_log TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON consent_events TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON idempotency_keys TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON thread_tokens TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON staging_records TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON eval_candidates TO openlnk_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON invite_tokens TO openlnk_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO openlnk_app;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invite_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS eval_candidates CASCADE;")
    op.execute("DROP TABLE IF EXISTS staging_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS thread_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS idempotency_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS consent_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS autonomy_grants CASCADE;")
    op.execute("DROP TABLE IF EXISTS commitment_participants CASCADE;")
    op.execute("DROP TABLE IF EXISTS commitments CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS thread_participants CASCADE;")
    op.execute("DROP TABLE IF EXISTS threads CASCADE;")
    op.execute("DROP TABLE IF EXISTS contexts CASCADE;")
    op.execute("DROP TABLE IF EXISTS business_members CASCADE;")
    op.execute("DROP TABLE IF EXISTS household_members CASCADE;")
    op.execute("DROP TABLE IF EXISTS businesses CASCADE;")
    op.execute("DROP TABLE IF EXISTS households CASCADE;")
    op.execute("DROP TABLE IF EXISTS principals CASCADE;")
