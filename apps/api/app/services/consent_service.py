"""Consent service — DPDP compliance (OL-120..123).

Records consent grant/withdrawal as audit events.
Enforces: no behavioral tracking, no advertising, 72h withdrawal deadline.
"""

from uuid import UUID

import structlog

logger = structlog.get_logger()

# OL-123: Withdrawal must be honored within this window
WITHDRAWAL_DEADLINE_HOURS = 72


class ConsentService:
    """Manages consent records and DPDP compliance."""

    def __init__(self) -> None:
        # In production, backed by ConsentEvent table
        self._consents: dict[str, dict] = {}

    def record_consent(
        self,
        *,
        principal_id: UUID,
        scope: str,
        action: str,
        method: str,
    ) -> dict:
        """Record a consent grant or withdrawal (OL-120, OL-123).

        Creates an audit log entry for every consent event.
        """
        key = f"{principal_id}:{scope}"

        # Audit log entry (in production, writes to audit_log table)
        logger.info(
            "consent_audit_recorded",
            principal_id=str(principal_id),
            scope=scope,
            action=action,
            method=method,
        )

        self._consents[key] = {
            "principal_id": str(principal_id),
            "scope": scope,
            "action": action,
            "method": method,
        }

        return {"recorded": True, "action": action}

    def has_consent(self, *, principal_id: UUID, scope: str) -> bool:
        """Check if consent has been granted for a scope."""
        key = f"{principal_id}:{scope}"
        record = self._consents.get(key)
        if record is None:
            return False
        return record["action"] == "grant"

    def allows_behavioral_tracking(self) -> bool:
        """OL-121: No behavioral tracking ever."""
        return False

    def allows_targeted_advertising(self) -> bool:
        """OL-121: No targeted advertising ever."""
        return False
