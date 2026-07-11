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
