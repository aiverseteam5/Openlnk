"""Tests for API health endpoint and basic app structure."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.req("OL-141")
class TestHealthEndpoint:
    """All services containerized; just dev brings up the full stack."""

    async def test_health_returns_ok(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    async def test_v1_commitments_endpoint_exists(self):
        """API uses /v1 prefix from day one (CLAUDE.md)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # /v1/commitments exists (returns 422 without headers, not 404)
            resp = await client.get("/v1/commitments/00000000-0000-0000-0000-000000000000")
            assert resp.status_code != 404 or resp.status_code == 422
