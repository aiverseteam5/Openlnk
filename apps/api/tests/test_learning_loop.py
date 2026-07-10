"""Tests for OL-093 — per-user nudge timing and quiet-hour learning.

Features MUST serve create/protect/close commitments (PRD §8 test).
No engagement mechanics.
"""

from uuid import uuid4

import pytest


@pytest.mark.req("OL-093")
class TestLearningLoop:
    """OL-093: Learn nudge timing only through commitment lifecycle features."""

    def test_learning_only_from_commitment_actions(self):
        """Learning features must originate from commitment lifecycle events."""
        from app.services.learning_service import LearningService

        service = LearningService()

        # Commitment lifecycle events are valid learning signals
        assert service.is_valid_signal(event_type="commitment_accepted") is True
        assert service.is_valid_signal(event_type="commitment_done") is True
        assert service.is_valid_signal(event_type="reminder_sent") is True
        assert service.is_valid_signal(event_type="commitment_at_risk") is True

    def test_rejects_engagement_signals(self):
        """Engagement-only signals are rejected (PRD §8: no engagement mechanics)."""
        from app.services.learning_service import LearningService

        service = LearningService()

        # Engagement-only events are NOT valid learning signals
        assert service.is_valid_signal(event_type="app_opened") is False
        assert service.is_valid_signal(event_type="screen_viewed") is False
        assert service.is_valid_signal(event_type="notification_clicked") is False
        assert service.is_valid_signal(event_type="session_started") is False

    def test_learn_nudge_timing(self):
        """System learns when a user is most responsive to reminders."""
        from app.services.learning_service import LearningService

        service = LearningService()
        principal_id = uuid4()

        # Record commitment responses at different hours
        for hour in [9, 9, 10, 9, 9, 10]:
            service.record_response_time(
                principal_id=principal_id,
                hour_of_day=hour,
                event_type="commitment_accepted",
            )

        preferred = service.get_preferred_nudge_hour(principal_id=principal_id)
        assert preferred == 9  # Most common response hour

    def test_learn_quiet_hour_patterns(self):
        """System learns quiet-hour patterns from commitment interaction gaps."""
        from app.services.learning_service import LearningService

        service = LearningService()
        principal_id = uuid4()

        # Record active hours (responses happen 8-22, quiet 22-8)
        for hour in [8, 9, 10, 14, 15, 18, 20, 21]:
            service.record_response_time(
                principal_id=principal_id,
                hour_of_day=hour,
                event_type="commitment_done",
            )

        quiet = service.suggest_quiet_hours(principal_id=principal_id)
        # Quiet hours should cover the gap where no responses occur
        assert quiet is not None
        assert quiet["start_hour"] >= 21  # After last response
        assert quiet["end_hour"] <= 9  # Before first response

    def test_prd_section8_feature_test(self):
        """Every learned feature must pass the PRD §8 test:
        does it create, protect, or close a commitment?"""
        from app.services.learning_service import COMMITMENT_LIFECYCLE_EVENTS

        # All allowed event types must serve commitment lifecycle
        lifecycle_verbs = {"create", "protect", "close"}
        for event in COMMITMENT_LIFECYCLE_EVENTS:
            assert event["serves"] in lifecycle_verbs, (
                f"Event '{event['type']}' does not serve a commitment lifecycle stage"
            )

    def test_no_learning_without_sufficient_data(self):
        """No nudge timing suggestion without minimum data points."""
        from app.services.learning_service import LearningService

        service = LearningService()
        principal_id = uuid4()

        # Only 1 data point — not enough
        service.record_response_time(
            principal_id=principal_id,
            hour_of_day=10,
            event_type="commitment_accepted",
        )

        preferred = service.get_preferred_nudge_hour(principal_id=principal_id)
        assert preferred is None  # Insufficient data
