"""Database engine and session management.

Key invariants (CLAUDE.md + eng review):
- Every connection sets app.principal_id GUC before any query (RLS enforcement)
- Unset GUC → PostgreSQL error, not empty results (Sentry alert)
- Uses openlnk_app role (no superuser at runtime — eng review C1)
- Session-mode pooling required (transaction-mode breaks GUC — TODOS T-002)
"""

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_principal_id(
    x_principal_id: str = Header(..., alias="X-Principal-Id"),
) -> UUID:
    """Extract principal ID from request header.

    Gate 1: header-based identity. Will be replaced by JWT/OTP auth
    before Gate 2. The header value is used to set the Postgres GUC
    for RLS enforcement.
    """
    return UUID(x_principal_id)


async def get_db(
    principal_id: Annotated[UUID, Depends(get_principal_id)],
) -> AsyncGenerator[AsyncSession]:
    """Yield a DB session with app.principal_id GUC set for RLS.

    IMPORTANT: This GUC MUST be set before any query. RLS policies reference
    current_setting('app.principal_id'). If unset, Postgres raises an error
    (not empty results). This is the correct behavior — silent empty results
    would be a data-leak risk.
    """
    async with async_session() as session:
        # Set the principal GUC for RLS (CLAUDE.md sacred rule #4)
        await session.execute(
            text("SET LOCAL app.principal_id = :pid"),
            {"pid": str(principal_id)},
        )
        yield session
