"""Auth router — OTP login, token refresh, session management.

OL-146: Phone-OTP via MSG91 (primary) + fallback.
OL-146a: JWT access (15min) + refresh (90d, rotated).
Routers hold zero business logic (CLAUDE.md).
"""

import re

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session
from app.services.auth_service import auth_service

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])

# E.164 phone validation (India-first, supports international)
_E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")


class SendOtpRequest(BaseModel):
    phone_e164: str = Field(
        ...,
        description="Phone number in E.164 format (e.g., +919876543210)",
        examples=["+919876543210"],
    )


class SendOtpResponse(BaseModel):
    sent: bool
    provider: str


class VerifyOtpRequest(BaseModel):
    phone_e164: str
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/send-otp", response_model=SendOtpResponse)
async def send_otp(body: SendOtpRequest) -> SendOtpResponse:
    """Send OTP to phone number via MSG91 (or fallback).

    Rate limited at Caddy (IP) and per-phone (OL-144).
    No auth required — this is the login entry point.
    """
    if not _E164_PATTERN.match(body.phone_e164):
        raise HTTPException(
            status_code=422,
            detail="Phone must be in E.164 format (e.g., +919876543210)",
        )

    result = auth_service.send_otp(phone_e164=body.phone_e164)

    if not result["sent"]:
        raise HTTPException(
            status_code=503,
            detail="OTP delivery failed. Please try again.",
        )

    return SendOtpResponse(sent=result["sent"], provider=result["provider"])


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOtpRequest) -> TokenResponse:
    """Verify OTP and issue JWT access + refresh tokens.

    Creates a new principal if phone number is not registered.
    """
    if not _E164_PATTERN.match(body.phone_e164):
        raise HTTPException(status_code=422, detail="Invalid phone format")

    verified = auth_service.verify_otp(
        phone_e164=body.phone_e164,
        otp=body.otp,
    )

    if not verified:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    # Get or create principal — needs a DB session without RLS
    # (auth is pre-authentication, no principal_id yet)
    async with async_session() as db:
        principal = await auth_service.get_or_create_principal(
            db=db,
            phone_e164=body.phone_e164,
        )
        await db.commit()

        tokens = auth_service.issue_tokens(principal_id=principal.id)

    logger.info("auth_login", principal_id=str(principal.id), phone=body.phone_e164[-4:])

    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Rotate refresh token and issue new access + refresh pair.

    OL-146a: Refresh tokens are single-use (rotated on every use).
    """
    tokens = auth_service.rotate_refresh_token(refresh_token=body.refresh_token)

    if tokens is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    return TokenResponse(**tokens)


async def get_db_no_rls() -> AsyncSession:
    """DB session without RLS — for auth endpoints only."""
    async with async_session() as session:
        yield session
