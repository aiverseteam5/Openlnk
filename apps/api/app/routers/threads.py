"""Web-thread token resolution endpoints (OL-080..085).

Routers hold zero business logic (CLAUDE.md). Delegate to WebThreadService.
Guest tokens grant access to exactly one thread (ADR-005).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.web_thread_service import WebThreadService

router = APIRouter(prefix="/threads", tags=["threads"])

_thread_service = WebThreadService(secret_key=settings.jwt_secret)


class ThreadResolveResponse(BaseModel):
    thread_id: str
    principal_id: str
    commitments: list[dict]


class ThreadActionRequest(BaseModel):
    action: str
    version: int


class ThreadMessageRequest(BaseModel):
    text: str
    token: str


class ThreadMessageResponse(BaseModel):
    status: str
    thread_id: str


class ThreadFunnelRequest(BaseModel):
    event_type: str
    token: str


@router.post("/funnel")
async def track_funnel(body: ThreadFunnelRequest) -> dict:
    """Track funnel events — open/return (OL-085). Fire-and-forget."""
    claims = _thread_service.validate_token(body.token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Non-critical event tracking — log and return
    return {"status": "ok"}


@router.post("/messages", response_model=ThreadMessageResponse)
async def send_message(body: ThreadMessageRequest) -> ThreadMessageResponse:
    """Accept a guest message on a thread (OL-053 Propose rung).

    Messages are queued for owner review — raw content is never
    persisted server-side (ADR-002).
    """
    claims = _thread_service.validate_token(body.token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    _thread_service.queue_message(
        thread_id=claims["thread_id"],
        text=body.text,
    )

    return ThreadMessageResponse(
        status="queued",
        thread_id=claims["thread_id"],
    )


@router.get("/resolve/{token}", response_model=ThreadResolveResponse)
async def resolve_token(token: str) -> ThreadResolveResponse:
    """Resolve a thread token to thread data (OL-080).

    Returns thread commitments if token is valid.
    No signup required — zero-install access.
    """
    claims = _thread_service.validate_token(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    thread_data = _thread_service.get_thread_data(
        thread_id=claims["thread_id"],
    )

    return ThreadResolveResponse(
        thread_id=claims["thread_id"],
        principal_id=claims["principal_id"],
        commitments=thread_data.get("commitments", []),
    )
