"""OpenLnk API — commitment-native communication."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, businesses, commitments, contexts, extraction, health, sync, threads

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup/shutdown lifecycle."""
    logger.info("openlnk_api_starting")
    yield
    logger.info("openlnk_api_stopping")


app = FastAPI(
    title="OpenLnk API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten before Gate 2
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# /v1 prefix from day one (CLAUDE.md)
app.include_router(health.router)
app.include_router(auth.router, prefix="/v1")
app.include_router(businesses.router, prefix="/v1")
app.include_router(commitments.router, prefix="/v1")
app.include_router(contexts.router, prefix="/v1")
app.include_router(extraction.router, prefix="/v1")
app.include_router(sync.router, prefix="/v1")
app.include_router(threads.router, prefix="/v1")
