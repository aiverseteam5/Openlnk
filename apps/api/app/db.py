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

from fastapi import Depends, Header, HTTPException
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
    authorization: str | None = Header(None),
    x_principal_id: str | None = Header(None, alias="X-Principal-Id"),
) -> UUID:
    """Extract principal ID from JWT Bearer token or dev header.

    Production: Authorization: Bearer <jwt>
    Dev fallback: X-Principal-Id header (only when no JWT provided).
    """
    # Try JWT first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        from app.services.auth_service import auth_service

        principal_id = auth_service.decode_access_token(token)
        if principal_id is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return principal_id

    # Dev fallback — X-Principal-Id header
    if x_principal_id:
        try:
            return UUID(x_principal_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid X-Principal-Id format")

    raise HTTPException(status_code=401, detail="Authentication required")


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
        # Use set_config() instead of SET LOCAL — asyncpg doesn't support
        # parameterized SET statements ($1 syntax error).
        await session.execute(
            text("SELECT set_config('app.principal_id', :pid, true)"),
            {"pid": str(principal_id)},
        )
        yield session
