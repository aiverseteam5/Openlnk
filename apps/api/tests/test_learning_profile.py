"""Tests for the learning profile endpoints — nudge suggestions + quiet hours.

Tests the LearningService integration surfaced via /me/* routes.
"""

from uuid import uuid4

import pytest

from app.services.learning_service import LearningService


@pytest.mark.req("OL-093")
class TestLearningProfileService:
    """LearningService nudge/quiet-hour suggestions for surfacing in UI."""

    def test_preferred_nudge_hour_requires_min_data(self):
        service = LearningService()
        pid = uuid4()

        # Not enough data
        for hour in [9, 10]:
            service.record_response_time(
                principal_id=pid, hour_of_day=hour, event_type="commitment_done",
            )
        assert service.get_preferred_nudge_hour(principal_id=pid) is None

    def test_preferred_nudge_hour_returns_mode(self):
        service = LearningService()
        pid = uuid4()

        for hour in [9, 9, 10, 9, 14, 9]:
            service.record_response_time(
                principal_id=pid, hour_of_day=hour, event_type="commitment_done",
            )
        assert service.get_preferred_nudge_hour(principal_id=pid) == 9

    def test_suggest_quiet_hours_finds_largest_gap(self):
        service = LearningService()
        pid = uuid4()

        # Active at 8, 9, 10, 18, 19, 20 — largest gap is 20→8 (12 hours quiet)
        for hour in [8, 9, 10, 18, 19, 20]:
            service.record_response_time(
                principal_id=pid, hour_of_day=hour, event_type="reminder_acknowledged",
            )

        result = service.suggest_quiet_hours(principal_id=pid)
        assert result is not None
        # Gap runs from last active hour (20) to first active hour (8)
        assert result["start_hour"] == 20
        assert result["end_hour"] == 8

    def test_suggest_quiet_hours_returns_none_with_insufficient_data(self):
        service = LearningService()
        pid = uuid4()
        assert service.suggest_quiet_hours(principal_id=pid) is None

    def test_engagement_signals_rejected_from_nudge_learning(self):
        service = LearningService()
        pid = uuid4()

        # Try recording with an engagement event — should be silently ignored
        service.record_response_time(
            principal_id=pid, hour_of_day=10, event_type="app_opened",
        )
        # No data stored
        assert len(service._response_times.get(pid, [])) == 0

    def test_data_points_count(self):
        service = LearningService()
        pid = uuid4()

        for hour in [8, 9, 10]:
            service.record_response_time(
                principal_id=pid, hour_of_day=hour, event_type="commitment_created",
            )

        assert len(service._response_times[pid]) == 3
