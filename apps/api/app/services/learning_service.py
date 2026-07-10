"""Learning loop service — Gate 4 (OL-093).

Per-user nudge timing and quiet-hour pattern learning.
All features MUST pass the PRD §8 test: create, protect, or close commitments.
No engagement mechanics.
"""

from collections import Counter, defaultdict
from uuid import UUID

import structlog

logger = structlog.get_logger()

# Minimum data points before making a suggestion
MIN_DATA_POINTS = 5

# Valid commitment lifecycle events — each must serve create/protect/close
COMMITMENT_LIFECYCLE_EVENTS: list[dict] = [
    {"type": "commitment_created", "serves": "create"},
    {"type": "commitment_accepted", "serves": "create"},
    {"type": "commitment_done", "serves": "close"},
    {"type": "commitment_cancelled", "serves": "close"},
    {"type": "commitment_broken", "serves": "close"},
    {"type": "commitment_at_risk", "serves": "protect"},
    {"type": "reminder_sent", "serves": "protect"},
    {"type": "reminder_acknowledged", "serves": "protect"},
]

_VALID_SIGNAL_TYPES = frozenset(e["type"] for e in COMMITMENT_LIFECYCLE_EVENTS)

# Engagement-only events — explicitly rejected (PRD §8)
_ENGAGEMENT_EVENTS = frozenset(
    {
        "app_opened",
        "screen_viewed",
        "notification_clicked",
        "session_started",
        "tab_switched",
        "scroll_depth",
    }
)


class LearningService:
    """Learns per-user nudge timing and quiet-hour patterns (OL-093).

    Only learns from commitment lifecycle events.
    Never from engagement-only signals.
    """

    def __init__(self) -> None:
        # In production, backed by analytics table
        self._response_times: dict[UUID, list[int]] = defaultdict(list)

    def is_valid_signal(self, *, event_type: str) -> bool:
        """Check if an event type is a valid learning signal.

        PRD §8 test: only commitment lifecycle events qualify.
        Engagement-only events are explicitly rejected.
        """
        if event_type in _ENGAGEMENT_EVENTS:
            return False
        return event_type in _VALID_SIGNAL_TYPES

    def record_response_time(
        self,
        *,
        principal_id: UUID,
        hour_of_day: int,
        event_type: str,
    ) -> None:
        """Record when a user responds to a commitment-related event."""
        if not self.is_valid_signal(event_type=event_type):
            logger.warning(
                "invalid_learning_signal_rejected",
                event_type=event_type,
                principal_id=str(principal_id),
            )
            return

        self._response_times[principal_id].append(hour_of_day)
        logger.info(
            "learning_signal_recorded",
            principal_id=str(principal_id),
            hour_of_day=hour_of_day,
            event_type=event_type,
        )

    def get_preferred_nudge_hour(self, *, principal_id: UUID) -> int | None:
        """Get the user's preferred nudge hour based on response patterns.

        Returns None if insufficient data.
        """
        times = self._response_times.get(principal_id, [])
        if len(times) < MIN_DATA_POINTS:
            return None

        counter = Counter(times)
        return counter.most_common(1)[0][0]

    def suggest_quiet_hours(self, *, principal_id: UUID) -> dict | None:
        """Suggest quiet hours based on response-time gaps.

        Finds the longest gap in the user's response pattern
        to suggest when they're likely sleeping/unavailable.
        """
        times = self._response_times.get(principal_id, [])
        if len(times) < MIN_DATA_POINTS:
            return None

        active_hours = sorted(set(times))
        if len(active_hours) < 2:
            return None

        # Find the largest gap between active hours (wrapping at 24)
        max_gap = 0
        gap_start = active_hours[-1]
        gap_end = active_hours[0]

        for i in range(len(active_hours)):
            next_i = (i + 1) % len(active_hours)
            if next_i == 0:
                gap = (24 - active_hours[i]) + active_hours[next_i]
            else:
                gap = active_hours[next_i] - active_hours[i]

            if gap > max_gap:
                max_gap = gap
                gap_start = active_hours[i]
                gap_end = active_hours[next_i]

        return {
            "start_hour": gap_start,
            "end_hour": gap_end,
        }
