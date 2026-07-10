"""Tests for OL-054 — Bounded-auto rung behavior.

WHILE at rung Bounded-auto, the system shall auto-send only whitelisted
deterministic classes (reminder, confirmation) within configured quiet hours.
"""

from datetime import time

import pytest

from app.models import AutonomyRung
from app.services.policy_engine import PolicyEngine


@pytest.mark.req("OL-054")
class TestBoundedAuto:
    """Bounded-auto allows only whitelisted actions within quiet hours."""

    def test_bounded_auto_allows_reminder(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_reminder",
            commitment_class="fee",
        )
        assert decision.allowed is True

    def test_bounded_auto_allows_confirmation(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_confirmation",
            commitment_class="fee",
        )
        assert decision.allowed is True

    def test_bounded_auto_blocks_non_whitelisted(self):
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_negotiation",
            commitment_class="fee",
        )
        assert decision.allowed is False
        assert decision.requires_approval is True

    def test_bounded_auto_respects_quiet_hours(self):
        """Actions during quiet hours are queued, not sent."""
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_reminder",
            commitment_class="fee",
            quiet_hours=(time(22, 0), time(7, 0)),
            current_time=time(23, 30),
        )
        assert decision.allowed is False
        assert decision.reason == "quiet_hours_active"

    def test_bounded_auto_allows_outside_quiet_hours(self):
        """Actions outside quiet hours proceed normally."""
        engine = PolicyEngine()
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_reminder",
            commitment_class="fee",
            quiet_hours=(time(22, 0), time(7, 0)),
            current_time=time(10, 0),
        )
        assert decision.allowed is True

    def test_bounded_auto_quiet_hours_wrap_midnight(self):
        """Quiet hours spanning midnight (22:00-07:00) work correctly."""
        engine = PolicyEngine()
        # 2 AM is inside 22:00-07:00
        decision = engine.evaluate(
            rung=AutonomyRung.BOUNDED_AUTO,
            action_type="send_reminder",
            commitment_class="schedule",
            quiet_hours=(time(22, 0), time(7, 0)),
            current_time=time(2, 0),
        )
        assert decision.allowed is False
        assert decision.reason == "quiet_hours_active"

    def test_quiet_hours_model_exists(self):
        """Principal quiet hours are stored per user."""
        from app.models import Principal

        # quiet_hours_start and quiet_hours_end fields exist
        fields = {c.name for c in Principal.__table__.columns}
        assert "quiet_hours_start" in fields
        assert "quiet_hours_end" in fields
