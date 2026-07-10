"""Shared test fixtures.

Two test tiers:
- Unit tests: no database, test schemas/models/logic directly
- Integration tests: testcontainers-Postgres with RLS (OL-041 tests)
"""

import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_container():
    """Start a testcontainers Postgres for integration tests.

    Scoped to session so we only spin up one container per test run.
    Skipped if Docker is not available.
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    with PostgresContainer(
        image="postgres:16-alpine",
        username="openlnk_app",
        password="test",
        dbname="openlnk_test",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
async def db_engine(pg_container):
    """Create an async engine connected to the test Postgres."""
    url = pg_container.get_connection_url()
    async_url = url.replace("psycopg2", "asyncpg").replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(async_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession]:
    """Yield a transactional DB session that rolls back after each test."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        test_principal = uuid4()
        await session.execute(
            text("SET LOCAL app.principal_id = :pid"),
            {"pid": str(test_principal)},
        )
        yield session
        await session.rollback()


def make_principal_id() -> str:
    """Generate a random UUID string for test principal IDs."""
    return str(uuid4())
