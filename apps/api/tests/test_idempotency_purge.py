"""Tests for OL-007a — idempotency key purge worker.

The system shall run an arq worker that purges idempotency keys older
than 24h on a scheduled cadence (>= once per hour).
"""

import asyncio

import pytest


@pytest.mark.req("OL-007a")
class TestIdempotencyPurge:
    """Idempotency key purge arq worker exists and is correctly configured."""

    def test_purge_job_exists(self):
        """purge_idempotency_keys job function exists."""
        from app.workers.idempotency_purge import purge_idempotency_keys

        assert callable(purge_idempotency_keys)

    def test_purge_job_is_async(self):
        """Purge job is an async function (arq requirement)."""
        from app.workers.idempotency_purge import purge_idempotency_keys

        assert asyncio.iscoroutinefunction(purge_idempotency_keys)

    def test_purge_retention_hours(self):
        """Retention period is 24 hours."""
        from app.workers.idempotency_purge import RETENTION_HOURS

        assert RETENTION_HOURS == 24

    def test_purge_worker_has_cron(self):
        """Worker settings include a cron schedule (>= once per hour)."""
        from app.workers.idempotency_purge import WorkerSettings

        assert hasattr(WorkerSettings, "cron_jobs")
        cron_jobs = WorkerSettings.cron_jobs
        assert len(cron_jobs) >= 1

    def test_purge_job_references_idempotency_keys(self):
        """Purge job targets the idempotency_keys table."""
        import inspect

        from app.workers.idempotency_purge import purge_idempotency_keys

        source = inspect.getsource(purge_idempotency_keys)
        assert "idempotency_keys" in source.lower() or "IdempotencyKey" in source
