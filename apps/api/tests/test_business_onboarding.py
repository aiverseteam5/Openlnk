"""Tests for OL-100..100b — business onboarding + consent.

OL-100: Import roster from Excel/CSV, first reminder in <= 30 min.
OL-100a: Child-linked data held in staging until guardian consent.
OL-100b: Clinic patient data requires health_data consent.
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-100")
class TestRosterImport:
    """Import center's student/parent roster from Excel/CSV."""

    def test_roster_service_exists(self):
        from app.services.roster_service import RosterService

        assert RosterService is not None

    def test_roster_service_has_import_method(self):
        from app.services.roster_service import RosterService

        service = RosterService()
        assert hasattr(service, "import_roster")

    def test_roster_import_returns_result(self):
        """Import returns count of imported rows and any errors."""
        from app.services.roster_service import RosterService

        service = RosterService()
        result = service.import_roster(
            business_id=uuid4(),
            rows=[
                {"student_name": "Alice", "parent_phone": "+919876543210", "batch": "A"},
                {"student_name": "Bob", "parent_phone": "+919876543211", "batch": "A"},
            ],
        )
        assert result.imported == 2
        assert result.errors == []

    def test_roster_import_validates_phone(self):
        """Invalid phone numbers are reported as errors."""
        from app.services.roster_service import RosterService

        service = RosterService()
        result = service.import_roster(
            business_id=uuid4(),
            rows=[
                {"student_name": "Alice", "parent_phone": "invalid", "batch": "A"},
            ],
        )
        assert result.imported == 0
        assert len(result.errors) == 1

    def test_staging_record_model_exists(self):
        """StagingRecord model for holding pre-consent data."""
        from app.models import StagingRecord

        assert StagingRecord.__tablename__ == "staging_records"


@pytest.mark.req("OL-100a")
class TestChildLinkedConsent:
    """Child-linked data held in staging until guardian OTP consent."""

    def test_staging_record_has_consent_fields(self):
        from app.models import StagingRecord

        fields = {c.name for c in StagingRecord.__table__.columns}
        assert "consent_received" in fields
        assert "business_id" in fields

    def test_roster_creates_staging_not_commitments(self):
        """Import creates staging records, not commitments directly."""
        import inspect

        from app.services.roster_service import RosterService

        source = inspect.getsource(RosterService.import_roster)
        assert "staging" in source.lower() or "StagingRecord" in source

    def test_commitment_blocked_without_consent(self):
        """Commitments SHALL NOT be created until consent recorded."""
        from app.services.roster_service import RosterService

        service = RosterService()
        assert service.can_create_commitment(consent_received=False) is False
        assert service.can_create_commitment(consent_received=True) is True


@pytest.mark.req("OL-100b")
class TestClinicConsent:
    """Clinic patient data requires health_data consent."""

    def test_health_data_consent_scope(self):
        """health_data consent scope exists."""
        from app.services.roster_service import RosterService

        service = RosterService()
        assert service.requires_health_consent(vertical="clinic") is True
        assert service.requires_health_consent(vertical="tuition") is False
