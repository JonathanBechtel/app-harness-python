"""Every budgeted route stays within its statement count."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.perf._capture import count_statements
from tests.integration.perf.budgets import BUDGETS


@pytest.mark.asyncio
@pytest.mark.parametrize("route", sorted(BUDGETS))
async def test_route_query_budget(
    route: str, app_client: AsyncClient, async_engine: AsyncEngine
) -> None:
    """Rendering the route issues no more SQL statements than its budget allows."""
    with count_statements(async_engine) as statements:
        resp = await app_client.get(route)
    assert resp.status_code < 500
    assert len(statements) <= BUDGETS[route], (
        f"{route} issued {len(statements)} statements (budget {BUDGETS[route]}). See budgets.py for the protocol.\n"
        + "\n".join(statements)
    )
