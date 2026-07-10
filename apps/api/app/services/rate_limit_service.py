"""Rate limiting service — OL-144.

FastAPI per-token rate limiting; web-thread tokens additionally per-thread throttled.
Caddy handles per-IP limiting at the edge.
"""

from collections import defaultdict

import structlog

logger = structlog.get_logger()


class RateLimitService:
    """Per-token and per-thread rate limiting."""

    def __init__(self) -> None:
        # In production, backed by Redis sliding window
        self._token_counts: dict[str, int] = defaultdict(int)
        self._thread_counts: dict[str, int] = defaultdict(int)

    def check_rate_limit(self, *, token_id: str, limit: int) -> bool:
        """Check per-token rate limit. Returns True if allowed."""
        current = self._token_counts[token_id]
        if current >= limit:
            logger.warning("rate_limit_exceeded", token_id=token_id, limit=limit)
            return False
        self._token_counts[token_id] += 1
        return True

    def check_thread_rate_limit(self, *, thread_id: str, limit: int) -> bool:
        """Check per-thread rate limit for web-thread tokens."""
        current = self._thread_counts[thread_id]
        if current >= limit:
            logger.warning(
                "thread_rate_limit_exceeded", thread_id=thread_id, limit=limit
            )
            return False
        self._thread_counts[thread_id] += 1
        return True


def get_caddy_rate_limit_config() -> dict:
    """Return Caddy IP rate limit configuration."""
    return {
        "per_ip_requests_per_second": 50,
        "burst": 100,
    }
