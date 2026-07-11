"""Tests for Gate 4 — Calendar fusion (OL-070..072).

Read-only Google Calendar sync, conflict detection, household overlay.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest


@pytest.mark.req("OL-070")
class TestCalendarSync:
    """OL-070: Read-only sync with Google Calendar per consenting member."""

    def test_sync_requires_consent(self):
        """Calendar sync only proceeds if the member has granted consent."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        member_id = uuid4()

        # No consent → sync refused
        result = service.sync_calendar(
            principal_id=member_id,
            household_id=uuid4(),
            consent_granted=False,
        )
        assert result["synced"] is False
        assert result["reason"] == "consent_not_granted"

    def test_sync_succeeds_with_consent(self):
        """Calendar sync proceeds when member grants consent."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        member_id = uuid4()

        result = service.sync_calendar(
            principal_id=member_id,
            household_id=uuid4(),
            consent_granted=True,
        )
        assert result["synced"] is True

    def test_sync_is_read_only(self):
        """Sync is read-only — no writes to external calendar."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        assert service.is_read_only() is True

    def test_sync_scoped_per_household_member(self):
        """Each household member syncs independently."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        household_id = uuid4()
        member_a = uuid4()
        member_b = uuid4()

        service.sync_calendar(
            principal_id=member_a,
            household_id=household_id,
            consent_granted=True,
        )
        service.sync_calendar(
            principal_id=member_b,
            household_id=household_id,
            consent_granted=True,
        )

        synced = service.get_synced_members(household_id=household_id)
        assert member_a in synced
        assert member_b in synced


@pytest.mark.req("OL-071")
class TestConflictDetection:
    """OL-071: Surface conflicts before commitment acceptance."""

    def test_detect_calendar_conflict(self):
        """Detect when a new commitment conflicts with a calendar event."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        assignee_id = uuid4()
        now = datetime.now(UTC)

        # Add an existing event
        service.add_calendar_event(
            principal_id=assignee_id,
            title="Team meeting",
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=3),
        )

        # Check for conflict with a commitment at the same time
        conflicts = service.check_conflicts(
            assignee_id=assignee_id,
            due_time=now + timedelta(hours=2, minutes=30),
        )
        assert len(conflicts) > 0
        assert conflicts[0]["title"] == "Team meeting"

    def test_no_conflict_when_times_dont_overlap(self):
        """No conflict when commitment time doesn't overlap events."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        assignee_id = uuid4()
        now = datetime.now(UTC)

        service.add_calendar_event(
            principal_id=assignee_id,
            title="Morning standup",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=1, minutes=30),
        )

        conflicts = service.check_conflicts(
            assignee_id=assignee_id,
            due_time=now + timedelta(hours=5),
        )
        assert len(conflicts) == 0

    def test_conflict_with_existing_commitment(self):
        """Detect conflict with another commitment's due time."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        assignee_id = uuid4()
        now = datetime.now(UTC)

        # Add an existing commitment slot
        service.add_commitment_slot(
            principal_id=assignee_id,
            title="Fee payment due",
            due_time=now + timedelta(hours=4),
        )

        conflicts = service.check_conflicts(
            assignee_id=assignee_id,
            due_time=now + timedelta(hours=4),
        )
        assert len(conflicts) > 0

    def test_conflict_surfaced_before_acceptance(self):
        """Conflicts are returned as pre-acceptance warnings."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        assignee_id = uuid4()
        now = datetime.now(UTC)

        service.add_calendar_event(
            principal_id=assignee_id,
            title="Class",
            start=now + timedelta(hours=3),
            end=now + timedelta(hours=4),
        )

        result = service.pre_acceptance_check(
            assignee_id=assignee_id,
            commitment_due=now + timedelta(hours=3, minutes=30),
        )
        assert result["has_conflicts"] is True
        assert len(result["conflicts"]) > 0
        assert result["can_accept"] is True  # Can still accept, just warned


@pytest.mark.req("OL-072")
class TestHouseholdCalendarOverlay:
    """OL-072: Household calendar overlay combining member calendars + commitments."""

    def test_overlay_combines_member_events(self):
        """Overlay includes events from all synced household members."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        household_id = uuid4()
        member_a = uuid4()
        member_b = uuid4()
        now = datetime.now(UTC)

        service.sync_calendar(
            principal_id=member_a, household_id=household_id, consent_granted=True
        )
        service.sync_calendar(
            principal_id=member_b, household_id=household_id, consent_granted=True
        )

        service.add_calendar_event(
            principal_id=member_a,
            title="Parent meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        service.add_calendar_event(
            principal_id=member_b,
            title="Doctor appointment",
            start=now + timedelta(hours=3),
            end=now + timedelta(hours=4),
        )

        overlay = service.get_household_overlay(
            household_id=household_id,
            date=now.date(),
        )
        titles = [e["title"] for e in overlay["events"]]
        assert "Parent meeting" in titles
        assert "Doctor appointment" in titles

    def test_overlay_includes_commitments(self):
        """Overlay includes commitment due dates alongside calendar events."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        household_id = uuid4()
        member = uuid4()
        now = datetime.now(UTC)

        service.sync_calendar(principal_id=member, household_id=household_id, consent_granted=True)
        service.add_commitment_slot(
            principal_id=member,
            title="Fee due",
            due_time=now + timedelta(minutes=30),
        )

        overlay = service.get_household_overlay(
            household_id=household_id,
            date=now.date(),
        )
        commitment_items = [e for e in overlay["events"] if e["type"] == "commitment"]
        assert len(commitment_items) > 0

    def test_overlay_scoped_by_context(self):
        """Overlay is scoped to the household context (OL-040)."""
        from app.services.calendar_service import CalendarService

        service = CalendarService()
        household_a = uuid4()
        household_b = uuid4()
        member_a = uuid4()
        member_b = uuid4()
        now = datetime.now(UTC)

        service.sync_calendar(
            principal_id=member_a, household_id=household_a, consent_granted=True
        )
        service.sync_calendar(
            principal_id=member_b, household_id=household_b, consent_granted=True
        )

        service.add_calendar_event(
            principal_id=member_a,
            title="Household A event",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )
        service.add_calendar_event(
            principal_id=member_b,
            title="Household B event",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
        )

        overlay_a = service.get_household_overlay(household_id=household_a, date=now.date())
        titles_a = [e["title"] for e in overlay_a["events"]]
        assert "Household A event" in titles_a
        assert "Household B event" not in titles_a  # No cross-context leakage
