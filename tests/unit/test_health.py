"""Liveness probe behaviour, without a database."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.observability.middleware import REQUEST_ID_HEADER


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_reports_env_and_release(client: AsyncClient) -> None:
    """GET /health returns ok, the environment, and the release sha, with no DB access."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["env"] == "dev"
    assert body["release_sha"] == "testsha0000"


@pytest.mark.asyncio
async def test_request_id_is_echoed_or_minted(client: AsyncClient) -> None:
    """A safe inbound X-Request-ID is echoed; an unsafe one is replaced with a fresh id."""
    resp = await client.get("/health", headers={REQUEST_ID_HEADER: "abc-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "abc-123"
    resp = await client.get("/health", headers={REQUEST_ID_HEADER: "bad\nvalue"})
    assert resp.headers[REQUEST_ID_HEADER] != "bad\nvalue"
    assert len(resp.headers[REQUEST_ID_HEADER]) == 32


@pytest.mark.asyncio
async def test_landing_page_renders(client: AsyncClient) -> None:
    """The optional web layer serves the placeholder page through the shared base template."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert 'data-testid="landing"' in resp.text
