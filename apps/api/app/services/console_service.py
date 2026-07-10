"""Console service — business dashboard + WhatsApp share (OL-101, OL-103a, OL-105).

Dashboard shows batches, schedule, fee cycle, and commitment states.
WhatsApp share CTA generates wa.me deep-link on commitment done.
ROI metrics show fees-recovered vs subscription cost.
"""

from urllib.parse import quote
from uuid import UUID

import structlog

logger = structlog.get_logger()


class ConsoleService:
    """Business console service."""

    def get_dashboard_sections(self) -> dict:
        """OL-101: Return dashboard sections for the console view."""
        return {
            "batches": [],
            "schedule": [],
            "fee_cycle": [],
            "commitments": {
                "pending": [],
                "at_risk": [],
                "closed": [],
            },
        }

    def generate_whatsapp_share(
        self,
        *,
        whatsapp_number: str,
        commitment_title: str,
        commitment_date: str,
    ) -> str:
        """OL-103a: Generate WhatsApp share deep-link for done commitments.

        User-triggered only, NOT eligible for Bounded-auto execution.
        """
        text = f"Payment confirmed: {commitment_title} ({commitment_date})"
        return f"https://wa.me/{whatsapp_number}?text={quote(text)}"

    def get_roi_metrics(self, business_id: UUID) -> dict:
        """OL-105: Fees-recovered-this-period vs subscription cost."""
        # In production, queries commitment state transitions
        return {
            "fees_recovered_paise": 0,
            "subscription_cost_paise": 0,
            "period": "current_month",
        }
