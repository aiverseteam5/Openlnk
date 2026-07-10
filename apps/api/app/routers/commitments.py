"""Commitment CRUD endpoints.

Routers hold zero business logic (CLAUDE.md). Delegate to CommitmentService.
Every mutation requires Idempotency-Key header (sacred rule #5).
Every commitment write checks version (sacred rule #6).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.schemas import (
    CommitmentCreate,
    CommitmentResponse,
    CommitmentStateTransition,
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
