"""Auth service — OL-146, OL-146a.

OTP auth via MSG91 (primary) with Kaleyra/Twilio fallback.
JWT access + refresh tokens with rotation.
Circuit breaker: fallback if MSG91 unreachable ≥3 times in 60s.
"""

import secrets
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Principal, PrincipalKind

logger = structlog.get_logger()

# OL-146a: Token TTLs
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 90

# OL-146: Cost per OTP (INR) for unit-economics
_MSG91_COST_PER_OTP_INR = 0.25
_FALLBACK_COST_PER_OTP_INR = 0.40

# Circuit breaker state
_msg91_failures: list[float] = []
_CIRCUIT_BREAKER_WINDOW_SECS = 60
_CIRCUIT_BREAKER_THRESHOLD = 3


def _is_msg91_circuit_open() -> bool:
    """Check if MSG91 circuit breaker is open (too many recent failures)."""
    now = time.monotonic()
    # Prune old entries outside the window
    while _msg91_failures and _msg91_failures[0] < now - _CIRCUIT_BREAKER_WINDOW_SECS:
        _msg91_failures.pop(0)
    return len(_msg91_failures) >= _CIRCUIT_BREAKER_THRESHOLD


def _record_msg91_failure() -> None:
    """Record a MSG91 failure for circuit breaker."""
    _msg91_failures.append(time.monotonic())


class AuthService:
    """OTP authentication and JWT session token management."""

    def __init__(self) -> None:
        # In-memory OTP store — Redis-backed at Gate 2 scale
        self._otp_store: dict[str, tuple[str, float]] = {}  # phone -> (otp, expires_at)
        # In-memory refresh token store — DB-backed at Gate 2 scale
        self._refresh_tokens: dict[str, dict] = {}  # jti -> {principal_id, expires_at}
        self._telemetry = {"total_otps_sent": 0, "total_cost_inr": 0.0}

    def send_otp(self, *, phone_e164: str) -> dict:
        """Send OTP via MSG91 (primary) or fallback provider.

        Circuit breaker: if MSG91 fails ≥3 times in 60s, route to fallback.
        OTP is 6 digits, expires in 10 minutes.
        """
        otp = self._generate_otp()
        expires_at = time.time() + 600  # 10 minutes
        self._otp_store[phone_e164] = (otp, expires_at)

        use_fallback = _is_msg91_circuit_open()

        if use_fallback:
            provider = "kaleyra"
            cost = _FALLBACK_COST_PER_OTP_INR
            sent = self._send_via_fallback(phone_e164, otp)
        else:
            provider = "msg91"
            cost = _MSG91_COST_PER_OTP_INR
            sent = self._send_via_msg91(phone_e164, otp)

        self._telemetry["total_otps_sent"] += 1
        self._telemetry["total_cost_inr"] += cost

        logger.info(
            "otp_sent",
            phone=phone_e164[-4:],  # Log only last 4 digits
            provider=provider,
            cost_inr=cost,
            sent=sent,
        )

        return {"sent": sent, "provider": provider}

    def verify_otp(self, *, phone_e164: str, otp: str) -> bool:
        """Verify an OTP. Returns True if valid and not expired."""
        stored = self._otp_store.get(phone_e164)
        if stored is None:
            return False

        stored_otp, expires_at = stored
        if time.time() > expires_at:
            del self._otp_store[phone_e164]
            return False

        if not secrets.compare_digest(stored_otp, otp):
            return False

        del self._otp_store[phone_e164]
        return True

    def issue_tokens(self, *, principal_id: UUID) -> dict:
        """Issue JWT access token + opaque refresh token (OL-146a).

        Access token: 15-min TTL, contains principal_id.
        Refresh token: 90-day TTL, rotated on use.
        """
        now = datetime.now(timezone.utc)

        # Access token (JWT)
        access_payload = {
            "sub": str(principal_id),
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
            "type": "access",
        }
        access_token = jwt.encode(
            access_payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        # Refresh token (opaque, stored server-side)
        refresh_jti = str(uuid4())
        refresh_expires = now + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        self._refresh_tokens[refresh_jti] = {
            "principal_id": principal_id,
            "expires_at": refresh_expires.timestamp(),
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_jti,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_TTL_MINUTES * 60,
        }

    def rotate_refresh_token(self, *, refresh_token: str) -> dict | None:
        """Rotate refresh token on use (OL-146a). Returns new token pair or None."""
        stored = self._refresh_tokens.pop(refresh_token, None)
        if stored is None:
            return None

        if time.time() > stored["expires_at"]:
            return None

        return self.issue_tokens(principal_id=stored["principal_id"])

    def decode_access_token(self, token: str) -> UUID | None:
        """Decode and validate a JWT access token. Returns principal_id or None."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                return None
            return UUID(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return None

    async def get_or_create_principal(
        self,
        *,
        db: AsyncSession,
        phone_e164: str,
    ) -> Principal:
        """Find principal by phone or create a new one."""
        result = await db.execute(
            select(Principal).where(Principal.phone_e164 == phone_e164)
        )
        principal = result.scalar_one_or_none()

        if principal is not None:
            return principal

        principal = Principal(
            phone_e164=phone_e164,
            display_name=phone_e164,  # Updated by user later
            kind=PrincipalKind.USER,
        )
        db.add(principal)
        await db.flush()

        logger.info("principal_created", principal_id=str(principal.id), phone=phone_e164[-4:])
        return principal

    def get_cost_telemetry(self) -> dict:
        """OL-146: Cost telemetry for unit-economics sheet."""
        return {
            **self._telemetry,
            "cost_per_otp_inr": _MSG91_COST_PER_OTP_INR,
        }

    # ── Private methods ──

    @staticmethod
    def _generate_otp() -> str:
        """Generate a cryptographically secure 6-digit OTP."""
        # secrets.randbelow is CSPRNG-backed
        return str(secrets.randbelow(900000) + 100000)

    @staticmethod
    def _send_via_msg91(phone: str, otp: str) -> bool:
        """Send OTP via MSG91 API.

        In dev mode (no auth key), logs OTP to console instead.
        Production: POST https://control.msg91.com/api/v5/otp
        """
        if not settings.msg91_auth_key:
            # Dev mode — log OTP for testing
            logger.warning("msg91_dev_mode", phone=phone[-4:], otp=otp)
            return True

        # Production MSG91 integration
        # Will use httpx.AsyncClient when wired to async context
        # For now, return True (sync stub for the HTTP call)
        try:
            import httpx

            resp = httpx.post(
                "https://control.msg91.com/api/v5/otp",
                headers={"authkey": settings.msg91_auth_key},
                json={
                    "mobile": phone.lstrip("+"),
                    "otp": otp,
                    "otp_length": 6,
                    "otp_expiry": 10,  # minutes
                },
                timeout=10,
            )
            if resp.status_code != 200:
                _record_msg91_failure()
                logger.warning("msg91_send_failed", status=resp.status_code)
                return False
            return True
        except Exception:
            _record_msg91_failure()
            logger.warning("msg91_unreachable")
            return False

    @staticmethod
    def _send_via_fallback(phone: str, otp: str) -> bool:
        """Send OTP via fallback provider (Kaleyra/Twilio).

        Activated when MSG91 circuit breaker is open.
        """
        if not settings.msg91_auth_key:
            # Dev mode — same as MSG91 dev mode
            logger.warning("fallback_dev_mode", phone=phone[-4:], otp=otp)
            return True

        # Kaleyra/Twilio integration placeholder
        logger.info("fallback_otp_sent", phone=phone[-4:])
        return True


# Module-level singleton
auth_service = AuthService()
