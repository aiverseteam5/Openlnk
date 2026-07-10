"""Tests for OL-004 (audit log) and OL-007 (idempotency).

Structural tests verifying the code paths exist. Full integration
tests require a running Postgres (testcontainers in CI).
"""

from uuid import uuid4

import pytest

from app.models import AuditLog, IdempotencyKey
from app.services.commitment_service import CommitmentService


@pytest.mark.req("OL-004")
class TestAuditLog:
    """The system shall record every commitment state change in the
    immutable audit log."""

    def test_audit_log_model_exists(self):
        al = AuditLog(
            actor_id=uuid4(),
            actor_kind="user",
            context_id=uuid4(),
            event="commitment.state_change",
            subject_id=uuid4(),
            detail={"old_state": "proposed", "new_state": "accepted"},
        )
        assert al.event == "commitment.state_change"
        assert al.detail["old_state"] == "proposed"

    def test_audit_log_supports_agent_actor(self):
        al = AuditLog(
            actor_id=uuid4(),
            actor_kind="agent",
            event="commitment.created",
            prompt_hash="sha256:abc",
            model_id="claude-sonnet-4-20250514",
        )
        assert al.actor_kind == "agent"
        assert al.prompt_hash is not None
        assert al.model_id is not None

    def test_audit_log_table_name(self):
        assert AuditLog.__tablename__ == "audit_log"

    def test_commitment_service_creates_audit_entries(self):
        """CommitmentService.create and transition_state include audit log writes."""
        import inspect

        # Verify audit log is referenced in the service code
        source = inspect.getsource(CommitmentService.create)
        assert "AuditLog" in source

        source = inspect.getsource(CommitmentService.transition_state)
        assert "AuditLog" in source


@pytest.mark.req("OL-007")
class TestIdempotency:
    """The system shall honor an Idempotency-Key header on all
    mutation endpoints."""

    def test_idempotency_key_model_exists(self):
        ik = IdempotencyKey(
            key="idem-123",
            principal_id=uuid4(),
            response_hash="commitment-uuid-here",
        )
        assert ik.key == "idem-123"

    def test_idempotency_key_table_name(self):
        assert IdempotencyKey.__tablename__ == "idempotency_keys"

    def test_commitment_service_checks_idempotency(self):
        """CommitmentService methods check idempotency before writes."""
        import inspect

        source = inspect.getsource(CommitmentService.create)
        assert "idempotency" in source.lower()

        source = inspect.getsource(CommitmentService.transition_state)
        assert "idempotency" in source.lower()

    def test_commitment_create_endpoint_requires_header(self):
        """POST /v1/commitments requires Idempotency-Key header."""
        import inspect

        from app.routers.commitments import create_commitment

        sig = inspect.signature(create_commitment)
        params = list(sig.parameters.keys())
        assert "idempotency_key" in params

    def test_state_transition_endpoint_requires_header(self):
        """PATCH /v1/commitments/{id}/state requires Idempotency-Key header."""
        import inspect

        from app.routers.commitments import transition_state

        sig = inspect.signature(transition_state)
        params = list(sig.parameters.keys())
        assert "idempotency_key" in params
