"""Tests for context auto-clustering — OL-042, OL-043."""

from uuid import uuid4

import pytest

from app.models import ContextKind
from app.services.context_service import ContextService


@pytest.mark.req("OL-042")
class TestAutoCluster:
    """The system shall auto-cluster threads into typed contexts
    from participant and content signal, with user override."""

    def test_determine_context_kind_household(self):
        """Household participants → household context."""
        service = ContextService()
        kind = service.determine_context_kind(
            household_id=uuid4(),
            business_id=None,
        )
        assert kind == ContextKind.HOUSEHOLD

    def test_determine_context_kind_business(self):
        """Business participants → business_batch context."""
        service = ContextService()
        kind = service.determine_context_kind(
            household_id=None,
            business_id=uuid4(),
        )
        assert kind == ContextKind.BUSINESS_BATCH

    def test_determine_context_kind_rejects_both(self):
        """Cannot have both household_id and business_id."""
        service = ContextService()
        with pytest.raises(ValueError, match="exactly one"):
            service.determine_context_kind(
                household_id=uuid4(),
                business_id=uuid4(),
            )

    def test_determine_context_kind_rejects_neither(self):
        """Must have at least one axis."""
        service = ContextService()
        with pytest.raises(ValueError, match="exactly one"):
            service.determine_context_kind(
                household_id=None,
                business_id=None,
            )

    def test_generate_label(self):
        """Auto-generated label is non-empty."""
        service = ContextService()
        label = service.generate_label(
            kind=ContextKind.HOUSEHOLD,
            participant_names=["Alice", "Bob"],
        )
        assert len(label) > 0
        assert "Alice" in label or "Bob" in label


@pytest.mark.req("OL-043")
class TestUnifiedLedger:
    """WHILE a user belongs to multiple contexts, the system shall render
    a unified ledger view without merging underlying context data."""

    def test_unified_ledger_preserves_context_ids(self):
        """Ledger items retain their original context_id."""
        # This is an API-level test — for now verify the schema supports it
        from app.schemas import CommitmentResponse

        fields = CommitmentResponse.model_fields
        assert "context_id" in fields
