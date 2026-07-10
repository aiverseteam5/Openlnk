"""Extraction arq job — runs on redis-extraction (ephemeral, no persistence).

Eng review decisions:
- Text extraction: 60s hard cancel
- Voice/camera extraction: 120s hard cancel
- On timeout: discard all in-memory content, mark job failed
- On Pydantic ValidationError: retry once, then fail with visible error (T12)
- On success: create commitment via CommitmentService
"""

import asyncio

import structlog

from app.config import settings
from app.services.llm import ExtractionFailedError

logger = structlog.get_logger()


async def extraction_job(
    ctx: dict,
    message_id: str,
    thread_id: str,
    provenance_kind: str,
) -> dict:
    """Extract commitments from a message.

    Runs on redis-extraction (ephemeral). Hard timeout enforced by arq
    job_timeout. Content is NEVER persisted to Redis disk (ADR-002).

    Args:
        ctx: arq context (includes redis connection)
        message_id: UUID of the message to extract from
        thread_id: UUID of the thread containing the message
        provenance_kind: 'message', 'voice', or 'camera'

    Returns:
        Dict with extraction results or failure status.
    """
    timeout = (
        settings.extraction_timeout_text_secs
        if provenance_kind == "message"
        else settings.extraction_timeout_media_secs
    )

    logger.info(
        "extraction_starting",
        message_id=message_id,
        provenance_kind=provenance_kind,
        timeout_secs=timeout,
    )

    try:
        result = await asyncio.wait_for(
            _run_extraction(message_id, thread_id, provenance_kind),
            timeout=timeout,
        )
        return {"status": "success", "commitments_extracted": len(result)}

    except TimeoutError:
        logger.warning(
            "extraction_timeout",
            message_id=message_id,
            timeout_secs=timeout,
        )
        # Content discarded — ADR-002 ephemeral window enforced
        return {
            "status": "timeout",
            "error": f"Extraction timed out after {timeout}s. Create commitment manually.",
        }

    except ExtractionFailedError as e:
        logger.warning(
            "extraction_failed",
            message_id=message_id,
            reason=e.reason,
        )
        return {
            "status": "failed",
            "error": f"Extraction failed: {e.reason}. Create commitment manually.",
        }


async def _run_extraction(
    message_id: str,
    thread_id: str,
    provenance_kind: str,
) -> list:
    """Core extraction logic: fetch message → LLM → parse → create commitment.

    This function is wrapped in asyncio.wait_for() for the hard timeout.
    """
    # TODO: implement
    # 1. Fetch message body from DB (encrypted at rest)
    # 2. If voice: transcribe via ASR
    # 3. If camera: OCR
    # 4. Send text to LLM via LLMAdapter
    # 5. Parse ExtractionResult (Pydantic)
    # 6. Create commitment(s) via CommitmentService
    # 7. Write audit_log entry
    raise NotImplementedError("_run_extraction not yet implemented")


# arq worker class configuration
class WorkerSettings:
    """arq worker settings — connects to redis-extraction."""

    functions = [extraction_job]  # noqa: RUF012
    redis_settings = None  # Set from config at startup

    # Hard timeout per job (overridden per provenance_kind in the job itself)
    job_timeout = 120  # max of text (60) and media (120)
