"""Console service — business dashboard + WhatsApp share (OL-101, OL-103a, OL-105).

Dashboard shows batches, schedule, fee cycle, and commitment states.
WhatsApp share CTA generates wa.me deep-link on commitment done.
ROI metrics show fees-recovered vs subscription cost.
"""

from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Commitment, CommitmentState

logger = structlog.get_logger()


class ConsoleService:
    """Business console service."""

    async def get_dashboard_sections(
        self,
        *,
        db: AsyncSession,
        context_id: UUID,
    ) -> dict:
        """OL-101: Return dashboard sections for the console view."""
        # Pending commitments
        pending_result = await db.execute(
            select(Commitment).where(
                Commitment.context_id == context_id,
                Commitment.state.in_([
                    CommitmentState.PROPOSED.value,
                    CommitmentState.ACCEPTED.value,
                    CommitmentState.IN_PROGRESS.value,
                ]),
            ).order_by(Commitment.due_at.asc().nullslast()).limit(20)
        )
        pending = pending_result.scalars().all()

        # At-risk commitments
        at_risk_result = await db.execute(
            select(Commitment).where(
                Commitment.context_id == context_id,
                Commitment.due_at < datetime.now(UTC),
                Commitment.state.not_in([
                    CommitmentState.DONE.value,
                    CommitmentState.BROKEN.value,
                    CommitmentState.CANCELLED.value,
                ]),
            ).order_by(Commitment.due_at.asc()).limit(20)
        )
        at_risk = at_risk_result.scalars().all()

        # Recently closed
        closed_result = await db.execute(
            select(Commitment).where(
                Commitment.context_id == context_id,
                Commitment.state.in_([
                    CommitmentState.DONE.value,
                    CommitmentState.CANCELLED.value,
                ]),
            ).order_by(Commitment.updated_at.desc()).limit(20)
        )
        closed = closed_result.scalars().all()

        return {
            "commitments": {
                "pending": [_commitment_summary(c) for c in pending],
                "at_risk": [_commitment_summary(c) for c in at_risk],
                "closed": [_commitment_summary(c) for c in closed],
            },
        }

    async def get_roi_metrics(
        self,
        *,
        db: AsyncSession,
        context_id: UUID,
    ) -> dict:
        """OL-105: Fees-recovered-this-period vs subscription cost."""
        month_start = datetime.now(UTC).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        fees_result = await db.execute(
            select(func.coalesce(func.sum(Commitment.amount_paise), 0)).where(
                Commitment.context_id == context_id,
                Commitment.class_ == "fee",
                Commitment.state == CommitmentState.DONE.value,
                Commitment.updated_at >= month_start,
            )
        )
        fees_recovered = fees_result.scalar() or 0

        return {
            "fees_recovered_paise": fees_recovered,
            "subscription_cost_paise": 150000,
            "period": "current_month",
        }

    def generate_whatsapp_share(
        self,
        *,
        whatsapp_number: str,
        commitment_title: str,
        commitment_date: str,
    ) -> str:
        """OL-103a: Generate WhatsApp share deep-link for done commitments."""
        text = f"Payment confirmed: {commitment_title} ({commitment_date})"
        return f"https://wa.me/{whatsapp_number}?text={quote(text)}"


def _commitment_summary(c: Commitment) -> dict:
    """Minimal commitment dict for dashboard display."""
    return {
        "id": str(c.id),
        "title": c.title,
        "class": c.class_,
        "state": c.state,
        "amount_paise": c.amount_paise,
        "due_at": c.due_at.isoformat() if c.due_at else None,
    }
