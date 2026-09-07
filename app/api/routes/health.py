"""Liveness and readiness probes.

Two probes, deliberately separate. ``/health`` touches no database: an
orchestrator should restart a replica on it, and a database outage is not a
reason to cycle every replica. ``/health/db`` runs a bounded ``SELECT 1``
through the app's own pool and reports 503 when that fails, so a saturated pool
or an unreachable database is visible to monitoring instead of inferred from
user reports.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.health import DbHealth, Health
from app.utils.db import check_database_readiness

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
async def health() -> Health:
    """Liveness: the process is up and serving."""
    return Health(status="ok", env=settings.env, release_sha=settings.release_sha)


@router.get("/health/db", response_model=DbHealth, responses={503: {"model": DbHealth}})
async def health_db() -> JSONResponse:
    """Readiness: a request can get a working database connection right now."""
    report = await check_database_readiness()
    payload = DbHealth(
        status="ok" if report.database_ok else "unavailable",
        database_ok=report.database_ok,
        latency_ms=report.latency_ms,
        error=report.error,
    )
    return JSONResponse(
        status_code=200 if report.database_ok else 503,
        content=payload.model_dump(),
    )
