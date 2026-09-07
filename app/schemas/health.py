"""Health probe response shapes."""

from __future__ import annotations

from pydantic import BaseModel


class Health(BaseModel):
    """Liveness response."""

    status: str
    env: str
    release_sha: str | None = None


class DbHealth(BaseModel):
    """Readiness response."""

    status: str
    database_ok: bool
    latency_ms: float | None = None
    error: str | None = None
