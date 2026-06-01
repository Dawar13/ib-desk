"""FastAPI application for the IB Desk API (Phase 0).

The lifespan opens the asyncpg pool from settings.database_url when it is set,
catching and logging any failure so the app still starts and the health
endpoint can report a disconnected database. CORS is restricted to the
configured web origin for GET requests. The three Phase 0 endpoints live in
app.routes.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.database_url:
        try:
            await db.open_pool(settings.database_url)
        except Exception as exc:
            logger.warning(
                "Could not open database pool, continuing with database disconnected: %s",
                exc,
            )
    try:
        yield
    finally:
        await db.close_pool()


settings = get_settings()

app = FastAPI(title=settings.service_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
