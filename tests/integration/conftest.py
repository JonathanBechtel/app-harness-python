"""Integration fixtures: a real Postgres, isolated per session by schema.

Explicit opt-in with an anti-silent-skip: skipping is right on a laptop with no
database, but on a box that is EXPECTED to run the suite (CI, anything
bootstrapped) ``PYTEST_REQUIRE_DB=1`` turns a missing URL into a failure --
otherwise the suite exits 0 with every test skipped, indistinguishable from
green.

Isolation: one randomly named schema per session; tables created from
SQLModel metadata; each test runs in a rolled-back transaction unless it is
marked ``committed_db`` (or uses ``app_client``), in which case it gets real
connections and the schema is truncated afterwards.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

# Pinned to THIS checkout's .env: a bare load_dotenv() walks up and can borrow a
# parent checkout's database from inside a worktree.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _load_database_url() -> str:
    test_url = os.getenv("TEST_DATABASE_URL")
    app_url = os.getenv("DATABASE_URL")
    if not test_url:
        msg = "No TEST_DATABASE_URL configured for integration tests."
        if os.getenv("PYTEST_REQUIRE_DB", "0") == "1":
            raise RuntimeError(
                f"{msg} PYTEST_REQUIRE_DB=1 says this environment must run them, not skip them."
            )
        pytest.skip(msg)
    if os.getenv("PYTEST_ALLOW_DB", "0") != "1":
        raise RuntimeError("Set PYTEST_ALLOW_DB=1 to confirm TEST_DATABASE_URL is safe to mutate.")
    if app_url and os.getenv("PYTEST_ALLOW_TEST_DB_EQUALS_DATABASE_URL", "0") != "1":
        t, a = make_url(test_url), make_url(app_url)
        if (t.host, t.port, t.database) == (a.host, a.port, a.database):
            pytest.skip(
                "TEST_DATABASE_URL equals DATABASE_URL; refusing (override with PYTEST_ALLOW_TEST_DB_EQUALS_DATABASE_URL=1)."
            )
    return test_url


@pytest.fixture(scope="session")
def database_url() -> str:
    """The Postgres URL the suite targets."""
    return _load_database_url()


@pytest.fixture(scope="session")
def test_schema() -> str:
    """A unique schema name for this session."""
    return f"pytest_{secrets.token_hex(6)}"


@pytest_asyncio.fixture(scope="session")
async def async_engine(database_url: str, test_schema: str) -> AsyncGenerator[AsyncEngine, None]:
    """Engine whose connections default to the isolated schema, with tables created from metadata."""
    import importlib
    import pkgutil

    from app import models as models_pkg

    for _, name, _ in pkgutil.walk_packages(models_pkg.__path__, models_pkg.__name__ + "."):
        importlib.import_module(name)

    setup = create_async_engine(database_url, pool_pre_ping=True)
    async with setup.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{test_schema}"'))
        await conn.execute(text(f'SET search_path TO "{test_schema}"'))
        await conn.run_sync(SQLModel.metadata.create_all)
    await setup.dispose()

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": f'"{test_schema}"'}},
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{test_schema}" CASCADE'))
        await engine.dispose()


def _needs_committed(request: pytest.FixtureRequest) -> bool:
    return (
        request.node.get_closest_marker("committed_db") is not None
        or "app_client" in request.fixturenames
    )


@pytest_asyncio.fixture()
async def test_connection(
    request: pytest.FixtureRequest, async_engine: AsyncEngine
) -> AsyncGenerator[AsyncConnection | None, None]:
    """Rollback boundary for ordinary tests; None for committed_db / HTTP-client tests."""
    if _needs_committed(request):
        yield None
        return
    async with async_engine.connect() as conn:
        tx = await conn.begin()
        try:
            yield conn
        finally:
            if tx.is_active:
                await tx.rollback()


@pytest.fixture()
def session_factory(
    async_engine: AsyncEngine, test_connection: AsyncConnection | None
) -> async_sessionmaker[AsyncSession]:
    """Sessions joined to the rollback connection, or independent committed sessions."""
    if test_connection is None:
        return async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
    return async_sessionmaker(
        bind=test_connection,
        expire_on_commit=False,
        class_=AsyncSession,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture(autouse=True)
async def database_isolation(
    request: pytest.FixtureRequest,
    async_engine: AsyncEngine,
    test_schema: str,
    test_connection: AsyncConnection | None,
) -> AsyncGenerator[None, None]:
    """Truncate every table after a committed test; rollback tests need nothing."""
    yield
    if not _needs_committed(request):
        return
    async with async_engine.begin() as conn:
        rows = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = :s"), {"s": test_schema}
        )
        tables = [r[0] for r in rows]
        if tables:
            refs = ", ".join(f'"{test_schema}"."{t}"' for t in tables)
            await conn.execute(text(f"TRUNCATE TABLE {refs} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture()
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """A session for setup and verification."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def app_client(
    session_factory: async_sessionmaker[AsyncSession],
    async_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client over the ASGI app with the DB dependency overridden and the probe engine swapped."""
    from app.main import app
    from app.utils import db

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[db.get_session] = _override
    monkeypatch.setattr(db, "engine", async_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(db.get_session, None)
