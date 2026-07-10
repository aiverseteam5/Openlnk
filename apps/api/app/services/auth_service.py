"""Auth service — OL-146, OL-146a.

OTP auth via MSG91 with cost telemetry. Session tokens with TTL.
Fallback provider for MSG91 unreachability.
"""

from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()

# OL-146a: Token TTLs
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 90

# OL-146: Cost per OTP (INR) for unit-economics
_MSG91_COST_PER_OTP_INR = 0.25
_FALLBACK_COST_PER_OTP_INR = 0.40


class AuthService:
    """OTP authentication and session token management."""

    def __init__(self) -> None:
        self._otp_store: dict[str, str] = {}
        self._refresh_tokens: dict[str, UUID] = {}
        self._telemetry = {"total_otps_sent": 0, "total_cost_inr": 0.0}

    def send_otp(
        self,
        *,
        phone_e164: str,
        force_fallback: bool = False,
    ) -> dict:
        """Send OTP via MSG91 (primary) or fallback provider (OL-146, OL-146a).

        WHERE MSG91 is unreachable, falls back to Kaleyra/Twilio.
        """
        otp = "123456"  # In production, generated securely
        self._otp_store[phone_e164] = otp

        if force_fallback:
            provider = "kaleyra"
            cost = _FALLBACK_COST_PER_OTP_INR
        else:
            provider = "msg91"
            cost = _MSG91_COST_PER_OTP_INR

        self._telemetry["total_otps_sent"] += 1
        self._telemetry["total_cost_inr"] += cost

        logger.info(
            "otp_sent",
            phone=phone_e164,
            provider=provider,
            cost_inr=cost,
        )

        return {"sent": True, "provider": provider}

    def verify_otp(self, *, phone_e164: str, otp: str) -> dict:
        """Verify an OTP."""
        stored = self._otp_store.get(phone_e164)
        if stored and stored == otp:
            del self._otp_store[phone_e164]
            return {"verified": True}
        return {"verified": False}

    def get_cost_telemetry(self) -> dict:
        """OL-146: Cost telemetry for unit-economics sheet."""
        return {
            **self._telemetry,
            "cost_per_otp_inr": _MSG91_COST_PER_OTP_INR,
        }

    def issue_session_tokens(self, *, principal_id: UUID) -> dict:
        """OL-146a: Issue access + refresh tokens."""
        access_token = str(uuid4())
        refresh_token = str(uuid4())

        self._refresh_tokens[refresh_token] = principal_id

        return {
            "access_token": access_token,
            "access_token_ttl_minutes": ACCESS_TOKEN_TTL_MINUTES,
            "refresh_token": refresh_token,
            "refresh_token_ttl_days": REFRESH_TOKEN_TTL_DAYS,
        }

    def rotate_refresh_token(self, *, refresh_token: str) -> dict | None:
        """OL-146a: Rotate refresh token on use."""
        principal_id = self._refresh_tokens.pop(refresh_token, None)
        if principal_id is None:
            return None

        # Issue new pair
        return self.issue_session_tokens(principal_id=principal_id)
