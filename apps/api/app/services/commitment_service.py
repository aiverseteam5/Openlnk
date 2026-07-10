"""Commitment service — business logic for commitment lifecycle.

Key invariants:
- Every state transition validates the transition is legal
- Every write checks version for optimistic concurrency (stale → 409)
- at_risk is computed at query time, never stored
- Audit log entry for every state change
"""

from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Commitment, CommitmentState, IdempotencyKey
from app.schemas import (
    CommitmentCreate,
    CommitmentResponse,
    CommitmentStateTransition,
)

logger = structlog.get_logger()

# Legal state transitions (from → set of valid to states)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"accepted", "cancelled"},
    "accepted": {"in_progress", "cancelled"},
    "in_progress": {"done", "broken", "cancelled"},
    "done": set(),
    "broken": set(),
    "cancelled": set(),
}


def _is_at_risk(commitment: Commitment) -> bool:
    """Compute at_risk flag: due_at < now() AND state not terminal."""
    if commitment.due_at is None:
        return False
    terminal = {CommitmentState.DONE, CommitmentState.BROKEN, CommitmentState.CANCELLED}
    return commitment.due_at < datetime.utcnow() and commitment.state not in terminal


def _to_response(commitment: Commitment) -> CommitmentResponse:
    """Map ORM model to Pydantic response with computed at_risk."""
    return CommitmentResponse.model_validate(
        {
            "id": commitment.id,
            "context_id": commitment.context_id,
            "owner_id": commitment.owner_id,
            "counterparty_id": commitment.counterparty_id,
            "title": commitment.title,
            "class": commitment.class_,
            "amount_paise": commitment.amount_paise,
            "currency": commitment.currency,
            "due_at": commitment.due_at,
            "state": commitment.state,
            "version": commitment.version,
            "at_risk": _is_at_risk(commitment),
            "provenance_kind": commitment.provenance_kind,
            "extraction_confidence": float(commitment.extraction_confidence)
            if commitment.extraction_confidence is not None
            else None,
            "created_at": commitment.created_at,
            "updated_at": commitment.updated_at,
        }
    )


class CommitmentService:
    """Commitment CRUD + state machine.

    DailyBriefService query contract (eng review P1):
    - Daily brief MUST use a single JOIN query across commitments + contexts
    - MUST compute at_risk in SQL: due_at < now() AND state NOT IN (done, broken, cancelled)
    - <200ms at 100 commitments (Playwright perf test)
    """

    def __init__(self, session: AsyncSession, principal_id: UUID) -> None:
        self._session = session
        self._principal_id = principal_id

    async def _check_idempotency(self, key: str) -> IdempotencyKey | None:
        """Return existing idempotency record if key was already used."""
        result = await self._session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.key == key,
                IdempotencyKey.principal_id == self._principal_id,
            )
        )
        return result.scalar_one_or_none()

    async def _record_idempotency(self, key: str, response_hash: str) -> None:
        """Record an idempotency key after successful operation."""
        self._session.add(
            IdempotencyKey(
                key=key,
                principal_id=self._principal_id,
                response_hash=response_hash,
            )
        )

    async def create(
        self,
        data: CommitmentCreate,
        *,
        idempotency_key: str,
    ) -> CommitmentResponse:
        """Create a new commitment with state=proposed, version=1."""
        # Idempotency check
        existing = await self._check_idempotency(idempotency_key)
        if existing is not None:
            # Return the previously created commitment
            commitment = await self._session.get(Commitment, UUID(existing.response_hash))
            if commitment is not None:
                return _to_response(commitment)

        commitment = Commitment(
            context_id=data.context_id,
            owner_id=data.owner_id,
            counterparty_id=data.counterparty_id,
            title=data.title,
            class_=data.class_,
            amount_paise=data.amount_paise,
            currency=data.currency,
            due_at=data.due_at,
            state=CommitmentState.PROPOSED,
            version=1,
            provenance_kind=data.provenance_kind,
            provenance_ref=data.provenance_ref,
            extracted_by=self._principal_id,
        )
        self._session.add(commitment)
        await self._session.flush()

        # Record idempotency (response_hash = commitment ID for retrieval)
        await self._record_idempotency(idempotency_key, str(commitment.id))

        # Audit log
        self._session.add(
            AuditLog(
                actor_id=self._principal_id,
                actor_kind="user",
                context_id=data.context_id,
                event="commitment.created",
                subject_id=commitment.id,
                detail={
                    "title": data.title,
                    "class": data.class_,
                    "state": "proposed",
                },
            )
        )

        await self._session.commit()

        logger.info(
            "commitment_created",
            commitment_id=str(commitment.id),
            title=data.title,
            class_=data.class_,
        )
        return _to_response(commitment)

    async def get(self, commitment_id: UUID) -> CommitmentResponse | None:
        """Get a commitment by ID (RLS-filtered)."""
        commitment = await self._session.get(Commitment, commitment_id)
        if commitment is None:
            return None
        return _to_response(commitment)

    async def transition_state(
        self,
        commitment_id: UUID,
        data: CommitmentStateTransition,
        *,
        idempotency_key: str,
    ) -> CommitmentResponse:
        """Transition commitment state with version check.

        - Validates transition is legal per VALID_TRANSITIONS
        - Checks data.version matches DB version (stale → 409)
        - Increments version on success
        - Writes audit_log entry
        """
        # Idempotency check
        existing = await self._check_idempotency(idempotency_key)
        if existing is not None:
            commitment = await self._session.get(Commitment, UUID(existing.response_hash))
            if commitment is not None:
                return _to_response(commitment)

        commitment = await self._session.get(Commitment, commitment_id)
        if commitment is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Commitment not found")

        # Version check — optimistic concurrency (sacred rule #6)
        if commitment.version != data.version:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail={
                    "type": "stale_version",
                    "title": "Version conflict",
                    "detail": f"Expected version {data.version}, found {commitment.version}",
                    "current_version": commitment.version,
                },
            )

        # Validate transition
        current_state = str(commitment.state)
        valid_next = VALID_TRANSITIONS.get(current_state, set())
        if data.new_state not in valid_next:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=422,
                detail={
                    "type": "invalid_transition",
                    "title": "Invalid state transition",
                    "detail": f"Cannot transition from {current_state} to {data.new_state}",
                    "valid_transitions": sorted(valid_next),
                },
            )

        old_state = current_state
        commitment.state = CommitmentState(data.new_state)
        commitment.version += 1
        commitment.updated_at = datetime.utcnow()

        # Record idempotency
        await self._record_idempotency(idempotency_key, str(commitment.id))

        # Audit log
        self._session.add(
            AuditLog(
                actor_id=self._principal_id,
                actor_kind="user",
                context_id=commitment.context_id,
                event="commitment.state_changed",
                subject_id=commitment.id,
                detail={
                    "old_state": old_state,
                    "new_state": data.new_state,
                    "version": commitment.version,
                },
            )
        )

        await self._session.commit()

        logger.info(
            "commitment_state_changed",
            commitment_id=str(commitment_id),
            old_state=old_state,
            new_state=data.new_state,
            version=commitment.version,
        )
        return _to_response(commitment)
