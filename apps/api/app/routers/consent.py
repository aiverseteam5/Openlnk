"""Consent routes — guardian OTP consent for child-linked data (OL-100a, OL-120, OL-123).

Flow:
1. Owner sends consent request → OTP sent to parent phone
2. Parent verifies OTP → consent recorded, staging_record updated
3. Consent withdrawal via same endpoint with action=withdraw

Routers hold zero business logic (CLAUDE.md).
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session, get_db, get_principal_id
from app.models import (
    Business,
    BusinessMember,
    ConsentAction,
    ConsentEvent,
    Principal,
    StagingRecord,
)
from app.services.auth_service import auth_service

logger = structlog.get_logger()

router = APIRouter(prefix="/consent", tags=["consent"])


# ── Schemas ──


class SendConsentRequest(BaseModel):
    staging_record_id: int
    business_id: str


class SendConsentResponse(BaseModel):
    sent: bool
    phone_last4: str


class VerifyConsentRequest(BaseModel):
    staging_record_id: int
    business_id: str
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ConsentStatusResponse(BaseModel):
    staging_record_id: int
    student_name: str
    consent_received: bool


class WithdrawConsentRequest(BaseModel):
    staging_record_id: int
    business_id: str


# ── Routes ──


@router.post("/send-otp", response_model=SendConsentResponse)
async def send_consent_otp(
    body: SendConsentRequest,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> SendConsentResponse:
    """Send consent OTP to parent phone for a staging record.

    Only the business owner/staff can trigger this (OL-100a).
    """
    biz_id = UUID(body.business_id)

    # Verify caller is a business member
    member = await db.execute(
        select(BusinessMember).where(
            BusinessMember.business_id == biz_id,
            BusinessMember.principal_id == principal_id,
        )
    )
    if member.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this business")

    # Get staging record
    result = await db.execute(
        select(StagingRecord).where(
            StagingRecord.id == body.staging_record_id,
            StagingRecord.business_id == biz_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Student record not found")

    if record.consent_received:
        return SendConsentResponse(sent=True, phone_last4=record.parent_phone[-4:])

    # Send OTP to parent phone
    otp_result = auth_service.send_otp(phone_e164=record.parent_phone)

    if not otp_result["sent"]:
        raise HTTPException(status_code=503, detail="OTP delivery failed")

    logger.info(
        "consent_otp_sent",
        staging_record_id=record.id,
        student=record.student_name,
        phone=record.parent_phone[-4:],
    )

    return SendConsentResponse(sent=True, phone_last4=record.parent_phone[-4:])


@router.post("/verify-otp", response_model=ConsentStatusResponse)
async def verify_consent_otp(
    body: VerifyConsentRequest,
    principal_id: UUID = Depends(get_principal_id),
) -> ConsentStatusResponse:
    """Verify parent OTP and record guardian consent (OL-120).

    On success: staging_record.consent_received = true,
    ConsentEvent audit entry created.
    """
    biz_id = UUID(body.business_id)

    # Use a fresh session without RLS for consent recording
    # (parent may not have a principal yet)
    async with async_session() as db:
        # Get staging record
        result = await db.execute(
            select(StagingRecord).where(
                StagingRecord.id == body.staging_record_id,
                StagingRecord.business_id == biz_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Student record not found")

        if record.consent_received:
            return ConsentStatusResponse(
                staging_record_id=record.id,
                student_name=record.student_name,
                consent_received=True,
            )

        # Verify OTP against parent phone
        verified = auth_service.verify_otp(
            phone_e164=record.parent_phone,
            otp=body.otp,
        )
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")

        # Get or create parent principal
        parent = await auth_service.get_or_create_principal(
            db=db, phone_e164=record.parent_phone,
        )

        # Update staging record
        await db.execute(
            update(StagingRecord)
            .where(StagingRecord.id == record.id)
            .values(consent_received=True)
        )

        # Record consent event (DPDP audit trail, OL-120/OL-123)
        consent_event = ConsentEvent(
            principal_id=parent.id,
            scope=f"child_data:{record.student_name}",
            action=ConsentAction.GRANT,
            method="otp_verified",
        )
        db.add(consent_event)

        await db.commit()

        logger.info(
            "guardian_consent_granted",
            staging_record_id=record.id,
            student=record.student_name,
            parent_id=str(parent.id),
        )

        return ConsentStatusResponse(
            staging_record_id=record.id,
            student_name=record.student_name,
            consent_received=True,
        )


@router.post("/withdraw", response_model=ConsentStatusResponse)
async def withdraw_consent(
    body: WithdrawConsentRequest,
    principal_id: UUID = Depends(get_principal_id),
) -> ConsentStatusResponse:
    """Withdraw guardian consent (OL-123). Honored within 72 hours."""
    biz_id = UUID(body.business_id)

    async with async_session() as db:
        result = await db.execute(
            select(StagingRecord).where(
                StagingRecord.id == body.staging_record_id,
                StagingRecord.business_id == biz_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Student record not found")

        # Update staging record
        await db.execute(
            update(StagingRecord)
            .where(StagingRecord.id == record.id)
            .values(consent_received=False)
        )

        # Record withdrawal event
        consent_event = ConsentEvent(
            principal_id=principal_id,
            scope=f"child_data:{record.student_name}",
            action=ConsentAction.WITHDRAW,
            method="user_request",
        )
        db.add(consent_event)

        await db.commit()

        logger.info(
            "guardian_consent_withdrawn",
            staging_record_id=record.id,
            student=record.student_name,
        )

        return ConsentStatusResponse(
            staging_record_id=record.id,
            student_name=record.student_name,
            consent_received=False,
        )


@router.get("/{business_id}/status", response_model=list[ConsentStatusResponse])
async def get_consent_status(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> list[ConsentStatusResponse]:
    """Get consent status for all students in a business."""
    result = await db.execute(
        select(StagingRecord)
        .where(StagingRecord.business_id == business_id)
        .order_by(StagingRecord.student_name)
    )
    records = result.scalars().all()
    return [
        ConsentStatusResponse(
            staging_record_id=r.id,
            student_name=r.student_name,
            consent_received=r.consent_received,
        )
        for r in records
    ]
