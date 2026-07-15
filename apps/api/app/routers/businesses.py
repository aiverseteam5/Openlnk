"""Business console routes — dashboard, roster, fee cycles (OL-100..105).

Business owners manage their tuition center: view dashboard, import
student rosters, configure fee cycles, and see ROI metrics.
Routers hold zero business logic (CLAUDE.md).
"""

import csv
import io
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.models import (
    Business,
    BusinessMember,
    Commitment,
    CommitmentState,
    Context,
    StagingRecord,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/businesses", tags=["businesses"])


# ── Schemas ──


class BusinessResponse(BaseModel):
    id: str
    name: str
    vertical: str
    upi_vpa: str | None
    whatsapp_number: str | None
    subscription_state: str


class DashboardResponse(BaseModel):
    business: BusinessResponse
    counts: dict
    roi: dict


class StagingRecordResponse(BaseModel):
    id: int
    student_name: str
    parent_phone: str
    batch: str | None
    consent_received: bool


class RosterImportResponse(BaseModel):
    imported: int
    errors: list[str]
    records: list[StagingRecordResponse]


class FeeCycleRequest(BaseModel):
    cycle_label: str = Field(..., examples=["July 2026"])
    amount_paise: int = Field(..., ge=100, description="Fee amount in paise")
    batch: str | None = None


class FeeCycleResponse(BaseModel):
    generated: int
    cycle_label: str


# ── Routes ──


@router.get("", response_model=list[BusinessResponse])
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> list[BusinessResponse]:
    """List businesses the principal is a member of."""
    result = await db.execute(
        select(Business)
        .join(BusinessMember, Business.id == BusinessMember.business_id)
        .where(BusinessMember.principal_id == principal_id)
    )
    businesses = result.scalars().all()
    return [
        BusinessResponse(
            id=str(b.id),
            name=b.name,
            vertical=b.vertical,
            upi_vpa=b.upi_vpa,
            whatsapp_number=b.whatsapp_number,
            subscription_state=b.subscription_state,
        )
        for b in businesses
    ]


@router.get("/{business_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> DashboardResponse:
    """OL-101: Business console dashboard with counts and ROI."""
    # Verify membership
    member = await db.execute(
        select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.principal_id == principal_id,
        )
    )
    if member.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this business")

    business_result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = business_result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    # Get context for this business
    ctx_result = await db.execute(
        select(Context).where(Context.business_id == business_id)
    )
    context = ctx_result.scalar_one_or_none()

    # Commitment counts by state
    counts = {"pending": 0, "at_risk": 0, "done": 0, "total": 0, "students": 0}
    if context:
        for state_label, state_filter in [
            ("pending", [CommitmentState.PROPOSED, CommitmentState.ACCEPTED, CommitmentState.IN_PROGRESS]),
            ("done", [CommitmentState.DONE]),
        ]:
            count_result = await db.execute(
                select(func.count(Commitment.id)).where(
                    Commitment.context_id == context.id,
                    Commitment.state.in_([s.value for s in state_filter]),
                )
            )
            counts[state_label] = count_result.scalar() or 0

        total_result = await db.execute(
            select(func.count(Commitment.id)).where(
                Commitment.context_id == context.id
            )
        )
        counts["total"] = total_result.scalar() or 0

    # Student count from staging
    student_result = await db.execute(
        select(func.count(StagingRecord.id)).where(
            StagingRecord.business_id == business_id
        )
    )
    counts["students"] = student_result.scalar() or 0

    # ROI (OL-105) — real queries
    if context:
        # fees recovered = sum(amount_paise) for done fee commitments this month
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fees_result = await db.execute(
            select(func.coalesce(func.sum(Commitment.amount_paise), 0)).where(
                Commitment.context_id == context.id,
                Commitment.class_ == "fee",
                Commitment.state == CommitmentState.DONE.value,
                Commitment.updated_at >= month_start,
            )
        )
        fees_recovered = fees_result.scalar() or 0

        # at-risk count
        at_risk_result = await db.execute(
            select(func.count(Commitment.id)).where(
                Commitment.context_id == context.id,
                Commitment.due_at < datetime.now(UTC),
                Commitment.state.not_in([
                    CommitmentState.DONE.value,
                    CommitmentState.BROKEN.value,
                    CommitmentState.CANCELLED.value,
                ]),
            )
        )
        counts["at_risk"] = at_risk_result.scalar() or 0
    else:
        fees_recovered = 0

    # Subscription cost: fixed ₹1,500/month for now (OL-105 PRD §9)
    roi = {
        "fees_recovered_paise": fees_recovered,
        "subscription_cost_paise": 150000,
        "period": "current_month",
    }

    return DashboardResponse(
        business=BusinessResponse(
            id=str(business.id),
            name=business.name,
            vertical=business.vertical,
            upi_vpa=business.upi_vpa,
            whatsapp_number=business.whatsapp_number,
            subscription_state=business.subscription_state,
        ),
        counts=counts,
        roi=roi,
    )


@router.get("/{business_id}/roster", response_model=list[StagingRecordResponse])
async def list_roster(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
) -> list[StagingRecordResponse]:
    """List staging records (imported roster) for a business."""
    result = await db.execute(
        select(StagingRecord)
        .where(StagingRecord.business_id == business_id)
        .order_by(StagingRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        StagingRecordResponse(
            id=r.id,
            student_name=r.student_name,
            parent_phone=r.parent_phone,
            batch=r.batch,
            consent_received=r.consent_received,
        )
        for r in records
    ]


@router.post("/{business_id}/roster/import", response_model=RosterImportResponse)
async def import_roster(
    business_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> RosterImportResponse:
    """OL-100: Import student roster from CSV.

    Expected columns: student_name, parent_phone, batch (optional).
    Data goes to staging_records until guardian consent (OL-100a).
    """
    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM from Excel exports
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    errors: list[str] = []
    records: list[StagingRecordResponse] = []

    for i, row in enumerate(reader, start=1):
        student_name = row.get("student_name", "").strip()
        parent_phone = row.get("parent_phone", "").strip()
        batch = row.get("batch", "").strip() or None

        if not student_name:
            errors.append(f"Row {i}: missing student_name")
            continue
        if not parent_phone:
            errors.append(f"Row {i}: missing parent_phone")
            continue

        # Normalize Indian numbers
        if parent_phone.startswith("0"):
            parent_phone = "+91" + parent_phone[1:]
        elif not parent_phone.startswith("+"):
            parent_phone = "+91" + parent_phone

        record = StagingRecord(
            business_id=business_id,
            student_name=student_name,
            parent_phone=parent_phone,
            batch=batch,
        )
        db.add(record)
        await db.flush()

        records.append(
            StagingRecordResponse(
                id=record.id,
                student_name=record.student_name,
                parent_phone=record.parent_phone,
                batch=record.batch,
                consent_received=False,
            )
        )
        imported += 1

    await db.commit()

    logger.info(
        "roster_imported",
        business_id=str(business_id),
        imported=imported,
        errors=len(errors),
    )

    return RosterImportResponse(imported=imported, errors=errors, records=records)


@router.post("/{business_id}/fee-cycles", response_model=FeeCycleResponse)
async def generate_fee_cycle(
    business_id: UUID,
    body: FeeCycleRequest,
    db: AsyncSession = Depends(get_db),
    principal_id: UUID = Depends(get_principal_id),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> FeeCycleResponse:
    """OL-102: Generate fee commitments for enrolled students.

    Creates a fee commitment for each consented staging record in the
    business (optionally filtered by batch).
    """
    # Get context for this business
    ctx_result = await db.execute(
        select(Context).where(Context.business_id == business_id)
    )
    context = ctx_result.scalar_one_or_none()
    if context is None:
        raise HTTPException(status_code=404, detail="No context for this business")

    # Get business for UPI VPA
    biz_result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = biz_result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    # Get consented students
    query = select(StagingRecord).where(
        StagingRecord.business_id == business_id,
        StagingRecord.consent_received == True,  # noqa: E712
    )
    if body.batch:
        query = query.where(StagingRecord.batch == body.batch)

    result = await db.execute(query)
    students = result.scalars().all()

    generated = 0
    for student in students:
        commitment = Commitment(
            context_id=context.id,
            owner_id=principal_id,
            counterparty_id=None,
            title=f"{body.cycle_label} fee — {student.student_name}",
            class_="fee",
            amount_paise=body.amount_paise,
            state=CommitmentState.PROPOSED,
            version=1,
            provenance_kind="manual",
        )
        db.add(commitment)
        generated += 1

    await db.commit()

    logger.info(
        "fee_cycle_generated",
        business_id=str(business_id),
        cycle=body.cycle_label,
        generated=generated,
    )

    return FeeCycleResponse(generated=generated, cycle_label=body.cycle_label)
