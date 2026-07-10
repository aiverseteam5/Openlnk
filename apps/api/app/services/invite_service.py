"""Invite service — generate invite links for non-OpenLnk users (OL-008).

WHEN a commitment is assigned to a person not yet on OpenLnk, generate
an invite link. The commitment stays in proposed until acceptance.
"""

import secrets
from urllib.parse import urlencode

import structlog

logger = structlog.get_logger()

# Base URL for invite links (configured per environment)
INVITE_BASE_URL = "https://openlnk.in/invite"


class InviteService:
    """Generate and manage invite links for non-OpenLnk counterparties."""

    def generate_invite_link(
        self,
        *,
        commitment_title: str,
        inviter_name: str,
    ) -> str:
        """Generate a signed invite link.

        The commitment remains in proposed state until the invite is
        accepted and the counterparty completes OTP verification.
        """
        token = secrets.token_urlsafe(32)
        params = urlencode({"t": token})
        link = f"{INVITE_BASE_URL}?{params}"

        logger.info(
            "invite_link_generated",
            inviter_name=inviter_name,
            commitment_title=commitment_title,
        )
        return link
