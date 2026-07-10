"""Context endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get("")
async def list_contexts() -> list[dict]:
    """List contexts for the authenticated principal."""
    # TODO: implement with RLS-filtered query
    return []
