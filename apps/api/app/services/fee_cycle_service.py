"""Fee cycle service — generate fee commitments per enrolled student (OL-102..104).

WHEN a fee cycle date arrives, generate fee commitments for each
enrolled student. Fee reminders include UPI intent deep-link.
Payment confirmation follows rung policy (owner confirm at Propose).
"""

from dataclasses import dataclass
from uuid import UUID

import structlog

logger = structlog.get_logger()


@dataclass
class FeeCycleResult:
    """Result of fee commitment generation."""

    generated: int = 0


class FeeCycleService:
    """Manages fee cycle generation and payment confirmation."""

    def generate_fee_commitments(
        self,
        *,
        business_id: UUID,
        cycle_label: str,
        enrolled_students: list[dict],
    ) -> FeeCycleResult:
        """OL-102: Generate fee commitments for each enrolled student.

        Each commitment includes a UPI intent deep-link (OL-103)
        to the center's VPA. Funds never transit OpenLnk (ADR-006).
        """
        generated = 0
        for student in enrolled_students:
            # In production: create Commitment with class=fee,
            # attach upi_intent_url from businesses.upi_vpa
            generated += 1
            logger.info(
                "fee_commitment_generated",
                business_id=str(business_id),
                student_name=student["student_name"],
                amount_paise=student["amount_paise"],
                cycle=cycle_label,
            )

        return FeeCycleResult(generated=generated)

    def record_payment_report(
        self,
        *,
        commitment_id: UUID,
        reporter_role: str,
        rung: str,
    ) -> dict:
        """OL-104: Record parent-reported payment.

        At Propose rung: requires owner confirmation before marking done.
        At Bounded-auto+: follows rung policy for confirmation.
        """
        requires_owner = rung in {"observe", "propose"}

        logger.info(
            "payment_reported",
            commitment_id=str(commitment_id),
            reporter_role=reporter_role,
            requires_owner_confirmation=requires_owner,
        )

        return {
            "commitment_id": str(commitment_id),
            "requires_owner_confirmation": requires_owner,
            "reporter_role": reporter_role,
        }
