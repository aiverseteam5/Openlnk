"""Tests for OL-142, OL-142a — Postgres PITR configuration.

These are infrastructure requirements. Tests verify the configuration
structure is defined; actual PITR verification is an ops procedure.
"""

import pytest


@pytest.mark.req("OL-142")
class TestPITRDrill:
    """OL-142: Nightly Postgres PITR verified restore drill monthly."""

    def test_pitr_drill_schedule_defined(self):
        """PITR restore drill schedule is defined."""
        from app.services.backup_service import get_pitr_config

        config = get_pitr_config()
        assert config["backup_frequency"] == "continuous"
        assert config["restore_drill_cadence"] == "monthly"

    def test_pitr_drill_verification_required(self):
        """Drill must verify successful restore, not just backup existence."""
        from app.services.backup_service import get_pitr_config

        config = get_pitr_config()
        assert config["drill_requires_restore_verification"] is True


@pytest.mark.req("OL-142a")
class TestPITRS3:
    """OL-142a: PITR to S3 (ap-south-1) before Gate 2 go-live."""

    def test_s3_region_is_mumbai(self):
        """PITR backups target ap-south-1 (Mumbai) per OL-122."""
        from app.services.backup_service import get_pitr_config

        config = get_pitr_config()
        assert config["s3_region"] == "ap-south-1"

    def test_gate2_entry_blocker(self):
        """PITR restore verification is a Gate 2 entry blocker."""
        from app.services.backup_service import get_pitr_config

        config = get_pitr_config()
        assert config["gate2_entry_blocker"] is True

    def test_pre_gate2_drill_required(self):
        """Monthly drill does not satisfy Gate 2 — a pre-Gate-2 drill is required."""
        from app.services.backup_service import get_pitr_config

        config = get_pitr_config()
        assert config["pre_gate2_restore_drill_required"] is True
