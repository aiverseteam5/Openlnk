"""Extraction endpoint — enqueues messages for LLM extraction.

Content flows through redis-extraction (ephemeral, no persistence — ADR-002).
ExtractionJob has a hard 60s timeout for text, 120s for voice/camera.
"""

from fastapi import APIRouter, Header

from app.schemas import ExtractionRequest, ExtractionResponse

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("", response_model=ExtractionResponse, status_code=202)
async def enqueue_extraction(
    body: ExtractionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> ExtractionResponse:
    """Enqueue a message for extraction. Returns 202 Accepted.

    The extraction job runs asynchronously via arq on redis-extraction.
    Results are delivered via WebSocket (sync protocol, ADR-001).
    """
    # TODO: enqueue arq job on redis-extraction
    return ExtractionResponse(job_id="placeholder", status="queued")
