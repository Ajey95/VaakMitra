"""
ASD-Edge-ST 2.0 — Backend FastAPI Application Entry Point

Exposes:
  /api/v1/  — Unity-facing session endpoints (M3.1)
  /therapist/ — Therapist-facing report and plan endpoints (M3.4)
  /docs      — OpenAPI interactive documentation

Startup sequence:
  1. Initialise structured logging
  2. Create DB tables (idempotent)
  3. Load therapist policy
  4. Initialise session orchestrator
  5. Start background sync loop

Run with:
  uvicorn asd_backend.main:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from asd_backend import __version__
from asd_backend.config import settings
from asd_backend.db.database import init_db
from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.session.api import router as session_router, init_orchestrator
from asd_backend.sync.therapist_api import router as therapist_router
from asd_backend.sync.service import SyncService


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if os.environ.get("ASD_TESTING") == "1":
        # In test mode: DB and orchestrator are initialised by test fixtures
        yield
        return

    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("backend.startup", version=__version__)

    # Initialise database
    await init_db()
    log.info("db.initialised")

    # Load therapist policy
    if settings.policy_path.exists():
        policy = TherapistPolicy.from_file(settings.policy_path)
        log.info("policy.loaded", version=policy.policy_version)
    else:
        policy = TherapistPolicy.default()
        log.warning("policy.default_used", path=str(settings.policy_path))

    # Initialise session orchestrator
    init_orchestrator(policy=policy)
    log.info("orchestrator.ready")

    # Start background sync loop
    sync_service = SyncService()
    sync_task = asyncio.create_task(sync_service.run_forever(interval_s=60.0))
    log.info("sync.loop_scheduled")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    sync_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await sync_task
    log.info("backend.shutdown")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ASD-Edge-ST 2.0 Backend",
    description=(
        "On-device backend for the ASD-Edge-ST speech therapy system. "
        "Provides session orchestration, adaptive dialogue, encrypted local storage, "
        "and privacy-safe therapist metric sync."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

import os as _os
if _os.environ.get("ASD_TESTING") != "1":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount routers
app.include_router(session_router)
app.include_router(therapist_router)


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "asd_backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
