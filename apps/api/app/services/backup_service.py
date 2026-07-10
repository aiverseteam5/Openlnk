"""Backup configuration — OL-142, OL-142a.

Postgres PITR to S3 (ap-south-1). Configuration structure for
infrastructure setup. Actual PITR is an ops procedure.
"""


def get_pitr_config() -> dict:
    """Return PITR backup configuration.

    OL-142: Nightly PITR, verified restore drill monthly.
    OL-142a: S3 target in ap-south-1, Gate 2 entry blocker.
    """
    return {
        "backup_frequency": "continuous",
        "s3_region": "ap-south-1",
        "s3_bucket_env_var": "PITR_S3_BUCKET",
        "restore_drill_cadence": "monthly",
        "drill_requires_restore_verification": True,
        "gate2_entry_blocker": True,
        "pre_gate2_restore_drill_required": True,
    }
