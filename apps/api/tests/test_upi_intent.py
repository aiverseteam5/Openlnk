"""Tests for OL-010 — UPI intent deep-link.

WHERE a commitment carries class fee or payment, the system shall attach
a UPI intent deep-link per ADR-006.
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-010")
class TestUpiIntent:
    """UPI intent deep-link for fee/payment commitments."""

    def test_upi_service_exists(self):
        from app.services.upi_service import UpiService

        assert UpiService is not None

    def test_generate_upi_intent(self):
        """Generate a UPI intent URL from VPA and amount."""
        from app.services.upi_service import UpiService

        service = UpiService()
        url = service.generate_intent_url(
            vpa="center@upi",
            amount_paise=150000,
            payee_name="ABC Tuition",
            note="Fee - July 2026",
        )
        assert url.startswith("upi://pay")
        assert "center%40upi" in url or "center@upi" in url
        assert "1500.00" in url  # 150000 paise = 1500.00 INR

    def test_upi_intent_requires_vpa(self):
        """UPI intent requires a valid VPA."""
        from app.services.upi_service import UpiService

        service = UpiService()
        with pytest.raises(ValueError, match="VPA"):
            service.generate_intent_url(
                vpa="",
                amount_paise=100,
                payee_name="Test",
                note="Test",
            )

    def test_upi_intent_validates_vpa_format(self):
        """VPA must match {name}@{bank} format (OL-103b)."""
        from app.services.upi_service import UpiService

        service = UpiService()
        with pytest.raises(ValueError, match="format"):
            service.generate_intent_url(
                vpa="invalid-no-at-sign",
                amount_paise=100,
                payee_name="Test",
                note="Test",
            )

    def test_upi_intent_amount_conversion(self):
        """Amount is correctly converted from paise to rupees."""
        from app.services.upi_service import UpiService

        service = UpiService()
        url = service.generate_intent_url(
            vpa="shop@ybl",
            amount_paise=99,
            payee_name="Shop",
            note="Test",
        )
        assert "0.99" in url
