"""Extraction endpoint — enqueues messages for LLM extraction.

Content flows through redis-extraction (ephemeral, no persistence — ADR-002).
ExtractionJob has a hard 60s timeout for text, 120s for voice/camera.
Routers hold zero business logic (CLAUDE.md).
"""

from uuid import uuid4

import structlog
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header

from app.config import settings
from app.schemas import ExtractionRequest, ExtractionResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/extract", tags=["extraction"])

_arq_pool: ArqRedis | None = None


async def _get_arq_pool() -> ArqRedis:
    """Lazy-init arq connection to redis-extraction."""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(
            RedisSettings.from_dsn(settings.redis_extraction_url)
        )
    return _arq_pool


@router.post("", response_model=ExtractionResponse, status_code=202)
async def enqueue_extraction(
    body: ExtractionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    arq_pool: ArqRedis = Depends(_get_arq_pool),
) -> ExtractionResponse:
    """Enqueue a message for extraction. Returns 202 Accepted.

    The extraction job runs asynchronously via arq on redis-extraction.
    Results are delivered via WebSocket (sync protocol, ADR-001).
    """
    job_id = str(uuid4())

    await arq_pool.enqueue_job(
        "extraction_job",
        message_id=str(body.message_id),
        thread_id=str(body.thread_id),
        provenance_kind="message",  # voice/camera added at Gate 1b/1c
        _job_id=job_id,
    )

    logger.info(
        "extraction_enqueued",
        job_id=job_id,
        message_id=str(body.message_id),
        idempotency_key=idempotency_key,
    )

    return ExtractionResponse(job_id=job_id, status="queued")
