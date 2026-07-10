"""Tests for OL-056 (demotion) and OL-057 (kill switch).

OL-056: User correction demotes exactly one rung and logs the cause.
OL-057: Per-context kill switch reverts all pairs to Observe.
"""

import pytest

from app.models import AutonomyRung
from app.services.autonomy_service import AutonomyService


@pytest.mark.req("OL-056")
class TestDemotion:
    """User correction demotes exactly one rung."""

    def test_demote_from_trusted_to_bounded(self):
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.TRUSTED_AUTO,
            cause="user_corrected_send",
        )
        assert result.demoted is True
        assert result.new_rung == AutonomyRung.BOUNDED_AUTO

    def test_demote_from_bounded_to_propose(self):
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.BOUNDED_AUTO,
            cause="user_reverted_action",
        )
        assert result.demoted is True
        assert result.new_rung == AutonomyRung.PROPOSE

    def test_demote_from_propose_to_observe(self):
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.PROPOSE,
            cause="user_rejected_proposal",
        )
        assert result.demoted is True
        assert result.new_rung == AutonomyRung.OBSERVE

    def test_cannot_demote_below_observe(self):
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.OBSERVE,
            cause="impossible",
        )
        assert result.demoted is False
        assert result.new_rung == AutonomyRung.OBSERVE

    def test_demotion_logs_cause(self):
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.BOUNDED_AUTO,
            cause="user_corrected_reminder_text",
        )
        assert result.reason == "user_corrected_reminder_text"

    def test_demotion_is_exactly_one_rung(self):
        """Demotion drops exactly one rung, never resets to observe."""
        service = AutonomyService()
        result = service.demote(
            current_rung=AutonomyRung.TRUSTED_AUTO,
            cause="correction",
        )
        # Must be BOUNDED_AUTO, not OBSERVE
        assert result.new_rung == AutonomyRung.BOUNDED_AUTO
        assert result.new_rung != AutonomyRung.OBSERVE


@pytest.mark.req("OL-057")
class TestKillSwitch:
    """Per-context kill switch reverts all pairs to Observe."""

    def test_kill_switch_returns_observe(self):
        service = AutonomyService()
        rung = service.kill_switch()
        assert rung == AutonomyRung.OBSERVE

    def test_kill_switch_method_exists(self):
        service = AutonomyService()
        assert hasattr(service, "kill_switch")
        assert callable(service.kill_switch)
