"""Notification service — blocker-only notifications + daily brief.

OL-060: Notify only when user is the blocker.
OL-061: Batch non-blocking info into daily brief.
OL-062: Record notifications-avoided as metric.
OL-063: Quiet hours — queue to next window.
OL-064: Daily brief includes commitments, conflicts, at-risk.
"""

from collections import defaultdict
from datetime import datetime, time
from uuid import UUID

import structlog

logger = structlog.get_logger()

# Reasons that make a user the blocker
_BLOCKER_REASONS = frozenset(
    {
        "at_risk",
        "awaiting_acceptance",
        "awaiting_approval",
    }
)


class NotificationService:
    """Determines whether to notify a user and tracks avoided notifications."""

    def __init__(self) -> None:
        self._avoided: dict[UUID, list[str]] = defaultdict(list)

    @property
    def avoided_count(self) -> int:
        return sum(len(v) for v in self._avoided.values())

    def should_notify(
        self,
        *,
        principal_id: UUID,
        reason: str,
        is_blocker: bool,
    ) -> bool:
        """OL-060: Only notify when user is the blocker."""
        if not is_blocker:
            self.record_avoided(principal_id=principal_id, reason=reason)
            return False
        return True

    def record_avoided(self, *, principal_id: UUID, reason: str) -> None:
        """OL-062: Record a suppressed notification as metric."""
        self._avoided[principal_id].append(reason)
        logger.info(
            "notification_avoided",
            principal_id=str(principal_id),
            reason=reason,
        )

    def get_avoided_count(self, principal_id: UUID) -> int:
        """Get count of avoided notifications for a principal."""
        return len(self._avoided.get(principal_id, []))

    def queue_for_next_window(
        self,
        *,
        principal_id: UUID,
        action_type: str,
        quiet_hours_end: time,
    ) -> dict:
        """OL-063: Queue action to send after quiet hours end."""
        # In production, this creates an arq job scheduled for quiet_hours_end
        send_after = datetime.combine(datetime.utcnow().date(), quiet_hours_end)
        logger.info(
            "action_queued_for_next_window",
            principal_id=str(principal_id),
            action_type=action_type,
            send_after=send_after.isoformat(),
        )
        return {"queued": True, "send_after": send_after.isoformat()}


class DailyBriefService:
    """Builds and delivers the daily brief (OL-061, OL-064)."""

    def __init__(self) -> None:
        self.pending_items: list[dict] = []

    def queue_item(
        self,
        *,
        principal_id: UUID,
        item_type: str,
        data: dict,
    ) -> None:
        """OL-061: Queue a non-blocking item for the daily brief."""
        self.pending_items.append(
            {
                "principal_id": str(principal_id),
                "item_type": item_type,
                "data": data,
            }
        )

    def get_brief_sections(self) -> dict:
        """OL-064: Return the sections included in the daily brief.

        Includes: today's commitments, conflicts, at-risk items.
        Excludes: everything else.
        """
        return {
            "todays_commitments": [],
            "conflicts": [],
            "at_risk": [],
        }
