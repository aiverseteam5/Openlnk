"""Idempotency key purge worker (OL-007a).

Runs on redis-jobs (durable). Purges idempotency keys older than 24h
on a scheduled cadence (hourly via arq cron).
"""

from datetime import UTC, datetime, timedelta

import structlog
from arq.cron import cron
from sqlalchemy import delete

from app.models import IdempotencyKey

logger = structlog.get_logger()

# OL-007a: keys older than this are purged
RETENTION_HOURS = 24


async def purge_idempotency_keys(ctx: dict) -> dict:
    """Delete IdempotencyKey rows older than 24 hours.

    Runs as an arq cron job on redis-jobs (durable, AOF).
    """
    from app.db import async_session

    cutoff = datetime.now(UTC) - timedelta(hours=RETENTION_HOURS)

    async with async_session() as session:
        result = await session.execute(
            delete(IdempotencyKey).where(IdempotencyKey.created_at < cutoff)
        )
        deleted = result.rowcount
        await session.commit()

    logger.info("idempotency_keys_purged", deleted=deleted, cutoff=cutoff.isoformat())
    return {"status": "success", "deleted": deleted}


class WorkerSettings:
    """arq worker settings for idempotency purge — connects to redis-jobs."""

    cron_jobs = [cron(purge_idempotency_keys, hour=None, minute=0)]  # noqa: RUF012
    redis_settings = None  # Set from config at startup
