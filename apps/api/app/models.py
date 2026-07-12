"""SQLAlchemy ORM models — maps to DB-SCHEMA.sql.

The commitment is the crown jewel. at_risk is COMPUTED at query time,
never stored. upi_intent_url is computed at render from businesses.upi_vpa.
"""

import enum
from datetime import UTC, datetime, time
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Timezone-aware UTC datetime for TIMESTAMPTZ columns.

    DB-SCHEMA.sql uses timestamptz for all timestamp columns.
    asyncpg handles timezone-aware datetimes correctly with timestamptz.
    """
    return datetime.now(UTC)


from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)

# All timestamp columns in DB-SCHEMA.sql are timestamptz.
# SQLAlchemy needs DateTime(timezone=True) to match.
TZDateTime = DateTime(timezone=True)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ─── Enums (matching DB CHECK constraints) ───


class PrincipalKind(enum.StrEnum):
    USER = "user"
    GUEST = "guest"
    AGENT = "agent"


class ContextKind(enum.StrEnum):
    HOUSEHOLD = "household"
    BUSINESS_BATCH = "business_batch"


class CommitmentState(enum.StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BROKEN = "broken"
    CANCELLED = "cancelled"


class CommitmentClass(enum.StrEnum):
    FEE = "fee"
    SCHEDULE = "schedule"
    TASK = "task"
    PAYMENT = "payment"
    CUSTOM = "custom"


class AutonomyRung(enum.StrEnum):
    OBSERVE = "observe"
    PROPOSE = "propose"
    BOUNDED_AUTO = "bounded_auto"
    TRUSTED_AUTO = "trusted_auto"


class ConsentAction(enum.StrEnum):
    GRANT = "grant"
    WITHDRAW = "withdraw"


# ─── Models ───


class Principal(Base):
    __tablename__ = "principals"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_e164: Mapped[str | None] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[PrincipalKind] = mapped_column(String(10), nullable=False)
    quiet_hours_start: Mapped[time | None] = mapped_column()  # OL-054, OL-063
    quiet_hours_end: Mapped[time | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class Household(Base):
    __tablename__ = "households"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    vertical: Mapped[str] = mapped_column(Text, default="tuition")
    upi_vpa: Mapped[str | None] = mapped_column(Text)
    whatsapp_number: Mapped[str | None] = mapped_column(Text)
    subscription_state: Mapped[str] = mapped_column(String(20), default="trial")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class HouseholdMember(Base):
    __tablename__ = "household_members"

    household_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("households.id"), primary_key=True
    )
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member")
    guardian_consent_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class BusinessMember(Base):
    __tablename__ = "business_members"

    business_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id"), primary_key=True
    )
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="staff")


class Context(Base):
    __tablename__ = "contexts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[ContextKind] = mapped_column(String(20), nullable=False)
    household_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("households.id")
    )
    business_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id")
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN household_id IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN business_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="one_axis",
        ),
    )


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contexts.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class ThreadParticipant(Base):
    __tablename__ = "thread_participants"

    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("threads.id"), primary_key=True
    )
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), primary_key=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    body: Mapped[str | None] = mapped_column(Text)
    media_ref: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)

    __table_args__ = (UniqueConstraint("thread_id", "seq"),)


class Commitment(Base):
    """The crown jewel. See DB-SCHEMA.sql for full documentation.

    at_risk is NOT a column — compute at query time:
        WHERE due_at < now() AND state NOT IN ('done', 'broken', 'cancelled')
    """

    __tablename__ = "commitments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contexts.id"), nullable=False
    )
    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    counterparty_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    class_: Mapped[CommitmentClass] = mapped_column("class", String(20), nullable=False)
    amount_paise: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text, default="INR")
    due_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    state: Mapped[CommitmentState] = mapped_column(String(20), default=CommitmentState.PROPOSED)
    version: Mapped[int] = mapped_column(default=1)
    provenance_kind: Mapped[str | None] = mapped_column(String(20))
    provenance_ref: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    prompt_hash: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(Text)
    extracted_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        CheckConstraint(
            "class NOT IN ('fee', 'payment') OR amount_paise IS NOT NULL",
            name="fee_needs_amount",
        ),
        Index("ix_commitments_context_state_due", "context_id", "state", "due_at"),
        Index(
            "ix_commitments_owner_active",
            "owner_id",
            "state",
            postgresql_where=text("state NOT IN ('done', 'cancelled')"),
        ),
    )


class CommitmentParticipant(Base):
    __tablename__ = "commitment_participants"

    commitment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("commitments.id"), primary_key=True
    )
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="counterparty")


class AutonomyGrant(Base):
    __tablename__ = "autonomy_grants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    granter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    contact_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    context_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contexts.id"), nullable=False
    )
    commitment_class: Mapped[str] = mapped_column(Text, nullable=False)
    rung: Mapped[AutonomyRung] = mapped_column(String(20), default=AutonomyRung.OBSERVE)
    clean_actions: Mapped[int] = mapped_column(default=0)
    window_started: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)

    __table_args__ = (
        UniqueConstraint("granter_id", "contact_id", "context_id", "commitment_class"),
    )


class AuditLog(Base):
    """Immutable audit log. REVOKE UPDATE, DELETE on openlnk_app role."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    actor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    actor_kind: Mapped[str] = mapped_column(String(10), nullable=False)
    context_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contexts.id")
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)  # type: ignore[assignment]
    prompt_hash: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(Text)


class StagingRecord(Base):
    """Pre-consent staging records for roster imports (OL-100a).

    Child-linked data is held here until guardian OTP consent.
    """

    __tablename__ = "staging_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False
    )
    student_name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_phone: Mapped[str] = mapped_column(Text, nullable=False)
    batch: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)  # type: ignore[assignment]
    consent_received: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[ConsentAction] = mapped_column(String(10), nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    principal_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    response_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class EvalCandidate(Base):
    """Labeled-candidate queue for eval set (OL-090).

    User corrections/rejections of extractions feed into this queue.
    Candidates are adjudicated by humans before entering the frozen eval set.
    """

    __tablename__ = "eval_candidates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    commitment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("commitments.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # reject | edit
    edits: Mapped[dict | None] = mapped_column(JSONB)
    adjudicated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)


class InviteToken(Base):
    """Invite tokens for non-OpenLnk counterparties (OL-008).

    Generated when a commitment targets someone not yet on the platform.
    The commitment stays in proposed until the invite is accepted.
    """

    __tablename__ = "invite_tokens"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    commitment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("commitments.id"), nullable=False
    )
    inviter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utc_now)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)


class ThreadToken(Base):
    """Multi-use, TTL-based tokens for web-thread guests (ADR-005).

    Eng review A3: rotated_from removed. Tokens are valid until expires_at
    or revoked. Compromise exposure = one thread, time-boxed, revocable.
    """

    __tablename__ = "thread_tokens"

    jti: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False
    )
    principal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("principals.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
