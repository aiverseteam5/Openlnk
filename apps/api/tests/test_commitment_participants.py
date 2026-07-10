"""Tests for OL-001a: group commitment support via commitment_participants."""

from uuid import uuid4

import pytest

from app.models import CommitmentParticipant


@pytest.mark.req("OL-001a")
class TestCommitmentParticipants:
    """The system shall support 0..N counterparties per commitment via
    the commitment_participants table."""

    def test_participant_model_exists(self):
        cp = CommitmentParticipant(
            commitment_id=uuid4(),
            principal_id=uuid4(),
            role="counterparty",
        )
        assert cp.role == "counterparty"

    def test_participant_role_owner(self):
        cp = CommitmentParticipant(
            commitment_id=uuid4(),
            principal_id=uuid4(),
            role="owner",
        )
        assert cp.role == "owner"

    def test_participant_role_observer(self):
        cp = CommitmentParticipant(
            commitment_id=uuid4(),
            principal_id=uuid4(),
            role="observer",
        )
        assert cp.role == "observer"

    def test_participant_table_name(self):
        assert CommitmentParticipant.__tablename__ == "commitment_participants"

    def test_participant_composite_pk(self):
        """Primary key is (commitment_id, principal_id)."""
        pk_cols = [c.name for c in CommitmentParticipant.__table__.primary_key.columns]
        assert "commitment_id" in pk_cols
        assert "principal_id" in pk_cols
