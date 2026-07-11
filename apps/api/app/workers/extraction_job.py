"""Extraction arq job — runs on redis-extraction (ephemeral, no persistence).

Eng review decisions:
- Text extraction: 60s hard cancel
- Voice/camera extraction: 120s hard cancel
- On timeout: discard all in-memory content, mark job failed
- On Pydantic ValidationError: retry once, then fail with visible error (T12)
- On success: create commitment via CommitmentService
"""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AuditLog, Commitment, CommitmentState, Message, Thread
from app.schemas import DeltaEvent, ExtractionResult
from app.services.llm import ExtractionFailedError, LLMAdapter
from app.services.sync import manager as sync_manager

logger = structlog.get_logger()

# Module-level adapter instance — reuses httpx connection pool across jobs
_llm_adapter: LLMAdapter | None = None


def _get_adapter() -> LLMAdapter:
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter


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
            _run_extraction(ctx, message_id, thread_id, provenance_kind),
            timeout=timeout,
        )
        return {"status": "success", "commitments_extracted": result}

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
    ctx: dict,
    message_id: str,
    thread_id: str,
    provenance_kind: str,
) -> int:
    """Core extraction logic: fetch message → LLM → parse → create commitment.

    This function is wrapped in asyncio.wait_for() for the hard timeout.
    Returns the number of commitments created.
    """
    db_session: AsyncSession = ctx["db_session"]
    adapter = _get_adapter()

    # 1. Fetch message body
    msg_result = await db_session.execute(
        select(Message).where(Message.id == message_id)  # type: ignore[arg-type]
    )
    message = msg_result.scalar_one_or_none()
    if message is None:
        raise ExtractionFailedError(f"Message {message_id} not found")

    text = message.body
    if not text:
        # Voice/camera: would need ASR/OCR here. For now, text only.
        raise ExtractionFailedError(
            f"No text body for {provenance_kind} message {message_id}. "
            "Voice/camera transcription not yet implemented."
        )

    # 2. Fetch thread for context_id
    thread_result = await db_session.execute(
        select(Thread).where(Thread.id == thread_id)  # type: ignore[arg-type]
    )
    thread = thread_result.scalar_one_or_none()
    if thread is None:
        raise ExtractionFailedError(f"Thread {thread_id} not found")

    # 3. Call LLM
    extraction: ExtractionResult = await adapter.extract_commitments(text)

    # 4. Filter by confidence threshold (OL-029a)
    threshold = settings.extraction_confidence_threshold
    confident = [c for c in extraction.commitments if c.confidence >= threshold]

    logger.info(
        "extraction_filtered",
        total=len(extraction.commitments),
        above_threshold=len(confident),
        threshold=threshold,
    )

    # 5. Create commitments
    created_count = 0
    for extracted in confident:
        due_at = None
        if extracted.due_at:
            try:
                due_at = datetime.fromisoformat(extracted.due_at)
            except ValueError:
                logger.warning("extraction_invalid_due_at", value=extracted.due_at)

        commitment = Commitment(
            context_id=thread.context_id,
            owner_id=message.sender_id,
            counterparty_id=None,  # Resolved later via counterparty matching
            title=extracted.title,
            class_=extracted.class_,
            amount_paise=extracted.amount_paise,
            due_at=due_at,
            state=CommitmentState.PROPOSED,
            version=1,
            provenance_kind=provenance_kind,
            provenance_ref=str(message_id),
            extraction_confidence=extracted.confidence,
            prompt_hash=extraction.prompt_hash,
            model_id=extraction.model_id,
            extracted_by=message.sender_id,
        )
        db_session.add(commitment)
        await db_session.flush()  # Get the commitment ID

        # 6. Audit log entry
        audit = AuditLog(
            actor_id=message.sender_id,
            actor_kind="agent",
            context_id=thread.context_id,
            event="commitment.extracted",
            subject_id=commitment.id,
            detail={
                "title": extracted.title,
                "class": extracted.class_,
                "confidence": extracted.confidence,
                "provenance_kind": provenance_kind,
            },
            prompt_hash=extraction.prompt_hash,
            model_id=extraction.model_id,
        )
        db_session.add(audit)

        # 7. Broadcast via WebSocket (sync protocol, ADR-001)
        delta = DeltaEvent(
            event="commitment.created",
            context_id=str(thread.context_id),
            subject_id=str(commitment.id),
            seq=0,  # Will be assigned by sync manager
            data={
                "title": extracted.title,
                "class": extracted.class_,
                "state": "proposed",
                "confidence": extracted.confidence,
            },
        )
        await sync_manager.broadcast(str(thread.context_id), delta)

        created_count += 1

    await db_session.commit()

    logger.info(
        "extraction_commitments_created",
        message_id=message_id,
        count=created_count,
    )

    return created_count


# arq worker class configuration
class WorkerSettings:
    """arq worker settings — connects to redis-extraction."""

    functions = [extraction_job]  # noqa: RUF012
    redis_settings = None  # Set from config at startup

    # Hard timeout per job (overridden per provenance_kind in the job itself)
    job_timeout = 120  # max of text (60) and media (120)
