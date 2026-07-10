"""Tests for OL-124 — data export and account deletion.

Deletion semantics per ADR-002 §Erasure:
- Commitment graph anonymized, not destroyed
- Encryption keys destroyed (effective erasure)
- Consent/audit events retained for compliance
- Principal soft-deleted (phone nulled, name anonymized)
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-124")
class TestDataExport:
    """OL-124: Data export."""

    def test_export_includes_commitments(self):
        """Export contains all commitments owned by the principal."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        export = service.export_data(principal_id=principal_id)
        assert "commitments" in export
        assert export["principal_id"] == str(principal_id)

    def test_export_includes_consent_events(self):
        """Export contains all consent events for the principal."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        export = service.export_data(principal_id=principal_id)
        assert "consent_events" in export

    def test_export_includes_contexts(self):
        """Export contains context memberships."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        export = service.export_data(principal_id=principal_id)
        assert "contexts" in export

    def test_export_format_is_json(self):
        """Export is machine-readable JSON."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        export = service.export_data(principal_id=principal_id)
        assert isinstance(export, dict)
        assert "exported_at" in export


@pytest.mark.req("OL-124")
class TestAccountDeletion:
    """OL-124: Account deletion per ADR-002 §Erasure."""

    def test_commitment_graph_anonymized_not_destroyed(self):
        """Commitments are anonymized, not deleted, to preserve counterparty ledgers."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["commitments_deleted"] is False
        assert result["commitments_anonymized"] is True

    def test_principal_soft_deleted(self):
        """Principal row is soft-deleted: phone nulled, name anonymized."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["principal_soft_deleted"] is True
        assert result["phone_nulled"] is True
        assert result["name_anonymized"] is True

    def test_encryption_keys_destroyed(self):
        """Encryption keys destroyed = effective erasure without data destruction."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["encryption_keys_destroyed"] is True

    def test_audit_log_retained(self):
        """Audit log entries retained for legal/regulatory compliance."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["audit_log_retained"] is True

    def test_consent_events_retained(self):
        """Consent events retained for DPDP compliance."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["consent_events_retained"] is True

    def test_tombstone_principal_created(self):
        """Owner/counterparty pointers replaced with tombstone principal."""
        from app.services.data_portability_service import DataPortabilityService

        service = DataPortabilityService()
        principal_id = uuid4()

        result = service.delete_account(principal_id=principal_id)
        assert result["tombstone_principal_used"] is True
        assert result["tombstone_kind"] == "deleted"
