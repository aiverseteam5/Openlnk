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
    allow_origins=[
        "http://localhost:5173",        # Vite dev
        "http://localhost:4173",        # Vite preview
        "http://195.35.20.139:5173",    # Hostinger dev
        "https://openlnk.in",          # Production (future)
        "https://www.openlnk.in",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Principal-Id"],
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
