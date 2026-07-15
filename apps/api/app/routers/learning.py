"""Learning profile routes — nudge suggestions and quiet hours (OL-093).

Surfaces the learning service for per-user nudge timing and quiet-hour
configuration.  Only commitment lifecycle events are accepted as learning
signals (PRD §8 — no engagement mechanics).

Commitment lifecycle stage served: **protect** (smart reminders).
Routers hold zero business logic (CLAUDE.md).
"""

from datetime import time
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.models import Principal
from app.services.learning_service import LearningService

logger = structlog.get_logger()

router = APIRouter(prefix="/me", tags=["learning"])

_learning_service = LearningService()


# ── Schemas ──


class LearningProfileResponse(BaseModel):
    preferred_nudge_hour: int | None  # 0-23, None if insufficient data
    suggested_quiet_hours: dict | None  # {start_hour: int, end_hour: int} or None
    quiet_hours_start: str | None  # Current configured quiet hours (HH:MM)
    quiet_hours_end: str | None
    data_points: int  # How many signals collected


class QuietHoursUpdate(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")  # HH:MM
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class LearningSignalRequest(BaseModel):
    event_type: str
    hour_of_day: int = Field(ge=0, le=23)


class LearningSignalResponse(BaseModel):
    accepted: bool
    reason: str | None = None


# ── Helpers ──


async def _build_profile(
    principal_id: UUID,
    db: AsyncSession,
) -> LearningProfileResponse:
    """Build a LearningProfileResponse from DB + in-memory service."""
    result = await db.execute(
        select(Principal).where(Principal.id == principal_id)
    )
    principal = result.scalar_one_or_none()
    if principal is None:
        raise HTTPException(status_code=404, detail="Principal not found")

    preferred_nudge_hour = _learning_service.get_preferred_nudge_hour(
        principal_id=principal_id,
    )
    suggested_quiet_hours = _learning_service.suggest_quiet_hours(
        principal_id=principal_id,
    )

    # Count data points from in-memory store
    data_points = len(
        _learning_service._response_times.get(principal_id, [])
    )

    return LearningProfileResponse(
        preferred_nudge_hour=preferred_nudge_hour,
        suggested_quiet_hours=suggested_quiet_hours,
        quiet_hours_start=(
            principal.quiet_hours_start.strftime("%H:%M")
            if principal.quiet_hours_start
            else None
        ),
        quiet_hours_end=(
            principal.quiet_hours_end.strftime("%H:%M")
            if principal.quiet_hours_end
            else None
        ),
        data_points=data_points,
    )


# ── Routes ──


@router.get("/learning-profile", response_model=LearningProfileResponse)
async def get_learning_profile(
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> LearningProfileResponse:
    """OL-093: Return the user's learning profile with nudge suggestions and quiet hours."""
    return await _build_profile(principal_id, db)


@router.patch("/quiet-hours", response_model=LearningProfileResponse)
async def update_quiet_hours(
    body: QuietHoursUpdate,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> LearningProfileResponse:
    """OL-093: Set quiet hours for the authenticated user."""
    # Parse HH:MM strings into time objects
    try:
        start_time = time.fromisoformat(body.start)
        end_time = time.fromisoformat(body.end)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid time format: {exc}",
        ) from exc

    result = await db.execute(
        select(Principal).where(Principal.id == principal_id)
    )
    principal = result.scalar_one_or_none()
    if principal is None:
        raise HTTPException(status_code=404, detail="Principal not found")

    principal.quiet_hours_start = start_time
    principal.quiet_hours_end = end_time
    await db.commit()

    logger.info(
        "quiet_hours_updated",
        principal_id=str(principal_id),
        start=body.start,
        end=body.end,
    )

    return await _build_profile(principal_id, db)


@router.post("/learning-signal", response_model=LearningSignalResponse)
async def record_learning_signal(
    body: LearningSignalRequest,
    principal_id: UUID = Depends(get_principal_id),
) -> LearningSignalResponse:
    """OL-093: Record a learning signal from a commitment lifecycle event."""
    if not _learning_service.is_valid_signal(event_type=body.event_type):
        return LearningSignalResponse(
            accepted=False,
            reason=f"Event type '{body.event_type}' is not a valid commitment lifecycle event",
        )

    _learning_service.record_response_time(
        principal_id=principal_id,
        hour_of_day=body.hour_of_day,
        event_type=body.event_type,
    )

    return LearningSignalResponse(accepted=True)
