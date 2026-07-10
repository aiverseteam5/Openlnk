"""Web-thread link mechanic — Gate 3 (OL-080..085).

Zero-install thread access via signed JWT tokens per ADR-005.
Funnel instrumentation per center and message class from first deploy.
"""

import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import defaultdict
from hashlib import sha256
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()

# OL-084: Performance budget (CI-enforced via size-limit)
MAX_BUNDLE_SIZE_KB = 120
_LIGHTHOUSE_INTERACTIVE_MS = 3000

# OL-081: Default token TTL (24 hours)
DEFAULT_TOKEN_TTL_SECONDS = 86400

# OL-085: Valid funnel event types
_VALID_FUNNEL_EVENTS = frozenset({"open", "return", "install"})


def get_bundle_budget() -> dict:
    """Return the web-thread performance budget for CI enforcement."""
    return {
        "max_gzipped_kb": MAX_BUNDLE_SIZE_KB,
        "lighthouse_interactive_ms": _LIGHTHOUSE_INTERACTIVE_MS,
        "ci_enforced": True,
    }


class WebThreadService:
    """Manages thread token lifecycle and web-thread access (OL-080..083).

    Tokens are signed JWTs scoped to exactly one thread, short-lived,
    with revocation support. Per ADR-005.
    """

    def __init__(self, *, secret_key: str) -> None:
        self._secret_key = secret_key.encode()
        # In production, revoked JTIs stored in Redis/DB
        self._revoked_jtis: set[str] = set()

    def _b64_encode(self, data: bytes) -> str:
        return urlsafe_b64encode(data).rstrip(b"=").decode()

    def _b64_decode(self, s: str) -> bytes:
        padding = 4 - len(s) % 4
        if padding != 4:
            s += "=" * padding
        return urlsafe_b64decode(s)

    def _sign(self, header_b64: str, payload_b64: str) -> str:
        msg = f"{header_b64}.{payload_b64}".encode()
        sig = hmac.new(self._secret_key, msg, sha256).digest()
        return self._b64_encode(sig)

    def issue_token(
        self,
        *,
        thread_id: UUID,
        principal_id: UUID,
        ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    ) -> str:
        """Issue a signed, thread-scoped, expiring JWT (OL-081).

        Returns a compact JWT string: header.payload.signature
        """
        jti = str(uuid4())
        now = int(time.time())

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "jti": jti,
            "thread_id": str(thread_id),
            "principal_id": str(principal_id),
            "iat": now,
            "exp": now + ttl_seconds,
        }

        header_b64 = self._b64_encode(json.dumps(header).encode())
        payload_b64 = self._b64_encode(json.dumps(payload).encode())
        signature = self._sign(header_b64, payload_b64)

        logger.info(
            "thread_token_issued",
            jti=jti,
            thread_id=str(thread_id),
            principal_id=str(principal_id),
            ttl_seconds=ttl_seconds,
        )

        return f"{header_b64}.{payload_b64}.{signature}"

    def validate_token(self, token: str) -> dict | None:
        """Validate a thread token. Returns claims or None if invalid.

        Checks: signature, expiry, revocation (OL-081).
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts

            # Verify signature
            expected_sig = self._sign(header_b64, payload_b64)
            if not hmac.compare_digest(signature, expected_sig):
                return None

            # Decode payload
            payload = json.loads(self._b64_decode(payload_b64))

            # Check expiry
            if payload.get("exp", 0) < time.time():
                return None

            # Check revocation
            if payload.get("jti") in self._revoked_jtis:
                return None

            return payload
        except Exception:
            return None

    def revoke_token(self, *, jti: str) -> None:
        """Revoke a token by JTI (OL-081). Server-side revocable."""
        self._revoked_jtis.add(jti)
        logger.info("thread_token_revoked", jti=jti)

    def refresh_token(self, token: str) -> str | None:
        """Refresh a valid token with a new expiry (OL-082).

        Returns a new token or None if the original is invalid/expired.
        Token re-issue via the original link if session storage is wiped.
        """
        claims = self.validate_token(token)
        if claims is None:
            return None

        # Issue new token for the same thread + principal
        return self.issue_token(
            thread_id=UUID(claims["thread_id"]),
            principal_id=UUID(claims["principal_id"]),
        )

    def get_thread_data(self, *, thread_id: UUID) -> dict:
        """Retrieve thread data for rendering (OL-080).

        In production, queries the DB for thread commitments.
        """
        return {
            "thread_id": str(thread_id),
            "commitments": [],
        }

    def should_show_install_offer(self, *, active_thread_count: int) -> bool:
        """OL-083: Install offer only at ≥2 active threads, never before."""
        return active_thread_count >= 2


class FunnelService:
    """Funnel instrumentation for web-thread (OL-085).

    Records open/return/install events per center and per message class.
    This dataset IS the YC application.
    """

    def __init__(self) -> None:
        # In production, writes to analytics table/event stream
        self._events: list[dict] = []
        self._center_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._class_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

    def record_event(
        self,
        *,
        event_type: str,
        thread_id: UUID,
        center_id: UUID,
        message_class: str,
    ) -> dict:
        """Record a funnel event (open, return, install).

        Scoped per center and per message class from first deployment.
        """
        if event_type not in _VALID_FUNNEL_EVENTS:
            raise ValueError(
                f"invalid event_type '{event_type}'; "
                f"must be one of {sorted(_VALID_FUNNEL_EVENTS)}"
            )

        event = {
            "event_type": event_type,
            "thread_id": str(thread_id),
            "center_id": str(center_id),
            "message_class": message_class,
        }
        self._events.append(event)

        # Aggregate per center
        center_key = str(center_id)
        self._center_counts[center_key][event_type] += 1

        # Aggregate per message class within center
        self._class_counts[center_key][message_class][event_type] += 1

        logger.info("funnel_event_recorded", **event)
        return {"recorded": True, "event_type": event_type}

    def get_center_metrics(self, *, center_id: UUID) -> dict[str, int]:
        """Get funnel metrics for a center."""
        return dict(self._center_counts.get(str(center_id), {}))

    def get_class_metrics(self, *, center_id: UUID) -> dict[str, dict[str, int]]:
        """Get per-message-class funnel metrics for a center."""
        return dict(self._class_counts.get(str(center_id), {}))
