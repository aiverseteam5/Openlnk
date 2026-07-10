"""Tests for OL-055 — rung graduation with sliding window.

The system shall graduate a (contact x class) pair one rung only after
N clean actions over >= 14 days (N configurable, default 20).
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models import AutonomyRung
from app.services.autonomy_service import AutonomyService, GraduationResult


@pytest.mark.req("OL-055")
class TestGraduation:
    """Graduation requires N clean actions over >= 14 days."""

    def test_autonomy_service_exists(self):
        service = AutonomyService()
        assert hasattr(service, "check_graduation")

    def test_graduation_requires_min_actions(self):
        """Cannot graduate with fewer than N clean actions."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.OBSERVE,
            clean_actions=10,
            window_started=datetime.utcnow() - timedelta(days=20),
        )
        assert result.eligible is False

    def test_graduation_requires_min_window(self):
        """Cannot graduate if window is shorter than 14 days."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.OBSERVE,
            clean_actions=25,
            window_started=datetime.utcnow() - timedelta(days=5),
        )
        assert result.eligible is False

    def test_graduation_eligible(self):
        """Graduate when N actions over >= 14 days."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.OBSERVE,
            clean_actions=20,
            window_started=datetime.utcnow() - timedelta(days=15),
        )
        assert result.eligible is True
        assert result.next_rung == AutonomyRung.PROPOSE

    def test_graduation_advances_one_rung_only(self):
        """Graduation advances exactly one rung (sacred rule: no skipping)."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.PROPOSE,
            clean_actions=20,
            window_started=datetime.utcnow() - timedelta(days=15),
        )
        assert result.next_rung == AutonomyRung.BOUNDED_AUTO

    def test_graduation_from_bounded_to_trusted(self):
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.BOUNDED_AUTO,
            clean_actions=20,
            window_started=datetime.utcnow() - timedelta(days=15),
        )
        assert result.next_rung == AutonomyRung.TRUSTED_AUTO

    def test_no_graduation_from_trusted(self):
        """Already at top rung — no graduation possible."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.TRUSTED_AUTO,
            clean_actions=100,
            window_started=datetime.utcnow() - timedelta(days=30),
        )
        assert result.eligible is False
        assert result.next_rung is None

    def test_graduation_default_threshold_is_20(self):
        from app.services.autonomy_service import DEFAULT_GRADUATION_THRESHOLD

        assert DEFAULT_GRADUATION_THRESHOLD == 20

    def test_graduation_configurable_threshold(self):
        """Threshold N is configurable."""
        service = AutonomyService(graduation_threshold=10)
        result = service.check_graduation(
            current_rung=AutonomyRung.OBSERVE,
            clean_actions=10,
            window_started=datetime.utcnow() - timedelta(days=15),
        )
        assert result.eligible is True

    def test_graduation_result_includes_track_record(self):
        """Result includes track record info for showing user."""
        service = AutonomyService()
        result = service.check_graduation(
            current_rung=AutonomyRung.OBSERVE,
            clean_actions=20,
            window_started=datetime.utcnow() - timedelta(days=15),
        )
        assert result.clean_actions == 20
        assert result.days_in_window >= 14
