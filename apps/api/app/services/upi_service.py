"""UPI intent deep-link service (OL-010, ADR-006).

Generates UPI intent URLs for fee/payment commitments.
Funds never transit an OpenLnk account — link resolves to center's VPA.
"""

import re
from urllib.parse import quote, urlencode

import structlog

logger = structlog.get_logger()

# UPI VPA format: {name}@{bank}
VPA_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$")


class UpiService:
    """Generate UPI intent deep-links per ADR-006."""

    def generate_intent_url(
        self,
        *,
        vpa: str,
        amount_paise: int,
        payee_name: str,
        note: str,
    ) -> str:
        """Generate a UPI intent URL.

        Args:
            vpa: Payee's VPA (e.g., center@upi)
            amount_paise: Amount in paise (100 paise = 1 INR)
            payee_name: Display name for the payee
            note: Transaction note

        Returns:
            UPI intent URL (upi://pay?...)

        Raises:
            ValueError: If VPA is empty or malformed.
        """
        if not vpa:
            msg = "VPA is required for UPI intent"
            raise ValueError(msg)

        if not VPA_PATTERN.match(vpa):
            msg = f"VPA must match {{name}}@{{bank}} format, got: {vpa}"
            raise ValueError(msg)

        amount_inr = f"{amount_paise / 100:.2f}"

        params = urlencode({
            "pa": vpa,
            "pn": payee_name,
            "am": amount_inr,
            "cu": "INR",
            "tn": note,
        })

        url = f"upi://pay?{params}"

        logger.info(
            "upi_intent_generated",
            vpa=vpa,
            amount_inr=amount_inr,
        )
        return url
