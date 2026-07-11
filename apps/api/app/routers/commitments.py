"""Commitment CRUD endpoints.

Routers hold zero business logic (CLAUDE.md). Delegate to CommitmentService.
Every mutation requires Idempotency-Key header (sacred rule #5).
Every commitment write checks version (sacred rule #6).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.schemas import (
    CommitmentAmend,
    CommitmentCreate,
    CommitmentResponse,
    CommitmentStateTransition,
    CorrectionAction,
    CursorPage,
)
from app.services.commitment_service import CommitmentService

router = APIRouter(prefix="/commitments", tags=["commitments"])


def get_commitment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    principal_id: Annotated[UUID, Depends(get_principal_id)],
) -> CommitmentService:
    return CommitmentService(session, principal_id)


@router.post("", response_model=CommitmentResponse, status_code=201)
async def create_commitment(
    body: CommitmentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CommitmentResponse:
    """Create a new commitment. State defaults to PROPOSED."""
    return await service.create(body, idempotency_key=idempotency_key)


@router.get("", response_model=CursorPage)
async def list_commitments(
    context_id: UUID | None = Query(default=None),
    state: str | None = Query(default=None, pattern="^(proposed|accepted|in_progress|done|broken|cancelled)$"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CursorPage:
    """List commitments with cursor pagination. RLS-filtered."""
    return await service.list(
        context_id=context_id, state=state, cursor=cursor, limit=limit,
    )


@router.get("/{commitment_id}", response_model=CommitmentResponse)
async def get_commitment(
    commitment_id: UUID,
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CommitmentResponse:
    """Get a single commitment by ID."""
    result = await service.get(commitment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return result


@router.patch("/{commitment_id}/state", response_model=CommitmentResponse)
async def transition_state(
    commitment_id: UUID,
    body: CommitmentStateTransition,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CommitmentResponse:
    """Transition commitment state. Checks version for optimistic concurrency.

    Stale version → 409 (RFC 9457 problem+json).
    """
    return await service.transition_state(commitment_id, body, idempotency_key=idempotency_key)


@router.patch("/{commitment_id}/amend", response_model=CommitmentResponse)
async def amend_commitment(
    commitment_id: UUID,
    body: CommitmentAmend,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CommitmentResponse:
    """Amend commitment fields (OL-002a).

    For fee/payment after accepted: resets to proposed (re-acceptance required).
    """
    return await service.amend(commitment_id, body, idempotency_key=idempotency_key)


@router.post("/{commitment_id}/correct", response_model=CommitmentResponse)
async def correct_commitment(
    commitment_id: UUID,
    body: CorrectionAction,
    service: CommitmentService = Depends(get_commitment_service),  # noqa: B008
) -> CommitmentResponse:
    """Correct or reject an extracted commitment (OL-026).

    Corrections enter the eval-candidate queue (OL-090).
    """
    return await service.correct(commitment_id, body.action, body.edits)
