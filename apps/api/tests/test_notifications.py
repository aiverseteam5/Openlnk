"""Tests for OL-060..064 — notifications & silence.

OL-060: Notify only when user is the blocker.
OL-061: Batch non-blocking info into daily brief.
OL-062: Record notifications-avoided as metric.
OL-063: Respect per-user quiet hours.
OL-064: Daily brief includes today's commitments, conflicts, at-risk.
"""

from datetime import time
from uuid import uuid4

import pytest


@pytest.mark.req("OL-060")
class TestBlockerNotifications:
    """Notify user only when they are the blocker."""

    def test_notification_service_exists(self):
        from app.services.notification_service import NotificationService

        assert NotificationService is not None

    def test_should_notify_at_risk(self):
        """Notify when commitment assigned to user is at_risk."""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        assert service.should_notify(
            principal_id=uuid4(),
            reason="at_risk",
            is_blocker=True,
        )

    def test_should_notify_awaiting_acceptance(self):
        """Notify when commitment awaits user's acceptance."""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        assert service.should_notify(
            principal_id=uuid4(),
            reason="awaiting_acceptance",
            is_blocker=True,
        )

    def test_should_not_notify_non_blocker(self):
        """Do NOT notify when user is not the blocker."""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        assert not service.should_notify(
            principal_id=uuid4(),
            reason="informational",
            is_blocker=False,
        )


@pytest.mark.req("OL-061")
class TestDailyBriefBatching:
    """Non-blocking information batched into daily brief."""

    def test_daily_brief_service_exists(self):
        from app.services.notification_service import DailyBriefService

        assert DailyBriefService is not None

    def test_batch_non_blocking(self):
        """Non-blocking items are queued for daily brief."""
        from app.services.notification_service import DailyBriefService

        service = DailyBriefService()
        service.queue_item(
            principal_id=uuid4(),
            item_type="status_update",
            data={"message": "Commitment completed"},
        )
        assert len(service.pending_items) >= 1


@pytest.mark.req("OL-062")
class TestNotificationsAvoided:
    """Record notifications-avoided as a first-class metric."""

    def test_record_notification_avoided(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()
        service.record_avoided(
            principal_id=uuid4(),
            reason="non_blocker_suppressed",
        )
        assert service.avoided_count >= 1

    def test_avoided_metric_tracks_per_user(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()
        pid = uuid4()
        service.record_avoided(principal_id=pid, reason="quiet_hours")
        service.record_avoided(principal_id=pid, reason="batched")
        assert service.get_avoided_count(pid) == 2


@pytest.mark.req("OL-063")
class TestQuietHours:
    """Respect per-user quiet hours."""

    def test_quiet_hours_check(self):
        """Policy engine respects quiet hours on bounded-auto."""
        from app.models import AutonomyRung
        from app.services.policy_engine import PolicyEngine

        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_reminder",
            commitment_class="fee",
            quiet_hours=(time(22, 0), time(7, 0)),
            current_time=time(23, 0),
        )
        assert decision.allowed is False
        assert decision.reason == "quiet_hours_active"

    def test_quiet_hours_queues_to_next_window(self):
        """Actions during quiet hours are queued, not dropped."""
        from app.services.notification_service import NotificationService

        service = NotificationService()
        result = service.queue_for_next_window(
            principal_id=uuid4(),
            action_type="send_reminder",
            quiet_hours_end=time(7, 0),
        )
        assert result["queued"] is True
        assert result["send_after"] is not None


@pytest.mark.req("OL-064")
class TestDailyBriefContent:
    """Daily brief includes today's commitments, conflicts, at-risk."""

    def test_daily_brief_sections(self):
        from app.services.notification_service import DailyBriefService

        service = DailyBriefService()
        sections = service.get_brief_sections()
        assert "todays_commitments" in sections
        assert "conflicts" in sections
        assert "at_risk" in sections

    def test_daily_brief_excludes_non_relevant(self):
        """Brief excludes everything not in scope."""
        from app.services.notification_service import DailyBriefService

        service = DailyBriefService()
        sections = service.get_brief_sections()
        assert "marketing" not in sections
        assert "analytics" not in sections
