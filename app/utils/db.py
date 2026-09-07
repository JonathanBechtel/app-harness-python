"""Async engine, session dependency, and the readiness probe.

The readiness probe goes through the application's own pool rather than a
private connection: the question it answers is "can a request get a working
database connection right now", and a privileged side-channel probe would stay
green through exactly the pool-exhaustion incident it exists to detect.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.utils import (
    network_guard as _network_guard,  # noqa: F401  (installs the SQLAlchemy listeners)
)

# Must stay below settings.db_pool_timeout so /health/db reports saturation
# rather than waiting on it.
READINESS_TIMEOUT_SECONDS = 5.0

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request; the route owns the transaction."""
    async with SessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    """Close every pooled connection (shutdown)."""
    await engine.dispose()


@dataclass(frozen=True)
class ReadinessReport:
    """Outcome of one readiness probe. Never raises; a failure is a result."""

    database_ok: bool
    latency_ms: float | None
    error: str | None = None


async def check_database_readiness(
    timeout_seconds: float = READINESS_TIMEOUT_SECONDS,
) -> ReadinessReport:
    """Run a bounded ``SELECT 1`` through the app's pool and report the result."""
    started = time.perf_counter()

    async def _ping() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping(), timeout=timeout_seconds)
    except TimeoutError:
        return ReadinessReport(False, None, f"timed out after {timeout_seconds}s")
    except Exception as exc:  # noqa: BLE001 - the probe reports, never raises
        return ReadinessReport(False, None, f"{type(exc).__name__}: {exc}")
    return ReadinessReport(True, round((time.perf_counter() - started) * 1000, 1))
