"""Context endpoints.

Routers hold zero business logic (CLAUDE.md). Contexts are
household or business-batch scopes, RLS-filtered via Postgres GUC.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_principal_id
from app.models import Context

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get("")
async def list_contexts(
    session: Annotated[AsyncSession, Depends(get_db)],
    principal_id: Annotated[UUID, Depends(get_principal_id)],
) -> list[dict]:
    """List contexts for the authenticated principal. RLS-filtered."""
    result = await session.execute(
        select(Context).order_by(Context.created_at.desc())
    )
    contexts = result.scalars().all()
    return [
        {
            "id": str(ctx.id),
            "kind": ctx.kind,
            "household_id": str(ctx.household_id) if ctx.household_id else None,
            "business_id": str(ctx.business_id) if ctx.business_id else None,
            "label": ctx.label,
            "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
        }
        for ctx in contexts
    ]
