"""Extraction endpoint — text, voice, and camera extraction (OL-020, OL-021, OL-022).

Three ingestion routes converge on the same pipeline:
- Text: direct text content → LLM extraction
- Voice: base64 audio → Whisper ASR → LLM extraction
- Camera: base64 image → Claude Vision → extraction

Content is ephemeral — never persisted to disk (ADR-002).
Routers hold zero business logic (CLAUDE.md).
"""

from datetime import datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.db import get_db, get_principal_id
from app.models import AuditLog, Commitment, CommitmentState, Context
from app.schemas import (
    DeltaEvent,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionResult,
)
from app.services.llm import ExtractionFailedError, LLMAdapter
from app.services.sync import manager as sync_manager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter(prefix="/extract", tags=["extraction"])

# Module-level adapter — reuses httpx connection pool
_llm_adapter: LLMAdapter | None = None


def _get_adapter() -> LLMAdapter:
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter


@router.post("", response_model=ExtractionResponse, status_code=202)
async def extract(
    body: ExtractionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> ExtractionResponse:
    """Extract commitments from text, voice, or camera input.

    Processes synchronously for direct input (text/audio/image).
    Returns extracted commitments as proposed state.
    """
    job_id = str(uuid4())
    adapter = _get_adapter()

    logger.info(
        "extraction_start",
        job_id=job_id,
        provenance_kind=body.provenance_kind,
        has_text=body.text is not None,
        has_audio=body.audio_base64 is not None,
        has_image=body.image_base64 is not None,
    )

    try:
        # Route to appropriate extraction method
        if body.provenance_kind == "camera" and body.image_base64:
            extraction = await adapter.extract_from_image(body.image_base64)
        elif body.provenance_kind == "voice" and body.audio_base64:
            extraction = await adapter.extract_from_audio(body.audio_base64)
        elif body.text:
            extraction = await adapter.extract_commitments(body.text)
        else:
            raise HTTPException(
                status_code=422,
                detail="Provide text, audio_base64 (voice), or image_base64 (camera)",
            )

        # Find a context for the principal to create commitments in
        context_id: UUID | None = None
        if body.thread_id:
            context_id = body.thread_id  # Use as context hint
        else:
            # Find first context for this principal
            ctx_result = await db.execute(
                select(Context).limit(1)
            )
            ctx = ctx_result.scalar_one_or_none()
            if ctx:
                context_id = ctx.id

        # Create commitments from extraction results
        threshold = settings.extraction_confidence_threshold
        confident = [c for c in extraction.commitments if c.confidence >= threshold]
        created_count = 0

        for extracted in confident:
            due_at = None
            if extracted.due_at:
                try:
                    due_at = datetime.fromisoformat(extracted.due_at)
                    # Strip timezone for TIMESTAMP WITHOUT TIME ZONE
                    if due_at.tzinfo is not None:
                        due_at = due_at.replace(tzinfo=None)
                except ValueError:
                    pass

            commitment = Commitment(
                context_id=context_id,
                owner_id=principal_id,
                title=extracted.title,
                class_=extracted.class_,
                amount_paise=extracted.amount_paise,
                state=CommitmentState.PROPOSED,
                version=1,
                due_at=due_at,
                provenance_kind=body.provenance_kind,
                extraction_confidence=extracted.confidence,
                prompt_hash=extraction.prompt_hash,
                model_id=extraction.model_id,
                extracted_by=principal_id,
            )
            db.add(commitment)
            await db.flush()

            # Audit log
            audit = AuditLog(
                actor_id=principal_id,
                actor_kind="agent",
                context_id=context_id,
                event="commitment.extracted",
                subject_id=commitment.id,
                detail={
                    "title": extracted.title,
                    "class": extracted.class_,
                    "confidence": extracted.confidence,
                    "provenance_kind": body.provenance_kind,
                },
                prompt_hash=extraction.prompt_hash,
                model_id=extraction.model_id,
            )
            db.add(audit)

            # Broadcast via WebSocket
            if context_id:
                delta = DeltaEvent(
                    event="commitment.created",
                    context_id=str(context_id),
                    subject_id=str(commitment.id),
                    seq=0,
                    data={
                        "title": extracted.title,
                        "class": extracted.class_,
                        "state": "proposed",
                        "confidence": extracted.confidence,
                    },
                )
                await sync_manager.broadcast_to_context(context_id, delta)

            created_count += 1

        await db.commit()

        logger.info(
            "extraction_complete",
            job_id=job_id,
            total_extracted=len(extraction.commitments),
            above_threshold=created_count,
            provenance_kind=body.provenance_kind,
        )

        return ExtractionResponse(job_id=job_id, status="completed")

    except ExtractionFailedError as e:
        logger.warning("extraction_failed", job_id=job_id, reason=e.reason)
        raise HTTPException(status_code=422, detail=f"Extraction failed: {e.reason}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("extraction_error", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Extraction failed unexpectedly")
