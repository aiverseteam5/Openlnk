"""Tests for extraction worker requirements OL-024, OL-028.

Unit tests: timeout configuration, worker structure.
"""

import pytest

from app.config import settings
from app.workers.extraction_job import WorkerSettings, extraction_job


@pytest.mark.req("OL-024")
class TestEphemeralExtraction:
    """Raw content not persisted beyond ephemeral extraction window (≤60s)."""

    def test_text_timeout_is_60s(self):
        assert settings.extraction_timeout_text_secs == 60

    def test_media_timeout_is_120s(self):
        assert settings.extraction_timeout_media_secs == 120

    def test_worker_job_timeout_covers_max(self):
        """Worker job_timeout must be >= max of text and media timeouts."""
        assert WorkerSettings.job_timeout >= settings.extraction_timeout_text_secs
        assert WorkerSettings.job_timeout >= settings.extraction_timeout_media_secs


@pytest.mark.req("OL-028")
class TestExtractionRetry:
    """IF LLM unreachable, queue extraction jobs with exponential backoff."""

    def test_extraction_job_registered(self):
        """extraction_job is registered in WorkerSettings.functions."""
        assert extraction_job in WorkerSettings.functions

    def test_extraction_job_is_async(self):
        """extraction_job is an async function (arq requirement)."""
        import asyncio

        assert asyncio.iscoroutinefunction(extraction_job)
