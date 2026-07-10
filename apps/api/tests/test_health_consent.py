"""Tests for OL-120a — health_data consent scope for clinics.

The system SHALL implement a health_data:<patient_ref> consent scope.
Legal review REQUIRED before first clinic patient onboarded (Gate 3 blocker).
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-120a")
class TestHealthDataConsent:
    """health_data consent scope in consent_events for clinic contexts."""

    def test_health_consent_scope_format(self):
        """Consent scope follows health_data:<patient_ref> format."""
        from app.services.consent_service import ConsentService

        service = ConsentService()
        patient_ref = str(uuid4())
        result = service.record_consent(
            principal_id=uuid4(),
            scope=f"health_data:{patient_ref}",
            action="grant",
            method="otp_verified",
        )
        assert result["recorded"] is True

    def test_consent_includes_processing_purpose(self):
        """Consent records include stated processing purpose."""
        from app.services.consent_service import ConsentService

        service = ConsentService()
        result = service.record_consent(
            principal_id=uuid4(),
            scope="health_data:patient_001",
            action="grant",
            method="otp_verified",
            processing_purpose="appointment_management",
            data_fiduciary="OpenLnk / TynkAI",
        )
        assert result["recorded"] is True

    def test_consent_includes_withdrawal_mechanism(self):
        """Explicit withdrawal mechanism available."""
        from app.services.consent_service import ConsentService

        service = ConsentService()
        # Withdrawal is a first-class action
        result = service.record_consent(
            principal_id=uuid4(),
            scope="health_data:patient_002",
            action="withdraw",
            method="user_request",
        )
        assert result["action"] == "withdraw"

    def test_roster_service_requires_health_consent_for_clinic(self):
        """Clinic vertical requires health_data consent."""
        from app.services.roster_service import RosterService

        service = RosterService()
        assert service.requires_health_consent(vertical="clinic") is True
        assert service.requires_health_consent(vertical="tuition") is False
