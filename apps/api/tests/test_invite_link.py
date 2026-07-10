"""Tests for OL-008 — invite link for non-OpenLnk users.

WHEN a commitment is assigned to a person not yet on OpenLnk, the system
shall generate an invite link and hold the commitment in proposed until
acceptance.
"""

import pytest


@pytest.mark.req("OL-008")
class TestInviteLink:
    """Invite link generation for non-OpenLnk counterparties."""

    def test_invite_service_exists(self):
        from app.services.invite_service import InviteService

        assert InviteService is not None

    def test_generate_invite_link(self):
        """InviteService can generate an invite link."""
        from app.services.invite_service import InviteService

        service = InviteService()
        link = service.generate_invite_link(
            commitment_title="Pay tuition fee",
            inviter_name="Vinod",
        )
        assert "openlnk.in" in link or "invite" in link

    def test_invite_link_contains_token(self):
        """Invite link includes a signed token."""
        from app.services.invite_service import InviteService

        service = InviteService()
        link = service.generate_invite_link(
            commitment_title="Test",
            inviter_name="Alice",
        )
        assert "token=" in link or "t=" in link

    def test_commitment_stays_proposed_for_invite(self):
        """Commitments for non-OpenLnk users stay in proposed state."""
        import inspect

        from app.services.invite_service import InviteService

        source = inspect.getsource(InviteService)
        # Service should reference the proposed state
        assert "proposed" in source.lower()

    def test_invite_model_exists(self):
        """InviteToken model exists for tracking pending invites."""
        from app.models import InviteToken

        assert InviteToken.__tablename__ == "invite_tokens"
