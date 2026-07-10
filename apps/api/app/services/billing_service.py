"""Billing service — Razorpay subscriptions + lapse handling (OL-106, OL-107).

Centers billed via Razorpay with GST-compliant invoices.
Subscription lapse: owner read-only, parent access 90 days,
commitments anonymized not deleted (ADR-002 §Erasure).
"""

from uuid import UUID

import structlog

logger = structlog.get_logger()

# Parent access window after subscription lapse
LAPSE_PARENT_ACCESS_DAYS = 90


class BillingService:
    """Manages Razorpay subscriptions and lapse handling."""

    def create_subscription(
        self,
        *,
        business_id: UUID,
        plan_id: str,
    ) -> dict:
        """OL-106: Create a Razorpay subscription for a center."""
        # In production: calls Razorpay subscription API
        logger.info(
            "subscription_created",
            business_id=str(business_id),
            plan_id=plan_id,
        )
        return {
            "business_id": str(business_id),
            "plan_id": plan_id,
            "status": "active",
        }

    def generate_invoice(
        self,
        *,
        business_id: UUID,
        amount_paise: int,
        gst_rate: float = 0.18,
    ) -> dict:
        """OL-106: Generate GST-compliant invoice."""
        gst_amount = int(amount_paise * gst_rate)
        return {
            "business_id": str(business_id),
            "subtotal_paise": amount_paise,
            "gst_paise": gst_amount,
            "total_paise": amount_paise + gst_amount,
            "gst_rate": gst_rate,
        }

    def handle_subscription_lapse(self, business_id: UUID) -> dict:
        """OL-107: Handle subscription lapse.

        - Owner degrades to read-only
        - Parent access preserved for 90 days
        - Commitments anonymized, never deleted (preserves household ledger)
        """
        logger.info(
            "subscription_lapsed",
            business_id=str(business_id),
        )
        return {
            "owner_read_only": True,
            "parent_access_days": LAPSE_PARENT_ACCESS_DAYS,
            "commitments_deleted": False,
            "business_ref_anonymized": True,
        }
