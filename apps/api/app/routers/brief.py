"""Daily brief endpoint — AI-generated commitment summary.

Routers hold zero business logic (CLAUDE.md).
Commitment lifecycle stage: protect (surface what needs attention today).
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.models import Commitment, CommitmentState
from app.services.llm import LLMAdapter

logger = structlog.get_logger()

router = APIRouter(prefix="/brief", tags=["brief"])

_TERMINAL_STATES = [
    CommitmentState.DONE.value,
    CommitmentState.BROKEN.value,
    CommitmentState.CANCELLED.value,
]


# ── Schemas ──


class BriefCounts(BaseModel):
    at_risk: int
    due_today: int
    proposed: int
    done_today: int
    total_active: int


class BriefSummaryResponse(BaseModel):
    summary: str
    counts: BriefCounts
    generated_at: str


# ── Routes ──


@router.get("/summary", response_model=BriefSummaryResponse)
async def get_brief_summary(
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> BriefSummaryResponse:
    """Generate an AI-powered daily brief summarizing commitment status."""
    now = datetime.now(UTC)
    today = now.date()

    # at_risk: due_at < now AND state NOT terminal
    at_risk_result = await db.execute(
        select(func.count(Commitment.id)).where(
            Commitment.owner_id == principal_id,
            Commitment.due_at < now,
            Commitment.state.notin_(_TERMINAL_STATES),
        )
    )
    at_risk = at_risk_result.scalar() or 0

    # due_today: due_at is today AND state NOT terminal
    due_today_result = await db.execute(
        select(func.count(Commitment.id)).where(
            Commitment.owner_id == principal_id,
            cast(Commitment.due_at, Date) == today,
            Commitment.state.notin_(_TERMINAL_STATES),
        )
    )
    due_today = due_today_result.scalar() or 0

    # proposed: state == 'proposed'
    proposed_result = await db.execute(
        select(func.count(Commitment.id)).where(
            Commitment.owner_id == principal_id,
            Commitment.state == CommitmentState.PROPOSED.value,
        )
    )
    proposed = proposed_result.scalar() or 0

    # done_today: state == 'done' AND updated_at is today
    done_today_result = await db.execute(
        select(func.count(Commitment.id)).where(
            Commitment.owner_id == principal_id,
            Commitment.state == CommitmentState.DONE.value,
            cast(Commitment.updated_at, Date) == today,
        )
    )
    done_today = done_today_result.scalar() or 0

    # total_active: state NOT terminal
    total_active_result = await db.execute(
        select(func.count(Commitment.id)).where(
            Commitment.owner_id == principal_id,
            Commitment.state.notin_(_TERMINAL_STATES),
        )
    )
    total_active = total_active_result.scalar() or 0

    counts = BriefCounts(
        at_risk=at_risk,
        due_today=due_today,
        proposed=proposed,
        done_today=done_today,
        total_active=total_active,
    )

    # Generate AI summary
    llm = LLMAdapter()
    try:
        summary = await llm.generate_brief_summary(
            at_risk=at_risk,
            due_today=due_today,
            proposed=proposed,
            done_today=done_today,
            total_active=total_active,
        )
    finally:
        await llm.close()

    logger.info(
        "brief_summary_served",
        principal_id=str(principal_id),
        at_risk=at_risk,
        due_today=due_today,
        total_active=total_active,
    )

    return BriefSummaryResponse(
        summary=summary,
        counts=counts,
        generated_at=now.isoformat(),
    )
