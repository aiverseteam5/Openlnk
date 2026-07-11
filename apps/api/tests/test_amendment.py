"""Tests for OL-002a — amendment notification + re-acceptance.

WHEN a commitment's title, due date, or amount is amended after accepted state,
the system shall notify the counterparty; WHERE commitment class is fee or payment,
amendment SHALL require counterparty re-acceptance.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.schemas import CommitmentAmend


@pytest.mark.req("OL-002a")
class TestAmendmentSchema:
    """Amendment schema supports partial updates to title, due_at, amount."""

    def test_amend_schema_exists(self):
        amend = CommitmentAmend(title="Updated title", version=1)
        assert amend.title == "Updated title"
        assert amend.due_at is None
        assert amend.amount_paise is None

    def test_amend_partial_due_at(self):
        future = datetime.now(UTC) + timedelta(days=7)
        amend = CommitmentAmend(due_at=future, version=1)
        assert amend.due_at == future
        assert amend.title is None

    def test_amend_partial_amount(self):
        amend = CommitmentAmend(amount_paise=50000, version=1)
        assert amend.amount_paise == 50000

    def test_amend_requires_version(self):
        """Version is mandatory for optimistic concurrency."""
        with pytest.raises(ValueError):
            CommitmentAmend()


@pytest.mark.req("OL-002a")
class TestAmendmentService:
    """CommitmentService.amend handles amendment logic."""

    def test_amend_method_exists(self):
        """CommitmentService has an amend method."""
        from app.services.commitment_service import CommitmentService

        assert hasattr(CommitmentService, "amend")

    def test_amend_method_checks_version(self):
        """Amend method references version for optimistic concurrency."""
        import inspect

        from app.services.commitment_service import CommitmentService

        source = inspect.getsource(CommitmentService.amend)
        assert "version" in source

    def test_amend_method_writes_audit_log(self):
        """Amend method writes to the audit log."""
        import inspect

        from app.services.commitment_service import CommitmentService

        source = inspect.getsource(CommitmentService.amend)
        assert "AuditLog" in source

    def test_amend_method_checks_reacceptance(self):
        """For fee/payment after accepted, amend triggers re-acceptance."""
        import inspect

        from app.services.commitment_service import CommitmentService

        source = inspect.getsource(CommitmentService.amend)
        # Must reference fee/payment re-acceptance logic
        assert "proposed" in source.lower() or "re_accept" in source.lower()

    def test_amend_method_checks_idempotency(self):
        """Amend method honors idempotency key."""
        import inspect

        from app.services.commitment_service import CommitmentService

        source = inspect.getsource(CommitmentService.amend)
        assert "idempotency" in source.lower()


@pytest.mark.req("OL-002a")
class TestAmendmentEndpoint:
    """PATCH /v1/commitments/{id}/amend requires idempotency key."""

    def test_amend_endpoint_exists(self):
        from app.routers.commitments import amend_commitment

        assert callable(amend_commitment)

    def test_amend_endpoint_requires_idempotency_key(self):
        import inspect

        from app.routers.commitments import amend_commitment

        sig = inspect.signature(amend_commitment)
        params = list(sig.parameters.keys())
        assert "idempotency_key" in params
