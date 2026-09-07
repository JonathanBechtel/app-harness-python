"""Readiness probe against a real database."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health_db_reports_ok(app_client: AsyncClient) -> None:
    """GET /health/db returns 200 with database_ok=true when Postgres answers."""
    resp = await app_client.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database_ok"] is True
    assert body["latency_ms"] is not None


@pytest.mark.asyncio
async def test_session_is_isolated_to_schema(db_session: AsyncSession) -> None:
    """The test session's search_path points at the per-session schema, never public."""
    row = (await db_session.execute(text("SHOW search_path"))).scalar_one()
    assert "pytest_" in row
