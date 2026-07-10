"""Calendar fusion service — Gate 4 (OL-070..072).

Read-only Google Calendar sync, conflict detection, household overlay.
Lives behind the connector interface per ADR-001 §Interfaces.
"""

from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

import structlog

logger = structlog.get_logger()

# Conflict detection window: ±30 minutes around due time
_CONFLICT_WINDOW_MINUTES = 30


class CalendarService:
    """Calendar sync, conflict detection, and household overlay.

    In production, Google Calendar data comes through the calendar connector.
    This service handles the business logic layer.
    """

    def __init__(self) -> None:
        # In production, backed by calendar_events table + Google API connector
        self._synced_members: dict[str, set[UUID]] = defaultdict(set)
        self._events: dict[UUID, list[dict]] = defaultdict(list)
        self._commitment_slots: dict[UUID, list[dict]] = defaultdict(list)
        self._member_household: dict[UUID, UUID] = {}
        self._read_only = True

    def is_read_only(self) -> bool:
        """OL-070: Sync is read-only at Gate 4. Write ships at Gate 5."""
        return self._read_only

    def sync_calendar(
        self,
        *,
        principal_id: UUID,
        household_id: UUID,
        consent_granted: bool,
    ) -> dict:
        """OL-070: Sync read-only with Google Calendar per consenting member."""
        if not consent_granted:
            logger.info(
                "calendar_sync_refused",
                principal_id=str(principal_id),
                reason="consent_not_granted",
            )
            return {"synced": False, "reason": "consent_not_granted"}

        hh_key = str(household_id)
        self._synced_members[hh_key].add(principal_id)
        self._member_household[principal_id] = household_id

        logger.info(
            "calendar_synced",
            principal_id=str(principal_id),
            household_id=str(household_id),
        )
        return {"synced": True}

    def get_synced_members(self, *, household_id: UUID) -> set[UUID]:
        """Get all synced members for a household."""
        return self._synced_members.get(str(household_id), set())

    def add_calendar_event(
        self,
        *,
        principal_id: UUID,
        title: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """Add a calendar event (from Google Calendar sync)."""
        self._events[principal_id].append(
            {
                "title": title,
                "start": start,
                "end": end,
                "type": "calendar",
                "principal_id": str(principal_id),
            }
        )

    def add_commitment_slot(
        self,
        *,
        principal_id: UUID,
        title: str,
        due_time: datetime,
    ) -> None:
        """Add a commitment time slot for overlay + conflict detection."""
        self._commitment_slots[principal_id].append(
            {
                "title": title,
                "due_time": due_time,
                "type": "commitment",
                "principal_id": str(principal_id),
            }
        )

    def check_conflicts(
        self,
        *,
        assignee_id: UUID,
        due_time: datetime,
    ) -> list[dict]:
        """OL-071: Check for conflicts with calendar events or commitments."""
        conflicts = []

        # Check calendar events
        for event in self._events.get(assignee_id, []):
            if event["start"] <= due_time <= event["end"]:
                conflicts.append(event)

        # Check existing commitment slots
        for slot in self._commitment_slots.get(assignee_id, []):
            if slot["due_time"] == due_time:
                conflicts.append(slot)

        return conflicts

    def pre_acceptance_check(
        self,
        *,
        assignee_id: UUID,
        commitment_due: datetime,
    ) -> dict:
        """OL-071: Surface conflicts before acceptance."""
        conflicts = self.check_conflicts(
            assignee_id=assignee_id,
            due_time=commitment_due,
        )
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "can_accept": True,  # Conflicts are warnings, not blockers
        }

    def get_household_overlay(
        self,
        *,
        household_id: UUID,
        date: date,
    ) -> dict:
        """OL-072: Household calendar overlay combining member calendars + commitments.

        Scoped by household context (OL-040).
        """
        members = self.get_synced_members(household_id=household_id)
        all_events: list[dict] = []

        for member_id in members:
            # Calendar events for this member
            for event in self._events.get(member_id, []):
                if event["start"].date() == date:
                    all_events.append(event)

            # Commitment slots for this member
            for slot in self._commitment_slots.get(member_id, []):
                if slot["due_time"].date() == date:
                    all_events.append(slot)

        # Sort by start time
        all_events.sort(key=lambda e: e.get("start", e.get("due_time", datetime.min)))

        return {
            "household_id": str(household_id),
            "date": date.isoformat(),
            "events": all_events,
            "member_count": len(members),
        }
